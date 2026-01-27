"""
Docker runner for research problems.

Runs evaluations in local Docker containers.
"""

import json
import shutil
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Optional, Tuple

from .base import ResearchRunner, EvaluationResult, EvaluationStatus
from ..config import load_problem_config, DockerConfig, DEFAULT_DOCKER_IMAGE
from ..gen.solution_format import FAILED_EXTENSION


class DockerRunner(ResearchRunner):
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
        problems_dir: Optional[Path] = None,
        datasets_dir: Optional[Path] = None,
        timeout: Optional[int] = None,
    ):
        """
        Initialize DockerRunner.

        Args:
            base_dir: Base directory of Frontier-CS repo (auto-detected if None)
            problems_dir: Problems directory (overrides base_dir/research/problems if set)
            datasets_dir: Directory for cached datasets (default: base_dir/research/datasets)
            timeout: Timeout per evaluation in seconds (default: 1800, overrides problem config)
        """
        super().__init__(base_dir=base_dir, problems_dir=problems_dir)
        self.datasets_dir = datasets_dir or (self.research_dir / "datasets")
        self.timeout = timeout  # User-specified timeout, overrides problem config if set
        self._has_gpu: Optional[bool] = None

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

    def evaluate(
        self,
        problem_id: str,
        solution_code: str,
    ) -> EvaluationResult:
        """
        Evaluate a solution for a research problem.

        Args:
            problem_id: Problem ID (e.g., "flash_attn", "gemm_optimization/squares")
            solution_code: Python solution code

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

            return self._run_evaluation(problem_id, problem_path, solution_path)

    def evaluate_file(
        self,
        problem_id: str,
        solution_path: Path,
        *,
        solution_id: Optional[str] = None,  # Unused, for API compatibility with SkyPilotRunner
    ) -> EvaluationResult:
        """Evaluate a solution file for a research problem."""
        if not solution_path.exists():
            return EvaluationResult(
                problem_id=problem_id,
                status=EvaluationStatus.ERROR,
                message=f"Solution file not found: {solution_path}",
            )

        # Check for generation failure marker (.FAILED file)
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

        problem_path = self.get_problem_path(problem_id)
        if not problem_path.exists():
            return EvaluationResult(
                problem_id=problem_id,
                status=EvaluationStatus.ERROR,
                message=f"Problem not found: {problem_path}",
            )

        return self._run_evaluation(problem_id, problem_path, solution_path)

    def _run_evaluation(
        self,
        problem_id: str,
        problem_path: Path,
        solution_path: Path,
    ) -> EvaluationResult:
        """Run the actual evaluation in Docker."""
        start_time = time.time()

        # Load config from problem's config.yaml
        problem_config = load_problem_config(problem_path)
        runtime_config = problem_config.runtime
        docker_config = runtime_config.docker
        uv_project = problem_config.dependencies.get("uv_project")

        # Determine timeout: user-specified > problem config > default
        if self.timeout is not None:
            effective_timeout = self.timeout
        else:
            effective_timeout = runtime_config.timeout_seconds or self.DEFAULT_TIMEOUT

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
                uv_project=uv_project,
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
            score, score_unbounded, error = self._parse_score(logs)

            # If we got a score, treat as success (even if returncode != 0)
            # This distinguishes "solution failed, got 0" from "infrastructure error"
            if score is not None:
                return EvaluationResult(
                    problem_id=problem_id,
                    score=score,
                    score_unbounded=score_unbounded,
                    status=EvaluationStatus.SUCCESS,
                    logs=logs,
                    duration_seconds=duration,
                )

            # No score parsed - this is an infrastructure/evaluator error
            return EvaluationResult(
                problem_id=problem_id,
                status=EvaluationStatus.ERROR,
                message=error or f"Docker exited with code {result.returncode}",
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
            common_dir = self.problems_dir / parent / "common"
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
        uv_project: Optional[str] = None,
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
        run_script = self._get_run_script(uv_project=uv_project, dind=docker_config.dind)
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

    def _get_run_script(self, uv_project: Optional[str] = None, dind: bool = False) -> str:
        """Get the bash script to run inside Docker."""
        # Build uv install command if uv_project is specified
        if uv_project:
            uv_install_cmd = f'''
# Install dependencies from uv_project
if [ -d "{uv_project}" ] && [ -f "{uv_project}/pyproject.toml" ]; then
    echo "[framework] Installing dependencies from {uv_project}"
    uv pip install --system -e "{uv_project}"
fi
'''
        else:
            uv_install_cmd = "# No uv_project specified"

        # Build Docker CLI install command for DinD
        if dind:
            dind_install_cmd = '''
# Install Docker CLI for DinD
if ! command -v docker &>/dev/null; then
    echo "[framework] Installing Docker CLI for DinD..."
    DOCKER_VERSION="27.3.1"
    curl -fsSL "https://download.docker.com/linux/static/stable/x86_64/docker-${DOCKER_VERSION}.tgz" | tar xz -C /tmp
    mv /tmp/docker/docker /usr/local/bin/docker
    chmod +x /usr/local/bin/docker
    rm -rf /tmp/docker
fi
'''
        else:
            dind_install_cmd = "# DinD not enabled"

        return f'''
set -euo pipefail

# Copy workspace to writable location
cp -r /workspace/* /work/
cd /work

# Make all scripts executable
find /work -name "*.sh" -exec chmod +x {{}} \\;

# Create execution_env and copy solution BEFORE set_up_env.sh
# (some scripts expect this structure to exist)
mkdir -p /work/execution_env/solution_env
cp /work/solution/solution.py /work/execution_env/solution_env/

# Find the problem directory
PROBLEM_DIR=$(find research -mindepth 1 -maxdepth 4 -name "evaluator.py" -exec dirname {{}} \\; | head -1)
if [ -z "$PROBLEM_DIR" ]; then
    echo "ERROR: Could not find problem directory"
    exit 1
fi

cd "$PROBLEM_DIR"

# Install curl if not present (needed for uv install and other downloads)
if ! command -v curl &>/dev/null && ! command -v wget &>/dev/null; then
    if command -v apt-get &>/dev/null; then
        apt-get update -qq && apt-get install -y -qq curl >/dev/null 2>&1 || true
    fi
fi

{dind_install_cmd}

# Install uv if not present
if ! command -v uv &>/dev/null; then
    if command -v curl &>/dev/null; then
        curl -LsSf https://astral.sh/uv/install.sh | sh
    elif command -v wget &>/dev/null; then
        wget -qO- https://astral.sh/uv/install.sh | sh
    else
        pip install uv -q 2>/dev/null || true
    fi
    export PATH="$HOME/.local/bin:$PATH"
fi

{uv_install_cmd}

# Run setup if exists
if [ -f set_up_env.sh ]; then
    ./set_up_env.sh
fi

# Run evaluation
./evaluate.sh
'''

    def _parse_score(self, output: str) -> Tuple[Optional[float], Optional[float], Optional[str]]:
        """Parse score and score_unbounded from evaluation output.

        Expects last line to be either:
        - Single number: "85.5" (score_unbounded = score)
        - Two numbers: "85.5 120.3" (score score_unbounded)
        """
        lines = output.strip().split("\n")

        # Look for the last numeric line (ignoring log messages)
        for line in reversed(lines):
            line = line.strip()
            # Skip log messages
            if line.startswith("[") or "INFO" in line or "ERROR" in line:
                continue
            # Try to parse as number(s)
            parts = line.split()
            if not parts:
                continue
            try:
                score = float(parts[0])
                score_unbounded = float(parts[1]) if len(parts) > 1 else score
                return score, score_unbounded, None
            except ValueError:
                continue

        # Look for error messages
        for line in lines:
            if "Error" in line or "ERROR" in line:
                return None, None, line

        return None, None, "Could not parse score from output"
