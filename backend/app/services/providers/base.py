from abc import ABC, abstractmethod
from typing import List

from app.services.providers.provider_limits import (
    DEFAULT_CHUNK_SIZE,
    DEFAULT_MAX_OUTPUT_TOKENS,
    build_limits_payload,
    infer_local_model_profile,
)

class BaseLLMProvider(ABC):
    """
    Abstract Base Class for all LLM Providers.
    """
    
    @abstractmethod
    def validate_settings(self) -> bool:
        """
        Validates API keys and URLs required for the provider.
        """
        pass
        
    @abstractmethod
    def list_models(self) -> List[str]:
        """
        Lists available models for this provider (if supported).
        """
        pass
        
    @abstractmethod
    def generate(self, prompt: str, system_prompt: str, temperature: float = 0.2, max_tokens: int = 4000) -> str:
        """
        Sends a generation request to the LLM.
        """
        pass

    def get_model_limits(self, model_name: str) -> dict:
        """
        Returns a dictionary with 'max_output_tokens' and 'chunk_size' (context size in characters) 
        for the given model name.
        """
        model = model_name.lower()
        max_output_tokens = DEFAULT_MAX_OUTPUT_TOKENS
        chunk_size = DEFAULT_CHUNK_SIZE
        source = "fallback"
        notes = ""
        
        # Check cache if available (populated by list_models)
        cache = getattr(self, "_models_cache", None)
        class_name = self.__class__.__name__
        
        if cache:
            if class_name == "OpenRouterProvider":
                for m in cache:
                    if m.get("id") == model_name:
                        context_len = m.get("context_length")
                        if context_len:
                            # 1 token ≈ 4 characters, cap at 1,000,000 chars (approx 250k tokens)
                            chunk_size = min(context_len * 4, 1000000)
                        
                        top_prov = m.get("top_provider")
                        if top_prov and isinstance(top_prov, dict):
                            max_tokens = top_prov.get("max_completion_tokens")
                            if max_tokens:
                                max_output_tokens = max_tokens
                        source = "detected"
                        notes = "Discovered from provider model metadata."
                        break
            elif class_name == "GeminiProvider":
                for m in cache:
                    cached_name = m.get("name", "").split("/")[-1]
                    if cached_name == model_name or m.get("name") == model_name:
                        input_limit = m.get("inputTokenLimit")
                        output_limit = m.get("outputTokenLimit")
                        if input_limit:
                            chunk_size = min(int(input_limit) * 4, 1000000)
                        if output_limit:
                            max_output_tokens = int(output_limit)
                        source = "detected"
                        notes = "Discovered from provider model metadata."
                        break

        # Fallback mappings based on model name substrings (for Ollama, OpenAI, or if cache lookup failed)
        if chunk_size == DEFAULT_CHUNK_SIZE and max_output_tokens == DEFAULT_MAX_OUTPUT_TOKENS:
            # Gemini Pro (huge context)
            if any(x in model for x in ["gemini-1.5-pro", "gemini-2.0-pro", "gemini-2.5-pro", "gemini-3.5-pro", "gemini-pro"]):
                max_output_tokens = 8192
                chunk_size = 500000
                source = "fallback"
                notes = "Fallback profile inferred from Gemini Pro model family."
            # Gemini Flash / Standard (large context)
            elif any(x in model for x in ["gemini-1.5", "gemini-2.5", "gemini-2.0", "gemini-3.5", "gemini-3.1", "gemini-"]):
                max_output_tokens = 8192
                chunk_size = 200000
                source = "fallback"
                notes = "Fallback profile inferred from Gemini model family."
            # GPT-4o Mini / o1 / o3 Mini (large output, medium context)
            elif any(x in model for x in ["gpt-4o-mini", "o1-mini", "o3-mini"]):
                max_output_tokens = 16384
                chunk_size = 60000
                source = "fallback"
                notes = "Fallback profile inferred from compact reasoning model family."
            # GPT-4 / GPT-4o / Claude / o1 / o3
            elif any(x in model for x in ["gpt-4", "gpt-4o", "claude-3", "claude-3.5", "o1", "o3"]):
                max_output_tokens = 8192 if "claude" in model else 4096
                chunk_size = 80000 if "claude" in model or "gpt-4o" in model else 60000
                source = "fallback"
                notes = "Fallback profile inferred from cloud model family."
            # Local models / Ollama / LM Studio
            elif any(x in model for x in ["llama-3", "mistral", "gemma", "phi"]):
                return infer_local_model_profile(model_name)

        return build_limits_payload(
            max_output_tokens,
            chunk_size,
            source=source,
            notes=notes,
        )
