#!/usr/bin/env python3
"""
Generate LLM solutions from problem README files.

Supports multiple providers: OpenAI, Google (Gemini), Anthropic (Claude), xAI (Grok), DeepSeek.

Usage:
    python generate_solutions.py --model gpt-5
    python generate_solutions.py research/flash_attn --model claude-sonnet-4-5
"""

import sys
import os
import json
import time
import argparse
import re
import shutil
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
import threading
from typing import Optional, Dict, Any, List, Tuple
from datetime import datetime
from importlib import metadata

from test_scripts.llm_interface import (
    LLMInterface,
    GPT,
    Gemini,
    Claude,
    Claude_Opus,
    Claude_Sonnet_4_5,
    DeepSeek,
    Grok,
)

from frontier_cs.config import load_runtime_config, get_effective_gpu_type
from frontier_cs.models import get_model_prefix, detect_provider, is_reasoning_model

PREPARE_ENV_TEMPLATE = """#!/usr/bin/env bash
set -euo pipefail
echo "[{solution_name}] No additional environment preparation required."
"""

SOLVE_TEMPLATE = """#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR=$(cd "$(dirname "${{BASH_SOURCE[0]}}")" && pwd)
TARGET_DIR="/work/Frontier-CS/execution_env/solution_env"
mkdir -p "$TARGET_DIR"
cp "$SCRIPT_DIR/resources/solution.py" "$TARGET_DIR/solution.py"
echo "[{solution_name}] solution.py staged"
"""

SOLUTION_TEMPLATE = "{generated_code}\n"

REQUIRED_NUMPY_VERSION = "2.3.4"

# Base system prompt template - environment section will be injected
SYSTEM_PROMPT_TEMPLATE = """You are an expert programmer. Generate Python code for the given problem.

{environment_section}
REQUIREMENTS:
1. Output ONLY Python code - no explanations, no markdown
2. Implement ALL required classes/functions from the API section
3. Use efficient algorithms appropriate for the evaluation environment
4. Final class name must match the API specification exactly

Output ONLY the code, starting with imports."""

# ============================================================================
# Environment Configuration
# ============================================================================
# - gpu_type: We control via SkyPilot, default L4
# - environment: Problem-specific, describes the evaluation environment
#   (each problem must specify its own since we don't know which docker image it uses)

DEFAULT_GPU_TYPE = "L4"

# GPU specifications mapping (SkyPilot-compatible GPU types)
GPU_SPECS: Dict[str, Dict[str, str]] = {
    "L4": {"name": "NVIDIA L4", "vram": "24GB"},
    "A10G": {"name": "NVIDIA A10G", "vram": "24GB"},
    "A100": {"name": "NVIDIA A100", "vram": "40GB"},
    "A100-40GB": {"name": "NVIDIA A100", "vram": "40GB"},
    "A100-80GB": {"name": "NVIDIA A100", "vram": "80GB"},
    "H100": {"name": "NVIDIA H100", "vram": "80GB"},
    "V100": {"name": "NVIDIA V100", "vram": "16GB"},
    "V100-32GB": {"name": "NVIDIA V100", "vram": "32GB"},
    "T4": {"name": "NVIDIA T4", "vram": "16GB"},
}


@dataclass
class EnvConfig:
    """Environment configuration."""
    gpu_type: Optional[str] = None  # None = CPU, string = GPU type
    environment: Optional[str] = None  # Problem-specific environment description
    # Resources from config.yaml
    cpus: Optional[str] = None  # e.g., "8", "8+", "4-8"
    memory: Optional[str] = None  # e.g., "32", "32+"
    disk_size: Optional[int] = None  # GB
    instance_type: Optional[str] = None  # e.g., "n1-standard-8"


def _format_spec(spec: str) -> str:
    """Format a spec like '8+' to '8+ (or more)'."""
    if spec.endswith("+"):
        return f"{spec[:-1]}+ (or more)"
    return spec


def build_cpu_environment(config: EnvConfig) -> str:
    """Generate CPU environment description."""
    # Build CPU/memory spec from config or defaults
    cpu_spec = config.cpus or "8"
    mem_spec = config.memory or "16"

    cpu_display = _format_spec(cpu_spec)
    mem_display = _format_spec(mem_spec)

    lines = ["EVALUATION ENVIRONMENT:"]

    # Instance type if specified
    if config.instance_type:
        lines.append(f"- Instance: {config.instance_type}")

    lines.append(f"- CPU-only: {cpu_display} vCPUs, {mem_display}GB RAM (NO GPU)")

    if config.disk_size:
        lines.append(f"- Disk: {config.disk_size}GB")

    if config.environment:
        lines.append(f"- {config.environment}")
    return "\n".join(lines)


def build_gpu_environment(config: EnvConfig) -> str:
    """Generate GPU environment description from config."""
    gpu_type = config.gpu_type or DEFAULT_GPU_TYPE
    spec = GPU_SPECS.get(gpu_type, GPU_SPECS[DEFAULT_GPU_TYPE])

    lines = ["EVALUATION ENVIRONMENT:"]

    # Instance type if specified
    if config.instance_type:
        lines.append(f"- Instance: {config.instance_type}")

    lines.append(f"- GPU: {spec['name']} ({spec['vram']} VRAM)")

    # CPU/memory if specified
    if config.cpus or config.memory:
        cpu_spec = config.cpus or "8"
        mem_spec = config.memory or "32"
        cpu_display = _format_spec(cpu_spec)
        mem_display = _format_spec(mem_spec)
        lines.append(f"- CPU: {cpu_display} vCPUs, {mem_display}GB RAM")

    if config.disk_size:
        lines.append(f"- Disk: {config.disk_size}GB")

    if config.environment:
        lines.append(f"- {config.environment}")
    return "\n".join(lines)


# For backward compatibility
SYSTEM_PROMPT = SYSTEM_PROMPT_TEMPLATE.format(
    environment_section=build_cpu_environment(EnvConfig())
)

# Cache for docker image config
_DOCKER_CONFIG_CACHE: Dict[str, Tuple[str, bool, bool]] = {}


