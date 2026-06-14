from app.services.providers.openai_provider import OpenAIProvider

class OpenAICompatibleProvider(OpenAIProvider):
    """
    Generic OpenAI Compatible Provider for services like OpenRouter, local gateways, etc.
    """
    def __init__(self, api_key: str, base_url: str, model: str = ""):
        super().__init__(api_key=api_key, base_url=base_url, model=model)
