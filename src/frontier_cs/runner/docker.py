"""
Docker runner for research problems.

Runs evaluations in local Docker containers.
"""

import shutil
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Optional, Tuple

from .base import Runner, EvaluationResult, EvaluationStatus
from ..config import load_runtime_config, DockerConfig, DEFAULT_DOCKER_IMAGE


class DockerRunner(Runner):
    """
    Runner for research problems using local Docker.

    Executes evaluations in Docker containers with support for:
    - Custom Docker images per problem (configured in config.yaml)
    - GPU passthrough
    - Timeout enforcement
    - Docker-in-Docker (for security problems)
    """

    DEFAULT_TIMEOUT = 1800  # 30 minutes

    def __init__(
        self,
        base_dir: Optional[Path] = None,
        datasets_dir: Optional[Path] = None,
    ):
        """
        Initialize DockerRunner.

        Args:
            base_dir: Base directory of Frontier-CS repo (auto-detected if None)
            datasets_dir: Directory for cached datasets (default: base_dir/research/datasets)
        """
        self.base_dir = base_dir or self._find_base_dir()
        self.research_dir = self.base_dir / "research"
        self.datasets_dir = datasets_dir or (self.research_dir / "datasets")
        self._has_gpu: Optional[bool] = None

    def _find_base_dir(self) -> Path:
        """Find the Frontier-CS base directory."""
        candidates = [
            Path(__file__).parents[4],  # src/frontier_cs/runner/docker.py -> repo root
            Path.cwd(),
            Path.cwd().parent,
        ]
        for candidate in candidates:
            if (candidate / "research").is_dir() and (candidate / "pyproject.toml").exists():
                return candidate
        raise RuntimeError("Could not find Frontier-CS base directory")

    @property
    def has_gpu(self) -> bool:
        """Check if GPU is available."""
        if self._has_gpu is None:
            try:
                result = subprocess.run(
                    ["nvidia-smi"],
                    capture_output=True,
                    timeout=5,
                )
                self._has_gpu = result.returncode == 0
            except (subprocess.TimeoutExpired, FileNotFoundError):
                self._has_gpu = False
        return self._has_gpu

    def get_problem_path(self, problem_id: str) -> Path:
        """Get the path to a research problem directory."""
        return self.research_dir / "problems" / problem_id

    def evaluate(
        self,
        problem_id: str,
        solution_code: str,
        *,
        timeout: Optional[int] = None,
    ) -> EvaluationResult:
        """
        Evaluate a solution for a research problem.

        Args:
            problem_id: Problem ID (e.g., "flash_attn", "gemm_optimization/squares")
            solution_code: Python solution code
            timeout: Optional timeout in seconds

        Returns:
            EvaluationResult with score and status
        """
        problem_path = self.get_problem_path(problem_id)

        if not problem_path.exists():
            return EvaluationResult(
                problem_id=problem_id,
                status=EvaluationStatus.ERROR,
                message=f"Problem not found: {problem_path}",
            )

        # Create temp directory with solution
        with tempfile.TemporaryDirectory(prefix="frontier_eval_") as temp_dir:
            temp_path = Path(temp_dir)
            solution_path = temp_path / "solution.py"
            solution_path.write_text(solution_code, encoding="utf-8")

            return self._run_evaluation(problem_id, problem_path, solution_path, timeout)

    def evaluate_file(
        self,
        problem_id: str,
        solution_path: Path,
        *,
        timeout: Optional[int] = None,
        solution_id: Optional[str] = None,  # Unused, for API compatibility with SkyPilotRunner
    ) -> EvaluationResult:
        """Evaluate a solution file for a research problem."""
        if not solution_path.exists():
            return EvaluationResult(
                problem_id=problem_id,
                status=EvaluationStatus.ERROR,
                message=f"Solution file not found: {solution_path}",
            )

        problem_path = self.get_problem_path(problem_id)
        if not problem_path.exists():
            return EvaluationResult(
                problem_id=problem_id,
                status=EvaluationStatus.ERROR,
                message=f"Problem not found: {problem_path}",
            )

        return self._run_evaluation(problem_id, problem_path, solution_path, timeout)

    def _run_evaluation(
        self,
        problem_id: str,
        problem_path: Path,
        solution_path: Path,
        timeout: Optional[int],
    ) -> EvaluationResult:
        """Run the actual evaluation in Docker."""
        start_time = time.time()

        # Load config from problem's config.yaml
        runtime_config = load_runtime_config(problem_path)
        docker_config = runtime_config.docker

        # Determine timeout
        effective_timeout = timeout or runtime_config.timeout_seconds or self.DEFAULT_TIMEOUT

        # Check GPU requirements
        needs_gpu = docker_config.gpu or runtime_config.requires_gpu or runtime_config.resources.has_gpu
        if needs_gpu and not self.has_gpu:
            return EvaluationResult(
                problem_id=problem_id,
                status=EvaluationStatus.SKIPPED,
                message="GPU required but not available",
            )

        # Create workspace
        with tempfile.TemporaryDirectory(prefix="frontier_workspace_") as workspace_dir:
            workspace = Path(workspace_dir)
            self._setup_workspace(workspace, problem_id, problem_path, solution_path)

            # Run Docker
            result, logs = self._run_docker(
                workspace=workspace,
                docker_config=docker_config,
                needs_gpu=needs_gpu,
                timeout=effective_timeout,
            )

            duration = time.time() - start_time

            if result.returncode == 124:  # timeout exit code
                return EvaluationResult(
                    problem_id=problem_id,
                    status=EvaluationStatus.TIMEOUT,
                    message=f"Evaluation timed out after {effective_timeout}s",
                    logs=logs,
                    duration_seconds=duration,
                )

            # Parse score from output
            score, error = self._parse_score(logs)

            if error or result.returncode != 0:
                return EvaluationResult(
                    problem_id=problem_id,
                    status=EvaluationStatus.ERROR,
                    message=error or f"Docker exited with code {result.returncode}",
                    logs=logs,
                    duration_seconds=duration,
                )

            return EvaluationResult(
                problem_id=problem_id,
                score=score,
                status=EvaluationStatus.SUCCESS,
                logs=logs,
                duration_seconds=duration,
            )

    def _setup_workspace(
        self,
        workspace: Path,
        problem_id: str,
        problem_path: Path,
        solution_path: Path,
    ) -> None:
        """Set up the Docker workspace."""
        # Create directory structure
        research_dir = workspace / "research" / problem_id
        research_dir.mkdir(parents=True)

        # Copy problem files
        for item in problem_path.iterdir():
            if item.is_file():
                shutil.copy2(item, research_dir / item.name)
            elif item.is_dir() and item.name != "__pycache__":
                shutil.copytree(item, research_dir / item.name)

        # Copy common directories from parent levels
        parts = problem_id.split("/")
        for i in range(1, len(parts)):
            parent = "/".join(parts[:i])
            common_dir = self.research_dir / "problems" / parent / "common"
            if common_dir.is_dir():
                dest = workspace / "research" / parent / "common"
                shutil.copytree(common_dir, dest)

        # Create solution structure
        solution_dir = workspace / "solution"
        solution_dir.mkdir(parents=True)
        shutil.copy2(solution_path, solution_dir / "solution.py")

    def _run_docker(
        self,
        workspace: Path,
        docker_config: DockerConfig,
        needs_gpu: bool,
        timeout: int,
    ) -> Tuple[subprocess.CompletedProcess, str]:
        """Run the Docker container."""
        cmd = ["docker", "run", "--rm"]

        # GPU flags
        if needs_gpu:
            cmd.extend(["--gpus", "all"])

        # Docker-in-Docker flags
        if docker_config.dind:
            cmd.extend(["-v", "/var/run/docker.sock:/var/run/docker.sock"])

        # Mount workspace
        cmd.extend(["-v", f"{workspace}:/workspace:ro"])

        # Mount datasets if they exist
        if self.datasets_dir.exists():
            cmd.extend(["-v", f"{self.datasets_dir}:/datasets:ro"])

        # Working directory
        cmd.extend(["-w", "/work"])

        # Image
        cmd.append(docker_config.image)

        # Run script
        run_script = self._get_run_script()
        cmd.extend(["bash", "-c", run_script])

        # Wrap with timeout
        if timeout:
            cmd = ["timeout", "--foreground", f"{timeout}s"] + cmd

        # Execute
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
        )

        logs = result.stdout + "\n" + result.stderr
        return result, logs

    def _get_run_script(self) -> str:
        """Get the bash script to run inside Docker."""
        return '''
set -euo pipefail

# Copy workspace to writable location
cp -r /workspace/* /work/
cd /work

# Find the problem directory
PROBLEM_DIR=$(find research -mindepth 1 -maxdepth 4 -name "evaluator.py" -exec dirname {} \\; | head -1)
if [ -z "$PROBLEM_DIR" ]; then
    echo "ERROR: Could not find problem directory"
    exit 1
fi

cd "$PROBLEM_DIR"

# Run setup if exists
if [ -f set_up_env.sh ]; then
    chmod +x set_up_env.sh
    ./set_up_env.sh
fi

# Copy solution
mkdir -p /work/execution_env/solution_env
cp /work/solution/solution.py /work/execution_env/solution_env/

# Run evaluation
chmod +x evaluate.sh
./evaluate.sh
'''

    def _parse_score(self, output: str) -> Tuple[Optional[float], Optional[str]]:
        """Parse score from evaluation output."""
        lines = output.strip().split("\n")

        # Look for the last numeric line (ignoring log messages)
        for line in reversed(lines):
            line = line.strip()
            # Skip log messages
            if line.startswith("[") or "INFO" in line or "ERROR" in line:
                continue
            # Try to parse as number
            try:
                return float(line), None
            except ValueError:
                continue

        # Look for error messages
        for line in lines:
            if "Error" in line or "ERROR" in line:
                return None, line

        return None, "Could not parse score from output"
