"""
Unified evaluation API for Frontier-CS.

Provides a single interface for evaluating both algorithmic and research problems,
with support for different backends (local Docker, SkyPilot cloud).
"""

import atexit
import signal
from pathlib import Path
from typing import List, Literal, Optional, Union

from .runner import AlgorithmicLocalRunner, EvaluationResult, ResearchDockerRunner
from .runner.base import Runner
from .runner.cluster_cleanup import ActiveClusterRegistry
from .runner.research_skypilot import ResearchSkyPilotRunner
from .runner.algorithmic_skypilot import AlgorithmicSkyPilotRunner


TrackType = Literal["algorithmic", "research"]
BackendType = Literal["docker", "skypilot"]


class SingleEvaluator:
    """
    Unified evaluator for Frontier-CS problems.

    Example usage:
        evaluator = SingleEvaluator()

        # Algorithmic problem (uses Docker by default)
        result = evaluator.evaluate("algorithmic", problem_id=1, code=cpp_code)

        # Research problem (uses SkyPilot by default)
        result = evaluator.evaluate("research", problem_id="flash_attn", code=py_code)

        # Override backend
        result = evaluator.evaluate("research", problem_id="flash_attn", code=py_code,
                                   backend="docker")
    """

    def __init__(
        self,
        backend: Optional[BackendType] = None,
        base_dir: Optional[Path] = None,
        judge_url: str = "http://localhost:8081",
        cloud: str = "gcp",
        region: Optional[str] = None,
        keep_cluster: bool = False,
        idle_timeout: Optional[int] = 10,
        timeout: Optional[int] = None,
        register_cleanup: bool = True,
    ):
        """
        Initialize SingleEvaluator.

        Args:
            backend: Override default backend ("docker" or "skypilot").
                     If None, auto-detects: research -> skypilot, algorithmic -> docker
            base_dir: Base directory of Frontier-CS repo (auto-detected if None)
            judge_url: URL of the algorithmic judge server
            cloud: Cloud provider for SkyPilot ("gcp", "aws", "azure")
            region: Cloud region for SkyPilot
            keep_cluster: Keep SkyPilot cluster running after evaluation (disables autostop)
            idle_timeout: Minutes of idleness before autostop (default: 10, None to disable)
            timeout: Timeout per evaluation in seconds (default: None, uses runner default)
        """
        self.default_backend = backend
        self.base_dir = base_dir
        self.judge_url = judge_url
        self.cloud = cloud
        self.region = region
        self.keep_cluster = keep_cluster
        self.idle_timeout = idle_timeout
        self.timeout = timeout
        self._register_cleanup = register_cleanup

        # Lazy-initialized runners
        self._algorithmic_runner: Optional[AlgorithmicLocalRunner] = None
        self._algorithmic_skypilot_runner: Optional[Runner] = None
        self._docker_runner: Optional[ResearchDockerRunner] = None
        self._skypilot_runner: Optional[Runner] = None

        if self._register_cleanup:
            self._register_cleanup_hooks()

    def _register_cleanup_hooks(self) -> None:
        if self.keep_cluster:
            return

        def cleanup_on_exit():
            try:
                names = ActiveClusterRegistry.snapshot()
                if names:
                    ResearchSkyPilotRunner.down_clusters(names)
            except Exception:
                pass
            try:
                ResearchSkyPilotRunner.down_cluster(AlgorithmicSkyPilotRunner.CLUSTER_NAME)
            except Exception:
                pass

        def signal_handler(signum, frame):
            print("\n\nInterrupted! Cleaning up...")
            cleanup_on_exit()
            raise SystemExit(1)

        atexit.register(cleanup_on_exit)
        signal.signal(signal.SIGINT, signal_handler)


    @property
    def algorithmic_runner(self) -> AlgorithmicLocalRunner:
        """Get or create the algorithmic runner."""
        if self._algorithmic_runner is None:
            self._algorithmic_runner = AlgorithmicLocalRunner(judge_url=self.judge_url)
        return self._algorithmic_runner

    @property
    def algorithmic_skypilot_runner(self) -> Runner:
        """Get or create the algorithmic SkyPilot runner."""
        if self._algorithmic_skypilot_runner is None:
            from .runner.algorithmic_skypilot import AlgorithmicSkyPilotRunner
            self._algorithmic_skypilot_runner = AlgorithmicSkyPilotRunner(
                base_dir=self.base_dir,
                cloud=self.cloud,
                region=self.region,
                keep_cluster=self.keep_cluster,
                idle_timeout=self.idle_timeout,
            )
        return self._algorithmic_skypilot_runner

    @property
    def docker_runner(self) -> ResearchDockerRunner:
        """Get or create the Docker runner."""
        if self._docker_runner is None:
            self._docker_runner = ResearchDockerRunner(
                base_dir=self.base_dir, timeout=self.timeout
            )
        return self._docker_runner

    @property
    def skypilot_runner(self) -> Runner:
        """Get or create the SkyPilot runner."""
        if self._skypilot_runner is None:
            from .runner.research_skypilot import ResearchSkyPilotRunner
            self._skypilot_runner = ResearchSkyPilotRunner(
                base_dir=self.base_dir,
                cloud=self.cloud,
                region=self.region,
                keep_cluster=self.keep_cluster,
                idle_timeout=self.idle_timeout,
            )
        return self._skypilot_runner

    def _get_runner(self, track: TrackType, backend: Optional[BackendType] = None) -> Runner:
        """Get the appropriate runner for a track and backend."""
        # Priority: explicit backend > init backend > track default
        if backend:
            effective_backend = backend
        elif self.default_backend:
            effective_backend = self.default_backend
        else:
            # Auto-detect: research -> skypilot, algorithmic -> docker
            effective_backend = "skypilot" if track == "research" else "docker"

        if track == "algorithmic":
            if effective_backend == "skypilot":
                return self.algorithmic_skypilot_runner
            return self.algorithmic_runner

        if effective_backend == "skypilot":
            return self.skypilot_runner
        return self.docker_runner

    def evaluate(
        self,
        track: TrackType,
        problem_id: Union[str, int],
        code: str,
        *,
        backend: Optional[BackendType] = None,
    ) -> EvaluationResult:
        """
        Evaluate a solution for a single problem.

        Args:
            track: Problem track ("algorithmic" or "research")
            problem_id: Problem identifier (int for algorithmic, str for research)
            code: Solution code (C++ for algorithmic, Python for research)
            backend: Backend to use ("docker" or "skypilot"), defaults to init value

        Returns:
            EvaluationResult with score and status
        """
        runner = self._get_runner(track, backend)
        return runner.evaluate(str(problem_id), code)

    def evaluate_file(
        self,
        track: TrackType,
        problem_id: Union[str, int],
        solution_path: Path,
        *,
        backend: Optional[BackendType] = None,
    ) -> EvaluationResult:
        """
        Evaluate a solution file for a single problem.

        Args:
            track: Problem track
            problem_id: Problem identifier
            solution_path: Path to solution file
            backend: Backend to use

        Returns:
            EvaluationResult with score and status
        """
        runner = self._get_runner(track, backend)
        return runner.evaluate_file(str(problem_id), solution_path)

    def list_problems(self, track: TrackType) -> List[str]:
        """
        List all available problems for a track.

        Args:
            track: Problem track

        Returns:
            List of problem identifiers
        """
        if track == "algorithmic":
            # Read from local ./algorithmic/problems directory
            try:
                alg_base = self.docker_runner.base_dir / "algorithmic" / "problems"
            except Exception:
                return []
            
            if not alg_base or not alg_base.exists():
                return []
            
            problems = []
            for item in alg_base.iterdir():
                if item.is_dir() and not item.name.startswith("."):
                    problems.append(item.name)
            
            # Sort numerically if possible
            def sort_key(name):
                try:
                    return (0, int(name))
                except ValueError:
                    return (1, name)
            
            return sorted(problems, key=sort_key)

        # Research problems - count by evaluator.py files (matches update_problem_count.py logic)
        research_problems_dir = self.docker_runner.research_dir / "problems"
        if not research_problems_dir.exists():
            return []

        problems = []
        
        # Special case: poc_generation has 4 subcategories
        poc_dir = research_problems_dir / "poc_generation"
        if poc_dir.exists():
            # List the 4 subcategories directly
            problems.extend([
                "research/poc_generation/heap_buffer_overflow",
                "research/poc_generation/heap_use_after_free",
                "research/poc_generation/stack_buffer_overflow",
                "research/poc_generation/uninitialized_value"
            ])
        
        # Find all evaluator.py files, excluding those in poc_generation
        for evaluator_file in research_problems_dir.rglob("evaluator.py"):
            # Skip if it's under poc_generation directory
            if "poc_generation" not in str(evaluator_file):
                # Get relative path from research_problems_dir
                problem_path = evaluator_file.parent.relative_to(research_problems_dir)
                problems.append("research/" + str(problem_path))
        
        # Also include local algorithmic problems (from ./algorithmic/problems)
        try:
            alg_base = self.docker_runner.base_dir / "algorithmic" / "problems"
        except Exception:
            alg_base = None

        if alg_base and alg_base.exists():
            for item in sorted(alg_base.iterdir(), key=lambda p: p.name):
                if item.is_dir() and not item.name.startswith("."):
                    problems.append(f"algorithmic/{item.name}")

        return sorted(problems)

    def get_problem_statement(
        self,
        track: TrackType,
        problem_id: Union[str, int],
    ) -> Optional[str]:
        """
        Get the problem statement/readme for a problem.

        Args:
            track: Problem track
            problem_id: Problem identifier

        Returns:
            Problem statement text, or None if not found
        """
        if track == "algorithmic":
            return self.algorithmic_runner.get_problem_statement(str(problem_id))

        # Research problem - read readme
        problem_path = self.docker_runner.get_problem_path(str(problem_id))
        readme = problem_path / "readme"
        if readme.exists():
            return readme.read_text(encoding="utf-8")
        return None


# Convenience function for quick evaluation
def evaluate(
    track: TrackType,
    problem_id: Union[str, int],
    code: str,
    *,
    backend: BackendType = "docker",
) -> EvaluationResult:
    """
    Quick evaluation function.

    Example:
        from frontier_cs import evaluate
        result = evaluate("research", "flash_attn", solution_code)
        print(f"Score: {result.score}")
    """
    evaluator = SingleEvaluator(backend=backend)
    return evaluator.evaluate(track, problem_id, code)