def load_docker_config(config_path: Optional[Path] = None) -> Dict[str, Tuple[str, bool, bool]]:
    """
    Load docker image configuration from docker_images.txt.

    Returns:
        Dict mapping problem_name -> (image, gpu_enabled, dind_enabled)
    """
    global _DOCKER_CONFIG_CACHE
    if _DOCKER_CONFIG_CACHE:
        return _DOCKER_CONFIG_CACHE

    if config_path is None:
        config_path = Path(__file__).parent / "docker_images.txt"

    if not config_path.exists():
        return {}

    config = {}
    for line in config_path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue

        problem_name, rest = line.split("=", 1)
        parts = rest.split(",")
        image = parts[0].strip() if parts else ""

        gpu_enabled = False
        dind_enabled = False

        for part in parts[1:]:
            part = part.strip().lower()
            if part in ("gpu", "true", "1"):
                gpu_enabled = True
            elif part in ("dind", "docker"):
                dind_enabled = True

        config[problem_name.strip()] = (image, gpu_enabled, dind_enabled)

    _DOCKER_CONFIG_CACHE = config
    return config


def load_env_config_from_problem(problem_path: Path) -> EnvConfig:
    """
    Load environment configuration from problem's config.yaml runtime section.

    Supported config.yaml runtime fields:
        - gpu_type: SkyPilot GPU type (e.g., "L4", "A100"). Affects both eval and generation.
        - resources.accelerators: SkyPilot accelerators (e.g., "L4:1", "A100:4")
        - resources.cpus: CPU specification (e.g., "8", "8+")
        - resources.memory: Memory in GB (e.g., "32", "32+")
        - resources.disk_size: Disk size in GB
        - resources.instance_type: Cloud instance type (e.g., "n1-standard-8")
        - environment: Problem-specific environment description (Python version, packages, etc.)

    Args:
        problem_path: Path to the problem directory

    Returns:
        EnvConfig with values from config
    """
    env_config = EnvConfig()

    # Use shared config_loader
    runtime_config = load_runtime_config(problem_path)

    # Get GPU type from resources.accelerators or legacy gpu_type
    gpu_type = get_effective_gpu_type(runtime_config)
    if gpu_type:
        env_config.gpu_type = gpu_type

    # Get resources
    res = runtime_config.resources
    if res.cpus:
        env_config.cpus = res.cpus
    if res.memory:
        env_config.memory = res.memory
    if res.disk_size:
        env_config.disk_size = res.disk_size
    if res.instance_type:
        env_config.instance_type = res.instance_type

    # Get environment description
    if runtime_config.environment:
        env_config.environment = runtime_config.environment

    return env_config


def get_system_prompt_for_problem(problem_name: str, problem_path: Optional[Path] = None) -> str:
    """
    Build system prompt with environment info.

    Priority (with fallbacks):
    1. config.yaml runtime section -> Use specified values, defaults for unspecified
    2. docker_images.txt GPU detection -> GPU with default config, or CPU
    3. Default CPU environment

    Args:
        problem_name: Name of the problem (e.g., 'gemm_optimization_squares')
        problem_path: Optional path to the problem directory

    Returns:
        Complete system prompt string with environment section
    """
    env_config = EnvConfig()  # Start with defaults

    # Priority 1: Try to load config from config.yaml
    if problem_path and problem_path.is_dir():
        env_config = load_env_config_from_problem(problem_path)

    # Priority 2: Fallback to docker_images.txt for GPU detection (if no gpu_type in config)
    if env_config.gpu_type is None:
        docker_config = load_docker_config()
        # Extract base problem name (handle nested paths like gemm_optimization/squares)
        base_name = problem_name.split("/")[0] if "/" in problem_name else problem_name
        # Also try underscore format (gemm_optimization_squares -> gemm_optimization)
        if "_" in base_name and base_name not in docker_config:
            base_name = base_name.split("_")[0]

        if base_name in docker_config:
            _, gpu_enabled, _ = docker_config[base_name]
            if gpu_enabled:
                env_config.gpu_type = DEFAULT_GPU_TYPE

    # Build environment section based on GPU or CPU mode
    if env_config.gpu_type:
        environment_section = build_gpu_environment(env_config)
    else:
        environment_section = build_cpu_environment(env_config)

    return SYSTEM_PROMPT_TEMPLATE.format(environment_section=environment_section)

MODEL_CONFIG_SUMMARY: Dict[str, Dict[str, Any]] = {}
MODEL_CONFIG_LOCK = threading.Lock()


def write_problems_from_pairs(pairs_path: Path, target_path: Path) -> None:
    if not pairs_path.is_file():
        return

    problems: List[str] = []
    seen: set[str] = set()
    for raw_line in pairs_path.read_text(encoding="utf-8").splitlines():
        stripped = raw_line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if ":" not in stripped:
            continue
        _, problem = stripped.split(":", 1)
        problem_clean = problem.strip()
        if not problem_clean:
            continue
        if not problem_clean.startswith("research/") and not problem_clean.startswith("./research/"):
            problem_clean = f"research/{problem_clean.lstrip('./')}"
        if problem_clean not in seen:
            seen.add(problem_clean)
            problems.append(problem_clean)

    if not problems:
        return

    target_path.write_text("\n".join(problems) + "\n", encoding="utf-8")


@dataclass
class GenerationTask:
    problem_path: Path
    display_path: str
    problem_name: str
    readme: str
    model: str
    provider: str
    reasoning_model: bool
    variant_index: int  # actual suffix index (0 -> no suffix)
    variant_position: int  # ordinal position in the configured variant list (0-based)
    solution_name: str
    total_variants: int = 1


