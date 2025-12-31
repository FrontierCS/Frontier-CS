"""
SkyPilot runner for research problems.

Runs evaluations on cloud VMs via SkyPilot.

Supports two result storage modes:
- scp (legacy): Fetch results via scp after job completes
- bucket: Write results directly to S3/GCS bucket during job execution
"""

import hashlib
import json
import shutil
import subprocess
import tempfile
import textwrap
import time
from datetime import datetime
from pathlib import Path
from typing import Optional, Tuple

from .base import Runner, EvaluationResult, EvaluationStatus
from ..config import load_runtime_config


def _sanitize_name(name: str) -> str:
    """Sanitize a name for use as cluster name."""
    cleaned = []
    valid = "abcdefghijklmnopqrstuvwxyz0123456789-"
    last_dash = False
    for ch in name.lower():
        if ch in valid:
            cleaned.append(ch)
            last_dash = ch == "-"
        else:
            if not last_dash:
                cleaned.append("-")
                last_dash = True
    return "".join(cleaned).strip("-") or "job"


class SkyPilotRunner(Runner):
    """
    Runner for research problems using SkyPilot.

    Executes evaluations on cloud VMs with support for:
    - Auto-scaling resources based on problem requirements
    - GPU provisioning
    - Custom Docker images (from config.yaml)
    """

    DEFAULT_CLOUD = "gcp"
    DEFAULT_CPUS = "8+"
    DEFAULT_MEMORY = "16+"
    DEFAULT_DISK_SIZE = 50
    DEFAULT_GPU = "L4:1"
    DEFAULT_TIMEOUT = 1800  # 30 minutes
    DEFAULT_IDLE_TIMEOUT = 10  # 10 minutes

    def __init__(
        self,
        base_dir: Optional[Path] = None,
        cloud: str = DEFAULT_CLOUD,
        region: Optional[str] = None,
        keep_cluster: bool = False,
        idle_timeout: Optional[int] = DEFAULT_IDLE_TIMEOUT,
        bucket_url: Optional[str] = None,
    ):
        """
        Initialize SkyPilotRunner.

        Args:
            base_dir: Base directory of Frontier-CS repo
            cloud: Cloud provider (gcp, aws, azure)
            region: Cloud region (optional)
            keep_cluster: Keep cluster running after evaluation (disables autostop)
            idle_timeout: Minutes of idleness before autostop (default: 10, None to disable)
            bucket_url: Optional bucket URL for result storage (s3://... or gs://...)
                       If provided, results are written to bucket instead of fetched via scp
        """
        self.base_dir = base_dir or self._find_base_dir()
        self.research_dir = self.base_dir / "research"
        self.cloud = cloud
        self.region = region
        self.keep_cluster = keep_cluster
        self.idle_timeout = idle_timeout if not keep_cluster else None
        self.bucket_url = bucket_url

    def _find_base_dir(self) -> Path:
        """Find the Frontier-CS base directory."""
        # src/frontier_cs/runner/skypilot.py -> repo root
        base = Path(__file__).parents[3]
        if not (base / "research").is_dir():
            raise RuntimeError(f"research/ not found in {base}")
        return base

    def get_problem_path(self, problem_id: str) -> Path:
        """Get the path to a research problem directory.

        With nested solution structure, problem_id is already the nested path
        (e.g., "cant_be_late/high_availability_loose_deadline_large_overhead").
        """
        return self.research_dir / "problems" / problem_id

    def evaluate(
        self,
        problem_id: str,
        solution_code: str,
        *,
        timeout: Optional[int] = None,
        solution_id: Optional[str] = None,
    ) -> EvaluationResult:
        """
        Evaluate a solution using SkyPilot.

        Args:
            problem_id: Problem ID (e.g., "flash_attn")
            solution_code: Python solution code
            timeout: Optional timeout in seconds
            solution_id: Optional solution ID for bucket storage (forms pair_id with problem_id)

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
        with tempfile.TemporaryDirectory(prefix="frontier_sky_") as temp_dir:
            temp_path = Path(temp_dir)
            solution_path = temp_path / "solution.py"
            solution_path.write_text(solution_code, encoding="utf-8")

            return self._run_evaluation(problem_id, problem_path, solution_path, timeout, solution_id)

    def evaluate_file(
        self,
        problem_id: str,
        solution_path: Path,
        *,
        timeout: Optional[int] = None,
        solution_id: Optional[str] = None,
    ) -> EvaluationResult:
        """Evaluate a solution file using SkyPilot."""
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

        return self._run_evaluation(problem_id, problem_path, solution_path, timeout, solution_id)

    def _run_evaluation(
        self,
        problem_id: str,
        problem_path: Path,
        solution_path: Path,
        timeout: Optional[int],
        solution_id: Optional[str] = None,
    ) -> EvaluationResult:
        """Run evaluation on SkyPilot."""
        import sky

        start_time = time.time()

        # Load config from config.yaml
        runtime_config = load_runtime_config(problem_path)
        docker_config = runtime_config.docker
        res = runtime_config.resources

        # Determine resources
        accelerators = res.accelerators
        if not accelerators and docker_config.gpu:
            accelerators = self.DEFAULT_GPU
        if not accelerators and runtime_config.requires_gpu:
            accelerators = self.DEFAULT_GPU

        # Determine timeout
        effective_timeout = timeout or runtime_config.timeout_seconds or self.DEFAULT_TIMEOUT

        # Create cluster name with date to avoid conflicts between runs
        date_str = datetime.now().strftime("%m%d%H%M")
        digest = hashlib.md5(f"{problem_id}-{date_str}".encode()).hexdigest()[:8]
        cluster_name = _sanitize_name(f"eval-{problem_id}-{digest}")[:63]

        # Build pair_id for bucket storage
        pair_id = f"{solution_id}:{problem_id}" if solution_id else None

        # Create workspace and task
        with tempfile.TemporaryDirectory(prefix="frontier_sky_workspace_") as workspace_dir:
            workspace = Path(workspace_dir)
            file_mounts = self._setup_mounts(workspace, problem_id, problem_path, solution_path)

            # Add bucket mount if using bucket storage
            if self.bucket_url:
                results_url = f"{self.bucket_url.rstrip('/')}/results"
                file_mounts["~/results_bucket"] = {
                    "source": results_url,
                    "mode": "MOUNT",
                }

            # Build SkyPilot resources
            resources = sky.Resources(
                cloud=res.cloud or self.cloud,
                region=res.region or self.region,
                cpus=res.cpus or self.DEFAULT_CPUS,
                memory=res.memory or self.DEFAULT_MEMORY,
                accelerators=accelerators,
                disk_size=res.disk_size or self.DEFAULT_DISK_SIZE,
                instance_type=res.instance_type,
                image_id=res.image_id,
            )

            # Build task
            run_script = self._get_run_script(
                problem_id,
                docker_config.image,
                docker_config.gpu,
                docker_config.dind,
                pair_id=pair_id if self.bucket_url else None,
            )
            task = sky.Task(
                name=cluster_name,
                setup=self._get_setup_script(),
                run=run_script,
                file_mounts=file_mounts,
            )
            task.set_resources(resources)

            # Launch and wait
            try:
                request_id = sky.launch(
                    task,
                    cluster_name=cluster_name,
                    idle_minutes_to_autostop=self.idle_timeout,
                )
                result = sky.stream_and_get(request_id)

                job_id = result[0] if isinstance(result, tuple) and len(result) > 0 else None
                handle = result[1] if isinstance(result, tuple) and len(result) > 1 else None

                # Wait for completion
                exit_code = 0
                if job_id is not None:
                    exit_code = sky.tail_logs(cluster_name, job_id, follow=True)

                duration = time.time() - start_time

                # Fetch results (bucket mode writes directly, scp mode fetches after)
                if self.bucket_url:
                    # Results already written to bucket by run script
                    # Return placeholder - caller should read from bucket
                    return EvaluationResult(
                        problem_id=problem_id,
                        status=EvaluationStatus.SUCCESS,
                        message="Results written to bucket",
                        duration_seconds=duration,
                    )
                else:
                    # Legacy scp mode - try to fetch score even if exit_code != 0
                    score, score_unbounded, logs = self._fetch_results(cluster_name, handle)

                    # If we got a score, treat as success (even if exit_code != 0)
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
                        message=f"Remote job failed with exit code {exit_code}",
                        logs=logs,
                        duration_seconds=duration,
                    )

            except Exception as e:
                return EvaluationResult(
                    problem_id=problem_id,
                    status=EvaluationStatus.ERROR,
                    message=str(e),
                    duration_seconds=time.time() - start_time,
                )

            finally:
                # Only down immediately if no autostop and not keeping cluster
                if not self.keep_cluster and self.idle_timeout is None:
                    try:
                        down_request = sky.down(cluster_name)
                        sky.stream_and_get(down_request)
                    except Exception:
                        pass

    def _setup_mounts(
        self,
        workspace: Path,
        problem_id: str,
        problem_path: Path,
        solution_path: Path,
    ) -> dict:
        """Set up file mounts for SkyPilot."""
        mounts = {}
        remote_base = "~/sky_workdir"

        # Mount problem
        mounts[f"{remote_base}/research/{problem_id}"] = str(problem_path.resolve())

        # Mount common directories
        parts = problem_id.split("/")
        for i in range(1, len(parts)):
            parent = "/".join(parts[:i])
            common_dir = self.research_dir / "problems" / parent / "common"
            if common_dir.is_dir():
                mounts[f"{remote_base}/research/{parent}/common"] = str(common_dir.resolve())

        # Mount solution
        solution_dir = workspace / "solution"
        solution_dir.mkdir(parents=True)
        shutil.copy2(solution_path, solution_dir / "solution.py")
        mounts[f"{remote_base}/solution"] = str(solution_dir.resolve())

        return mounts

    def _get_setup_script(self) -> str:
        """Get setup script for SkyPilot task."""
        return textwrap.dedent("""\
            set -euo pipefail

            # Install Docker
            if ! command -v docker &>/dev/null; then
                curl -fsSL https://get.docker.com | sudo sh
                sudo usermod -aG docker $USER
                sudo systemctl start docker
            fi

            # Make scripts executable
            find ~/sky_workdir -name '*.sh' -exec chmod +x {} \\; 2>/dev/null || true
        """)

    def _get_run_script(
        self,
        problem_id: str,
        docker_image: str,
        gpu: bool,
        dind: bool,
        pair_id: Optional[str] = None,
    ) -> str:
        """Get run script for SkyPilot task."""
        gpu_flags = "--gpus all" if gpu else ""
        dind_flags = '-v /var/run/docker.sock:/var/run/docker.sock' if dind else ""

        # Build bucket write command if pair_id is provided
        if pair_id:
            # Escape pair_id for shell and generate safe filename
            safe_pair_id = pair_id.replace(":", "__")
            bucket_write = textwrap.dedent(f'''
            # Write result to bucket as JSON
            SCORE=$(cat /results/score.txt 2>/dev/null || echo "")
            TIMESTAMP=$(date -Is)
            cat > ~/results_bucket/{safe_pair_id}.json << RESULT_EOF
            {{
              "pair_id": "{pair_id}",
              "score": ${{SCORE:-null}},
              "status": "success",
              "message": null,
              "duration_seconds": $SECONDS,
              "timestamp": "$TIMESTAMP",
              "logs": null
            }}
            RESULT_EOF
            echo "Result written to bucket: {safe_pair_id}.json"
            ''')
        else:
            bucket_write = ""

        return textwrap.dedent(f"""\
            set -euo pipefail
            SECONDS=0
            cd ~/sky_workdir

            # Create results directory
            mkdir -p results

            # Run evaluation in Docker
            docker run --rm {gpu_flags} {dind_flags} \\
                -v "$(pwd):/workspace:ro" \\
                -v "$(pwd)/results:/results" \\
                -w /work \\
                "{docker_image}" \\
                bash -c '
                    set -euo pipefail
                    cp -r /workspace/* /work/

                    # Make all scripts executable
                    find /work -name "*.sh" -exec chmod +x {{}} \\;

                    # Create execution_env and copy solution BEFORE set_up_env.sh
                    # (some scripts expect this structure to exist)
                    mkdir -p /work/execution_env/solution_env
                    cp /work/solution/solution.py /work/execution_env/solution_env/

                    # Create symlink at /execution_env for scripts using wrong relative paths
                    # (e.g., ../../../execution_env from nested problem dirs resolves to /execution_env)
                    ln -sfn /work/execution_env /execution_env 2>/dev/null || true

                    cd /work/research/{problem_id}

                    # Install uv if not present (needed by set_up_env.sh)
                    if ! command -v uv &>/dev/null; then
                        curl -LsSf https://astral.sh/uv/install.sh | sh
                        export PATH="$HOME/.local/bin:$PATH"
                    fi

                    # Setup environment
                    if [ -f set_up_env.sh ]; then
                        ./set_up_env.sh
                    fi

                    # Run evaluation
                    ./evaluate.sh | tee /results/output.txt

                    # Extract score (last line with number(s): "85.5" or "85.5 120.3")
                    grep -E "^-?[0-9]+\\.?[0-9]*(\\s+-?[0-9]+\\.?[0-9]*)?$" /results/output.txt | tail -1 > /results/score.txt || true
                '
            {bucket_write}
        """)

    def _fetch_results(self, cluster_name: str, handle: object) -> Tuple[Optional[float], Optional[float], Optional[str]]:
        """Fetch results from remote cluster via scp.

        Returns (score, score_unbounded, logs).
        """
        score = None
        score_unbounded = None
        logs = None

        with tempfile.TemporaryDirectory(prefix="frontier_results_") as temp_dir:
            temp_path = Path(temp_dir)

            # Try to scp results
            try:
                result = subprocess.run(
                    ["scp", "-r", "-o", "StrictHostKeyChecking=no",
                     f"{cluster_name}:~/sky_workdir/results", str(temp_path)],
                    capture_output=True,
                    text=True,
                    timeout=60,
                )

                if result.returncode == 0:
                    results_dir = temp_path / "results"

                    # Read score (format: "85.5" or "85.5 120.3")
                    score_file = results_dir / "score.txt"
                    if score_file.exists():
                        score_text = score_file.read_text().strip()
                        if score_text:
                            parts = score_text.split()
                            try:
                                score = float(parts[0])
                                score_unbounded = float(parts[1]) if len(parts) > 1 else score
                            except (ValueError, IndexError):
                                pass

                    # Read logs
                    output_file = results_dir / "output.txt"
                    if output_file.exists():
                        logs = output_file.read_text()

            except (subprocess.TimeoutExpired, Exception):
                pass

        return score, score_unbounded, logs

    # =========================================================================
    # Cluster Pool Methods - For efficient batch evaluation with cluster reuse
    # =========================================================================

    def create_cluster(
        self,
        cluster_name: str,
        *,
        accelerators: Optional[str] = None,
        cpus: Optional[str] = None,
        memory: Optional[str] = None,
        disk_size: Optional[int] = None,
    ) -> bool:
        """
        Create a cluster for reuse across multiple evaluations.

        Args:
            cluster_name: Name for the cluster
            accelerators: GPU spec (e.g., "T4:1", "L4:1")
            cpus: CPU spec (e.g., "8+")
            memory: Memory spec (e.g., "16+")
            disk_size: Disk size in GB

        Returns:
            True if cluster was created successfully
        """
        import sky

        resources = sky.Resources(
            cloud=self.cloud,
            region=self.region,
            cpus=cpus or self.DEFAULT_CPUS,
            memory=memory or self.DEFAULT_MEMORY,
            accelerators=accelerators or self.DEFAULT_GPU,
            disk_size=disk_size or self.DEFAULT_DISK_SIZE,
        )

        task = sky.Task(
            name=f"setup-{cluster_name}",
            setup=self._get_setup_script(),
            run="echo 'Cluster ready'",
        )
        task.set_resources(resources)

        try:
            request_id = sky.launch(
                task,
                cluster_name=cluster_name,
                idle_minutes_to_autostop=self.idle_timeout,
            )
            sky.stream_and_get(request_id)
            return True
        except Exception as e:
            print(f"Failed to create cluster {cluster_name}: {e}")
            return False

    def exec_on_cluster(
        self,
        cluster_name: str,
        problem_id: str,
        solution_path: Path,
        *,
        timeout: Optional[int] = None,
        solution_id: Optional[str] = None,
    ) -> EvaluationResult:
        """
        Execute evaluation on an existing cluster using sky.launch.

        Uses sky.launch instead of sky.exec because:
        - sky.exec does NOT sync file_mounts (only workdir)
        - sky.launch with existing cluster will:
          1. Skip provisioning (cluster already UP)
          2. Sync file_mounts
          3. Skip setup (provisioning was skipped)
          4. Execute the task

        Args:
            cluster_name: Name of existing cluster
            problem_id: Problem ID
            solution_path: Path to solution file
            timeout: Optional timeout in seconds
            solution_id: Optional solution ID

        Returns:
            EvaluationResult with score and status
        """
        import sky

        start_time = time.time()

        problem_path = self.get_problem_path(problem_id)
        if not problem_path.exists():
            return EvaluationResult(
                problem_id=problem_id,
                status=EvaluationStatus.ERROR,
                message=f"Problem not found: {problem_path}",
            )

        if not solution_path.exists():
            return EvaluationResult(
                problem_id=problem_id,
                status=EvaluationStatus.ERROR,
                message=f"Solution file not found: {solution_path}",
            )

        # Load config
        runtime_config = load_runtime_config(problem_path)
        docker_config = runtime_config.docker

        # Create workspace with file mounts
        with tempfile.TemporaryDirectory(prefix="frontier_exec_") as workspace_dir:
            workspace = Path(workspace_dir)
            file_mounts = self._setup_mounts(workspace, problem_id, problem_path, solution_path)

            # Build task with file_mounts
            run_script = self._get_run_script(
                problem_id,
                docker_config.image,
                docker_config.gpu,
                docker_config.dind,
            )
            task = sky.Task(
                name=f"eval-{problem_id}",
                run=run_script,
                file_mounts=file_mounts,
            )

            try:
                # Use sky.launch on existing cluster
                # - Skips provisioning (cluster already UP with same config)
                # - Syncs file_mounts
                # - Skips setup (provisioning was skipped)
                # - Executes the task
                request_id = sky.launch(
                    task,
                    cluster_name=cluster_name,
                    idle_minutes_to_autostop=self.idle_timeout,
                )
                result = sky.stream_and_get(request_id)

                job_id = result[0] if isinstance(result, tuple) and len(result) > 0 else None
                handle = result[1] if isinstance(result, tuple) and len(result) > 1 else None

                # Wait for completion
                exit_code = 0
                if job_id is not None:
                    exit_code = sky.tail_logs(cluster_name, job_id, follow=True)

                duration = time.time() - start_time

                # Fetch results
                score, score_unbounded, logs = self._fetch_results(cluster_name, handle)

                if score is not None:
                    return EvaluationResult(
                        problem_id=problem_id,
                        score=score,
                        score_unbounded=score_unbounded,
                        status=EvaluationStatus.SUCCESS,
                        logs=logs,
                        duration_seconds=duration,
                    )

                return EvaluationResult(
                    problem_id=problem_id,
                    status=EvaluationStatus.ERROR,
                    message=f"Job failed with exit code {exit_code}",
                    logs=logs,
                    duration_seconds=duration,
                )

            except Exception as e:
                return EvaluationResult(
                    problem_id=problem_id,
                    status=EvaluationStatus.ERROR,
                    message=str(e),
                    duration_seconds=time.time() - start_time,
                )

    @staticmethod
    def down_cluster(cluster_name: str) -> bool:
        """Terminate a cluster."""
        import sky

        try:
            request_id = sky.down(cluster_name)
            sky.stream_and_get(request_id)
            return True
        except Exception as e:
            print(f"Failed to terminate cluster {cluster_name}: {e}")
            return False

    @staticmethod
    def down_clusters(cluster_names: list) -> None:
        """Terminate multiple clusters in parallel."""
        import sky
        from concurrent.futures import ThreadPoolExecutor

        def down_one(name):
            try:
                request_id = sky.down(name)
                sky.stream_and_get(request_id)
            except Exception:
                pass

        with ThreadPoolExecutor(max_workers=len(cluster_names)) as executor:
            executor.map(down_one, cluster_names)
