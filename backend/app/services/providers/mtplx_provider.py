import json
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

import httpx

from app.services.providers.openai_provider import OpenAIProvider
from app.services.providers.provider_limits import (
    build_limits_payload,
    derive_output_tokens_from_context,
    infer_local_model_profile,
)


def normalize_mtplx_base_url(base_url: str) -> str:
    raw_url = (base_url or "").strip().rstrip("/")
    if not raw_url:
        return "http://127.0.0.1:8000/v1"
    if raw_url.endswith("/v1"):
        return raw_url
    return f"{raw_url}/v1"


class MTPLXProvider(OpenAIProvider):
    """
    MTPLX local provider.

    MTPLX exposes an OpenAI-compatible bridge, but the live daemon model is
    best discovered from `/health` and may not match the model alias a user
    types into the UI exactly.
    """

    def __init__(self, api_key: str = "", base_url: str = "", model: str = ""):
        key = api_key.strip() if api_key else "mtplx-local"
        url = normalize_mtplx_base_url(base_url)
        super().__init__(api_key=key, base_url=url, model=model.strip() if model else "")

    def _root_base_url(self) -> str:
        return self.base_url[:-3] if self.base_url.endswith("/v1") else self.base_url

    def _settings_path(self) -> Path:
        return Path.home() / "Library" / "Application Support" / "MTPLX" / "settings.json"

    def _request_headers(self) -> Dict[str, str]:
        headers: Dict[str, str] = {
            "Connection": "close",
        }
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
            headers["X-API-Key"] = self.api_key
        return headers

    def _load_settings_payload(self) -> Dict[str, Any]:
        settings_path = self._settings_path()
        if not settings_path.exists():
            return {}
        try:
            return json.loads(settings_path.read_text(encoding="utf-8"))
        except Exception:
            return {}

    def _expand_model_aliases(self, model_name: str) -> List[str]:
        raw = (model_name or "").strip()
        if not raw:
            return []

        candidates = [raw]
        model_path = Path(raw)
        if model_path.name:
            candidates.append(model_path.name)

        slash_variant = raw.replace("--", "/")
        dash_variant = raw.replace("/", "--")
        candidates.extend([slash_variant, dash_variant])

        if model_path.name:
            candidates.append(model_path.name.replace("--", "/"))
            candidates.append(model_path.name.replace("/", "--"))

        normalized: List[str] = []
        seen = set()
        for candidate in candidates:
            cleaned = candidate.strip()
            lowered = cleaned.lower()
            if not cleaned or lowered in seen:
                continue
            seen.add(lowered)
            normalized.append(cleaned)
        return normalized

    def _canonical_model_candidates(self) -> List[str]:
        payload = self._load_settings_payload()
        configured_model = str(payload.get("model") or "").strip()
        tuned_records = payload.get("tuned_control_records_by_model") or {}

        candidates: List[str] = []
        if configured_model:
            candidates.extend(self._expand_model_aliases(configured_model))

        if isinstance(tuned_records, dict):
            for key, value in tuned_records.items():
                candidates.extend(self._expand_model_aliases(str(key)))
                if isinstance(value, dict):
                    candidates.extend(self._expand_model_aliases(str(value.get("model_id") or "")))

        deduped: List[str] = []
        seen = set()
        for candidate in candidates:
            lowered = candidate.lower()
            if lowered in seen:
                continue
            seen.add(lowered)
            deduped.append(candidate)
        return deduped

    def _fetch_health(self) -> Optional[Dict[str, Any]]:
        try:
            response = httpx.get(
                f"{self._root_base_url()}/health",
                headers=self._request_headers(),
                timeout=5.0,
            )
            if response.status_code == 200:
                return response.json()
        except Exception:
            pass
        return None

    def _health_model_candidates(self) -> List[str]:
        payload = self._fetch_health() or {}
        live_model = (
            str(payload.get("model") or "")
            or str(payload.get("model_id") or "")
            or str(payload.get("served_model_id") or "")
        ).strip()
        candidates = self._expand_model_aliases(live_model)
        context_length = payload.get("context_window")
        if candidates:
            self._models_cache = [
                {
                    "id": candidate,
                    "context_length": context_length,
                    "max_context_length": context_length,
                }
                for candidate in candidates
            ]
        return candidates

    def normalize_model_name(self, model_name: str) -> str:
        return (model_name or "").strip().lower()

    def models_match(self, requested_model: str, response_model: str) -> bool:
        requested = {candidate.lower() for candidate in self._expand_model_aliases(requested_model)}
        response = {candidate.lower() for candidate in self._expand_model_aliases(response_model)}
        return bool(requested and response and requested.intersection(response))

    def validate_settings(self) -> bool:
        if self._fetch_health():
            return True

        try:
            response = httpx.get(
                f"{self.base_url}/models",
                headers=self._request_headers(),
                timeout=5.0,
            )
            if response.status_code == 200:
                return True
        except Exception:
            pass

        return bool(self._canonical_model_candidates())

    def list_models(self) -> List[str]:
        try:
            response = httpx.get(
                f"{self.base_url}/models",
                headers=self._request_headers(),
                timeout=10.0,
            )
            if response.status_code == 200:
                data = response.json()
                self._models_cache = data.get("data", [])
                models = [str(model.get("id") or "").strip() for model in self._models_cache]
                models = [model for model in models if model]
                if models:
                    return models
        except Exception:
            pass

        health_models = self._health_model_candidates()
        if health_models:
            return health_models

        fallback_models = self._canonical_model_candidates()
        if fallback_models:
            self._models_cache = [{"id": model_id} for model_id in fallback_models]
            return fallback_models

        return ["local-model"]

    def verify_selected_model(self) -> None:
        live_health = self._fetch_health() or {}
        live_model = (
            str(live_health.get("model") or "")
            or str(live_health.get("model_id") or "")
            or str(live_health.get("served_model_id") or "")
        ).strip()

        if not self.model:
            if live_model:
                self.model = live_model
                return
            available = self.list_models()
            if available:
                self.model = available[0]
                return
            raise Exception("No model configured for MTPLX provider")

        if live_model and self.models_match(self.model, live_model):
            self.model = live_model
            return

        available = self.list_models()
        if any(self.models_match(self.model, candidate) for candidate in available):
            if live_model:
                self.model = live_model
            return

        raise Exception(
            f"Selected MTPLX model '{self.model}' is not currently available from the local runtime"
        )

    def generate(
        self,
        prompt: str,
        system_prompt: str,
        temperature: float = 0.2,
        max_tokens: int = 4000,
        timeout_seconds: float = 3600.0,
    ) -> str:
        self.raise_if_cancelled()
        url = f"{self.base_url}/chat/completions"
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt},
            ],
            "temperature": temperature,
            "max_tokens": max_tokens,
            "max_completion_tokens": max_tokens,
        }

        max_attempts = 4
        backoff = 2.0

        for attempt in range(max_attempts):
            client = httpx.Client(
                headers=self._request_headers(),
                timeout=httpx.Timeout(
                    timeout_seconds,
                    connect=min(10.0, timeout_seconds),
                    read=timeout_seconds,
                    write=min(30.0, timeout_seconds),
                ),
                limits=httpx.Limits(max_connections=1, max_keepalive_connections=0),
            )
            try:
                def execute_request():
                    response = client.post(
                        url,
                        json=payload,
                    )
                    return response

                response = self.run_cancellable_call(
                    execute_request,
                    timeout_seconds=timeout_seconds,
                    on_abort=client.close,
                    poll_interval=0.5,
                )
                if response.status_code == 200:
                    data = response.json()
                    self.assert_response_model(str(data.get("model") or ""))
                    return data["choices"][0]["message"]["content"]

                if response.status_code in [429, 502, 503, 504] and attempt < max_attempts - 1:
                    self.sleep_with_cancellation(backoff)
                    backoff *= 2.0
                    continue

                raise Exception(f"MTPLX error ({response.status_code}): {response.text}")
            except TimeoutError as exc:
                raise httpx.TimeoutException(str(exc)) from exc
            except httpx.RequestError as exc:
                if attempt < max_attempts - 1:
                    self.sleep_with_cancellation(backoff)
                    backoff *= 2.0
                    continue
                raise exc
            finally:
                client.close()

    def get_model_limits(self, model_name: str) -> dict:
        if not getattr(self, "_models_cache", None):
            self._health_model_candidates()

        cache = getattr(self, "_models_cache", None) or []
        for cached_model in cache:
            cached_name = str(cached_model.get("id") or "")
            if not self.models_match(model_name, cached_name):
                continue

            context_length = (
                cached_model.get("context_length")
                or cached_model.get("max_context_length")
                or cached_model.get("max_model_len")
            )
            if context_length:
                return build_limits_payload(
                    derive_output_tokens_from_context(context_length) or 16384,
                    min(int(context_length) * 4, 1000000),
                    source="detected",
                    notes="Discovered from MTPLX daemon health/model metadata.",
                )

        return infer_local_model_profile(model_name)
