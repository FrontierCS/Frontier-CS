"""
Batch evaluator for running multiple evaluations with incremental progress.

Supports:
- Batch evaluation of multiple solution-problem pairs
- Incremental evaluation (resume from where you left off)
- Parallel execution (configurable concurrency)
- Both Docker and SkyPilot backends
- Bucket storage for results (S3/GCS)
- Progress bar with tqdm
- Export failed/pending/aggregated results
"""

import logging
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Callable, Iterator, List, Optional

try:
    from tqdm import tqdm
    HAS_TQDM = True
except ImportError:
    HAS_TQDM = False

from ..runner.base import EvaluationResult, EvaluationStatus
from ..runner.docker import DockerRunner
from .pair import Pair, expand_pairs, read_pairs_file, read_problems_file, read_models_file, read_variants_file
from .state import EvaluationState, PairResult

logger = logging.getLogger(__name__)


class BatchEvaluator:
    """
    Batch evaluator with incremental progress tracking.

    Example usage:
        # Evaluate all problems for a model
        evaluator = BatchEvaluator(results_dir="results/gpt5")
        evaluator.evaluate_model("gpt-5", problems=["flash_attn", "cross_entropy"])

        # Resume an interrupted evaluation
        evaluator = BatchEvaluator(results_dir="results/gpt5")
        evaluator.resume()

        # Evaluate from a pairs file
        evaluator = BatchEvaluator(results_dir="results/batch1")
        evaluator.# Use batch.scan_solutions_dir() or evaluate_pairs()
    """

    STATE_FILE = ".state.json"

    def __init__(
        self,
        results_dir: Path,
        *,
        base_dir: Optional[Path] = None,
        backend: str = "docker",
        track: str = "research",
        max_concurrent: int = 1,
        timeout: Optional[int] = None,
        bucket_url: Optional[str] = None,
        keep_cluster: bool = False,
        idle_timeout: Optional[int] = 10,
        judge_url: Optional[str] = None,
    ):
        """
        Initialize batch evaluator.

        Args:
            results_dir: Directory for results and state
            base_dir: Frontier-CS base directory (auto-detected if None)
            backend: Evaluation backend ("docker" or "skypilot")
            track: Evaluation track ("research" or "algorithmic")
            max_concurrent: Maximum concurrent evaluations
            timeout: Default timeout for evaluations (seconds)
            bucket_url: Optional bucket URL for result storage (s3://... or gs://...)
                       Only used with skypilot backend. Results are written directly
                       to the bucket and synced incrementally.
            keep_cluster: Keep SkyPilot cluster running after evaluation (disables autostop)
            idle_timeout: Minutes of idleness before autostop (default: 10, None to disable)
            judge_url: URL for algorithmic judge server (default: http://localhost:8081)
        """
        self.track = track
        self.results_dir = Path(results_dir)
        self.base_dir = base_dir or self._find_base_dir()
        self.backend = backend
        self.max_concurrent = max_concurrent
        self.timeout = timeout
        self.bucket_url = bucket_url
        self.judge_url = judge_url or "http://localhost:8081"
        self._bucket_storage = None

        # Initialize bucket storage if provided
        if bucket_url:
            from ..storage.bucket import BucketStorage
            self._bucket_storage = BucketStorage(
                bucket_url,
                local_cache=self.results_dir / ".bucket_cache",
            )

        self.state_path = self.results_dir / self.STATE_FILE
        self.state = EvaluationState.load(self.state_path)

        # Initialize runner based on track and backend
        if track == "algorithmic":
            if backend == "skypilot":
                from ..runner.algorithmic_skypilot import AlgorithmicSkyPilotRunner
                self._runner = AlgorithmicSkyPilotRunner(
                    base_dir=self.base_dir,
                    keep_cluster=keep_cluster,
                    idle_timeout=idle_timeout,
                )
            else:
                from ..runner.algorithmic import AlgorithmicRunner
                self._runner = AlgorithmicRunner(judge_url=self.judge_url)
        else:
            # research track
            if backend == "docker":
                self._runner = DockerRunner(base_dir=self.base_dir)
            else:
                from ..runner.skypilot import SkyPilotRunner
                self._runner = SkyPilotRunner(
                    base_dir=self.base_dir,
                    bucket_url=bucket_url,
                    keep_cluster=keep_cluster,
                    idle_timeout=idle_timeout,
                )

    def _find_base_dir(self) -> Path:
        """Find the Frontier-CS base directory."""
        # src/frontier_cs/batch/evaluator.py -> repo root
        base = Path(__file__).parents[3]
        if not (base / "pyproject.toml").exists():
            raise RuntimeError(f"pyproject.toml not found in {base}")
        return base

    def _save_state(self) -> None:
        """Save current state to disk."""
        self.state.save(self.state_path)

    def sync_from_bucket(self) -> int:
        """
        Sync results from bucket to local state.

        Downloads new results from the bucket and merges them into the local state.
        Uses incremental sync (--size-only) to only download changed files.

        Returns:
            Number of results synced from bucket
        """
        if not self._bucket_storage:
            logger.warning("No bucket storage configured")
            return 0

        # Sync files from bucket to local cache
        count = self._bucket_storage.sync_from_bucket()

        if count == 0:
            return 0

        # Read all results from bucket and merge into state
        bucket_results = self._bucket_storage.read_all_results()
        merged = 0

        for pair_id, result_data in bucket_results.items():
            # Check if we need to update local state
            existing = self.state.results.get(pair_id)

            # Update if: not in state, or bucket has newer/better result
            should_update = (
                existing is None
                or not existing.is_complete
                or (result_data.status == "success" and existing.status != "success")
            )

            if should_update:
                self.state.results[pair_id] = PairResult(
                    pair_id=pair_id,
                    score=result_data.score,
                    status=result_data.status,
                    message=result_data.message,
                    duration_seconds=result_data.duration_seconds,
                    timestamp=result_data.timestamp,
                )
                merged += 1

        if merged > 0:
            self._save_state()
            logger.info(f"Merged {merged} results from bucket into local state")

        return merged

    def evaluate_pairs(
        self,
        pairs: List[Pair],
        *,
        resume: bool = True,
        on_progress: Optional[Callable[[Pair, EvaluationResult], None]] = None,
        show_progress: bool = True,
    ) -> EvaluationState:
        """
        Evaluate a list of pairs.

        Args:
            pairs: List of pairs to evaluate
            resume: Skip already-completed pairs
            on_progress: Callback after each evaluation
            show_progress: Show tqdm progress bar

        Returns:
            Final evaluation state
        """
        # Sync from bucket first if using bucket storage (get results from previous runs)
        if self._bucket_storage:
            self.sync_from_bucket()

        # Initialize state
        if not self.state.started_at:
            self.state.started_at = time.strftime("%Y-%m-%dT%H:%M:%S")
            self.state.backend = self.backend
            self.state.total_pairs = len(pairs)
        self._save_state()

        # Get pending pairs
        if resume:
            pending = self.state.get_pending_pairs(pairs)
            if len(pending) < len(pairs):
                logger.info(f"Resuming: {len(pairs) - len(pending)} pairs already complete")
        else:
            pending = pairs

        if not pending:
            logger.info("All pairs already evaluated")
            self._export_all_results(pairs)
            return self.state

        logger.info(f"Evaluating {len(pending)} pairs (max_concurrent={self.max_concurrent})")

        # Evaluate pairs
        if self.max_concurrent == 1:
            self._evaluate_sequential(pending, on_progress, show_progress)
        else:
            self._evaluate_parallel(pending, on_progress, show_progress)

        # Export all results
        self._export_all_results(pairs)

        return self.state

    def _export_all_results(self, all_pairs: Optional[List[Pair]] = None) -> None:
        """Export all result files."""
        # Sync from bucket to get latest results (for bucket mode)
        if self._bucket_storage:
            self.sync_from_bucket()

        # Basic results
        self.state.export_csv(self.results_dir / "results.csv")
        self.state.export_summary(self.results_dir / "summary.txt")

        # Failed/pending/skipped
        failed_count = self.state.export_failed(self.results_dir / "failed.txt")
        pending_count = self.state.export_pending(self.results_dir / "pending.txt", all_pairs)
        skipped_count = self.state.export_skipped(self.results_dir / "skipped.txt")

        # Aggregated results
        self.state.export_aggregated_csv(self.results_dir / "by_model.csv", by="model")
        self.state.export_aggregated_csv(self.results_dir / "by_problem.csv", by="problem")

        logger.info(f"Results exported to {self.results_dir}")
        if failed_count > 0:
            logger.info(f"  - {failed_count} failed pairs in failed.txt")
        if pending_count > 0:
            logger.info(f"  - {pending_count} pending pairs in pending.txt")

    def _evaluate_sequential(
        self,
        pairs: List[Pair],
        on_progress: Optional[Callable[[Pair, EvaluationResult], None]],
        show_progress: bool = True,
    ) -> None:
        """Evaluate pairs sequentially with optional progress bar."""
        iterator = pairs
        pbar = None

        if show_progress and HAS_TQDM:
            pbar = tqdm(total=len(pairs), desc="Evaluating", unit="pair", dynamic_ncols=True)
            iterator = pairs  # We'll update pbar manually

        try:
            for i, pair in enumerate(pairs, 1):
                if pbar:
                    pbar.set_postfix_str(pair.id[:40])
                else:
                    logger.info(f"[{i}/{len(pairs)}] Evaluating {pair.id}")

                self.state.mark_running(pair)
                self._save_state()

                try:
                    result = self._evaluate_pair(pair)
                    self._record_result(pair, result)

                    if on_progress:
                        on_progress(pair, result)

                    # Log result
                    status_str = "OK" if result.success else "FAIL"
                    score_str = str(result.score) if result.success else (result.message or "error")
                    if pbar:
                        pbar.write(f"  [{status_str}] {pair.id}: {score_str}")

                except Exception as e:
                    logger.error(f"Error evaluating {pair.id}: {e}")
                    self.state.record_result(
                        pair,
                        score=None,
                        status="error",
                        message=str(e),
                    )
                    if pbar:
                        pbar.write(f"  [ERROR] {pair.id}: {e}")
                finally:
                    self._save_state()
                    if pbar:
                        pbar.update(1)
        finally:
            if pbar:
                pbar.close()

    def _evaluate_parallel(
        self,
        pairs: List[Pair],
        on_progress: Optional[Callable[[Pair, EvaluationResult], None]],
        show_progress: bool = True,
    ) -> None:
        """Evaluate pairs in parallel with optional progress bar."""
        pbar = None
        if show_progress and HAS_TQDM:
            pbar = tqdm(total=len(pairs), desc="Evaluating", unit="pair", dynamic_ncols=True)

        try:
            with ThreadPoolExecutor(max_workers=self.max_concurrent) as executor:
                futures = {}
                for pair in pairs:
                    self.state.mark_running(pair)
                    future = executor.submit(self._evaluate_pair, pair)
                    futures[future] = pair
                self._save_state()

                for future in as_completed(futures):
                    pair = futures[future]
                    try:
                        result = future.result()
                        self._record_result(pair, result)

                        if on_progress:
                            on_progress(pair, result)

                        # Log result
                        status_str = "OK" if result.success else "FAIL"
                        score_str = str(result.score) if result.success else (result.message or "error")
                        if pbar:
                            pbar.write(f"  [{status_str}] {pair.id}: {score_str}")

                    except Exception as e:
                        logger.error(f"Error evaluating {pair.id}: {e}")
                        self.state.record_result(
                            pair,
                            score=None,
                            status="error",
                            message=str(e),
                        )
                        if pbar:
                            pbar.write(f"  [ERROR] {pair.id}: {e}")
                    finally:
                        self._save_state()
                        if pbar:
                            pbar.update(1)
        finally:
            if pbar:
                pbar.close()

    def _evaluate_pair(self, pair: Pair) -> EvaluationResult:
        """Evaluate a single pair using the configured runner."""
        # Solutions are in track-specific directories
        if self.track == "algorithmic":
            solutions_dir = self.base_dir / "algorithmic" / "solutions"
        else:
            solutions_dir = self.base_dir / "research" / "solutions"
        solution_file = solutions_dir / pair.solution

        if not solution_file.exists():
            return EvaluationResult(
                problem_id=pair.problem,
                status=EvaluationStatus.ERROR,
                message=f"Solution file not found: {pair.solution}",
            )

        return self._runner.evaluate_file(
            pair.problem,
            solution_file,
            timeout=self.timeout,
            solution_id=pair.solution,
        )

    def _record_result(self, pair: Pair, result: EvaluationResult) -> None:
        """Record an evaluation result to state."""
        status_map = {
            EvaluationStatus.SUCCESS: "success",
            EvaluationStatus.ERROR: "error",
            EvaluationStatus.TIMEOUT: "timeout",
            EvaluationStatus.SKIPPED: "skipped",
        }
        self.state.record_result(
            pair,
            score=result.score,
            status=status_map.get(result.status, "error"),
            message=result.message,
            duration_seconds=result.duration_seconds,
        )

    def evaluate_model(
        self,
        model: str,
        problems: List[str],
        *,
        variants: Optional[List[int]] = None,
        resume: bool = True,
        on_progress: Optional[Callable[[Pair, EvaluationResult], None]] = None,
    ) -> EvaluationState:
        """
        Evaluate all problems for a given model.

        Args:
            model: Model name (e.g., "gpt-5", "claude-sonnet-4-5")
            problems: List of problem IDs
            variants: List of variant indices (default: [0])
            resume: Skip already-completed pairs
            on_progress: Callback after each evaluation

        Returns:
            Final evaluation state
        """
        if self.track == "algorithmic":
            solutions_dir = self.base_dir / "algorithmic" / "solutions"
            ext = "cpp"
        else:
            solutions_dir = self.base_dir / "research" / "solutions"
            ext = "py"
        pairs = expand_pairs(
            problems,
            [model],
            variants,
            solutions_dir=solutions_dir,
            validate_paths=True,
            ext=ext,
        )

        if not pairs:
            logger.warning(f"No valid pairs found for model {model}")
            return self.state

        return self.evaluate_pairs(pairs, resume=resume, on_progress=on_progress)

    def evaluate_problem(
        self,
        problem: str,
        models: List[str],
        *,
        variants: Optional[List[int]] = None,
        resume: bool = True,
        on_progress: Optional[Callable[[Pair, EvaluationResult], None]] = None,
    ) -> EvaluationState:
        """
        Evaluate a problem across all given models.

        Args:
            problem: Problem ID (e.g., "flash_attn")
            models: List of model names
            variants: List of variant indices (default: [0])
            resume: Skip already-completed pairs
            on_progress: Callback after each evaluation

        Returns:
            Final evaluation state
        """
        if self.track == "algorithmic":
            solutions_dir = self.base_dir / "algorithmic" / "solutions"
            ext = "cpp"
        else:
            solutions_dir = self.base_dir / "research" / "solutions"
            ext = "py"
        pairs = expand_pairs(
            [problem],
            models,
            variants,
            solutions_dir=solutions_dir,
            validate_paths=True,
            ext=ext,
        )

        if not pairs:
            logger.warning(f"No valid pairs found for problem {problem}")
            return self.state

        return self.evaluate_pairs(pairs, resume=resume, on_progress=on_progress)

    def evaluate_pairs_file(
        self,
        pairs_file: Path,
        *,
        resume: bool = True,
        on_progress: Optional[Callable[[Pair, EvaluationResult], None]] = None,
    ) -> EvaluationState:
        """
        Evaluate pairs from a pairs file.

        Args:
            pairs_file: Path to pairs file (solution:problem per line)
            resume: Skip already-completed pairs
            on_progress: Callback after each evaluation

        Returns:
            Final evaluation state
        """
        pairs = read_pairs_file(pairs_file)
        return self.evaluate_pairs(pairs, resume=resume, on_progress=on_progress)

    def evaluate_from_files(
        self,
        problems_file: Path,
        models_file: Path,
        *,
        variants_file: Optional[Path] = None,
        resume: bool = True,
        on_progress: Optional[Callable[[Pair, EvaluationResult], None]] = None,
    ) -> EvaluationState:
        """
        Evaluate pairs by expanding problems × models × variants.

        Args:
            problems_file: Path to problems file (one per line)
            models_file: Path to models file (one per line)
            variants_file: Path to variants file (optional, defaults to [0])
            resume: Skip already-completed pairs
            on_progress: Callback after each evaluation

        Returns:
            Final evaluation state
        """
        problems = read_problems_file(problems_file)
        models = read_models_file(models_file)
        variants = read_variants_file(variants_file) if variants_file else [0]

        if self.track == "algorithmic":
            solutions_dir = self.base_dir / "algorithmic" / "solutions"
            ext = "cpp"
        else:
            solutions_dir = self.base_dir / "research" / "solutions"
            ext = "py"
        pairs = expand_pairs(
            problems,
            models,
            variants,
            solutions_dir=solutions_dir,
            validate_paths=True,
            ext=ext,
        )

        logger.info(f"Expanded {len(problems)} problems × {len(models)} models × {len(variants)} variants = {len(pairs)} pairs")

        return self.evaluate_pairs(pairs, resume=resume, on_progress=on_progress)

    def resume(
        self,
        on_progress: Optional[Callable[[Pair, EvaluationResult], None]] = None,
    ) -> EvaluationState:
        """
        Resume an interrupted evaluation.

        Requires that the state file exists from a previous run.

        Returns:
            Final evaluation state
        """
        if not self.state.results:
            raise ValueError("No previous evaluation state found")

        # Reconstruct pairs from state
        pairs = [
            Pair(solution=pair_id.split(":")[0], problem=pair_id.split(":")[1])
            for pair_id in self.state.results.keys()
        ]

        # Add any pairs that were never started
        # This handles the case where we added pairs to the state but never evaluated them

        return self.evaluate_pairs(pairs, resume=True, on_progress=on_progress)

    def get_status(self) -> dict:
        """Get current evaluation status."""
        return {
            "total_pairs": self.state.total_pairs,
            "completed": self.state.completed_count,
            "successful": self.state.success_count,
            "errors": self.state.error_count,
            "pending": self.state.total_pairs - self.state.completed_count,
            "started_at": self.state.started_at,
            "updated_at": self.state.updated_at,
        }

    def retry_failed(
        self,
        on_progress: Optional[Callable[[Pair, EvaluationResult], None]] = None,
        show_progress: bool = True,
    ) -> EvaluationState:
        """
        Retry all failed pairs from the current state.

        Returns:
            Final evaluation state
        """
        failed_pairs = self.state.get_failed_pairs()
        if not failed_pairs:
            logger.info("No failed pairs to retry")
            return self.state

        logger.info(f"Retrying {len(failed_pairs)} failed pairs")

        # Clear failed status so they can be retried
        for pair in failed_pairs:
            del self.state.results[pair.id]
        self._save_state()

        return self.evaluate_pairs(failed_pairs, resume=False, on_progress=on_progress, show_progress=show_progress)

    def evaluate_missing(
        self,
        problems: List[str],
        models: List[str],
        *,
        variants: Optional[List[int]] = None,
        on_progress: Optional[Callable[[Pair, EvaluationResult], None]] = None,
        show_progress: bool = True,
    ) -> EvaluationState:
        """
        Evaluate only missing pairs (those not yet in results).

        Useful for completing an evaluation run after adding new models/problems.

        Args:
            problems: List of all problem IDs
            models: List of all model names
            variants: List of variant indices (default: [0])
            on_progress: Callback after each evaluation
            show_progress: Show progress bar

        Returns:
            Final evaluation state
        """
        if self.track == "algorithmic":
            solutions_dir = self.base_dir / "algorithmic" / "solutions"
            ext = "cpp"
        else:
            solutions_dir = self.base_dir / "research" / "solutions"
            ext = "py"
        all_pairs = expand_pairs(
            problems,
            models,
            variants,
            solutions_dir=solutions_dir,
            validate_paths=True,
            ext=ext,
        )

        # Find pairs not in current state
        missing = [p for p in all_pairs if p.id not in self.state.results]

        if not missing:
            logger.info("No missing pairs to evaluate")
            return self.state

        logger.info(f"Found {len(missing)} missing pairs out of {len(all_pairs)} total")

        # Update total_pairs to include all pairs
        self.state.total_pairs = len(all_pairs)
        self._save_state()

        return self.evaluate_pairs(missing, resume=False, on_progress=on_progress, show_progress=show_progress)
