"""
Configuration loading for problem runtime settings.

Loads and parses problem config.yaml files, including runtime resources
and docker configuration.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Optional

import yaml


DEFAULT_DOCKER_IMAGE = "python:3.11-slim-trixie"


@dataclass
class ResourcesConfig:
    """SkyPilot-compatible resources configuration."""

    accelerators: Optional[str] = None  # e.g., "L4:1", "A100:4"
    instance_type: Optional[str] = None  # e.g., "n1-standard-8"
    cpus: Optional[str] = None  # e.g., "8", "8+"
    memory: Optional[str] = None  # e.g., "32", "32+"
    disk_size: Optional[int] = None  # GB
    disk_tier: Optional[str] = None  # "high", "medium", "low"
    cloud: Optional[str] = None  # "gcp", "aws", "azure"
    region: Optional[str] = None
    image_id: Optional[str] = None  # VM image for SkyPilot

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dict, excluding None values."""
        return {k: v for k, v in vars(self).items() if v is not None}

    @property
    def has_gpu(self) -> bool:
        return self.accelerators is not None

    @property
    def gpu_type(self) -> Optional[str]:
        """Extract GPU type from accelerators (e.g., 'L4:1' -> 'L4')."""
        if not self.accelerators:
            return None
        return self.accelerators.split(":")[0]


@dataclass
class DockerConfig:
    """Docker configuration for running evaluations."""

    image: str = DEFAULT_DOCKER_IMAGE
    gpu: bool = False  # Whether to pass --gpus all
    dind: bool = False  # Docker-in-Docker (mount docker socket)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DockerConfig":
        """Create DockerConfig from a dictionary."""
        return cls(
            image=data.get("image", DEFAULT_DOCKER_IMAGE),
            gpu=bool(data.get("gpu", False)),
            dind=bool(data.get("dind", False)),
        )


@dataclass
class RuntimeConfig:
    """Complete runtime configuration from config.yaml."""

    timeout_seconds: Optional[int] = None
    requires_gpu: Optional[bool] = None
    resources: ResourcesConfig = field(default_factory=ResourcesConfig)
    docker: DockerConfig = field(default_factory=DockerConfig)
    environment: Optional[str] = None  # For LLM prompts


@dataclass
class ProblemConfig:
    """Full problem configuration from config.yaml."""

    tag: Optional[str] = None  # Problem category: os, hpc, ai, db, pl, security
    runtime: RuntimeConfig = field(default_factory=RuntimeConfig)
    dependencies: Dict[str, Any] = field(default_factory=dict)


def load_problem_config(problem_path: Path) -> ProblemConfig:
    """
    Load full problem configuration from config.yaml.

    Example config.yaml:
    ```yaml
    tag: hpc
    runtime:
      timeout_seconds: 1800
      docker:
        image: andylizf/triton-tlx:tlx-nv-cu122
        gpu: true
      resources:
        accelerators: "L4:1"
        cpus: "8+"
    ```
    """
    config_file = problem_path / "config.yaml"
    problem_config = ProblemConfig()

    if not config_file.exists():
        return problem_config

    try:
        with open(config_file, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f) or {}
    except Exception:
        return problem_config

    # Parse tag
    if config.get("tag"):
        problem_config.tag = str(config["tag"])

    # Parse dependencies (datasets are handled by set_up_env.sh, not framework)
    problem_config.dependencies = config.get("dependencies", {})

    # Parse runtime section
    runtime = config.get("runtime", {})
    rt = problem_config.runtime

    if runtime.get("timeout_seconds"):
        rt.timeout_seconds = int(runtime["timeout_seconds"])
    if runtime.get("requires_gpu") is not None:
        rt.requires_gpu = bool(runtime["requires_gpu"])
    if runtime.get("environment"):
        rt.environment = str(runtime["environment"])

    # Parse docker section
    docker = runtime.get("docker", {})
    if docker:
        rt.docker = DockerConfig.from_dict(docker)
    elif runtime.get("requires_gpu"):
        # Legacy: if requires_gpu is set but no docker config, assume GPU needed
        rt.docker.gpu = True

    # Parse resources section
    resources = runtime.get("resources", {})
    if resources:
        res = rt.resources
        for key in ["accelerators", "instance_type", "cpus", "memory", "disk_tier", "cloud", "region", "image_id"]:
            if resources.get(key):
                setattr(res, key, str(resources[key]))
        if resources.get("disk_size"):
            res.disk_size = int(resources["disk_size"])

    return problem_config


def load_runtime_config(problem_path: Path) -> RuntimeConfig:
    """Load runtime configuration from problem's config.yaml."""
    return load_problem_config(problem_path).runtime


def load_docker_config_from_yaml(problem_path: Path) -> DockerConfig:
    """Load docker configuration from problem's config.yaml."""
    return load_problem_config(problem_path).runtime.docker


def get_effective_gpu_type(runtime_config: RuntimeConfig) -> Optional[str]:
    """
    Get effective GPU type from runtime config.

    Priority:
    1. resources.accelerators (extract type, e.g., "L4:1" -> "L4")
    2. docker.gpu flag (returns default "L4" if True)
    3. requires_gpu flag (returns default "L4" if True)
    4. None (CPU only)
    """
    # Check accelerators first
    if runtime_config.resources.accelerators:
        return runtime_config.resources.gpu_type

    # Check docker GPU flag
    if runtime_config.docker.gpu:
        return "L4"  # Default GPU type

    # Check legacy requires_gpu
    if runtime_config.requires_gpu:
        return "L4"

    return None
