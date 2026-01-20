"""
Persistent state tracking for incremental batch evaluation.

Tracks completed pairs to enable resume functionality.
Supports hash-based cache invalidation for solutions and problems.
"""

import hashlib
import json
import csv
import tempfile
import os
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

from .pair import Pair
from ..gen.solution_format import parse_solution_filename


def hash_file(path: Path) -> str:
    """Compute SHA256 hash of a file."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()[:16]  # Use first 16 chars for brevity


def hash_directory(path: Path, extensions: Optional[Set[str]] = None) -> str:
    """
    Compute hash of all relevant files in a directory.

    Args:
        path: Directory path
        extensions: File extensions to include (default: common code/config files)

    Returns:
        Combined hash of all file contents and paths
    """
    if extensions is None:
        extensions = {".py", ".sh", ".yaml", ".yml", ".txt", ".json", ".md", ""}

    h = hashlib.sha256()
    files = []

    for p in sorted(path.rglob("*")):
        if not p.is_file():
            continue
        # Skip hidden files and __pycache__
        if any(part.startswith(".") or part == "__pycache__" for part in p.parts):
            continue
        # Filter by extension
        if extensions and p.suffix not in extensions:
            continue
        files.append(p)

    for p in files:
        # Include relative path in hash (so renames are detected)
        rel_path = p.relative_to(path)
        h.update(str(rel_path).encode("utf-8"))
        h.update(b"\x00")
        # Include file content
        try:
            with open(p, "rb") as f:
                for chunk in iter(lambda: f.read(8192), b""):
                    h.update(chunk)
        except (IOError, OSError):
            pass
        h.update(b"\x00")

    return h.hexdigest()[:16]


@dataclass
class PairResult:
    """Result of evaluating a single pair."""

    pair_id: str  # "solution:problem"
    score: Optional[float] = None
    score_unbounded: Optional[float] = None  # Unbounded score for algorithmic problems
    status: str = "pending"  # pending, running, success, error, timeout, skipped
    message: Optional[str] = None
    duration_seconds: Optional[float] = None
    timestamp: Optional[str] = None
    solution_hash: Optional[str] = None  # Hash of solution file
    problem_hash: Optional[str] = None   # Hash of problem directory

    @property
    def is_complete(self) -> bool:
        """Whether this pair has been evaluated (regardless of success/failure)."""
        # A pair is "complete" if it has any terminal status, not just success
        # This prevents automatic re-runs of errors - use --retry-failed for that
        return self.status in ("success", "error", "timeout", "skipped")

    @property
    def is_success(self) -> bool:
        return self.status == "success"

    def hashes_match(self, solution_hash: Optional[str], problem_hash: Optional[str]) -> bool:
        """Check if stored hashes match the provided hashes."""
        # If no hashes stored, consider it a match (backwards compatibility)
        if self.solution_hash is None and self.problem_hash is None:
            return True
        return self.solution_hash == solution_hash and self.problem_hash == problem_hash


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
                score_unbounded=result_data.get("score_unbounded"),
                status=result_data.get("status", "pending"),
                message=result_data.get("message"),
                duration_seconds=result_data.get("duration_seconds"),
                timestamp=result_data.get("timestamp"),
                solution_hash=result_data.get("solution_hash"),
                problem_hash=result_data.get("problem_hash"),
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
                    "score_unbounded": r.score_unbounded,
                    "status": r.status,
                    "message": r.message,
                    "duration_seconds": r.duration_seconds,
                    "timestamp": r.timestamp,
                    "solution_hash": r.solution_hash,
                    "problem_hash": r.problem_hash,
                }
                for pair_id, r in list(self.results.items())
            },
        }

        path.parent.mkdir(parents=True, exist_ok=True)

        # Atomic write: write to temp file, then rename
        # This prevents corruption from concurrent writes or crashes
        fd, tmp_path = tempfile.mkstemp(
            dir=path.parent,
            prefix=".state_tmp_",
            suffix=".json"
        )
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
            os.replace(tmp_path, path)  # Atomic on POSIX
        except:
            # Clean up temp file on error
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
            raise

    def get_pending_pairs(
        self,
        pairs: List[Pair],
        hashes: Optional[Dict[str, Tuple[str, str]]] = None,
    ) -> Tuple[List[Pair], List[Pair]]:
        """
        Get pairs that need evaluation.

        Args:
            pairs: List of pairs to check
            hashes: Optional dict mapping pair.id to (solution_hash, problem_hash)

        Returns:
            Tuple of (pending_pairs, invalidated_pairs)
            - pending_pairs: pairs that haven't been evaluated or have stale hashes
            - invalidated_pairs: subset of pending that were invalidated due to hash mismatch
        """
        pending = []
        invalidated = []

        for p in pairs:
            result = self.results.get(p.id)

            # Not evaluated yet
            if result is None or not result.is_complete:
                pending.append(p)
                continue

            # Check hash validity if hashes provided
            if hashes and p.id in hashes:
                sol_hash, prob_hash = hashes[p.id]
                if not result.hashes_match(sol_hash, prob_hash):
                    pending.append(p)
                    invalidated.append(p)

        return pending, invalidated

    def is_complete(self, pair: Pair, hashes: Optional[Tuple[str, str]] = None) -> bool:
        """
        Check if a pair has been evaluated with valid hashes.

        Args:
            pair: Pair to check
            hashes: Optional (solution_hash, problem_hash) tuple

        Returns:
            True if evaluated and hashes match (or no hashes to check)
        """
        result = self.results.get(pair.id)
        if result is None or not result.is_complete:
            return False

        if hashes:
            return result.hashes_match(hashes[0], hashes[1])

        return True

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
        solution_hash: Optional[str] = None,
        problem_hash: Optional[str] = None,
        score_unbounded: Optional[float] = None,
    ) -> None:
        """Record the result of evaluating a pair."""
        self.results[pair.id] = PairResult(
            pair_id=pair.id,
            score=score,
            score_unbounded=score_unbounded,
            status=status,
            message=message,
            duration_seconds=duration_seconds,
            timestamp=datetime.now().isoformat(),
            solution_hash=solution_hash,
            problem_hash=problem_hash,
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
            writer.writerow([
                "solution", "problem", "score", "score_unbounded", "status", "message",
                "duration_seconds", "timestamp", "solution_hash", "problem_hash"
            ])

            for pair_id, result in sorted(self.results.items()):
                solution, problem = pair_id.split(":", 1)
                writer.writerow([
                    solution,
                    problem,
                    f"{result.score:.3f}" if result.score is not None else "",
                    f"{result.score_unbounded:.3f}" if result.score_unbounded is not None else "",
                    result.status,
                    result.message or "",
                    f"{result.duration_seconds:.3f}" if result.duration_seconds else "",
                    result.timestamp or "",
                    result.solution_hash or "",
                    result.problem_hash or "",
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
        """
        Get list of pairs that should be retried.

        Includes both explicit failures (error/timeout) AND zero-score successes.

        !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
        !!! DO NOT CHANGE THIS LOGIC - IT IS INTENTIONAL !!!
        !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!

        We cannot reliably distinguish between:
        - A solution that legitimately scores 0
        - An evaluator bug that prints "0" before exit(1)
        - Infrastructure issues that cause 0 output

        Retrying zero-score results is the correct approach because:
        1. A truly zero-score solution will just score 0 again (no harm)
        2. A flaky failure will get a chance to succeed
        3. The cost of re-running is low compared to missing valid scores
        """
        return [
            Pair(solution=pair_id.split(":")[0], problem=pair_id.split(":")[1])
            for pair_id, r in self.results.items()
            if r.status in ("error", "timeout") or (r.is_success and r.score == 0)
        ]

    def get_successful_pairs(self) -> List[Pair]:
        """Get list of successful pairs."""
        return [
            Pair(solution=pair_id.split(":")[0], problem=pair_id.split(":")[1])
            for pair_id, r in self.results.items()
            if r.is_success
        ]

    def aggregate_by_model(
        self, valid_problems: Optional[Set[str]] = None
    ) -> Dict[str, Dict[str, any]]:
        """Aggregate results by model (solution prefix before first _).

        Args:
            valid_problems: If provided, only include results for these problems.
                           Orphaned results (problem no longer exists) are skipped.

        Returns metrics including:
            - total, successful, failed: raw counts
            - avg_score, min_score, max_score: simple aggregates
            - score_at_1: average of base variant (variant=0) scores across problems
            - avg_at_5: average of per-problem mean scores (across 5 variants)
            - score_at_5: average of per-problem max scores (across 5 variants)
            - pass_at_1: fraction of problems where base variant scores > 0
            - pass_at_5: fraction of problems where any variant scores > 0
        """
        # First pass: group by (model, problem, variant)
        # Structure: {model: {problem: {variant: score}}}
        by_model_problem: Dict[str, Dict[str, Dict[int, float]]] = {}
        by_model: Dict[str, List[PairResult]] = {}

        for pair_id, result in self.results.items():
            problem = pair_id.split(":")[1]
            # Skip orphaned results if valid_problems is provided
            if valid_problems is not None and problem not in valid_problems:
                continue

            solution = pair_id.split(":")[0]
            # Extract model and variant from nested path
            # Solution format: {problem}/{model}.ext or {problem}/{model}_{variant}.ext
            filename = Path(solution).name
            parsed = parse_solution_filename(filename)
            if parsed:
                model, variant, _ = parsed
            else:
                model = filename.rsplit(".", 1)[0]
                variant = 0

            # Collect for simple aggregation
            if model not in by_model:
                by_model[model] = []
            by_model[model].append(result)

            # Collect for @k metrics (only successful results with scores)
            if result.is_success and result.score is not None:
                score = max(0, min(100, result.score))  # Clamp to 0-100
                if model not in by_model_problem:
                    by_model_problem[model] = {}
                if problem not in by_model_problem[model]:
                    by_model_problem[model][problem] = {}
                by_model_problem[model][problem][variant] = score

        aggregated = {}
        for model, results in by_model.items():
            successful = [r for r in results if r.is_success]
            # Clamp bounded scores to 0-100 (some evaluators may return extreme values)
            scores = [max(0, min(100, r.score)) for r in successful if r.score is not None]
            unbounded = [r.score_unbounded for r in successful if r.score_unbounded is not None]

            # Compute @k metrics from per-problem variant scores
            score_at_1_list = []
            avg_at_5_list = []
            score_at_5_list = []
            pass_at_1_count = 0
            pass_at_5_count = 0
            total_problems = 0

            if model in by_model_problem:
                for problem, variant_scores in by_model_problem[model].items():
                    # Only count problems where we have the base variant (variant=0)
                    if 0 not in variant_scores:
                        continue
                    total_problems += 1

                    score1 = variant_scores.get(0, 0)
                    all_scores = [variant_scores.get(i, 0) for i in range(5)]

                    score_at_1_list.append(score1)
                    avg_at_5_list.append(sum(all_scores) / len(all_scores))
                    score_at_5_list.append(max(all_scores))

                    if score1 > 0:
                        pass_at_1_count += 1
                    if max(all_scores) > 0:
                        pass_at_5_count += 1

            aggregated[model] = {
                "total": len(results),
                "successful": len(successful),
                "failed": len(results) - len(successful),
                "avg_score": sum(scores) / len(scores) if scores else None,
                "min_score": min(scores) if scores else None,
                "max_score": max(scores) if scores else None,
                "avg_score_unbounded": sum(unbounded) / len(unbounded) if unbounded else None,
                "min_score_unbounded": min(unbounded) if unbounded else None,
                "max_score_unbounded": max(unbounded) if unbounded else None,
                # Paper metrics (@k)
                "score_at_1": sum(score_at_1_list) / len(score_at_1_list) if score_at_1_list else None,
                "avg_at_5": sum(avg_at_5_list) / len(avg_at_5_list) if avg_at_5_list else None,
                "score_at_5": sum(score_at_5_list) / len(score_at_5_list) if score_at_5_list else None,
                "pass_at_1": pass_at_1_count / total_problems if total_problems > 0 else None,
                "pass_at_5": pass_at_5_count / total_problems if total_problems > 0 else None,
                "num_problems": total_problems,
            }
        return aggregated

    def aggregate_by_problem(
        self, valid_problems: Optional[Set[str]] = None
    ) -> Dict[str, Dict[str, any]]:
        """Aggregate results by problem.

        Args:
            valid_problems: If provided, only include results for these problems.
                           Orphaned results (problem no longer exists) are skipped.
        """
        by_problem: Dict[str, List[PairResult]] = {}
        for pair_id, result in self.results.items():
            problem = pair_id.split(":")[1]
            # Skip orphaned results if valid_problems is provided
            if valid_problems is not None and problem not in valid_problems:
                continue
            if problem not in by_problem:
                by_problem[problem] = []
            by_problem[problem].append(result)

        aggregated = {}
        for problem, results in by_problem.items():
            successful = [r for r in results if r.is_success]
            # Clamp bounded scores to 0-100 (some evaluators may return extreme values)
            scores = [max(0, min(100, r.score)) for r in successful if r.score is not None]
            unbounded = [r.score_unbounded for r in successful if r.score_unbounded is not None]
            aggregated[problem] = {
                "total": len(results),
                "successful": len(successful),
                "failed": len(results) - len(successful),
                "avg_score": sum(scores) / len(scores) if scores else None,
                "min_score": min(scores) if scores else None,
                "max_score": max(scores) if scores else None,
                "avg_score_unbounded": sum(unbounded) / len(unbounded) if unbounded else None,
                "min_score_unbounded": min(unbounded) if unbounded else None,
                "max_score_unbounded": max(unbounded) if unbounded else None,
            }
        return aggregated

    def export_aggregated_csv(
        self, path: Path, by: str = "model", valid_problems: Optional[Set[str]] = None
    ) -> None:
        """Export aggregated results to CSV (by 'model' or 'problem').

        Args:
            path: Output CSV path
            by: Aggregation key - 'model' or 'problem'
            valid_problems: If provided, only include results for these problems.
                           Used to filter out orphaned results (results for problems
                           that have been restructured or removed from the filesystem).
        """
        path.parent.mkdir(parents=True, exist_ok=True)

        if by == "model":
            data = self.aggregate_by_model(valid_problems)
            key_name = "model"
            # Include paper metrics (@k) for model aggregation
            headers = [
                key_name, "total", "successful", "failed",
                "score_at_1", "avg_at_5", "score_at_5", "pass_at_1", "pass_at_5", "num_problems",
                "avg_score", "min_score", "max_score",
                "avg_score_unbounded", "min_score_unbounded", "max_score_unbounded"
            ]
        else:
            data = self.aggregate_by_problem(valid_problems)
            key_name = "problem"
            headers = [
                key_name, "total", "successful", "failed",
                "avg_score", "min_score", "max_score",
                "avg_score_unbounded", "min_score_unbounded", "max_score_unbounded"
            ]

        with path.open("w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(headers)
            for key, stats in sorted(data.items()):
                if by == "model":
                    writer.writerow([
                        key,
                        stats["total"],
                        stats["successful"],
                        stats["failed"],
                        f"{stats['score_at_1']:.2f}" if stats.get("score_at_1") is not None else "",
                        f"{stats['avg_at_5']:.2f}" if stats.get("avg_at_5") is not None else "",
                        f"{stats['score_at_5']:.2f}" if stats.get("score_at_5") is not None else "",
                        f"{stats['pass_at_1']:.4f}" if stats.get("pass_at_1") is not None else "",
                        f"{stats['pass_at_5']:.4f}" if stats.get("pass_at_5") is not None else "",
                        stats.get("num_problems", ""),
                        f"{stats['avg_score']:.3f}" if stats["avg_score"] is not None else "",
                        f"{stats['min_score']:.3f}" if stats["min_score"] is not None else "",
                        f"{stats['max_score']:.3f}" if stats["max_score"] is not None else "",
                        f"{stats['avg_score_unbounded']:.3f}" if stats.get("avg_score_unbounded") is not None else "",
                        f"{stats['min_score_unbounded']:.3f}" if stats.get("min_score_unbounded") is not None else "",
                        f"{stats['max_score_unbounded']:.3f}" if stats.get("max_score_unbounded") is not None else "",
                    ])
                else:
                    writer.writerow([
                        key,
                        stats["total"],
                        stats["successful"],
                        stats["failed"],
                        f"{stats['avg_score']:.3f}" if stats["avg_score"] is not None else "",
                        f"{stats['min_score']:.3f}" if stats["min_score"] is not None else "",
                        f"{stats['max_score']:.3f}" if stats["max_score"] is not None else "",
                        f"{stats['avg_score_unbounded']:.3f}" if stats.get("avg_score_unbounded") is not None else "",
                        f"{stats['min_score_unbounded']:.3f}" if stats.get("min_score_unbounded") is not None else "",
                        f"{stats['max_score_unbounded']:.3f}" if stats.get("max_score_unbounded") is not None else "",
                    ])
