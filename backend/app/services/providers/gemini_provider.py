from typing import List
import httpx
from app.services.providers.base import BaseLLMProvider

class GeminiProvider(BaseLLMProvider):
    def __init__(self, api_key: str, base_url: str = "", model: str = ""):
        self.api_key = api_key
        # Default Google Generative Language URL
        self.base_url = base_url.strip() if base_url else "https://generativelanguage.googleapis.com/v1beta"
        self.model = model.strip() if model else "gemini-1.5-flash"

    def validate_settings(self) -> bool:
        if not self.api_key:
            return False
        try:
            url = f"{self.base_url}/models?key={self.api_key}"
            resp = httpx.get(url, timeout=10.0)
            return resp.status_code == 200
        except Exception:
            return False

    def list_models(self) -> List[str]:
        try:
            url = f"{self.base_url}/models?key={self.api_key}"
            resp = httpx.get(url, timeout=10.0)
            if resp.status_code == 200:
                data = resp.json()
                self._models_cache = data.get("models", [])
                return [m["name"].split("/")[-1] for m in self._models_cache]
        except Exception:
            pass
        return ["gemini-1.5-flash", "gemini-1.5-pro"]

    def generate(self, prompt: str, system_prompt: str, temperature: float = 0.2, max_tokens: int = 4000) -> str:
        url = f"{self.base_url}/models/{self.model}:generateContent?key={self.api_key}"
        
        payload = {
            "contents": [
                {
                    "parts": [{"text": prompt}]
                }
            ],
            "generationConfig": {
                "temperature": temperature,
                "maxOutputTokens": max_tokens
            }
        }
        
        if system_prompt:
            payload["systemInstruction"] = {
                "parts": [{"text": system_prompt}]
            }
            
        import time
        max_attempts = 4
        backoff = 2.0
        
        for attempt in range(max_attempts):
            try:
                with httpx.Client() as client:
                    resp = client.post(url, json=payload, timeout=3600.0)
                    if resp.status_code == 200:
                        data = resp.json()
                        try:
                            return data["candidates"][0]["content"]["parts"][0]["text"]
                        except (KeyError, IndexError):
                            raise Exception(f"Failed to parse Gemini response: {data}")
                    
                    if resp.status_code in [429, 502, 503, 504] and attempt < max_attempts - 1:
                        time.sleep(backoff)
                        backoff *= 2.0
                        continue
                        
                    raise Exception(f"Gemini error ({resp.status_code}): {resp.text}")
            except httpx.RequestError as e:
                if attempt < max_attempts - 1:
                    time.sleep(backoff)
                    backoff *= 2.0
                    continue
                raise e
