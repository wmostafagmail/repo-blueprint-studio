from typing import List
import httpx
from app.services.providers.openai_provider import OpenAIProvider

class OpenRouterProvider(OpenAIProvider):
    """
    OpenRouter LLM Provider. Inherits from OpenAIProvider but overrides 
    default base URL and requests headers to fit OpenRouter standards.
    """
    def __init__(self, api_key: str, base_url: str = "", model: str = ""):
        url = base_url.strip() if base_url else "https://openrouter.ai/api/v1"
        model_name = model.strip() if model else "google/gemini-2.5-flash"
        super().__init__(api_key=api_key, base_url=url, model=model_name)

    def _get_headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "HTTP-Referer": "https://github.com/google-gemini/antigravity",
            "X-Title": "Repo Blueprint Studio",
            "Content-Type": "application/json"
        }

    def validate_settings(self) -> bool:
        if not self.api_key:
            return False
        try:
            url = f"{self.base_url}/models"
            headers = self._get_headers()
            resp = httpx.get(url, headers=headers, timeout=10.0)
            return resp.status_code == 200
        except Exception:
            return False

    def list_models(self) -> List[str]:
        try:
            url = f"{self.base_url}/models"
            headers = self._get_headers()
            resp = httpx.get(url, headers=headers, timeout=10.0)
            if resp.status_code == 200:
                data = resp.json()
                self._models_cache = data.get("data", [])
                return [m["id"] for m in self._models_cache]
        except Exception:
            pass
        return ["google/gemini-2.5-flash", "openai/gpt-4o", "meta-llama/llama-3-8b-instruct:free"]

    def generate(
        self,
        prompt: str,
        system_prompt: str,
        temperature: float = 0.2,
        max_tokens: int = 4000,
        timeout_seconds: float = 3600.0,
    ) -> str:
        url = f"{self.base_url}/chat/completions"
        headers = self._get_headers()
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
                    resp = client.post(url, headers=headers, json=payload, timeout=timeout_seconds)
                    if resp.status_code == 200:
                        data = resp.json()
                        self.assert_response_model(data.get("model"))
                        return data["choices"][0]["message"]["content"]
                    
                    if resp.status_code in [429, 502, 503, 504] and attempt < max_attempts - 1:
                        time.sleep(backoff)
                        backoff *= 2.0
                        continue
                        
                    raise Exception(f"OpenRouter error ({resp.status_code}): {resp.text}")
            except httpx.RequestError as e:
                if attempt < max_attempts - 1:
                    time.sleep(backoff)
                    backoff *= 2.0
                    continue
                raise e
