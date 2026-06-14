from typing import List
import httpx
from app.services.providers.base import BaseLLMProvider

class OpenAIProvider(BaseLLMProvider):
    def __init__(self, api_key: str, base_url: str = "", model: str = ""):
        self.api_key = api_key
        self.base_url = base_url.strip() if base_url else "https://api.openai.com/v1"
        self.model = model.strip() if model else "gpt-4o"

    def validate_settings(self) -> bool:
        if not self.api_key:
            return False
        try:
            url = f"{self.base_url}/models"
            headers = {"Authorization": f"Bearer {self.api_key}"}
            resp = httpx.get(url, headers=headers, timeout=10.0)
            return resp.status_code == 200
        except Exception:
            return False

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
        return ["gpt-4o", "gpt-4-turbo", "gpt-3.5-turbo"]

    def generate(self, prompt: str, system_prompt: str, temperature: float = 0.2, max_tokens: int = 4000) -> str:
        url = f"{self.base_url}/chat/completions"
        headers = {"Authorization": f"Bearer {self.api_key}"}
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt}
            ],
            "temperature": temperature,
            "max_tokens": max_tokens
        }
        
        import time
        max_attempts = 4
        backoff = 2.0
        
        for attempt in range(max_attempts):
            try:
                with httpx.Client() as client:
                    resp = client.post(url, headers=headers, json=payload, timeout=3600.0)
                    if resp.status_code == 200:
                        data = resp.json()
                        return data["choices"][0]["message"]["content"]
                    
                    if resp.status_code in [429, 502, 503, 504] and attempt < max_attempts - 1:
                        time.sleep(backoff)
                        backoff *= 2.0
                        continue
                        
                    raise Exception(f"OpenAI error ({resp.status_code}): {resp.text}")
            except httpx.RequestError as e:
                if attempt < max_attempts - 1:
                    time.sleep(backoff)
                    backoff *= 2.0
                    continue
                raise e
