"""
Abstract base class for evaluation runners.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, Optional


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
    """

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
