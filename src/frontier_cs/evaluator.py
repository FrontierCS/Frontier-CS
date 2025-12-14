"""
Unified evaluation API for Frontier-CS.

Provides a single interface for evaluating both algorithmic and research problems,
with support for different backends (local Docker, SkyPilot cloud).
"""

from pathlib import Path
from typing import Iterator, List, Literal, Optional, Union

from .runner import EvaluationResult, DockerRunner, AlgorithmicRunner
from .runner.base import Runner


TrackType = Literal["algorithmic", "research"]
BackendType = Literal["docker", "skypilot"]


class FrontierCSEvaluator:
    """
    Unified evaluator for Frontier-CS problems.

    Example usage:
        evaluator = FrontierCSEvaluator()

        # Algorithmic problem
        result = evaluator.evaluate("algorithmic", problem_id=1, code=cpp_code)

        # Research problem (local Docker)
        result = evaluator.evaluate("research", problem_id="flash_attn", code=py_code)

        # Research problem (SkyPilot)
        result = evaluator.evaluate("research", problem_id="flash_attn", code=py_code,
                                   backend="skypilot")

        # Batch evaluation
        results = evaluator.evaluate_batch("research",
                                          problem_ids=["flash_attn", "cross_entropy"],
                                          code=py_code)
    """

    def __init__(
        self,
        backend: BackendType = "docker",
        base_dir: Optional[Path] = None,
        judge_url: str = "http://localhost:8081",
        cloud: str = "gcp",
        region: Optional[str] = None,
    ):
        """
        Initialize FrontierCSEvaluator.

        Args:
            backend: Default backend for research problems ("docker" or "skypilot")
            base_dir: Base directory of Frontier-CS repo (auto-detected if None)
            judge_url: URL of the algorithmic judge server
            cloud: Cloud provider for SkyPilot ("gcp", "aws", "azure")
            region: Cloud region for SkyPilot
        """
        self.default_backend = backend
        self.base_dir = base_dir
        self.judge_url = judge_url
        self.cloud = cloud
        self.region = region

        # Lazy-initialized runners
        self._algorithmic_runner: Optional[AlgorithmicRunner] = None
        self._docker_runner: Optional[DockerRunner] = None
        self._skypilot_runner: Optional[Runner] = None

    @property
    def algorithmic_runner(self) -> AlgorithmicRunner:
        """Get or create the algorithmic runner."""
        if self._algorithmic_runner is None:
            self._algorithmic_runner = AlgorithmicRunner(judge_url=self.judge_url)
        return self._algorithmic_runner

    @property
    def docker_runner(self) -> DockerRunner:
        """Get or create the Docker runner."""
        if self._docker_runner is None:
            self._docker_runner = DockerRunner(base_dir=self.base_dir)
        return self._docker_runner

    @property
    def skypilot_runner(self) -> Runner:
        """Get or create the SkyPilot runner."""
        if self._skypilot_runner is None:
            from .runner.skypilot import SkyPilotRunner
            self._skypilot_runner = SkyPilotRunner(
                base_dir=self.base_dir,
                cloud=self.cloud,
                region=self.region,
            )
        return self._skypilot_runner

    def _get_runner(self, track: TrackType, backend: Optional[BackendType] = None) -> Runner:
        """Get the appropriate runner for a track and backend."""
        if track == "algorithmic":
            return self.algorithmic_runner

        effective_backend = backend or self.default_backend
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
        timeout: Optional[int] = None,
    ) -> EvaluationResult:
        """
        Evaluate a solution for a single problem.

        Args:
            track: Problem track ("algorithmic" or "research")
            problem_id: Problem identifier (int for algorithmic, str for research)
            code: Solution code (C++ for algorithmic, Python for research)
            backend: Backend to use ("docker" or "skypilot"), defaults to init value
            timeout: Optional timeout in seconds

        Returns:
            EvaluationResult with score and status
        """
        runner = self._get_runner(track, backend)
        return runner.evaluate(str(problem_id), code, timeout=timeout)

    def evaluate_file(
        self,
        track: TrackType,
        problem_id: Union[str, int],
        solution_path: Path,
        *,
        backend: Optional[BackendType] = None,
        timeout: Optional[int] = None,
    ) -> EvaluationResult:
        """
        Evaluate a solution file for a single problem.

        Args:
            track: Problem track
            problem_id: Problem identifier
            solution_path: Path to solution file
            backend: Backend to use
            timeout: Optional timeout in seconds

        Returns:
            EvaluationResult with score and status
        """
        runner = self._get_runner(track, backend)
        return runner.evaluate_file(str(problem_id), solution_path, timeout=timeout)

    def evaluate_batch(
        self,
        track: TrackType,
        problem_ids: List[Union[str, int]],
        code: str,
        *,
        backend: Optional[BackendType] = None,
        timeout: Optional[int] = None,
    ) -> List[EvaluationResult]:
        """
        Evaluate a solution against multiple problems.

        Args:
            track: Problem track
            problem_ids: List of problem identifiers
            code: Solution code (same code for all problems)
            backend: Backend to use
            timeout: Optional timeout per problem

        Returns:
            List of EvaluationResult, one per problem
        """
        runner = self._get_runner(track, backend)
        results = []
        for pid in problem_ids:
            result = runner.evaluate(str(pid), code, timeout=timeout)
            results.append(result)
        return results

    def evaluate_batch_iter(
        self,
        track: TrackType,
        problem_ids: List[Union[str, int]],
        code: str,
        *,
        backend: Optional[BackendType] = None,
        timeout: Optional[int] = None,
    ) -> Iterator[EvaluationResult]:
        """
        Evaluate a solution against multiple problems, yielding results as they complete.

        Args:
            track: Problem track
            problem_ids: List of problem identifiers
            code: Solution code
            backend: Backend to use
            timeout: Optional timeout per problem

        Yields:
            EvaluationResult for each problem as it completes
        """
        runner = self._get_runner(track, backend)
        for pid in problem_ids:
            yield runner.evaluate(str(pid), code, timeout=timeout)

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
    timeout: Optional[int] = None,
) -> EvaluationResult:
    """
    Quick evaluation function.

    Example:
        from frontier_cs import evaluate
        result = evaluate("research", "flash_attn", solution_code)
        print(f"Score: {result.score}")
    """
    evaluator = FrontierCSEvaluator(backend=backend)
    return evaluator.evaluate(track, problem_id, code, timeout=timeout)
