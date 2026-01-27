"""Solution generation utilities.

Shared modules for research and algorithmic solution generation scripts.

Modules:
    llm_interface: LLM interface classes (GPT, Claude, Gemini, etc.)
    llm: LLM client instantiation and provider detection
    api_keys: API key pool management
    colors: Terminal color utilities
    io: Common I/O utilities
    failed_marker: Failed marker file utilities
    model_resolution: Model selection resolution
    executor: Concurrent execution utilities
    summary: Generation summary printing
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
    KeyInfo,
    ensure_env_loaded,
    precheck_api_keys,
    precheck_required_providers,
    KeyCheckResult,
    ValidKeyInfo,
)
from .colors import (
    bold, dim, red, green, yellow, blue, cyan, magenta,
    success, error, warning, info, header, section,
    model_name, problem_name, solution_name,
    print_header, print_section, print_success, print_error, print_warning, print_info,
)
from .failed_marker import (
    get_failed_path,
    has_failed_marker,
    write_failed_marker,
)
from .model_resolution import (
    resolve_models,
    ModelResolutionResult,
)
from .executor import (
    run_with_pool,
    ExecutionResult,
    acquire_key_for_provider,
)
from .summary import (
    print_generation_summary,
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
    "KeyInfo",
    "ensure_env_loaded",
    "precheck_api_keys",
    "precheck_required_providers",
    "KeyCheckResult",
    "ValidKeyInfo",
    # Colors
    "bold", "dim", "red", "green", "yellow", "blue", "cyan", "magenta",
    "success", "error", "warning", "info", "header", "section",
    "model_name", "problem_name", "solution_name",
    "print_header", "print_section", "print_success", "print_error", "print_warning", "print_info",
    # Failed marker
    "get_failed_path",
    "has_failed_marker",
    "write_failed_marker",
    # Model resolution
    "resolve_models",
    "ModelResolutionResult",
    # Executor
    "run_with_pool",
    "ExecutionResult",
    "acquire_key_for_provider",
    # Summary
    "print_generation_summary",
]
