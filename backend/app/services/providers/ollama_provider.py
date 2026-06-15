from typing import List
import httpx
from app.services.providers.base import BaseLLMProvider
from app.services.providers.provider_limits import (
    build_limits_payload,
    derive_output_tokens_from_context,
    extract_int_from_keys,
    extract_int_from_text,
)

class OllamaProvider(BaseLLMProvider):
    def __init__(self, api_key: str = "", base_url: str = "", model: str = ""):
        self.base_url = base_url.strip() if base_url else "http://localhost:11434"
        self.model = model.strip() if model else "llama3"

    def validate_settings(self) -> bool:
        try:
            # Check if ollama service is running
            url = f"{self.base_url}/api/tags"
            resp = httpx.get(url, timeout=5.0)
            return resp.status_code == 200
        except Exception:
            return False

    def list_models(self) -> List[str]:
        try:
            url = f"{self.base_url}/api/tags"
            resp = httpx.get(url, timeout=5.0)
            if resp.status_code == 200:
                data = resp.json()
                self._models_cache = data.get("models", [])
                return [m["name"] for m in self._models_cache]
        except Exception:
            pass
        return ["llama3", "mistral", "gemma"]

    def verify_selected_model(self) -> None:
        if not self.model:
            raise Exception("No model configured for Ollama provider")

        try:
            url = f"{self.base_url}/api/show"
            resp = httpx.post(url, json={"name": self.model}, timeout=10.0)
            if resp.status_code != 200:
                raise Exception(f"Ollama model verification failed ({resp.status_code}): {resp.text}")
        except Exception as e:
            raise Exception(f"Selected Ollama model '{self.model}' could not be verified: {str(e)}") from e

    def get_model_limits(self, model_name: str) -> dict:
        limits = super().get_model_limits(model_name)
        try:
            url = f"{self.base_url}/api/show"
            resp = httpx.post(url, json={"name": model_name}, timeout=5.0)
            if resp.status_code == 200:
                data = resp.json()
                model_info = data.get("model_info", {})
                context_length = None
                for k, v in model_info.items():
                    if k.endswith(".context_length") or k == "context_length":
                        context_length = v
                        break
                if not context_length:
                    context_length = extract_int_from_keys(
                        data,
                        ["context_length", "num_ctx", "max_context_length", "n_ctx"],
                    )

                output_tokens = extract_int_from_keys(
                    data,
                    [
                        "max_output_tokens",
                        "max_completion_tokens",
                        "num_predict",
                        "n_predict",
                    ],
                )

                parameters_text = data.get("parameters", "")
                if isinstance(parameters_text, str):
                    if not context_length:
                        context_length = extract_int_from_text(
                            parameters_text,
                            [r"num_ctx\s+(\d+)", r"context_length\s+(\d+)"],
                        )
                    if not output_tokens:
                        output_tokens = extract_int_from_text(
                            parameters_text,
                            [r"num_predict\s+(\d+)", r"n_predict\s+(\d+)"],
                        )

                if context_length:
                    chunk_size = min(int(context_length) * 4, 1000000)
                    output_tokens = output_tokens or derive_output_tokens_from_context(context_length)
                    limits = build_limits_payload(
                        output_tokens or limits["max_output_tokens"],
                        chunk_size,
                        source="detected",
                        notes="Discovered from Ollama model metadata.",
                    )
        except Exception:
            pass
        return limits


    def generate(self, prompt: str, system_prompt: str, temperature: float = 0.2, max_tokens: int = 4000) -> str:
        url = f"{self.base_url}/api/chat"
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt}
            ],
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens
            },
            "stream": False
        }
        
        with httpx.Client() as client:
            resp = client.post(url, json=payload, timeout=3600.0)
            if resp.status_code != 200:
                raise Exception(f"Ollama error ({resp.status_code}): {resp.text}")
            data = resp.json()
            self.assert_response_model(data.get("model"))
            return data["message"]["content"]
