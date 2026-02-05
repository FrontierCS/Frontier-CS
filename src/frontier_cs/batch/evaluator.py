"""
Batch evaluator for running multiple evaluations with incremental progress.

Supports:
- Batch evaluation of multiple solution-problem pairs
- Incremental evaluation (resume from where you left off)
- Parallel execution with configurable workers and clusters
- Both Docker and SkyPilot backends
- Bucket storage for results (S3/GCS)
- Progress bar with tqdm
- Export failed/pending/aggregated results
"""

import hashlib
import logging
import queue
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path
from typing import Callable, Dict, List, Optional, Set

from tqdm import tqdm

from ..runner.base import EvaluationResult, EvaluationStatus
from ..runner.research_docker import ResearchDockerRunner
from ..config import get_problem_extension, ResourceSignature
from .pair import Pair, expand_pairs, read_pairs_file, read_problems_file, read_models_file, read_variants_file
from .state import EvaluationState, PairResult, hash_file, hash_directory

logger = logging.getLogger(__name__)


class BatchEvaluator:
    """
    Batch evaluator with incremental progress tracking.

    Parameters:
    - workers: Number of parallel workers/concurrent evaluations
    - clusters: Number of SkyPilot clusters (research + skypilot only)

    For SkyPilot research track, each worker uses a dedicated cluster.
    For SkyPilot algorithmic track, all workers share a single go-judge cluster.
    For Docker backend, workers are threads running local evaluations.

    Example usage:
        # Evaluate with 4 parallel workers on 4 SkyPilot clusters
        evaluator = BatchEvaluator(
            results_dir="results/batch1",
            backend="skypilot",
            workers=4,
            clusters=4,
        )
        evaluator.evaluate_pairs(pairs)
    """

    # State file per track to avoid mixing research/algorithmic pairs
    STATE_FILE_TEMPLATE = ".state.{track}.json"

    def __init__(
        self,
        results_dir: Path,
        *,
        base_dir: Optional[Path] = None,
        solutions_dir: Optional[Path] = None,
        problems_dir: Optional[Path] = None,
        backend: str = "docker",
        track: str = "research",
        workers: int = 1,
        clusters: Optional[int] = None,
        timeout: Optional[int] = 1000,  # Default 1000s timeout per evaluation
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
            solutions_dir: Solutions directory (overrides base_dir for solution lookup if set)
            problems_dir: Problems directory (overrides base_dir for problem lookup if set)
            backend: Evaluation backend ("docker" or "skypilot")
            track: Evaluation track ("research" or "algorithmic")
            workers: Number of parallel workers/concurrent evaluations (default: 1)
            clusters: Number of SkyPilot clusters (research + skypilot only, default: same as workers)
            timeout: Default timeout for evaluations (seconds)
            bucket_url: Optional bucket URL for result storage (s3://... or gs://...)
            keep_cluster: Keep SkyPilot clusters running after evaluation
            idle_timeout: Minutes of idleness before autostop (default: 10)
            judge_url: URL for algorithmic judge server (default: http://localhost:8081)
        """
        self.track = track
        self.results_dir = Path(results_dir)
        self.base_dir = base_dir or self._find_base_dir()
        self.solutions_dir = Path(solutions_dir) if solutions_dir else None
        self.problems_dir = Path(problems_dir) if problems_dir else None
        self.backend = backend
        self.clusters = clusters if clusters is not None else workers  # Default: same as workers
        # Ensure workers >= clusters to avoid idle clusters
        self.workers = max(workers, self.clusters)
        self.timeout = timeout
        self.bucket_url = bucket_url
        self.keep_cluster = keep_cluster
        self.idle_timeout = idle_timeout
        self.judge_url = judge_url or "http://localhost:8081"
        self._bucket_storage = None

        # Initialize bucket storage if provided
        if bucket_url:
            from ..storage.bucket import BucketStorage
            self._bucket_storage = BucketStorage(
                bucket_url,
                local_cache=self.results_dir / ".bucket_cache",
            )

        # Use track-specific state file to avoid mixing research/algorithmic pairs
        state_file = self.STATE_FILE_TEMPLATE.format(track=track)
        self.state_path = self.results_dir / state_file
        self.state = EvaluationState.load(self.state_path)
        self._pair_hashes: Dict[str, tuple] = {}

        # Initialize runner based on track and backend
        self._runner = self._create_runner()

        # For SkyPilot cluster pools (keyed by ResourceSignature)
        self._cluster_pools: Dict[ResourceSignature, List[str]] = {}

        # Lock for thread-safe state saving
        self._state_lock = threading.Lock()

    def _find_base_dir(self) -> Path:
        """Find the Frontier-CS base directory."""
        base = Path(__file__).parents[3]
        if not (base / "pyproject.toml").exists():
            raise RuntimeError(f"pyproject.toml not found in {base}")
        return base

    def _get_problems_dir(self) -> Path:
        """Get the problems directory for the current track."""
        if self.problems_dir:
            return self.problems_dir
        if self.track == "algorithmic":
            return self.base_dir / "algorithmic" / "problems"
        return self.base_dir / "research" / "problems"

    def _get_problem_extension(self, problem: str) -> str:
        """Get file extension for a problem based on its config.yaml.

        For algorithmic track, always returns "cpp".
        For research track, reads config.yaml to determine language.
        """
        if self.track == "algorithmic":
            return "cpp"

        # Research track: use shared function
        problems_dir = self._get_problems_dir()
        problem_path = problems_dir / problem
        return get_problem_extension(problem_path)

    def _build_problem_extensions(self, problems: List[str]) -> Dict[str, str]:
        """Build a mapping of problem -> extension for a list of problems."""
        return {problem: self._get_problem_extension(problem) for problem in problems}

    def _group_pairs_by_resources(self, pairs: List[Pair]) -> Dict[ResourceSignature, List[Pair]]:
        """Group pairs by their resource requirements (delegates to runner)."""
        groups: Dict[ResourceSignature, List[Pair]] = {}
        for pair in pairs:
            sig = self._runner.get_resource_signature(pair.problem)
            groups.setdefault(sig, []).append(pair)
        return groups

    def _create_runner(self):
        """Create the appropriate runner based on track and backend."""
        if self.track == "algorithmic":
            if self.backend == "skypilot":
                from ..runner.algorithmic_skypilot import AlgorithmicSkyPilotRunner
                return AlgorithmicSkyPilotRunner(
                    base_dir=self.base_dir,
                    problems_dir=self.problems_dir,
                    keep_cluster=self.keep_cluster,
                    idle_timeout=self.idle_timeout,
                )
            else:
                from ..runner.algorithmic_local import AlgorithmicLocalRunner
                return AlgorithmicLocalRunner(
                    judge_url=self.judge_url,
                    problems_dir=self.problems_dir,
                )
        else:
            # research track
            if self.backend == "docker":
                return ResearchDockerRunner(
                    base_dir=self.base_dir,
                    problems_dir=self.problems_dir,
                    timeout=self.timeout,
                )
            else:
                from ..runner.research_skypilot import ResearchSkyPilotRunner
                return ResearchSkyPilotRunner(
                    base_dir=self.base_dir,
                    problems_dir=self.problems_dir,
                    bucket_url=self.bucket_url,
                    keep_cluster=self.keep_cluster,
                    idle_timeout=self.idle_timeout,
                )

    def _save_state(self) -> None:
        """Save current state to disk (thread-safe)."""
        with self._state_lock:
            self.state.save(self.state_path)

    def _compute_hashes(self, pairs: List[Pair]) -> Dict[str, tuple]:
        """Compute hashes for all pairs for cache invalidation."""
        hashes = {}
        problem_hash_cache: Dict[str, Optional[str]] = {}
        solutions_dir = self._get_default_solutions_dir()

        for pair in pairs:
            solution_path = solutions_dir / pair.solution

            sol_hash = hash_file(solution_path) if solution_path.exists() else None

            if pair.problem not in problem_hash_cache:
                if self.problems_dir:
                    # Use explicit problems_dir if set
                    probs_dir = self.problems_dir
                elif self.track == "algorithmic":
                    probs_dir = self.base_dir / "algorithmic" / "problems"
                else:
                    probs_dir = self.base_dir / "research" / "problems"
                problem_path = probs_dir / pair.problem
                prob_hash = hash_directory(problem_path) if problem_path.exists() else None
                problem_hash_cache[pair.problem] = prob_hash
                logger.debug(f"Problem hash: {pair.problem} -> {prob_hash}")

            hashes[pair.id] = (sol_hash, problem_hash_cache[pair.problem])

        logger.debug(f"Computed hashes for {len(hashes)} pairs, {len(problem_hash_cache)} unique problems")
        return hashes

    def sync_from_bucket(self) -> int:
        """Sync results from bucket to local state."""
        if not self._bucket_storage:
            logger.warning("No bucket storage configured")
            return 0

        count = self._bucket_storage.sync_from_bucket()
        if count == 0:
            return 0

        bucket_results = self._bucket_storage.read_all_results()
        merged = 0

        for pair_id, result_data in bucket_results.items():
            existing = self.state.results.get(pair_id)
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
                    solution_hash=getattr(result_data, "solution_hash", None),
                    problem_hash=getattr(result_data, "problem_hash", None),
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
        Evaluate a list of pairs using the worker pool.

        Args:
            pairs: List of pairs to evaluate
            resume: Skip already-completed pairs (with hash validation)
            on_progress: Callback after each evaluation
            show_progress: Show tqdm progress bar

        Returns:
            Final evaluation state
        """
        # Sync from bucket first if using bucket storage
        if self._bucket_storage:
            self.sync_from_bucket()

        # Initialize state
        if not self.state.started_at:
            self.state.started_at = time.strftime("%Y-%m-%dT%H:%M:%S")
            self.state.backend = self.backend
        # Always update total_pairs to reflect current pairs count
        self.state.total_pairs = len(pairs)
        self._save_state()

        # Compute hashes for cache invalidation
        logger.info("Computing hashes for solution/problem pairs...")
        self._pair_hashes = self._compute_hashes(pairs)

        # Get pending pairs
        if resume:
            pending, invalidated = self.state.get_pending_pairs(pairs, self._pair_hashes)
            if invalidated:
                logger.warning(f"⚠️  {len(invalidated)} pair(s) invalidated due to changes:")
                for pair in invalidated:
                    result = self.state.results.get(pair.id)
                    sol_hash, prob_hash = self._pair_hashes.get(pair.id, (None, None))
                    old_sol = result.solution_hash if result else None
                    old_prob = result.problem_hash if result else None
                    changes = []
                    if old_sol != sol_hash:
                        changes.append(f"solution: {old_sol} -> {sol_hash}")
                    if old_prob != prob_hash:
                        changes.append(f"problem: {old_prob} -> {prob_hash}")
                    logger.warning(f"  - {pair.id}: {', '.join(changes)}")
            completed = len(pairs) - len(pending)
            if completed > 0:
                logger.info(f"Resuming: {completed} pairs already complete")
        else:
            pending = pairs

        if not pending:
            logger.info("All pairs already evaluated")
            self._export_all_results(pairs)
            return self.state

        # Adjust workers to not exceed pending pairs count
        effective_workers = min(self.workers, len(pending))
        effective_clusters = min(self.clusters, len(pending))
        if effective_workers < self.workers:
            logger.info(f"Adjusting workers: {self.workers} -> {effective_workers} (only {len(pending)} pairs)")
            self.workers = effective_workers
            self.clusters = effective_clusters

        logger.info(f"Evaluating {len(pending)} pairs (workers={self.workers}, clusters={self.clusters})")

        # Evaluate with unified worker pool
        self._evaluate_with_workers(pending, on_progress, show_progress)

        # Export all results
        self._export_all_results(pairs)

        return self.state

    def _evaluate_with_workers(
        self,
        pairs: List[Pair],
        on_progress: Optional[Callable[[Pair, EvaluationResult], None]],
        show_progress: bool = True,
    ) -> None:
        """
        Evaluate pairs using a pool of workers.

        For Docker: Each worker is a thread that runs docker evaluations.
        For SkyPilot (research): Each worker uses a dedicated cluster. Clusters are created
                     once at the start and reused for all evaluations. Pairs are grouped
                     by resource requirements, with separate cluster pools for each group.
        For SkyPilot (algorithmic): All workers share a single go-judge cluster.

        When workers=1, this is equivalent to sequential evaluation.
        """
        # Create work queue
        work_queue: queue.Queue[Pair] = queue.Queue()
        for pair in pairs:
            work_queue.put(pair)

        # Setup progress bar
        pbar = None
        if show_progress:
            pbar = tqdm(total=len(pairs), desc="Evaluating", unit="pair", dynamic_ncols=True)

        # For SkyPilot research track with multiple clusters, create reusable cluster pools
        # Algorithmic track uses a single go-judge cluster with HTTP requests, no cluster pool needed
        # Each resource signature gets its own pool of clusters
        cluster_pools: Dict[ResourceSignature, queue.Queue[str]] = {}
        if self.backend == "skypilot" and self.clusters > 1 and self.track != "algorithmic":
            self._create_cluster_pool(pairs)
            # Populate cluster pools for load-balancing
            for sig, cluster_names in self._cluster_pools.items():
                cluster_pools[sig] = queue.Queue()
                for cluster_name in cluster_names:
                    cluster_pools[sig].put(cluster_name)

        try:
            # Define worker function
            def worker(worker_id: int):
                while True:
                    try:
                        pair = work_queue.get_nowait()
                    except queue.Empty:
                        break

                    self.state.mark_running(pair)
                    self._save_state()

                    # Acquire cluster from the appropriate pool based on pair's resource signature
                    cluster_name = None
                    sig = None
                    if cluster_pools:
                        sig = self._runner.get_resource_signature(pair.problem)
                        pool = cluster_pools.get(sig)
                        if pool:
                            try:
                                cluster_name = pool.get(timeout=300)  # Wait up to 5 min for a cluster
                            except queue.Empty:
                                logger.warning(f"Worker {worker_id}: Timeout waiting for cluster ({sig}), using direct eval")

                    try:
                        # Execute evaluation
                        if cluster_name:
                            # Use cluster from pool with sky exec
                            result = self._runner.exec_on_cluster(
                                cluster_name,
                                pair.problem,
                                self._get_solution_path(pair),
                                solution_id=pair.solution,
                            )
                        else:
                            # Regular evaluation (docker or single skypilot)
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
                        # Return cluster to its pool
                        if cluster_name and sig and sig in cluster_pools:
                            cluster_pools[sig].put(cluster_name)
                        self._save_state()
                        if pbar:
                            pbar.update(1)
                        work_queue.task_done()

            # Run workers
            with ThreadPoolExecutor(max_workers=self.workers) as executor:
                futures = [executor.submit(worker, i) for i in range(self.workers)]
                for future in as_completed(futures):
                    try:
                        future.result()
                    except Exception as e:
                        logger.error(f"Worker error: {e}")

        finally:
            if pbar:
                pbar.close()

            # Cleanup clusters if we created them
            if self._cluster_pools and not self.keep_cluster:
                self._cleanup_cluster_pool()

    def _create_cluster_pool(self, pairs: List[Pair]) -> None:
        """Create resource-grouped pools of SkyPilot clusters for parallel evaluation.

        Groups pairs by their resource requirements (cloud, accelerators, instance_type)
        and creates separate cluster pools for each group. This ensures that:
        - CPU-only problems (e.g., nbody_simulation) get CPU-only clusters
        - GPU problems get GPU clusters
        - Problems requiring specific instance types get those instances
        """
        # Group pairs by resource signature
        resource_groups = self._group_pairs_by_resources(pairs)
        num_groups = len(resource_groups)

        logger.info(f"Found {num_groups} resource group(s) across {len(pairs)} pairs")
        for sig, group_pairs in resource_groups.items():
            logger.info(f"  - {sig}: {len(group_pairs)} pair(s)")

        # Distribute clusters across resource groups proportionally
        # (more pairs in a group = more clusters for that group)
        total_pairs = len(pairs)
        cluster_counts: Dict[ResourceSignature, int] = {}
        remaining_clusters = self.clusters

        for sig, group_pairs in resource_groups.items():
            # Proportional allocation, minimum 1 cluster per group
            proportion = len(group_pairs) / total_pairs
            count = max(1, int(self.clusters * proportion))
            cluster_counts[sig] = min(count, remaining_clusters)
            remaining_clusters -= cluster_counts[sig]

        # Distribute any remaining clusters to largest groups
        if remaining_clusters > 0:
            sorted_groups = sorted(resource_groups.keys(), key=lambda s: len(resource_groups[s]), reverse=True)
            for sig in sorted_groups:
                if remaining_clusters <= 0:
                    break
                cluster_counts[sig] += 1
                remaining_clusters -= 1

        # Add date hash to cluster names to avoid reusing old clusters with stale config
        date_str = datetime.now().strftime("%m%d%H%M")
        digest = hashlib.md5(date_str.encode()).hexdigest()[:6]

        # Create clusters for each resource group
        all_cluster_specs: List[tuple] = []  # (sig, cluster_name, ResourceSignature)
        cluster_idx = 0
        for sig, count in cluster_counts.items():
            for i in range(count):
                cluster_name = f"eval-worker-{cluster_idx}-{digest}"
                all_cluster_specs.append((sig, cluster_name))
                cluster_idx += 1

        logger.info(f"Creating {len(all_cluster_specs)} SkyPilot cluster(s) across {num_groups} resource group(s)...")

        # Create clusters in parallel
        def create_one(spec: tuple) -> tuple:
            sig, cluster_name = spec
            success = self._runner.create_cluster(cluster_name, sig)
            return (sig, cluster_name, success)

        with ThreadPoolExecutor(max_workers=len(all_cluster_specs)) as executor:
            results = list(executor.map(create_one, all_cluster_specs))

        # Organize results by signature
        self._cluster_pools = {}
        for sig, cluster_name, success in results:
            if sig not in self._cluster_pools:
                self._cluster_pools[sig] = []
            if success:
                self._cluster_pools[sig].append(cluster_name)

        # Report results
        total_created = sum(len(clusters) for clusters in self._cluster_pools.values())
        if total_created < len(all_cluster_specs):
            logger.warning(f"Only {total_created}/{len(all_cluster_specs)} clusters created successfully")

        if total_created == 0:
            raise RuntimeError("Failed to create any clusters")

        for sig, clusters in self._cluster_pools.items():
            logger.info(f"  - {sig}: {len(clusters)} cluster(s)")

    def _cleanup_cluster_pool(self) -> None:
        """Terminate all clusters in all pools."""
        if not self._cluster_pools:
            return

        # Collect all cluster names from all pools
        all_cluster_names = []
        for clusters in self._cluster_pools.values():
            all_cluster_names.extend(clusters)

        if not all_cluster_names:
            return

        logger.info(f"Terminating {len(all_cluster_names)} cluster(s)...")
        from ..runner.research_skypilot import ResearchSkyPilotRunner
        ResearchSkyPilotRunner.down_clusters(all_cluster_names)
        self._cluster_pools = {}

    def _get_default_solutions_dir(self) -> Path:
        """Get the solutions directory (explicit or default based on track)."""
        if self.solutions_dir:
            return self.solutions_dir
        elif self.track == "algorithmic":
            return self.base_dir / "algorithmic" / "solutions"
        else:
            return self.base_dir / "research" / "solutions"

    def _get_solution_path(self, pair: Pair) -> Path:
        """Get the solution file path for a pair."""
        return self._get_default_solutions_dir() / pair.solution

    def _evaluate_pair(self, pair: Pair) -> EvaluationResult:
        """Evaluate a single pair using the configured runner."""
        solution_file = self._get_solution_path(pair)

        if not solution_file.exists():
            return EvaluationResult(
                problem_id=pair.problem,
                status=EvaluationStatus.ERROR,
                message=f"Solution file not found: {pair.solution}",
            )

        return self._runner.evaluate_file(
            pair.problem,
            solution_file,
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

        sol_hash, prob_hash = self._pair_hashes.get(pair.id, (None, None))

        self.state.record_result(
            pair,
            score=result.score,
            status=status_map.get(result.status, "error"),
            message=result.message,
            duration_seconds=result.duration_seconds,
            solution_hash=sol_hash,
            problem_hash=prob_hash,
            score_unbounded=result.score_unbounded,
        )

    def _get_valid_problems(self) -> Set[str]:
        """
        Get the set of valid problem names from the filesystem.

        Scans the problems directory to find all valid problem directories.
        This is used to detect orphaned results in state (results for problems
        that have been restructured or removed).
        """
        if self.problems_dir:
            probs_dir = self.problems_dir
        elif self.track == "algorithmic":
            probs_dir = self.base_dir / "algorithmic" / "problems"
        else:
            probs_dir = self.base_dir / "research" / "problems"

        if not probs_dir.exists():
            logger.warning(f"Problems directory not found: {probs_dir}")
            return set()

        valid_problems: Set[str] = set()

        # Directories to exclude (not problems)
        exclude_dirs = {'resources', 'common', '__pycache__'}

        def scan_recursive(path: Path, prefix: str = "") -> None:
            """Recursively scan for problem directories (those with evaluator.py or similar)."""
            for item in path.iterdir():
                if not item.is_dir() or item.name.startswith(".") or item.name in exclude_dirs:
                    continue

                problem_name = f"{prefix}{item.name}" if prefix else item.name

                # Check if this is a valid problem directory
                # A problem directory must have evaluator.py (the actual evaluation script)
                # config.yaml alone is not sufficient - it may be shared config
                if self.track == "algorithmic":
                    is_problem = (item / "config.yaml").exists()
                else:
                    # Research problems must have evaluator.py to be a real problem
                    is_problem = (item / "evaluator.py").exists() or (item / "evaluate.py").exists()

                if is_problem:
                    valid_problems.add(problem_name)

                # Always recurse into subdirectories to find nested problems
                # (e.g., poc_generation/heap_buffer_overflow/arvo_21000)
                scan_recursive(item, f"{problem_name}/")

        scan_recursive(probs_dir)
        return valid_problems

    def _get_orphaned_pairs(self) -> Set[str]:
        """
        Detect orphaned results in state.

        Orphaned results are evaluation results stored in state for problems
        that no longer exist in the filesystem. This can happen when:
        - A problem is restructured (e.g., split into nested subproblems)
        - A problem is renamed or removed

        Returns:
            Set of orphaned pair IDs (solution:problem format)
        """
        valid_problems = self._get_valid_problems()
        if not valid_problems:
            # If we can't determine valid problems, don't filter anything
            return set()

        orphaned: Set[str] = set()
        for pair_id in self.state.results.keys():
            problem = pair_id.split(":")[1]
            if problem not in valid_problems:
                orphaned.add(pair_id)

        if orphaned:
            # Log warning with details about orphaned results
            orphaned_problems = sorted(set(pid.split(":")[1] for pid in orphaned))
            logger.warning(
                f"Found {len(orphaned)} orphaned result(s) in state for {len(orphaned_problems)} problem(s) "
                f"that no longer exist: {orphaned_problems}. "
                f"These will be excluded from aggregated reports."
            )

        return orphaned

    def _export_all_results(self, all_pairs: Optional[List[Pair]] = None) -> None:
        """Export all result files."""
        if self._bucket_storage:
            self.sync_from_bucket()

        self.state.export_csv(self.results_dir / "results.csv")
        self.state.export_summary(self.results_dir / "summary.txt")

        failed_count = self.state.export_failed(self.results_dir / "failed.txt")
        pending_count = self.state.export_pending(self.results_dir / "pending.txt", all_pairs)
        self.state.export_skipped(self.results_dir / "skipped.txt")

        # Detect orphaned pairs and filter them from aggregated reports
        valid_problems = self._get_valid_problems()
        if valid_problems:
            orphaned = self._get_orphaned_pairs()  # This logs the warning
            self.state.export_aggregated_csv(
                self.results_dir / "by_model.csv", by="model", valid_problems=valid_problems
            )
            self.state.export_aggregated_csv(
                self.results_dir / "by_problem.csv", by="problem", valid_problems=valid_problems
            )
        else:
            # Fallback: no filtering if we can't determine valid problems
            self.state.export_aggregated_csv(self.results_dir / "by_model.csv", by="model")
            self.state.export_aggregated_csv(self.results_dir / "by_problem.csv", by="problem")

        logger.info(f"Results exported to {self.results_dir}")
        if failed_count > 0:
            logger.info(f"  - {failed_count} failed pairs in failed.txt")
        if pending_count > 0:
            logger.info(f"  - {pending_count} pending pairs in pending.txt")

    # =========================================================================
    # Convenience methods
    # =========================================================================

    def evaluate_model(
        self,
        model: str,
        problems: List[str],
        *,
        variants: Optional[List[int]] = None,
        resume: bool = True,
        on_progress: Optional[Callable[[Pair, EvaluationResult], None]] = None,
    ) -> EvaluationState:
        """Evaluate all problems for a given model."""
        solutions_dir = self._get_default_solutions_dir()
        problem_extensions = self._build_problem_extensions(problems)

        pairs = expand_pairs(
            problems, [model], variants,
            solutions_dir=solutions_dir, validate_paths=True,
            problem_extensions=problem_extensions,
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
        """Evaluate a problem across all given models."""
        solutions_dir = self._get_default_solutions_dir()
        problem_extensions = self._build_problem_extensions([problem])

        pairs = expand_pairs(
            [problem], models, variants,
            solutions_dir=solutions_dir, validate_paths=True,
            problem_extensions=problem_extensions,
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
        """Evaluate pairs from a pairs file."""
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
        """Evaluate pairs by expanding problems × models × variants."""
        problems = read_problems_file(problems_file)
        models = read_models_file(models_file)
        variants = read_variants_file(variants_file) if variants_file else [0]

        solutions_dir = self._get_default_solutions_dir()
        problem_extensions = self._build_problem_extensions(problems)

        pairs = expand_pairs(
            problems, models, variants,
            solutions_dir=solutions_dir, validate_paths=True,
            problem_extensions=problem_extensions,
        )

        logger.info(f"Expanded {len(problems)} problems × {len(models)} models × {len(variants)} variants = {len(pairs)} pairs")
        return self.evaluate_pairs(pairs, resume=resume, on_progress=on_progress)

    def resume(
        self,
        on_progress: Optional[Callable[[Pair, EvaluationResult], None]] = None,
    ) -> EvaluationState:
        """Resume an interrupted evaluation."""
        if not self.state.results:
            raise ValueError("No previous evaluation state found")

        pairs = [
            Pair(solution=pair_id.split(":")[0], problem=pair_id.split(":")[1])
            for pair_id in self.state.results.keys()
        ]

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

        Includes both error/timeout AND score=0 pairs, because we cannot
        reliably distinguish between a legitimate 0 score and a failure
        that printed "0" before exiting.
        """
        failed_pairs = self.state.get_failed_pairs()
        if not failed_pairs:
            logger.info("No failed pairs to retry")
            return self.state

        logger.info(f"Retrying {len(failed_pairs)} failed pairs")

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
        """Evaluate only missing pairs (those not yet in results)."""
        solutions_dir = self._get_default_solutions_dir()
        problem_extensions = self._build_problem_extensions(problems)

        all_pairs = expand_pairs(
            problems, models, variants,
            solutions_dir=solutions_dir, validate_paths=True,
            problem_extensions=problem_extensions,
        )

        missing = [p for p in all_pairs if p.id not in self.state.results]

        if not missing:
            logger.info("No missing pairs to evaluate")
            return self.state

        logger.info(f"Found {len(missing)} missing pairs out of {len(all_pairs)} total")

        self.state.total_pairs = len(all_pairs)
        self._save_state()

        return self.evaluate_pairs(missing, resume=False, on_progress=on_progress, show_progress=show_progress)
