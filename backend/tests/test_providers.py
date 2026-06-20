from backend.app.services.providers import get_provider
from backend.app.services.providers.openai_provider import OpenAIProvider
from backend.app.services.providers.openrouter_provider import OpenRouterProvider
from backend.app.services.providers.gemini_provider import GeminiProvider
from backend.app.services.providers.lmstudio_provider import LMStudioProvider
from backend.app.services.providers.mtplx_provider import MTPLXProvider
from backend.app.services.providers.base import GenerationCancelledError
from backend.app.services.providers.mock_provider import MockProvider

def test_provider_factory_mapping():
    # Verify mock provider mapping
    provider = get_provider("mock")
    assert isinstance(provider, MockProvider)
    
    # Verify openai mapping
    provider = get_provider("openai", api_key="test-key")
    assert isinstance(provider, OpenAIProvider)
    
    # Verify openrouter mapping
    provider = get_provider("openrouter", api_key="test-key")
    assert isinstance(provider, OpenRouterProvider)
    assert provider.base_url == "https://openrouter.ai/api/v1"
    
    # Verify gemini mapping
    provider = get_provider("gemini", api_key="test-key")
    assert isinstance(provider, GeminiProvider)

    provider = get_provider("lmstudio", base_url="http://localhost:1234/v1")
    assert isinstance(provider, LMStudioProvider)

    provider = get_provider("mtplx", base_url="http://127.0.0.1:8000/v1")
    assert isinstance(provider, MTPLXProvider)

def test_openrouter_headers():
    provider = get_provider("openrouter", api_key="test-key-or")
    headers = provider._get_headers()
    assert headers["Authorization"] == "Bearer test-key-or"
    assert "openrouter" in headers["HTTP-Referer"] or "antigravity" in headers["HTTP-Referer"]
    assert headers["X-Title"] == "Repo Blueprint Studio"

def test_mock_provider_generation():
    provider = get_provider("mock")
    output = provider.generate(prompt="Repository: my-test-project\nURL: https://github.com/my-org/my-test-project", system_prompt="")
    assert "# my-test-project Rebuild Blueprint" in output
    assert "## 12. Data Model and Database Design" in output
    assert "## 25. Clean-Room Notes" in output

def test_provider_limits_resolution():
    provider = get_provider("openai", api_key="test-key")
    # Verify GPT-4o-mini limits
    limits_mini = provider.get_model_limits("gpt-4o-mini")
    assert limits_mini["max_output_tokens"] == 16384
    assert limits_mini["chunk_size"] == 60000
    
    # Verify Llama 3 limits
    limits_llama = provider.get_model_limits("meta-llama/llama-3-8b-instruct")
    assert limits_llama["max_output_tokens"] == 4096
    assert limits_llama["chunk_size"] == 20000
    assert limits_llama["source"] == "fallback"

    # Verify fallback for unknown model
    limits_fallback = provider.get_model_limits("some-random-unknown-model")
    assert limits_fallback["max_output_tokens"] == 4000
    assert limits_fallback["chunk_size"] == 10000

def test_openrouter_generation_retries_on_429():
    from unittest.mock import patch
    import httpx
    
    provider = get_provider("openrouter", api_key="test-key-retry", model="google/gemini-2.5-flash")
    
    with patch("httpx.Client.post") as mock_post:
        mock_resp_429 = httpx.Response(429, text="Rate limited")
        mock_resp_200 = httpx.Response(200, json={"choices": [{"message": {"content": "Success content"}}]})
        mock_post.side_effect = [mock_resp_429, mock_resp_200]
        
        with patch("time.sleep") as mock_sleep:
            output = provider.generate(prompt="Test prompt", system_prompt="")
            assert output == "Success content"
            assert mock_post.call_count == 2
            mock_sleep.assert_called_once_with(2.0)

def test_ollama_provider_limits():
    from unittest.mock import patch
    import httpx
    
    # 1. Test when show API succeeds
    provider = get_provider("ollama", base_url="http://localhost:11434")
    with patch("httpx.post") as mock_post:
        mock_resp = httpx.Response(200, json={
            "model_info": {
                "gemma4.context_length": 131072,
                "general.architecture": "gemma4"
            }
        })
        mock_post.return_value = mock_resp
        
        limits = provider.get_model_limits("gemma4:latest")
        assert limits["chunk_size"] == 524288
        assert limits["max_output_tokens"] == 16384
        assert limits["source"] == "detected"
        mock_post.assert_called_once_with(
            "http://localhost:11434/api/show",
            json={"name": "gemma4:latest"},
            timeout=5.0
        )

    # 2. Test fallback when show API fails/throws error
    with patch("httpx.post") as mock_post:
        mock_post.side_effect = Exception("Connection refused")
        limits = provider.get_model_limits("gemma4:latest")
        assert limits["chunk_size"] == 40000
        assert limits["source"] == "fallback"