class APIKeyPool:
    def __init__(self, keys: List[str], *, name: str):
        self.name = name
        self._states = [
            {
                "key": key,
                "failures": 0,
                "disabled": False,
                "backoff_until": 0.0,
            }
            for key in keys
        ]
        self._lock = threading.Lock()
        self._index = 0

    def acquire(self) -> Tuple[Optional[str], Optional[int]]:
        with self._lock:
            if not self._states:
                return None, None
            now = time.time()
            for _ in range(len(self._states)):
                idx = self._index % len(self._states)
                self._index += 1
                state = self._states[idx]
                if state["disabled"]:
                    continue
                if state["backoff_until"] > now:
                    continue
                return state["key"], idx
            return None, None

    def report_success(self, idx: Optional[int]) -> None:
        if idx is None:
            return
        with self._lock:
            if 0 <= idx < len(self._states):
                state = self._states[idx]
                state["failures"] = 0
                state["backoff_until"] = 0.0

    def report_failure(self, idx: Optional[int], error: Optional[str]) -> None:
        if idx is None:
            return
        with self._lock:
            if not (0 <= idx < len(self._states)):
                return
            state = self._states[idx]
            state["failures"] += 1
            reason = (error or "").lower()
            fatal_markers = ("invalid", "unauthorized", "forbidden", "permission", "auth")
            if any(marker in reason for marker in fatal_markers):
                if not state["disabled"]:
                    print(f"Disabling API key for {self.name}: appears invalid/unauthorized")
                state["disabled"] = True
                state["backoff_until"] = float("inf")
                return

            delay: int = min(600, 60 * state["failures"])
            state["backoff_until"] = max(state["backoff_until"], time.time() + delay)
            print(
                f"Backing off {delay:.0f}s for {self.name} key due to failure (count={state['failures']})."
            )

    def size(self) -> int:
        with self._lock:
            return len(self._states)


PROVIDER_ENV_KEY_MAP: Dict[str, List[str]] = {
    "openai": ["OPENAI_API_KEY"],
    "google": ["GOOGLE_API_KEY", "GEMINI_API_KEY"],
    "anthropic": ["ANTHROPIC_API_KEY"],
    "xai": ["XAI_API_KEY", "GROK_API_KEY"],
    "deepseek": ["DEEPSEEK_API_KEY"],
    # Special routing via OpenRouter (normalized OpenAI Chat Completions API)
    "openrouter": ["OPENROUTER_API_KEY"],
}


def _matches_env_base(key_name: str, base: str) -> bool:
    if key_name == base:
        return True
    if key_name.startswith(base):
        suffix = key_name[len(base) :]
        if not suffix:
            return True
        if suffix.isdigit():
            return True
        if suffix.startswith(('_', '-')):
            return True
    return False


def _collect_provider_keys(provider: str, base_names: List[str]) -> List[str]:
    keys: List[str] = []
    seen: set[str] = set()
    for env_name, value in os.environ.items():
        if not value:
            continue
        for base in base_names:
            if _matches_env_base(env_name, base):
                key_value = value.strip()
                if key_value and key_value not in seen:
                    seen.add(key_value)
                    keys.append(key_value)
    return keys


def _infer_provider_and_model(model: str) -> Tuple[str, str]:
    normalized = model.strip()
    if "/" in normalized:
        provider, actual_model = normalized.split("/", 1)
    else:
        provider, actual_model = "", normalized
    return provider.lower(), actual_model.strip()


def _detect_provider(model: str, actual_model_lower: Optional[str] = None) -> str:
    provider_hint, actual_model = _infer_provider_and_model(model)
    actual_lower = actual_model_lower or actual_model.lower()

    # Special-case: route Gemini 3 via OpenRouter instead of Google's SDK
    # Accept inputs like: "gemini 3", "gemini3", "gemini-3*", "google/gemini-3-*"
    # gemini3_markers = ("gemini 3", "gemini3", "gemini-3")
    # if any(ml in (model.lower()) for ml in gemini3_markers) or any(m in actual_lower for m in gemini3_markers):
    #     return "openrouter"

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


def _instantiate_llm_client(
    model: str,
    *,
    is_reasoning_model: bool,
    timeout: float,
    base_url: Optional[str],
    api_key: Optional[str],
) -> Tuple[LLMInterface, Dict[str, Any]]:
    provider_hint, actual_model = _infer_provider_and_model(model)
    actual_model_lower = actual_model.lower()
    provider = _detect_provider(model, actual_model_lower)
    config: Dict[str, Any] = {
        "requested_model": model,
        "actual_model": actual_model,
        "reasoning_mode": is_reasoning_model,
    }

    # OpenRouter special-case for Gemini 3
    if provider == "openrouter":
        # Determine full OpenRouter model slug.
        # If the caller passed a bare alias like "gemini 3"/"gemini3", normalize to Google's official slug.
        # If they passed something like "gemini-3-pro-preview", prefix with "google/".
        requested_lower = model.lower().strip()
        if requested_lower in {"gemini 3", "gemini3"}:
            or_slug = "google/gemini-3-pro-preview"
        elif "/" in model:
            # Use caller-provided slug as-is (expected to be 'google/gemini-3-*')
            or_slug = model
        else:
            if actual_model_lower.startswith("gemini-3"):
                or_slug = f"google/{actual_model}"
            else:
                # Fallback to the preview slug
                or_slug = "google/gemini-3-pro-preview"

        # Use OpenRouter base URL and key regardless of CLI base_url
        openrouter_base = "https://openrouter.ai/api/v1"
        # Prefer the provided key; otherwise fall back to env OPENROUTER_API_KEY.
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


def _build_key_pools(primary_openai_key: Optional[str]) -> Dict[str, APIKeyPool]:
    pools: Dict[str, APIKeyPool] = {}
    for provider, bases in PROVIDER_ENV_KEY_MAP.items():
        keys = _collect_provider_keys(provider, bases)
        if provider == "openai" and primary_openai_key:
            key = primary_openai_key.strip()
            if key and key not in keys:
                keys.insert(0, key)
        if keys:
            pools[provider] = APIKeyPool(keys, name=provider)
    return pools


def ensure_numpy_version(required: str) -> None:
    try:
        installed = metadata.version("numpy")
    except metadata.PackageNotFoundError as exc:
        raise RuntimeError(
            f"NumPy {required} is required but not installed; install it with `uv pip install --python .venv/bin/python numpy=={required}`."
        ) from exc
    if installed != required:
        raise RuntimeError(
            f"NumPy {required} is required, but found {installed}; reinstall the correct version with `uv pip install --python .venv/bin/python numpy=={required}`."
        )


def load_env_file(env_path: Path) -> None:
    """Load simple KEY=VALUE pairs from a .env file into os.environ."""
    if not env_path.is_file():
        return

    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.lower().startswith("export "):
            line = line[len("export ") :].strip()
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key:
            os.environ[key] = value


