from __future__ import annotations

import re
from typing import Any, Dict, Iterable, Optional

DEFAULT_MAX_OUTPUT_TOKENS = 4000
DEFAULT_CHUNK_SIZE = 10000
MAX_RECOMMENDED_OUTPUT_TOKENS = 32768
MAX_RECOMMENDED_CHUNK_SIZE = 1000000
MIN_SETTINGS_MAX_OUTPUT_TOKENS = 512
MIN_SETTINGS_CHUNK_SIZE = 4000
MIN_RECOMMENDED_OUTPUT_TOKENS = 1024
MIN_RECOMMENDED_CHUNK_SIZE = 8000

LOCAL_PROVIDER_NAMES = {"ollama", "lmstudio"}


def clamp_limit(value: Any, minimum: int, maximum: int) -> Optional[int]:
    try:
        normalized = int(value)
    except (TypeError, ValueError):
        return None
    if normalized <= 0:
        return None
    return max(minimum, min(normalized, maximum))


def build_limits_payload(
    max_output_tokens: Any,
    chunk_size: Any,
    *,
    source: str = "fallback",
    notes: str = "",
) -> Dict[str, Any]:
    resolved_max_output = clamp_limit(
        max_output_tokens,
        MIN_RECOMMENDED_OUTPUT_TOKENS,
        MAX_RECOMMENDED_OUTPUT_TOKENS,
    ) or DEFAULT_MAX_OUTPUT_TOKENS
    resolved_chunk_size = clamp_limit(
        chunk_size,
        MIN_RECOMMENDED_CHUNK_SIZE,
        MAX_RECOMMENDED_CHUNK_SIZE,
    ) or DEFAULT_CHUNK_SIZE
    return {
        "max_output_tokens": resolved_max_output,
        "maxOutputTokens": resolved_max_output,
        "chunk_size": resolved_chunk_size,
        "chunkSize": resolved_chunk_size,
        "source": source,
        "notes": notes,
    }


def is_local_provider_name(provider_name: str) -> bool:
    return provider_name.lower().strip() in LOCAL_PROVIDER_NAMES


def infer_local_model_profile(model_name: str) -> Dict[str, Any]:
    model = model_name.lower().strip()

    if any(token in model for token in ["128k", "131k", "200k", "256k", "1m"]):
        return build_limits_payload(
            16384,
            240000,
            source="fallback",
            notes="Large-context local model fallback profile.",
        )

    if any(token in model for token in ["64k", "65k", "70b", "72b", "mixtral", "qwen2.5", "qwen3", "deepseek", "coder"]):
        return build_limits_payload(
            12288,
            120000,
            source="fallback",
            notes="Expanded local model fallback profile.",
        )

    if any(token in model for token in ["llama3.1", "llama-3.1", "llama 3.1", "gemma3", "mistral-nemo", "32k"]):
        return build_limits_payload(
            8192,
            80000,
            source="fallback",
            notes="Medium-capacity local model fallback profile.",
        )

    if any(token in model for token in ["llama-3", "llama3", "mistral", "gemma", "phi"]):
        return build_limits_payload(
            4096,
            20000,
            source="fallback",
            notes="Conservative local model fallback profile.",
        )

    return build_limits_payload(
        6144,
        40000,
        source="fallback",
        notes="Generic local model fallback profile.",
    )


def derive_output_tokens_from_context(context_length: Any) -> Optional[int]:
    normalized_context = clamp_limit(context_length, 2048, 262144)
    if not normalized_context:
        return None
    derived = max(2048, normalized_context // 8)
    return clamp_limit(derived, MIN_RECOMMENDED_OUTPUT_TOKENS, 16384)


def extract_int_from_keys(payload: Any, keys: Iterable[str]) -> Optional[int]:
    if isinstance(payload, dict):
        lowered = {str(key).lower(): value for key, value in payload.items()}
        for key in keys:
            if key.lower() in lowered:
                extracted = clamp_limit(
                    lowered[key.lower()],
                    MIN_RECOMMENDED_OUTPUT_TOKENS,
                    MAX_RECOMMENDED_CHUNK_SIZE,
                )
                if extracted:
                    return extracted

        for value in payload.values():
            extracted = extract_int_from_keys(value, keys)
            if extracted:
                return extracted

    if isinstance(payload, list):
        for item in payload:
            extracted = extract_int_from_keys(item, keys)
            if extracted:
                return extracted

    return None


def extract_int_from_text(text: str, patterns: Iterable[str]) -> Optional[int]:
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if not match:
            continue
        extracted = clamp_limit(
            match.group(1),
            MIN_RECOMMENDED_OUTPUT_TOKENS,
            MAX_RECOMMENDED_CHUNK_SIZE,
        )
        if extracted:
            return extracted
    return None
