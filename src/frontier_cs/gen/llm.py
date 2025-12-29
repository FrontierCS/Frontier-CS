"""LLM client instantiation and provider detection."""

import os
import threading
from typing import Any, Dict, Optional, Tuple

from .llm_interface import (
    LLMInterface,
    GPT,
    Gemini,
    Claude,
    Claude_Opus,
    Claude_Sonnet_4_5,
    DeepSeek,
    Grok,
)

# Thread-safe storage for model configuration summary
MODEL_CONFIG_SUMMARY: Dict[str, Dict[str, Any]] = {}
MODEL_CONFIG_LOCK = threading.Lock()


def infer_provider_and_model(model: str) -> Tuple[str, str]:
    """Parse model string into provider hint and actual model name."""
    normalized = model.strip()
    if "/" in normalized:
        provider, actual_model = normalized.split("/", 1)
    else:
        provider, actual_model = "", normalized
    return provider.lower(), actual_model.strip()


def detect_provider(model: str, actual_model_lower: Optional[str] = None) -> str:
    """Detect the provider for a given model string."""
    provider_hint, actual_model = infer_provider_and_model(model)
    actual_lower = actual_model_lower or actual_model.lower()

    if (provider_hint in {"", "openai", "azure", "azure_openai"}) and actual_lower.startswith("gpt"):
        return "openai"
    if provider_hint in {"gemini", "google"} or "gemini" in actual_lower:
        return "google"
    if provider_hint == "anthropic" or "claude" in actual_lower:
        return "anthropic"
    if provider_hint == "xai" or "grok" in actual_lower:
        return "xai"
    if provider_hint == "deepseek" or "deepseek" in actual_lower:
        return "deepseek"
    return provider_hint or "openai"


def instantiate_llm_client(
    model: str,
    *,
    is_reasoning_model: bool,
    timeout: float,
    base_url: Optional[str],
    api_key: Optional[str],
) -> Tuple[LLMInterface, Dict[str, Any]]:
    """Create an LLM client instance for the given model."""
    provider_hint, actual_model = infer_provider_and_model(model)
    actual_model_lower = actual_model.lower()
    provider = detect_provider(model, actual_model_lower)
    config: Dict[str, Any] = {
        "requested_model": model,
        "actual_model": actual_model,
        "reasoning_mode": is_reasoning_model,
    }

    # OpenRouter special-case for Gemini 3
    if provider == "openrouter":
        requested_lower = model.lower().strip()
        if requested_lower in {"gemini 3", "gemini3"}:
            or_slug = "google/gemini-3-pro-preview"
        elif "/" in model:
            or_slug = model
        else:
            if actual_model_lower.startswith("gemini-3"):
                or_slug = f"google/{actual_model}"
            else:
                or_slug = "google/gemini-3-pro-preview"

        openrouter_base = "https://openrouter.ai/api/v1"
        resolved_key = api_key or os.getenv("OPENROUTER_API_KEY")
        reasoning_effort = "high" if is_reasoning_model else None
        client = GPT(
            model=or_slug,
            reasoning_effort=reasoning_effort,
            timeout=timeout,
            base_url=openrouter_base,
            api_key=resolved_key,
        )
        config.update({
            "provider": "openrouter",
            "interface": client.__class__.__name__,
            "reasoning_effort": reasoning_effort,
            "base_url": openrouter_base,
            "openrouter_model_slug": or_slug,
        })

    elif provider == "openai":
        reasoning_effort = "high" if is_reasoning_model else None
        client = GPT(
            model=actual_model,
            reasoning_effort=reasoning_effort,
            timeout=timeout,
            base_url=base_url,
            api_key=api_key,
        )
        config.update({
            "provider": provider,
            "interface": client.__class__.__name__,
            "reasoning_effort": reasoning_effort,
            "base_url": base_url or "https://api.openai.com/v1",
        })
    elif provider == "google":
        client = Gemini(model=actual_model, timeout=timeout, api_key=api_key)
        config.update({
            "provider": provider,
            "interface": client.__class__.__name__,
            "reasoning_effort": None,
        })
    elif provider == "anthropic":
        if "claude-sonnet-4-5" in actual_model_lower:
            client = Claude_Sonnet_4_5(model=actual_model, api_key=api_key)
        elif "claude-opus" in actual_model_lower:
            client = Claude_Opus(model=actual_model, api_key=api_key)
        else:
            client = Claude(model=actual_model, api_key=api_key)
        config.update({
            "provider": provider,
            "interface": client.__class__.__name__,
            "reasoning_effort": "thinking-enabled",
        })
    elif provider == "xai":
        reasoning_effort = "high" if is_reasoning_model else None
        client = Grok(
            model=actual_model,
            reasoning_effort=reasoning_effort,
            timeout=timeout,
            api_key=api_key,
        )
        config.update({
            "provider": provider,
            "interface": client.__class__.__name__,
            "reasoning_effort": reasoning_effort,
            "base_url": "https://api.x.ai/v1",
        })
    elif provider == "deepseek":
        client = DeepSeek(
            model=actual_model,
            timeout=timeout,
            api_key=api_key,
        )
        config.update({
            "provider": provider,
            "interface": client.__class__.__name__,
            "reasoning_effort": None,
            "base_url": "https://api.deepseek.com",
        })
    else:
        raise ValueError(f"Unsupported model identifier '{model}' for llm_interface integration.")

    if api_key:
        config["api_key_hint"] = f"***{api_key[-6:]}"

    with MODEL_CONFIG_LOCK:
        MODEL_CONFIG_SUMMARY[model] = config

    return client, config