def load_solution_targets(path: Path) -> List[Tuple[str, str]]:
    if not path.is_file():
        raise FileNotFoundError(f"Solutions file not found: {path}")

    targets: List[Tuple[str, str]] = []
    seen: set[str] = set()
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if ":" not in line:
            raise ValueError(f"Invalid solutions file line (expected solution:problem): {line}")
        solution, problem = line.split(":", 1)
        solution = solution.strip()
        problem = problem.strip()
        if not solution or not problem:
            continue
        key = f"{solution}:{problem}"
        if key in seen:
            continue
        seen.add(key)
        targets.append((solution, problem))

    if not targets:
        raise ValueError(f"No valid entries found in {path}")
    return targets


def read_models_file(path: Path) -> List[str]:
    models: List[str] = []
    seen: set[str] = set()
    if not path.is_file():
        return models
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line not in seen:
            models.append(line)
            seen.add(line)
    return models


def read_variant_indices_file(path: Path) -> List[int]:
    """Read variant indices from file.

    Format:
      - One integer per line (e.g., 0, 1, 2, 3, 4). 0 means no suffix.
      - Blank lines and lines starting with '#' are ignored.

    Backward compatibility:
      - If the file contains a single integer N, treat as variants [0..N-1].
    """
    if not path.is_file():
        return [0]
    raw: List[str] = []
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        raw.append(line)

    if not raw:
        return [0]

    # If single integer -> expand to range
    if len(raw) == 1:
        try:
            count = int(raw[0])
            if count <= 0:
                return [0]
            return list(range(count))
        except ValueError:
            pass  # fall through to per-line parsing

    seen: set[int] = set()
    indices: List[int] = []
    for entry in raw:
        try:
            idx = int(entry)
        except ValueError as exc:
            raise ValueError(f"Invalid variant index in {path}: '{entry}'") from exc
        if idx < 0:
            raise ValueError(f"Variant indices must be >= 0, got {idx}")
        if idx not in seen:
            seen.add(idx)
            indices.append(idx)
    if not indices:
        return [0]
    return indices


def sanitize_model_suffix(model: str) -> str:
    return re.sub(r"[^a-zA-Z0-9]+", "_", model).strip("_") or "model"


# get_model_prefix imported from frontier_cs.models


def read_readme(problem_path: Path) -> str:
    for name in ["readme", "README.md", "README", "readme.md"]:
        readme = problem_path / name
        if readme.exists():
            return readme.read_text(encoding='utf-8')
    raise FileNotFoundError(f"No README in {problem_path}")


def float_or_none(value: str) -> Optional[float]:
    text = str(value).strip()
    if text.lower() in {"none", "null"}:
        return None
    return float(text)


def int_or_none(value: str) -> Optional[int]:
    text = str(value).strip()
    if text.lower() in {"none", "null"}:
        return None
    return int(text)


def parse_extra_headers(entries: List[str]) -> Dict[str, str]:
    headers: Dict[str, str] = {}
    for entry in entries:
        if ":" not in entry:
            raise ValueError(f"Invalid header format (expected Key: Value): {entry}")
        key, value = entry.split(":", 1)
        headers[key.strip()] = value.strip()
    return headers


def load_json_args(payload_str: Optional[str]) -> Optional[Dict[str, Any]]:
    if not payload_str:
        return None
    try:
        data = json.loads(payload_str)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON for --payload-extra: {exc}") from exc
    if not isinstance(data, dict):
        raise ValueError("--payload-extra must be a JSON object")
    return data


def resolve_api_key(explicit_key: Optional[str], key_env: Optional[str]) -> Optional[str]:
    if explicit_key:
        return explicit_key
    if key_env:
        return os.getenv(key_env)
    return None


# is_reasoning delegates to is_reasoning_model from frontier_cs.models
def is_reasoning(model: str, override: Optional[bool]) -> bool:
    return is_reasoning_model(model, override)


