from app.services.providers.base import BaseLLMProvider
from app.services.providers.openai_provider import OpenAIProvider
from app.services.providers.gemini_provider import GeminiProvider
from app.services.providers.ollama_provider import OllamaProvider
from app.services.providers.lmstudio_provider import LMStudioProvider
from app.services.providers.mtplx_provider import MTPLXProvider
from app.services.providers.openai_compatible_provider import OpenAICompatibleProvider
from app.services.providers.openrouter_provider import OpenRouterProvider
from app.services.providers.mock_provider import MockProvider

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
    elif name == "mtplx":
        return MTPLXProvider(api_key=api_key, base_url=base_url, model=model)
    elif name == "openai_compatible":
        return OpenAICompatibleProvider(api_key=api_key, base_url=base_url, model=model)
    else:
        return MockProvider(api_key=api_key, base_url=base_url, model=model)
