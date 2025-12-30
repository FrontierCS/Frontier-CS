"""
Model name utilities for Frontier-CS.

Provides consistent model prefix conversion used across:
- Solution generation (generate_solutions.py)
- Solution matrix checking (frontier-eval check)
- Batch evaluation (frontier-eval batch)
"""

import re
from typing import Dict, List, Optional, Tuple

# Model prefix aliases for backward compatibility
MODEL_PREFIX_ALIASES: Dict[str, str] = {
    "grokcodefast1_": "grok4fastreasoning_",
}


def get_model_prefix(model: str) -> str:
    """
    Convert model name to the prefix format used in solution folder names.

    This is the canonical function for model prefix conversion. All tools
    should use this to ensure consistent naming.

    Examples:
        >>> get_model_prefix("gpt-5")
        'gpt5'
        >>> get_model_prefix("gpt-5.1-preview")
        'gpt5.1'
        >>> get_model_prefix("gemini/gemini-2.5-pro")
        'gemini2.5pro'
        >>> get_model_prefix("claude-sonnet-4-5-20250929")
        'claude4.5sonnet'
        >>> get_model_prefix("grok-3-fast-reasoning")
        'grok3fastreasoning'

    Args:
        model: Model name (e.g., "gpt-5", "gemini/gemini-2.5-pro")

    Returns:
        Normalized prefix for solution directory names
    """
    original = model

    # Remove provider prefix if present (e.g., 'gemini/gemini-2.5-pro' -> 'gemini-2.5-pro')
    if "/" in model:
        model = model.split("/", 1)[1]

    model_lower = model.lower().strip()

    # Handle GPT-5 variants
    # Keep 'gpt-5.1', 'gpt-5.2' etc. distinct so their artifacts prefix correctly
    if model_lower.startswith("gpt-5.2") or model_lower.startswith("gpt5.2"):
        return "gpt5.2"
    if model_lower.startswith("gpt-5.1") or model_lower.startswith("gpt5.1"):
        return "gpt5.1"
    if model_lower.startswith("gpt-5") or model_lower.startswith("gpt5"):
        return "gpt5"

    # Handle Gemini 2.5 Pro variants
    if "gemini-2.5-pro" in model_lower or "gemini2.5pro" in model_lower:
        return "gemini2.5pro"

    # Handle other Gemini variants (e.g., gemini-1.5-pro -> gemini1.5pro)
    gemini_match = re.match(r"gemini-?(\d+\.?\d*)-?pro", model_lower)
    if gemini_match:
        version = gemini_match.group(1)
        return f"gemini{version}pro"

    # Handle Claude variants (e.g., claude-sonnet-4-5-20250929 -> claude4.5sonnet)
    claude_match = re.match(r"claude-([a-z]+)-(\d+)-(\d+)", model_lower)
    if claude_match:
        family = claude_match.group(1)
        major = claude_match.group(2)
        minor = claude_match.group(3)
        return f"claude{major}.{minor}{family}"

    # Handle Grok variants - keep 'fast' and 'reasoning' in the prefix
    if "grok" in model_lower:
        sanitized = re.sub(r"[^a-zA-Z0-9]+", "", model_lower)
        if sanitized:
            return sanitized

    # Default: sanitize by removing all non-alphanumeric characters
    sanitized = re.sub(r"[^a-zA-Z0-9]+", "", model_lower)
    if not sanitized:
        raise ValueError(f"Unable to derive model prefix from '{original}'")
    return sanitized


def normalize_solution_name(name: str) -> str:
    """
    Normalize a solution directory name by applying prefix aliases.

    Args:
        name: Solution directory name

    Returns:
        Normalized name with aliases applied
    """
    for old_prefix, new_prefix in MODEL_PREFIX_ALIASES.items():
        if name.startswith(old_prefix):
            return new_prefix + name[len(old_prefix):]
    return name