def generate_code(
    readme: str,
    *,
    model: str,
    api_key: Optional[str],
    log_file: Path,
    api_base: str,
    endpoint: str,
    temperature: Optional[float],
    max_tokens: Optional[int],
    max_reasoning_tokens: Optional[int],
    is_reasoning_model: bool,
    extra_headers: Dict[str, str],
    timeout: float,
    payload_overrides: Optional[Dict[str, Any]],
    api_key_header: Optional[str],
    api_key_prefix: Optional[str],
    problem_name: str = "",
    problem_path: Optional[Path] = None,
) -> str:
    base_url = (api_base or "").strip()
    if base_url.lower() in {"none", ""}:
        base_url = None
    else:
        base_url = base_url.rstrip("/")

    endpoint_hint = (endpoint or "").strip() or "auto"

    # Get environment-specific system prompt from config.yaml or fallback to docker_images.txt
    system_prompt = get_system_prompt_for_problem(problem_name, problem_path)

    # Prepare prompts for llm_interface which expects a single user message.
    user_prompt = f"Problem:\n\n{readme}\n\nGenerate solution code:"
    combined_prompt = f"{system_prompt}\n\n{user_prompt}"

    # Log request details
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    final_headers: Dict[str, str] = dict(extra_headers)
    ignored_controls: Dict[str, Any] = {}
    if final_headers:
        ignored_controls["extra_headers"] = final_headers
    if payload_overrides:
        ignored_controls["payload_overrides"] = payload_overrides
    if api_key_header:
        ignored_controls["api_key_header"] = api_key_header
    if api_key_prefix:
        ignored_controls["api_key_prefix"] = api_key_prefix
    if temperature is not None:
        ignored_controls["temperature"] = temperature
    if max_tokens is not None and not is_reasoning_model:
        ignored_controls["max_tokens"] = max_tokens
    if max_reasoning_tokens is not None and is_reasoning_model:
        ignored_controls["max_reasoning_tokens"] = max_reasoning_tokens

    llm_client, llm_config = _instantiate_llm_client(
        model,
        is_reasoning_model=is_reasoning_model,
        timeout=timeout,
        base_url=base_url,
        api_key=api_key,
    )

    with open(log_file, 'w', encoding='utf-8') as f:
        f.write("=" * 80 + "\n")
        f.write("GPT GENERATION LOG\n")
        f.write(f"Timestamp: {timestamp}\n")
        f.write("=" * 80 + "\n\n")

        f.write(f"MODEL: {model}\n")
        f.write(f"INTERFACE CLASS: {llm_client.__class__.__name__}\n")
        for key, value in llm_config.items():
            f.write(f"{key.upper()}: {value}\n")
        f.write(f"ENDPOINT HINT: {endpoint_hint}\n")
        f.write(f"TIMEOUT: {timeout}s\n")
        f.write(f"REASONING MODEL: {is_reasoning_model}\n")
        f.write(f"API KEY PROVIDED: {'yes' if bool(api_key) else 'no'}\n")
        if ignored_controls:
            f.write("IGNORED CONTROLS (not supported by llm_interface):\n")
            f.write(json.dumps(ignored_controls, indent=2, ensure_ascii=False))
            f.write("\n")
        f.write("\n" + "=" * 80 + "\n")
        f.write("SYSTEM PROMPT:\n")
        f.write("=" * 80 + "\n")
        f.write(system_prompt)
        f.write("\n\n" + "=" * 80 + "\n")
        f.write("USER PROMPT:\n")
        f.write("=" * 80 + "\n")
        f.write(user_prompt)
        f.write("\n\n" + "=" * 80 + "\n")
        f.write("CALLING test_scripts.llm_interface...\n")
        f.write("=" * 80 + "\n\n")

    print(f"Calling llm_interface (model: {model})...")

    MAX_RETRIES = 5
    RETRY_DELAY = 30
    content: Optional[str] = None
    meta: Any = None
    for attempt in range(1, MAX_RETRIES + 1):
        response_text, meta = llm_client.call_llm(combined_prompt)
        content_ok = bool(response_text and not response_text.strip().lower().startswith("error:"))
        if content_ok:
            content = response_text
            break

        error_message = response_text or "Empty response"
        with open(log_file, 'a', encoding='utf-8') as f:
            f.write(f"ERROR calling llm_interface (attempt {attempt}/{MAX_RETRIES}): {error_message}\n")

        if attempt < MAX_RETRIES:
            sleep_time = RETRY_DELAY * attempt
            with open(log_file, 'a', encoding='utf-8') as f:
                f.write(f"Retrying after {sleep_time}s...\n")
            time.sleep(sleep_time)

    if content is None:
        raise RuntimeError("llm_interface call failed after retries")

    with open(log_file, 'a', encoding='utf-8') as f:
        f.write("=" * 80 + "\n")
        f.write("RAW OUTPUT:\n")
        f.write("=" * 80 + "\n")
        f.write(content)
        f.write("\n\n")
        f.write("=" * 80 + "\n")
        f.write("LLM METADATA (stringified):\n")
        f.write("=" * 80 + "\n")
        f.write(str(meta))
        f.write("\n\n")

    code = content.strip()

    # Try to extract code from markdown code blocks (```python ... ```)
    # This handles cases where LLM outputs explanation text before/after the code
    code_block_pattern = r'```(?:python)?\s*\n(.*?)```'
    matches = re.findall(code_block_pattern, code, re.DOTALL)
    if matches:
        # Use the longest code block (likely the main solution)
        code = max(matches, key=len).strip()
    else:
        # Fallback: try simple stripping if no code blocks found
        if code.startswith("```python"):
            code = code[9:].strip()
        if code.startswith("```"):
            code = code[3:].strip()
        if code.endswith("```"):
            code = code[:-3].strip()

    # Log cleaned code
    with open(log_file, 'a', encoding='utf-8') as f:
        f.write("=" * 80 + "\n")
        f.write("CLEANED CODE (after removing markdown):\n")
        f.write("=" * 80 + "\n")
        f.write(code)
        f.write("\n\n")
        f.write("=" * 80 + "\n")
        f.write("END OF LOG\n")
        f.write("=" * 80 + "\n")

    return code


def create_solution(repo_root: Path, name: str, code: str) -> Path:
    sol_dir = repo_root / "solutions" / name
    res_dir = sol_dir / "resources"
    res_dir.mkdir(parents=True, exist_ok=True)

    # prepare_env.sh
    prep = sol_dir / "prepare_env.sh"
    prep.write_text(PREPARE_ENV_TEMPLATE.format(solution_name=name))
    prep.chmod(0o755)

    # solve.sh
    solve = sol_dir / "solve.sh"
    solve.write_text(SOLVE_TEMPLATE.format(solution_name=name))
    solve.chmod(0o755)

    # solution.py
    solution = res_dir / "solution.py"
    solution.write_text(SOLUTION_TEMPLATE.format(generated_code=code))

    return sol_dir


def get_problem_name(problem_path: Path) -> str:
    """
    Extract the problem name from the problem path.
    Returns just the problem identifier without any model prefix.
    Examples:
    - research/vdb_pareto/balanced -> vdb_pareto_balanced
    - research/cant_be_late_multi/high_availability_loose_deadline -> cant_be_late_multi_high_availability_loose_deadline
    """
    if problem_path.is_absolute():
        try:
            problem_path = problem_path.relative_to(problem_path.anchor)
        except ValueError:
            pass

    parts = [p for p in problem_path.parts if p and p != "problems"]
    if not parts:
        raise ValueError(f"Unable to derive problem name from '{problem_path}'")
    return "_".join(parts)


