"""Environment configuration for solution generation."""

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Optional

from frontier_cs.config import load_runtime_config, get_effective_gpu_type

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

# Base system prompt template - environment section will be injected
SYSTEM_PROMPT_TEMPLATE = """You are an expert programmer. Generate Python code for the given problem.

{environment_section}
REQUIREMENTS:
1. Output ONLY Python code - no explanations, no markdown
2. Implement ALL required classes/functions from the API section
3. Use efficient algorithms appropriate for the evaluation environment
4. Final class name must match the API specification exactly

Output ONLY the code, starting with imports."""


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
    cpu_spec = config.cpus or "8"
    mem_spec = config.memory or "16"

    cpu_display = _format_spec(cpu_spec)
    mem_display = _format_spec(mem_spec)

    lines = ["EVALUATION ENVIRONMENT:"]

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

    if config.instance_type:
        lines.append(f"- Instance: {config.instance_type}")

    lines.append(f"- GPU: {spec['name']} ({spec['vram']} VRAM)")

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


def load_env_config_from_problem(problem_path: Path) -> EnvConfig:
    """
    Load environment configuration from problem's config.yaml runtime section.

    Supported config.yaml runtime fields:
        - gpu_type: SkyPilot GPU type (e.g., "L4", "A100")
        - resources.accelerators: SkyPilot accelerators (e.g., "L4:1", "A100:4")
        - resources.cpus: CPU specification (e.g., "8", "8+")
        - resources.memory: Memory in GB (e.g., "32", "32+")
        - resources.disk_size: Disk size in GB
        - resources.instance_type: Cloud instance type
        - environment: Problem-specific environment description
    """
    env_config = EnvConfig()
    runtime_config = load_runtime_config(problem_path)

    gpu_type = get_effective_gpu_type(runtime_config)
    if gpu_type:
        env_config.gpu_type = gpu_type

    res = runtime_config.resources
    if res.cpus:
        env_config.cpus = res.cpus
    if res.memory:
        env_config.memory = res.memory
    if res.disk_size:
        env_config.disk_size = res.disk_size
    if res.instance_type:
        env_config.instance_type = res.instance_type

    if runtime_config.environment:
        env_config.environment = runtime_config.environment

    return env_config


def get_system_prompt_for_problem(
    problem_name: str,
    problem_path: Optional[Path] = None,
    docker_config: Optional[Dict] = None,
) -> str:
    """
    Build system prompt with environment info.

    Priority (with fallbacks):
    1. config.yaml runtime section -> Use specified values
    2. docker_images.txt GPU detection -> GPU with default config, or CPU
    3. Default CPU environment
    """
    env_config = EnvConfig()

    # Priority 1: Try to load config from config.yaml
    if problem_path and problem_path.is_dir():
        env_config = load_env_config_from_problem(problem_path)

    # Priority 2: Fallback to docker_images.txt for GPU detection
    if env_config.gpu_type is None and docker_config:
        base_name = problem_name.split("/")[0] if "/" in problem_name else problem_name
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