def get_solution_filename(model: str, variant: int = 0, ext: str = "py") -> str:
    """
    Get solution filename from model and variant.

    Examples:
        >>> get_solution_filename("gpt-5")
        'gpt5.py'
        >>> get_solution_filename("gpt-5", variant=1)
        'gpt5_1.py'
        >>> get_solution_filename("claude-sonnet-4-5-20250929", variant=2)
        'claude4.5sonnet_2.py'

    Args:
        model: Model name (will be converted to prefix)
        variant: Variant index (0 = no suffix)
        ext: File extension (default: "py")

    Returns:
        Solution filename
    """
    prefix = get_model_prefix(model)
    suffix = "" if variant == 0 else f"_{variant}"
    return f"{prefix}{suffix}.{ext}"


def get_solution_path(
    solutions_dir: "Path",
    problem: str,
    model: str,
    variant: int = 0,
    ext: str = "py",
) -> "Path":
    """
    Get solution file path.

    New nested structure:
        solutions/{problem}/{model_prefix}.py
        solutions/{problem}/{model_prefix}_{variant}.py

    Examples:
        >>> get_solution_path(Path("solutions"), "llm_sql/large", "gpt-5")
        Path('solutions/llm_sql/large/gpt5.py')
        >>> get_solution_path(Path("solutions"), "flash_attn", "gpt-5", variant=1)
        Path('solutions/flash_attn/gpt5_1.py')

    Args:
        solutions_dir: Path to solutions directory
        problem: Problem ID (e.g., "flash_attn", "llm_sql/large")
        model: Model name
        variant: Variant index (0 = no suffix)
        ext: File extension (default: "py")

    Returns:
        Path to solution file
    """
    from pathlib import Path
    solutions_dir = Path(solutions_dir)
    filename = get_solution_filename(model, variant, ext)
    return solutions_dir / problem / filename


def parse_solution_path(
    solution_path: "Path",
    solutions_dir: "Path",
) -> Tuple[str, str, int]:
    """
    Parse a solution file path into components.

    Examples:
        >>> parse_solution_path(Path("solutions/llm_sql/large/gpt5.py"), Path("solutions"))
        ('llm_sql/large', 'gpt5', 0)
        >>> parse_solution_path(Path("solutions/flash_attn/gpt5_1.py"), Path("solutions"))
        ('flash_attn', 'gpt5', 1)

    Args:
        solution_path: Path to solution file
        solutions_dir: Path to solutions directory

    Returns:
        Tuple of (problem, model_prefix, variant)
    """
    from pathlib import Path
    solution_path = Path(solution_path)
    solutions_dir = Path(solutions_dir)

    # Get problem from directory structure
    rel = solution_path.relative_to(solutions_dir)
    problem = str(rel.parent)

    # Parse filename: {model_prefix}.py or {model_prefix}_{variant}.py
    stem = solution_path.stem  # e.g., "gpt5" or "gpt5_1"
    parts = stem.rsplit("_", 1)

    if len(parts) == 2 and parts[1].isdigit():
        model_prefix = parts[0]
        variant = int(parts[1])
    else:
        model_prefix = stem
        variant = 0

    return (problem, model_prefix, variant)


def detect_provider(model: str) -> str:
    """
    Detect the LLM provider from model name.

    Args:
        model: Model name

    Returns:
        Provider name: 'openai', 'google', 'anthropic', 'xai', 'deepseek', 'openrouter'
    """
    normalized = model.strip()
    if "/" in normalized:
        provider_hint, actual_model = normalized.split("/", 1)
    else:
        provider_hint, actual_model = "", normalized

    provider_hint = provider_hint.lower()
    actual_lower = actual_model.lower()

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


def is_reasoning_model(model: str, override: Optional[bool] = None) -> bool:
    """
    Determine if a model is a reasoning model.

    Args:
        model: Model name
        override: If set, use this value instead of auto-detection

    Returns:
        True if the model is a reasoning model
    """
    if override is not None:
        return override

    prefixes = ("gpt-5", "o1", "o3", "deepseek-reasoner")
    if any(model.startswith(p) for p in prefixes):
        return True

    normalized = model.lower()
    if "reasoning" in normalized and normalized.startswith("grok-"):
        return True

    return False
