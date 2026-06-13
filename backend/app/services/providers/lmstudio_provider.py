from backend.app.services.providers.openai_provider import OpenAIProvider

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
