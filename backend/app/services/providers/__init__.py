from backend.app.services.providers.base import BaseLLMProvider
from backend.app.services.providers.openai_provider import OpenAIProvider
from backend.app.services.providers.gemini_provider import GeminiProvider
from backend.app.services.providers.ollama_provider import OllamaProvider
from backend.app.services.providers.lmstudio_provider import LMStudioProvider
from backend.app.services.providers.openai_compatible_provider import OpenAICompatibleProvider
from backend.app.services.providers.openrouter_provider import OpenRouterProvider
from backend.app.services.providers.mock_provider import MockProvider

def get_provider(provider_name: str, api_key: str = "", base_url: str = "", model: str = "") -> BaseLLMProvider:
    """
    Factory function to instantiate the requested LLM provider.
    """
    name = provider_name.lower().strip()
    if name == "openai":
        return OpenAIProvider(api_key=api_key, base_url=base_url, model=model)
    elif name == "gemini":
        return GeminiProvider(api_key=api_key, base_url=base_url, model=model)
    elif name == "ollama":
        return OllamaProvider(api_key=api_key, base_url=base_url, model=model)
    elif name == "lmstudio":
        return LMStudioProvider(api_key=api_key, base_url=base_url, model=model)
    elif name == "openrouter":
        return OpenRouterProvider(api_key=api_key, base_url=base_url, model=model)
    elif name == "openai_compatible":
        return OpenAICompatibleProvider(api_key=api_key, base_url=base_url, model=model)
    else:
        return MockProvider(api_key=api_key, base_url=base_url, model=model)