def test_lmstudio_provider_limits_from_model_metadata():
    from unittest.mock import patch
    import httpx

    provider = get_provider("lmstudio", base_url="http://localhost:1234/v1")
    provider._models_cache = [
        {
            "id": "qwen2.5-coder-32b-instruct",
            "max_context_length": 65536,
            "max_output_tokens": 8192,
        }
    ]

    with patch("httpx.get") as mock_get:
        limits = provider.get_model_limits("qwen2.5-coder-32b-instruct")
        assert limits["chunk_size"] == 262144
        assert limits["max_output_tokens"] == 8192
        assert limits["source"] == "detected"
        mock_get.assert_not_called()

def test_lmstudio_provider_limits_fallback():
    provider = get_provider("lmstudio", base_url="http://localhost:1234/v1")
    limits = provider.get_model_limits("local-unknown-model")
    assert limits["chunk_size"] == 40000
    assert limits["max_output_tokens"] == 6144
    assert limits["source"] == "fallback"


def test_mtplx_provider_uses_health_for_validation_and_models():
    from unittest.mock import patch
    import httpx

    provider = get_provider("mtplx", base_url="http://127.0.0.1:8000/v1", model="Youssofal/Qwen3.6-27B-MTPLX-Optimized-Quality")

    with patch("httpx.get") as mock_get:
        mock_get.return_value = httpx.Response(200, json={
            "ok": True,
            "model": "Youssofal--Qwen3.6-27B-MTPLX-Optimized-Quality",
            "context_window": 262144,
        })

        assert provider.validate_settings() is True
        models = provider.list_models()
        assert "Youssofal--Qwen3.6-27B-MTPLX-Optimized-Quality" in models
        assert "Youssofal/Qwen3.6-27B-MTPLX-Optimized-Quality" in models

        provider.verify_selected_model()
        assert provider.model == "Youssofal--Qwen3.6-27B-MTPLX-Optimized-Quality"


def test_mtplx_provider_generation_uses_dual_auth_headers_and_alias_matching():
    from unittest.mock import patch
    import httpx

    provider = get_provider(
        "mtplx",
        api_key="mtplx-local",
        base_url="http://127.0.0.1:8000/v1",
        model="Youssofal/Qwen3.6-27B-MTPLX-Optimized-Quality",
    )

    with patch("httpx.get") as mock_get, patch("httpx.Client.post") as mock_post:
        mock_get.return_value = httpx.Response(200, json={
            "ok": True,
            "model": "Youssofal--Qwen3.6-27B-MTPLX-Optimized-Quality",
            "context_window": 262144,
        })
        mock_post.return_value = httpx.Response(200, json={
            "model": "Youssofal--Qwen3.6-27B-MTPLX-Optimized-Quality",
            "choices": [{"message": {"content": "MTPLX ready"}}],
        })

        provider.verify_selected_model()
        output = provider.generate(prompt="Hello", system_prompt="You are brief.", max_tokens=32)
        assert output == "MTPLX ready"

        _, kwargs = mock_post.call_args
        assert kwargs["headers"]["Authorization"] == "Bearer mtplx-local"
        assert kwargs["headers"]["X-API-Key"] == "mtplx-local"
        assert kwargs["json"]["model"] == "Youssofal--Qwen3.6-27B-MTPLX-Optimized-Quality"
        assert kwargs["json"]["max_tokens"] == 32
        assert kwargs["json"]["max_completion_tokens"] == 32


def test_mtplx_provider_generation_aborts_when_cancelled():
    from unittest.mock import patch
    import time
    import httpx

    provider = get_provider(
        "mtplx",
        api_key="mtplx-local",
        base_url="http://127.0.0.1:8000/v1",
        model="Youssofal/Qwen3.6-27B-MTPLX-Optimized-Quality",
    )

    state = {"cancelled": False}

    def cancel_checker():
        if state["cancelled"]:
            raise Exception("Job was cancelled by the user")

    def slow_post(*args, **kwargs):
        time.sleep(1.0)
        return httpx.Response(200, json={
            "model": "Youssofal--Qwen3.6-27B-MTPLX-Optimized-Quality",
            "choices": [{"message": {"content": "too late"}}],
        })

    provider.bind_cancel_checker(cancel_checker)

    with patch("httpx.Client.post", side_effect=slow_post):
        state["cancelled"] = True
        try:
            provider.generate(prompt="Hello", system_prompt="You are brief.", max_tokens=32, timeout_seconds=2.0)
            assert False, "Expected GenerationCancelledError"
        except GenerationCancelledError:
            assert True
