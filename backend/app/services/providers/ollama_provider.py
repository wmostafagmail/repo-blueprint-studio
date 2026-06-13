from typing import List
import httpx
from backend.app.services.providers.base import BaseLLMProvider

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
                return [m["name"] for m in data.get("models", [])]
        except Exception:
            pass
        return ["llama3", "mistral", "gemma"]

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
                if context_length:
                    # 1 token ≈ 4 characters, cap at 1,000,000 characters
                    chunk_size = min(context_length * 4, 1000000)
                    limits["chunk_size"] = chunk_size
                    limits["chunkSize"] = chunk_size
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
            return data["message"]["content"]
