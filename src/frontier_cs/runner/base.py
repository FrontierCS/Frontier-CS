"""
Abstract base class for evaluation runners.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
import json
from pathlib import Path
from typing import Any, Dict, Optional

from ..config import load_problem_config, ResourceSignature
from ..gen.solution_format import FAILED_EXTENSION

class EvaluationStatus(Enum):
    """Status of an evaluation."""
    SUCCESS = "success"
    ERROR = "error"
    TIMEOUT = "timeout"
    SKIPPED = "skipped"


@dataclass
class EvaluationResult:
    """Result of an evaluation run."""

    problem_id: str
    score: Optional[float] = None
    score_unbounded: Optional[float] = None  # For algorithmic problems with unbounded scoring
    status: EvaluationStatus = EvaluationStatus.SUCCESS
    message: Optional[str] = None
    logs: Optional[str] = None
    duration_seconds: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def success(self) -> bool:
        return self.status == EvaluationStatus.SUCCESS

    def __repr__(self) -> str:
        if self.success:
            return f"EvaluationResult(problem={self.problem_id}, score={self.score})"
        return f"EvaluationResult(problem={self.problem_id}, status={self.status.value}, message={self.message})"


class Runner(ABC):
    """Abstract base class for evaluation runners."""

    # Default timeout in seconds. Subclasses can override.
    DEFAULT_TIMEOUT: int = 1000  # ~17 minutes

    @abstractmethod
    def evaluate(
        self,
        problem_id: str,
        solution_code: str,
    ) -> EvaluationResult:
        """
        Evaluate a solution for a given problem.

        Args:
            problem_id: Problem identifier (e.g., "flash_attn", "gemm_optimization/squares")
            solution_code: Solution source code

        Returns:
            EvaluationResult with score and status
        """
        pass

    @abstractmethod
    def evaluate_file(
        self,
        problem_id: str,
        solution_path: Path,
        *,
        solution_id: Optional[str] = None,
    ) -> EvaluationResult:
        """
        Evaluate a solution file for a given problem.

        Args:
            problem_id: Problem identifier
            solution_path: Path to solution file
            solution_id: Optional solution identifier (for result tracking)

        Returns:
            EvaluationResult with score and status
        """
        pass

    def get_problem_path(self, problem_id: str) -> Path:
        """Get the path to a problem directory."""
        # Will be implemented by subclasses based on their base directory
        raise NotImplementedError


class ResearchRunner(Runner):
    """Base class for research problem runners (Docker and SkyPilot).

    Provides common functionality:
    - base_dir and problems_dir initialization
    - get_problem_path() implementation
    - get_resource_signature() for cluster pooling
    """

    # Default cloud provider. Subclasses (e.g., SkyPilot runner) can override.
    cloud: str = "gcp"

    def __init__(
        self,
        base_dir: Optional[Path] = None,
        problems_dir: Optional[Path] = None,
    ):
        self.base_dir = base_dir or self._find_base_dir()
        self.research_dir = self.base_dir / "research"
        self.problems_dir = Path(problems_dir) if problems_dir else (self.research_dir / "problems")

    def _find_base_dir(self) -> Path:
        """Find the Frontier-CS base directory."""
        # src/frontier_cs/runner/*.py -> repo root
        base = Path(__file__).parents[3]
        if not (base / "research").is_dir():
            raise RuntimeError(f"research/ not found in {base}")
        return base

    def get_problem_path(self, problem_id: str) -> Path:
        """Get the path to a research problem directory.

        With nested solution structure, problem_id is already the nested path
        (e.g., "cant_be_late/high_availability_loose_deadline_large_overhead").
        """
        return self.problems_dir / problem_id

    def _get_problem_path_or_error(
        self, problem_id: str
    ) -> tuple[Optional[Path], Optional[EvaluationResult]]:
        problem_path = self.get_problem_path(problem_id)
        if not problem_path.exists():
            return (
                None,
                EvaluationResult(
                    problem_id=problem_id,
                    status=EvaluationStatus.ERROR,
                    message=f"Problem not found: {problem_path}",
                ),
            )
        return (problem_path, None)

    def _validate_solution_file(
        self, problem_id: str, solution_path: Path
    ) -> Optional[EvaluationResult]:
        if not solution_path.exists():
            return EvaluationResult(
                problem_id=problem_id,
                status=EvaluationStatus.ERROR,
                message=f"Solution file not found: {solution_path}",
            )

        if solution_path.suffix == f".{FAILED_EXTENSION}":
            try:
                meta = json.loads(solution_path.read_text(encoding="utf-8"))
                error_msg = meta.get("error", "Generation failed")
            except (json.JSONDecodeError, OSError):
                error_msg = "Generation failed"
            return EvaluationResult(
                problem_id=problem_id,
                status=EvaluationStatus.ERROR,
                score=0,
                message=f"Generation failed: {error_msg}",
            )

        return None

    def _load_runtime_settings(self, problem_path: Path) -> dict:
        problem_config = load_problem_config(problem_path)
        runtime_config = problem_config.runtime
        docker_config = runtime_config.docker
        uv_project = problem_config.dependencies.get("uv_project")
        return {
            "problem_config": problem_config,
            "runtime": runtime_config,
            "docker": docker_config,
            "uv_project": uv_project,
            "timeout_seconds": runtime_config.timeout_seconds,
        }

    def get_resource_signature(self, problem_id: str) -> ResourceSignature:
        """Get the resource signature for a problem.

        Used for cluster pooling in batch evaluation - problems with the same
        signature can share clusters.

        Args:
            problem_id: Problem ID (e.g., "nbody_simulation/random_100k")

        Returns:
            ResourceSignature identifying the cluster resource requirements
        """
        problem_path = self.problems_dir / problem_id
        settings = self._load_runtime_settings(problem_path)
        return ResourceSignature.from_resources(settings["runtime"].resources, self.cloud)

    def _build_uv_install_cmd(self, uv_project: Optional[str]) -> str:
        if not uv_project:
            return "# No uv_project specified in config.yaml"

        return (
            f'if [ -d "{uv_project}" ] && [ -f "{uv_project}/pyproject.toml" ]; then\n'
            f'    echo "[framework] Installing dependencies from {uv_project}"\n'
            f'    if [ -f "{uv_project}/uv_overrides.txt" ]; then\n'
            f'        uv pip install --system --overrides "{uv_project}/uv_overrides.txt" -e "{uv_project}"\n'
            f'    else\n'
            f'        uv pip install --system -e "{uv_project}"\n'
            f'    fi\n'
            f'fi'
        )

    def _build_timeout_prefix(self, timeout_seconds: Optional[int]) -> str:
        return f"timeout {timeout_seconds}s " if timeout_seconds else ""