def main():
    base_dir = Path(__file__).parent
    repo_root = base_dir.parent  # Root of the repository
    ensure_numpy_version(REQUIRED_NUMPY_VERSION)
    load_env_file(base_dir / ".env")

    parser = argparse.ArgumentParser(description="Generate GPT solution from README")
    parser.add_argument("problem_path", nargs="?", help="Path to a single problem dir")
    # Mutually exclusive: prefer --model, otherwise read from models file
    model_group = parser.add_mutually_exclusive_group()
    model_group.add_argument("--model", help="Target model identifier (takes precedence if set)")
    model_group.add_argument("--models-file", help="Newline-delimited model list to evaluate")
    parser.add_argument("--api-key", help="API key value (overrides --api-key-env)")
    parser.add_argument("--api-key-env", help="Environment variable name that stores the API key")
    parser.add_argument("--api-base", default=os.getenv("MODEL_API_BASE", "https://api.openai.com/v1"),
                        help="Base URL for the API (default: https://api.openai.com/v1)")
    parser.add_argument("--endpoint", default=os.getenv("MODEL_API_ENDPOINT", "chat/completions"),
                        help="Informational endpoint hint recorded in logs (llm_interface uses provider defaults)")
    parser.add_argument("--api-key-header", default=os.getenv("MODEL_API_KEY_HEADER", "Authorization"),
                        help="Header used to send the API key (set to 'none' to omit)")
    parser.add_argument("--api-key-prefix", default=os.getenv("MODEL_API_KEY_PREFIX", "Bearer"),
                        help="Prefix applied before the API key value (use 'none' to disable)")
    parser.add_argument("--header", dest="extra_headers", action="append", default=[],
                        help="Additional HTTP header in Key:Value format (repeatable)")
    parser.add_argument("--temperature", type=float_or_none, default=0.7,
                        help="Sampling temperature or 'none' to omit")
    parser.add_argument("--max-tokens", type=int_or_none, default=65536,
                        help="Max completion tokens for standard models, or 'none'")
    parser.add_argument("--max-reasoning-tokens", type=int_or_none, default=65536,
                        help="Max completion tokens for reasoning models, or 'none'")
    parser.add_argument("--timeout", type=float, default=float(os.getenv("MODEL_API_TIMEOUT", "180")),
                        help="Request timeout in seconds (default: 180, override via MODEL_API_TIMEOUT)")
    parser.add_argument("--payload-extra",
                        help="JSON object reserved for LLM-specific overrides (currently ignored)")
    parser.add_argument("--reasoning-model", dest="reasoning_override", action="store_const", const=True, default=None,
                        help="Force treat the model as reasoning-style")
    parser.add_argument("--no-reasoning-model", dest="reasoning_override", action="store_const", const=False,
                        help="Force treat the model as standard (non-reasoning)")
    parser.add_argument("--force", action="store_true", help="Regenerate even if the solution directory already exists")
    parser.add_argument("--name", help="Solution name (auto-generated if not set)")
    parser.add_argument("--problem-list", dest="problem_list", help="File containing newline-separated problem directories")
    parser.add_argument("--solutions-file", help="File listing solution:problem entries to regenerate")
    parser.add_argument("--variants", type=int, default=None,
                        help="Number of solutions to generate per model. If omitted, read variant indices from num_solutions.txt")
    parser.add_argument("--concurrency", type=int, default=max(1, min(8, os.cpu_count() or 4)),
                        help="Maximum parallel generations (default: min(8, CPU count))")
    args = parser.parse_args()

    if not (args.problem_path or args.problem_list or args.solutions_file):
        # Default to problems.txt in repo if present
        default_list = (base_dir / "problems.txt")
        if default_list.is_file():
            args.problem_list = str(default_list)
            print(f"No problem targets provided; defaulting to {default_list}.")
        else:
            print("ERROR: Provide a problem path, --problem-list, or --solutions-file (and problems.txt not found)")
            sys.exit(1)

    endpoint_hint_normalized = (args.endpoint or "").strip().lower()
    if endpoint_hint_normalized not in {"", "chat/completions", "auto"}:
        print("NOTE: --endpoint is informational only; llm_interface selects the actual API path internally.")

    try:
        extra_headers = parse_extra_headers(args.extra_headers)
    except ValueError as exc:
        print(f"ERROR: {exc}")
        sys.exit(1)

    try:
        payload_overrides = load_json_args(args.payload_extra)
    except ValueError as exc:
        print(f"ERROR: {exc}")
        sys.exit(1)

    default_api_key = resolve_api_key(args.api_key, args.api_key_env)
    if args.api_key_env and args.api_key is None and default_api_key is None:
        print(f"WARNING: Environment variable {args.api_key_env} is not set; proceeding without API key.")

    api_key_header = args.api_key_header
    if api_key_header:
        if api_key_header.lower() == "none":
            api_key_header = None
        else:
            api_key_header = api_key_header.strip() or None

    api_key_prefix = args.api_key_prefix
    if api_key_prefix:
        if api_key_prefix.lower() == "none":
            api_key_prefix = None
        else:
            api_key_prefix = api_key_prefix.strip()

    if args.variants is not None and args.variants < 1:
        print("ERROR: --variants must be >= 1")
        sys.exit(1)

    if args.concurrency < 1:
        print("ERROR: --concurrency must be >= 1")
        sys.exit(1)

    problem_sources: List[Tuple[Path, str]] = []

    if args.problem_list:
        list_path = Path(args.problem_list)
        if not list_path.is_absolute():
            list_path = base_dir / list_path
        if not list_path.is_file():
            print(f"ERROR: Problem list file {list_path} not found")
            sys.exit(1)
        for raw_line in list_path.read_text(encoding="utf-8").splitlines():
            stripped = raw_line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            problem_sources.append((Path(stripped), stripped))

    if args.problem_path:
        problem_sources.append((Path(args.problem_path), args.problem_path))

    if not problem_sources and not args.solutions_file:
        print("ERROR: No valid problem paths provided")
        sys.exit(1)

    # de-duplicate while preserving order
    seen_problems: set[str] = set()
    normalized_problems: List[Tuple[Path, str]] = []
    if problem_sources:
        for path_obj, display in problem_sources:
            key = display
            if key in seen_problems:
                continue
            seen_problems.add(key)
            if not path_obj.is_absolute():
                resolved = base_dir / path_obj
            else:
                resolved = path_obj
            normalized_problems.append((resolved, display))

    if args.name and not args.solutions_file and len(normalized_problems) != 1:
        print("ERROR: --name can only be used when generating a single problem")
        sys.exit(1)

    # Create logs directory
    logs_dir = repo_root / "generation_logs"
    logs_dir.mkdir(exist_ok=True)

    # Resolve model selection precedence
    models_source_desc = ""
    if args.model:
        models_list = [args.model]
        print(f"Using model from --model: {args.model}")
        models_source_desc = f"--model ({args.model})"
    else:
        # If --models-file not provided, default to repo models.txt
        models_path = Path(args.models_file) if args.models_file else base_dir / "models.txt"
        if not models_path.is_absolute():
            models_path = base_dir / models_path
        models_list = read_models_file(models_path)
        if models_list:
            print(f"Detected {len(models_list)} models from {models_path}.")
            models_source_desc = f"models.txt ({models_path})"
        else:
            print(f"WARNING: Models file {models_path} not found or empty; falling back to default model 'gpt-4o'.")
            models_list = ["gpt-4o"]
            models_source_desc = f"fallback (gpt-4o)"

    provider_key_pools = _build_key_pools(default_api_key)
    if provider_key_pools:
        for provider, pool in provider_key_pools.items():
            print(f"Loaded {pool.size()} API key(s) for provider '{provider}'.")
    else:
        print("WARNING: No provider API key pools detected; falling back to default environment variables.")

    prefix_to_model: Dict[str, str] = {}
    for model in models_list:
        prefix = get_model_prefix(model)
        if prefix in prefix_to_model and prefix_to_model[prefix] != model:
            print(f"WARNING: Multiple models map to prefix '{prefix}'. Using {prefix_to_model[prefix]}.")
            continue
        prefix_to_model[prefix] = model

    solution_targets: List[Tuple[str, str]] = []
    solutions_path: Optional[Path] = None
    if args.solutions_file:
        solutions_path = Path(args.solutions_file)
        if not solutions_path.is_absolute():
            solutions_path = base_dir / solutions_path
        try:
            solution_targets = load_solution_targets(solutions_path)
            print(f"Loaded {len(solution_targets)} target solution(s) from {solutions_path}.")
        except Exception as exc:
            print(f"ERROR: {exc}")
            sys.exit(1)

    generated: List[str] = []
    skipped: List[str] = []
    failed: List[str] = []
    tasks: List[GenerationTask] = []

    if solution_targets:
        print(
            "[CONFIG] mode=solutions-file | "
            f"solutions_file={solutions_path} | models={models_source_desc} | "
            f"concurrency={args.concurrency} | force={'yes' if args.force else 'no'}"
        )
        problem_cache: Dict[str, Tuple[Path, str, str]] = {}
        for solution_name, problem_entry in solution_targets:
            model_prefix = solution_name.split("_", 1)[0]
            model = prefix_to_model.get(model_prefix)
            if not model:
                print(f"WARNING: No model mapping found for solution prefix '{model_prefix}'; skipping {solution_name}.")
                continue

            provider = _detect_provider(model)

            if problem_entry.startswith("research/"):
                relative_problem_str = problem_entry
            else:
                relative_problem_str = f"research/{problem_entry.lstrip('./')}"

            try:
                problem_path_real = (base_dir / relative_problem_str).resolve()
            except Exception:
                print(f"WARNING: Invalid problem path '{problem_entry}' for {solution_name}; skipping.")
                continue

            if not problem_path_real.is_dir():
                print(f"WARNING: Problem path {problem_path_real} not found; skipping {solution_name}.")
                continue

            cache_key = relative_problem_str
            if cache_key not in problem_cache:
                try:
                    readme_text = read_readme(problem_path_real)
                except FileNotFoundError as exc:
                    print(f"WARNING: {exc}; skipping {solution_name}.")
                    continue
                try:
                    rel_path_for_name = problem_path_real.relative_to(base_dir)
                except ValueError:
                    rel_path_for_name = Path(problem_path_real.name)
                problem_name = get_problem_name(rel_path_for_name)
                problem_cache[cache_key] = (problem_path_real, readme_text, problem_name)

            problem_path_real, readme_text, inferred_problem_name = problem_cache[cache_key]

            tail_parts = solution_name.rsplit("_", 1)
            variant_index = 0
            if len(tail_parts) == 2 and tail_parts[1].isdigit():
                variant_index = int(tail_parts[1])
            total_variants_for_task = max(variant_index + 1, 1)

            sol_dir = repo_root / "solutions" / solution_name
            if sol_dir.exists():
                if args.force:
                    try:
                        shutil.rmtree(sol_dir)
                    except Exception as exc:
                        print(
                            f"WARNING: Failed to remove existing solution directory {sol_dir}: {exc}; skipping",
                            file=sys.stderr,
                        )
                        skipped.append(solution_name)
                        continue
                else:
                    print(
                        f"WARNING: Solution '{solution_name}' already exists at {sol_dir}. "
                        "Skipping generation (rerun with --force to regenerate).",
                        file=sys.stderr,
                    )
                    skipped.append(solution_name)
                    continue

            tasks.append(
                GenerationTask(
                    problem_path=problem_path_real,
                    display_path=problem_entry,
                    problem_name=inferred_problem_name,
                    readme=readme_text,
                    model=model,
                    provider=provider,
                    reasoning_model=is_reasoning(model, args.reasoning_override),
                    variant_index=variant_index,
                    variant_position=variant_index,  # position not available; use index for label
                    solution_name=solution_name,
                    total_variants=total_variants_for_task,
                )
            )
    else:
        # Determine variant indices to generate per problem when not using --solutions-file
        variants_file = base_dir / "num_solutions.txt"
        variant_indices: List[int]
        if args.variants is None:
            try:
                variant_indices = read_variant_indices_file(variants_file)
            except Exception as exc:
                print(f"WARNING: Failed to read {variants_file}: {exc}; defaulting to [0]")
                variant_indices = [0]
        else:
            variant_indices = list(range(args.variants))

        # Config summary in problem-list mode
        problems_file_hint = args.problem_list or (base_dir / "problems.txt")
        print(
            "[CONFIG] mode=problem-list | "
            f"problems_file={problems_file_hint} (count={len(normalized_problems)}) | "
            f"models={models_source_desc} (count={len(models_list)}) | "
            f"variants_file={variants_file} indices={variant_indices} | "
            f"concurrency={args.concurrency} | force={'yes' if args.force else 'no'}"
        )

        for problem_path_real, display_path in normalized_problems:
            if not problem_path_real.is_dir():
                print(f"WARNING: Problem path {problem_path_real} not found; skipping")
                continue

            try:
                readme = read_readme(problem_path_real)
            except FileNotFoundError as exc:
                print(f"WARNING: {exc}; skipping {problem_path_real}")
                continue

            relative_problem_path = problem_path_real
            if problem_path_real.is_absolute():
                try:
                    relative_problem_path = problem_path_real.relative_to(base_dir)
                except ValueError:
                    relative_problem_path = Path(problem_path_real.name)

            problem_name = args.name or get_problem_name(relative_problem_path)

            for model in models_list:
                reasoning_model = is_reasoning(model, args.reasoning_override)
                model_prefix = get_model_prefix(model)
                provider = _detect_provider(model)

                for pos, variant_index in enumerate(variant_indices):
                    suffix = "" if variant_index == 0 else f"_{variant_index}"
                    solution_name = f"{model_prefix}_{problem_name}{suffix}"
                    sol_dir = repo_root / "solutions" / solution_name

                    if sol_dir.exists():
                        if args.force:
                            try:
                                shutil.rmtree(sol_dir)
                            except Exception as exc:
                                print(
                                    f"WARNING: Failed to remove existing solution directory {sol_dir}: {exc}; skipping",
                                    file=sys.stderr,
                                )
                                skipped.append(solution_name)
                                continue
                        else:
                            warning_msg = (
                                f"WARNING: Solution '{solution_name}' already exists at {sol_dir}. "
                                "Skipping generation (rerun with --force to regenerate)."
                            )
                            print(warning_msg, file=sys.stderr)
                            skipped.append(solution_name)
                            continue

                    tasks.append(
                        GenerationTask(
                            problem_path=problem_path_real,
                            display_path=display_path,
                            problem_name=problem_name,
                            readme=readme,
                            model=model,
                            provider=provider,
                            reasoning_model=reasoning_model,
                            variant_index=variant_index,
                            variant_position=pos,
                            solution_name=solution_name,
                            total_variants=len(variant_indices),
                        )
                    )

    total_tasks = len(tasks)
    if total_tasks == 0:
        print("No new tasks to generate.")
    else:
        print(
            f"Queued {total_tasks} generation task(s) across {len(models_list)} model(s) and {len(normalized_problems)} problem(s)."
        )

    def execute_task(task: GenerationTask) -> Tuple[str, str, Optional[str], str, Optional[int]]:
        variant_label = f"{task.variant_position + 1}/{task.total_variants}"
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        log_file = logs_dir / f"{task.solution_name}_{timestamp}.log"
        print(
            f"Generating {task.solution_name} (model: {task.model}, variant {variant_label}, problem: {task.display_path})..."
        )
        print(f"Log file: {log_file}")

        pool = provider_key_pools.get(task.provider)
        api_key_for_task: Optional[str] = None
        pool_token: Optional[int] = None

        if pool:
            api_key_for_task, pool_token = pool.acquire()
            if api_key_for_task is None:
                message = f"No available API key for provider {task.provider}; skipping."
                print(f"ERROR generating {task.solution_name}: {message}")
                return ("failed", task.solution_name, message, task.provider, None)
        else:
            candidate_keys: List[Optional[str]] = []
            if task.provider == "openai":
                candidate_keys.extend(
                    [
                        default_api_key,
                        os.getenv("OPENAI_API_KEY"),
                        os.getenv("OPENAI_API_KEY2"),
                        os.getenv("OPENAI_API_KEY_2"),
                    ]
                )
            elif task.provider == "openrouter":
                candidate_keys.extend(
                    [
                        os.getenv("OPENROUTER_API_KEY"),
                        os.getenv("OPENROUTER_API_KEY2"),
                        os.getenv("OPENROUTER_KEY"),
                    ]
                )
            elif task.provider == "google":
                candidate_keys.extend(
                    [
                        os.getenv("GOOGLE_API_KEY"),
                        os.getenv("GOOGLE_API_KEY2"),
                        os.getenv("GEMINI_API_KEY"),
                        os.getenv("GEMINI_API_KEY2"),
                    ]
                )
            elif task.provider == "anthropic":
                candidate_keys.extend(
                    [os.getenv("ANTHROPIC_API_KEY"), os.getenv("ANTHROPIC_API_KEY2")]
                )
            elif task.provider == "xai":
                candidate_keys.extend(
                    [
                        os.getenv("XAI_API_KEY"),
                        os.getenv("XAI_API_KEY2"),
                        os.getenv("GROK_API_KEY"),
                        os.getenv("GROK_API_KEY2"),
                    ]
                )
            api_key_for_task = next((k for k in candidate_keys if k), None)

        try:
            code = generate_code(
                task.readme,
                model=task.model,
                api_key=api_key_for_task,
                log_file=log_file,
                api_base=args.api_base,
                endpoint=args.endpoint,
                temperature=args.temperature,
                max_tokens=args.max_tokens,
                max_reasoning_tokens=args.max_reasoning_tokens,
                is_reasoning_model=task.reasoning_model,
                extra_headers=extra_headers,
                timeout=args.timeout,
                payload_overrides=payload_overrides,
                api_key_header=api_key_header,
                api_key_prefix=api_key_prefix,
                problem_name=task.problem_name,
                problem_path=task.problem_path,
            )
            sol_dir = create_solution(repo_root, task.solution_name, code)
            print(f"Created: {sol_dir}")
            print(f"Log saved: {log_file}")
            print(f"Add to pairs.txt: {task.solution_name}:{task.display_path}")
            return ("generated", task.solution_name, None, task.provider, pool_token)
        except Exception as exc:
            message = f"{exc} (log: {log_file})"
            print(f"ERROR generating {task.solution_name}: {exc}")
            return ("failed", task.solution_name, message, task.provider, pool_token)

    if total_tasks:
        max_workers = min(args.concurrency, total_tasks)
        print(f"Executing with concurrency={max_workers}...")
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_task = {executor.submit(execute_task, task): task for task in tasks}
            for future in as_completed(future_to_task):
                status, solution_name, error_text, provider, pool_token = future.result()
                pool = provider_key_pools.get(provider)
                if pool:
                    if status == "generated":
                        pool.report_success(pool_token)
                    else:
                        pool.report_failure(pool_token, error_text)
                if status == "generated":
                    generated.append(solution_name)
                else:
                    failed.append(solution_name if error_text is None else f"{solution_name} ({error_text})")

    print("\nSummary:")
    if generated:
        print(f"Generated {len(generated)} solution(s): {', '.join(generated)}")
    else:
        print("No new solutions generated.")
    if skipped:
        print(
            f"Skipped {len(skipped)} existing solution(s): {', '.join(skipped)}. "
            "Use --force to regenerate these."
        )
    if failed:
        print(f"Failed {len(failed)} solution(s): {', '.join(failed)}")



if __name__ == "__main__":
    main()
