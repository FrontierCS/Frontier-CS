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

    @abstractmethod
    def evaluate(
        self,
        problem_id: str,
        solution_code: str,
        *,
        timeout: Optional[int] = None,
    ) -> EvaluationResult:
        """
        Evaluate a solution for a given problem.

        Args:
            problem_id: Problem identifier (e.g., "flash_attn", "gemm_optimization/squares")
            solution_code: Solution source code
            timeout: Optional timeout in seconds

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
        timeout: Optional[int] = None,
        solution_id: Optional[str] = None,
    ) -> EvaluationResult:
        """
        Evaluate a solution file for a given problem.

        Args:
            problem_id: Problem identifier
            solution_path: Path to solution file
            timeout: Optional timeout in seconds
            solution_id: Optional solution identifier (for result tracking)

        Returns:
            EvaluationResult with score and status
        """
        pass

    def get_problem_path(self, problem_id: str) -> Path:
        """Get the path to a problem directory."""
        # Will be implemented by subclasses based on their base directory
        raise NotImplementedError
