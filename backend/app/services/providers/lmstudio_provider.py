from typing import Any, Dict, List, Optional

import httpx

from app.services.providers.openai_provider import OpenAIProvider
from app.services.providers.provider_limits import (
    build_limits_payload,
    derive_output_tokens_from_context,
    extract_int_from_keys,
)

class LMStudioProvider(OpenAIProvider):
    """
    LM Studio Local Provider. Subclasses OpenAIProvider since LM Studio 
    exposes a fully OpenAI-compatible /v1/chat/completions endpoint.
    """
    def __init__(self, api_key: str = "", base_url: str = "", model: str = ""):
        # Default api_key to 'lm-studio' and base_url to 'http://localhost:1234/v1'
        key = api_key.strip() if api_key else "lm-studio"
        url = base_url.strip() if base_url else "http://localhost:1234/v1"
        super().__init__(api_key=key, base_url=url, model=model)

    def list_models(self) -> List[str]:
        try:
            url = f"{self.base_url}/models"
            headers = {"Authorization": f"Bearer {self.api_key}"}
            resp = httpx.get(url, headers=headers, timeout=10.0)
            if resp.status_code == 200:
                data = resp.json()
                self._models_cache = data.get("data", [])
                return [m["id"] for m in self._models_cache]
        except Exception:
            pass
        return ["local-model"]

    def _find_cached_model(self, model_name: str) -> Optional[Dict[str, Any]]:
        cache = getattr(self, "_models_cache", None) or []
        for model in cache:
            if model.get("id") == model_name:
                return model
        return None

    def _fetch_model_details(self, model_name: str) -> Optional[Dict[str, Any]]:
        try:
            url = f"{self.base_url}/models/{model_name}"
            headers = {"Authorization": f"Bearer {self.api_key}"}
            resp = httpx.get(url, headers=headers, timeout=5.0)
            if resp.status_code == 200:
                return resp.json()
        except Exception:
            pass
        return None

    def get_model_limits(self, model_name: str) -> dict:
        limits = super().get_model_limits(model_name)
        model_payload = self._find_cached_model(model_name)
        if not model_payload:
            model_payload = self._fetch_model_details(model_name)
        if not model_payload:
            return limits

        context_length = extract_int_from_keys(
            model_payload,
            [
                "context_length",
                "max_context_length",
                "input_token_limit",
                "inputTokenLimit",
                "max_sequence_length",
            ],
        )
        output_tokens = extract_int_from_keys(
            model_payload,
            [
                "max_output_tokens",
                "max_completion_tokens",
                "completion_token_limit",
                "output_token_limit",
                "outputTokenLimit",
            ],
        )
        if context_length:
            limits = build_limits_payload(
                output_tokens or derive_output_tokens_from_context(context_length) or limits["max_output_tokens"],
                min(context_length * 4, 1000000),
                source="detected",
                notes="Discovered from LM Studio model metadata.",
            )
        return limits
