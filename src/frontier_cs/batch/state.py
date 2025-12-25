"""
Persistent state tracking for incremental batch evaluation.

Tracks completed pairs to enable resume functionality.
"""

import json
import csv
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Set

from .pair import Pair


@dataclass
class PairResult:
    """Result of evaluating a single pair."""

    pair_id: str  # "solution:problem"
    score: Optional[float] = None
    status: str = "pending"  # pending, running, success, error, timeout, skipped
    message: Optional[str] = None
    duration_seconds: Optional[float] = None
    timestamp: Optional[str] = None

    @property
    def is_complete(self) -> bool:
        """Whether this pair has a valid result (success with score)."""
        return self.status == "success" and self.score is not None

    @property
    def is_success(self) -> bool:
        return self.status == "success"


@dataclass
class EvaluationState:
    """
    Persistent state for batch evaluation.

    Tracks which pairs have been evaluated, their results, and metadata.
    """

    results: Dict[str, PairResult] = field(default_factory=dict)
    started_at: Optional[str] = None
    updated_at: Optional[str] = None
    total_pairs: int = 0
    backend: str = "docker"  # docker or skypilot
    config: Dict = field(default_factory=dict)  # Evaluation configuration

    @classmethod
    def load(cls, path: Path) -> "EvaluationState":
        """Load state from a JSON file."""
        if not path.exists():
            return cls()

        try:
            with path.open("r", encoding="utf-8") as f:
                data = json.load(f)
        except (json.JSONDecodeError, IOError):
            return cls()

        state = cls(
            started_at=data.get("started_at"),
            updated_at=data.get("updated_at"),
            total_pairs=data.get("total_pairs", 0),
            backend=data.get("backend", "docker"),
            config=data.get("config", {}),
        )

        # Load results
        for pair_id, result_data in data.get("results", {}).items():
            state.results[pair_id] = PairResult(
                pair_id=pair_id,
                score=result_data.get("score"),
                status=result_data.get("status", "pending"),
                message=result_data.get("message"),
                duration_seconds=result_data.get("duration_seconds"),
                timestamp=result_data.get("timestamp"),
            )

        return state

    def save(self, path: Path) -> None:
        """Save state to a JSON file."""
        self.updated_at = datetime.now().isoformat()

        data = {
            "started_at": self.started_at,
            "updated_at": self.updated_at,
            "total_pairs": self.total_pairs,
            "backend": self.backend,
            "config": self.config,
            "results": {
                pair_id: {
                    "score": r.score,
                    "status": r.status,
                    "message": r.message,
                    "duration_seconds": r.duration_seconds,
                    "timestamp": r.timestamp,
                }
                for pair_id, r in self.results.items()
            },
        }

        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    def get_pending_pairs(self, pairs: List[Pair]) -> List[Pair]:
        """Get pairs that haven't been successfully evaluated yet."""
        return [p for p in pairs if not self.is_complete(p)]

    def is_complete(self, pair: Pair) -> bool:
        """Check if a pair has been evaluated."""
        result = self.results.get(pair.id)
        return result is not None and result.is_complete

    def mark_running(self, pair: Pair) -> None:
        """Mark a pair as currently running."""
        self.results[pair.id] = PairResult(
            pair_id=pair.id,
            status="running",
            timestamp=datetime.now().isoformat(),
        )

    def record_result(
        self,
        pair: Pair,
        score: Optional[float],
        status: str,
        message: Optional[str] = None,
        duration_seconds: Optional[float] = None,
    ) -> None:
        """Record the result of evaluating a pair."""
        self.results[pair.id] = PairResult(
            pair_id=pair.id,
            score=score,
            status=status,
            message=message,
            duration_seconds=duration_seconds,
            timestamp=datetime.now().isoformat(),
        )

    @property
    def completed_count(self) -> int:
        """Number of completed evaluations."""
        return sum(1 for r in self.results.values() if r.is_complete)

    @property
    def success_count(self) -> int:
        """Number of successful evaluations."""
        return sum(1 for r in self.results.values() if r.is_success)

    @property
    def error_count(self) -> int:
        """Number of failed evaluations."""
        return sum(1 for r in self.results.values() if r.status in ("error", "timeout"))

    def export_csv(self, path: Path) -> None:
        """Export results to a CSV file."""
        path.parent.mkdir(parents=True, exist_ok=True)

        with path.open("w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["solution", "problem", "score", "status", "message", "duration_seconds", "timestamp"])

            for pair_id, result in sorted(self.results.items()):
                solution, problem = pair_id.split(":", 1)
                writer.writerow([
                    solution,
                    problem,
                    result.score if result.score is not None else "",
                    result.status,
                    result.message or "",
                    result.duration_seconds or "",
                    result.timestamp or "",
                ])

    def export_summary(self, path: Path) -> None:
        """Export a human-readable summary."""
        path.parent.mkdir(parents=True, exist_ok=True)

        lines = [
            f"Evaluation Summary - {datetime.now().isoformat()}",
            "=" * 50,
            f"Total pairs: {self.total_pairs}",
            f"Completed: {self.completed_count}",
            f"Successful: {self.success_count}",
            f"Errors: {self.error_count}",
            "",
            "Results:",
            "-" * 50,
        ]

        for pair_id, result in sorted(self.results.items()):
            solution, problem = pair_id.split(":", 1)
            if result.is_success:
                lines.append(f"{solution} -> {problem}: {result.score}")
            else:
                lines.append(f"{solution} -> {problem}: {result.status} - {result.message or 'N/A'}")

        path.write_text("\n".join(lines), encoding="utf-8")

    def export_failed(self, path: Path) -> int:
        """Export failed pairs to a file (solution:problem format). Returns count."""
        path.parent.mkdir(parents=True, exist_ok=True)
        failed = [
            pair_id for pair_id, r in self.results.items()
            if r.status in ("error", "timeout")
        ]
        path.write_text("\n".join(sorted(failed)) + "\n" if failed else "", encoding="utf-8")
        return len(failed)

    def export_pending(self, path: Path, all_pairs: Optional[List[Pair]] = None) -> int:
        """Export pending/incomplete pairs. Returns count."""
        path.parent.mkdir(parents=True, exist_ok=True)
        if all_pairs:
            # Export pairs not in results or not complete
            pending = [p.id for p in all_pairs if not self.is_complete(p)]
        else:
            # Export pairs that are in results but not complete
            pending = [
                pair_id for pair_id, r in self.results.items()
                if not r.is_complete
            ]
        path.write_text("\n".join(sorted(pending)) + "\n" if pending else "", encoding="utf-8")
        return len(pending)

    def export_skipped(self, path: Path) -> int:
        """Export skipped pairs. Returns count."""
        path.parent.mkdir(parents=True, exist_ok=True)
        skipped = [
            pair_id for pair_id, r in self.results.items()
            if r.status == "skipped"
        ]
        path.write_text("\n".join(sorted(skipped)) + "\n" if skipped else "", encoding="utf-8")
        return len(skipped)

    def get_failed_pairs(self) -> List[Pair]:
        """Get list of failed pairs."""
        return [
            Pair(solution=pair_id.split(":")[0], problem=pair_id.split(":")[1])
            for pair_id, r in self.results.items()
            if r.status in ("error", "timeout")
        ]

    def get_successful_pairs(self) -> List[Pair]:
        """Get list of successful pairs."""
        return [
            Pair(solution=pair_id.split(":")[0], problem=pair_id.split(":")[1])
            for pair_id, r in self.results.items()
            if r.is_success
        ]

    def aggregate_by_model(self) -> Dict[str, Dict[str, any]]:
        """Aggregate results by model (solution prefix before first _)."""
        by_model: Dict[str, List[PairResult]] = {}
        for pair_id, result in self.results.items():
            solution = pair_id.split(":")[0]
            # Extract model prefix (e.g., "gpt5_flash_attn" -> "gpt5")
            model = solution.split("_")[0] if "_" in solution else solution
            if model not in by_model:
                by_model[model] = []
            by_model[model].append(result)

        aggregated = {}
        for model, results in by_model.items():
            successful = [r for r in results if r.is_success]
            scores = [r.score for r in successful if r.score is not None]
            aggregated[model] = {
                "total": len(results),
                "successful": len(successful),
                "failed": len(results) - len(successful),
                "avg_score": sum(scores) / len(scores) if scores else None,
                "min_score": min(scores) if scores else None,
                "max_score": max(scores) if scores else None,
            }
        return aggregated

    def aggregate_by_problem(self) -> Dict[str, Dict[str, any]]:
        """Aggregate results by problem."""
        by_problem: Dict[str, List[PairResult]] = {}
        for pair_id, result in self.results.items():
            problem = pair_id.split(":")[1]
            if problem not in by_problem:
                by_problem[problem] = []
            by_problem[problem].append(result)

        aggregated = {}
        for problem, results in by_problem.items():
            successful = [r for r in results if r.is_success]
            scores = [r.score for r in successful if r.score is not None]
            aggregated[problem] = {
                "total": len(results),
                "successful": len(successful),
                "failed": len(results) - len(successful),
                "avg_score": sum(scores) / len(scores) if scores else None,
                "min_score": min(scores) if scores else None,
                "max_score": max(scores) if scores else None,
            }
        return aggregated

    def export_aggregated_csv(self, path: Path, by: str = "model") -> None:
        """Export aggregated results to CSV (by 'model' or 'problem')."""
        path.parent.mkdir(parents=True, exist_ok=True)

        if by == "model":
            data = self.aggregate_by_model()
            key_name = "model"
        else:
            data = self.aggregate_by_problem()
            key_name = "problem"

        with path.open("w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow([key_name, "total", "successful", "failed", "avg_score", "min_score", "max_score"])
            for key, stats in sorted(data.items()):
                writer.writerow([
                    key,
                    stats["total"],
                    stats["successful"],
                    stats["failed"],
                    f"{stats['avg_score']:.4f}" if stats["avg_score"] is not None else "",
                    stats["min_score"] if stats["min_score"] is not None else "",
                    stats["max_score"] if stats["max_score"] is not None else "",
                ])
