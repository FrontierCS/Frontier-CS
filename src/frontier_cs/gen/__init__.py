"""Solution generation utilities.

Shared modules for research and algorithmic solution generation scripts.

Modules:
    llm_interface: LLM interface classes (GPT, Claude, Gemini, etc.)
    llm: LLM client instantiation and provider detection
    api_keys: API key pool management
    colors: Terminal color utilities
    io: Common I/O utilities
"""

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
from .llm import (
    instantiate_llm_client,
    detect_provider,
    infer_provider_and_model,
)
from .api_keys import (
    build_key_pools,
    get_fallback_api_key,
    APIKeyPool,
)
from .colors import (
    bold, dim, red, green, yellow, blue, cyan, magenta,
    success, error, warning, info, header, section,
    model_name, problem_name, solution_name,
    print_header, print_section, print_success, print_error, print_warning, print_info,
)

__all__ = [
    # LLM interfaces
    "LLMInterface",
    "GPT",
    "Gemini",
    "Claude",
    "Claude_Opus",
    "Claude_Sonnet_4_5",
    "DeepSeek",
    "Grok",
    # LLM utilities
    "instantiate_llm_client",
    "detect_provider",
    "infer_provider_and_model",
    # API keys
    "build_key_pools",
    "get_fallback_api_key",
    "APIKeyPool",
    # Colors
    "bold", "dim", "red", "green", "yellow", "blue", "cyan", "magenta",
    "success", "error", "warning", "info", "header", "section",
    "model_name", "problem_name", "solution_name",
    "print_header", "print_section", "print_success", "print_error", "print_warning", "print_info",
]
