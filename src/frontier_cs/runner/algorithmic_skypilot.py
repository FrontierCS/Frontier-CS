"""
SkyPilot runner for algorithmic problems.

Automatically launches a go-judge VM on cloud and uses it for evaluation.
Uses SkyPilot Python API instead of subprocess calls.
"""

import textwrap
import time
from pathlib import Path
from typing import Optional

import requests

from .algorithmic import AlgorithmicRunner
from .base import EvaluationResult, EvaluationStatus


class AlgorithmicSkyPilotRunner(AlgorithmicRunner):
    """
    Runner that auto-launches go-judge on SkyPilot.

    On first evaluation, launches a cloud VM with go-judge if not already running.
    Subsequent evaluations reuse the same cluster until it autostops.
    """

    CLUSTER_NAME = "algo-judge"
    DEFAULT_IDLE_TIMEOUT = 10  # minutes
    DEFAULT_CLOUD = "gcp"
    DEFAULT_CPUS = "4+"
    DEFAULT_MEMORY = "8+"
    DEFAULT_DISK_SIZE = 50

    def __init__(
        self,
        base_dir: Optional[Path] = None,
        cloud: str = DEFAULT_CLOUD,
        region: Optional[str] = None,
        keep_cluster: bool = False,
        idle_timeout: Optional[int] = DEFAULT_IDLE_TIMEOUT,
    ):
        """
        Initialize AlgorithmicSkyPilotRunner.

        Args:
            base_dir: Base directory of Frontier-CS repo (auto-detected if None)
            cloud: Cloud provider (gcp, aws, azure)
            region: Cloud region (optional)
            keep_cluster: Keep cluster running after evaluation (disables autostop)
            idle_timeout: Minutes of idleness before autostop (default: 10, None to disable)
        """
        # Initialize parent class with placeholder URL (will be updated when cluster is ready)
        super().__init__(judge_url="http://localhost:8081")

        self.base_dir = base_dir or self._find_base_dir()
        self.cloud = cloud
        self.region = region
        self.keep_cluster = keep_cluster
        self.idle_timeout = idle_timeout if not keep_cluster else None
        self._judge_url: Optional[str] = None
        self._initialized = False

    def _find_base_dir(self) -> Path:
        """Find the Frontier-CS base directory."""
        candidates = [
            Path(__file__).parents[3],
            Path.cwd(),
            Path.cwd().parent,
        ]
        for candidate in candidates:
            if (candidate / "algorithmic").is_dir() and (candidate / "pyproject.toml").exists():
                return candidate
        raise RuntimeError("Could not find Frontier-CS base directory")

    def _get_cluster_status(self) -> Optional[str]:
        """Get the status of the algo-judge cluster."""
        import sky

        try:
            clusters = sky.status(cluster_names=[self.CLUSTER_NAME])
            if clusters:
                record = clusters[0]
                # sky.status returns records with 'status' attribute
                if hasattr(record, "status"):
                    return str(record.status)
                elif isinstance(record, dict):
                    return record.get("status")
        except Exception:
            pass
        return None

    def _get_cluster_ip(self) -> Optional[str]:
        """Get the IP of the algo-judge cluster if running."""
        import sky

        try:
            clusters = sky.status(cluster_names=[self.CLUSTER_NAME])
            if clusters:
                record = clusters[0]
                # Check status
                status = None
                if hasattr(record, "status"):
                    status = str(record.status)
                elif isinstance(record, dict):
                    status = record.get("status")

                if status == "UP":
                    # Get handle
                    handle = None
                    if hasattr(record, "handle"):
                        handle = record.handle
                    elif isinstance(record, dict):
                        handle = record.get("handle")

                    if handle and hasattr(handle, "head_ip"):
                        return handle.head_ip
        except Exception:
            pass
        return None

    def _is_cluster_running(self) -> bool:
        """Check if the algo-judge cluster is running."""
        status = self._get_cluster_status()
        return status == "UP"

    def _launch_cluster(self) -> bool:
        """Launch the algo-judge cluster using SkyPilot Python API."""
        import sky

        print(f"Launching cluster {self.CLUSTER_NAME} on {self.cloud}... (this may take a few minutes)")

        # Build resources
        resources = sky.Resources(
            cpus=self.DEFAULT_CPUS,
            memory=self.DEFAULT_MEMORY,
            disk_size=self.DEFAULT_DISK_SIZE,
            ports=["8081"],
        )

        # Build task
        task = sky.Task(
            name=self.CLUSTER_NAME,
            setup=self._get_setup_script(),
            run=self._get_run_script(),
            workdir=str(self.base_dir / "algorithmic"),
        )
        task.set_resources(resources)

        try:
            request_id = sky.launch(
                task,
                cluster_name=self.CLUSTER_NAME,
                idle_minutes_to_autostop=self.idle_timeout,
            )
            # Wait for launch to complete
            sky.stream_and_get(request_id)
            print(f"Cluster {self.CLUSTER_NAME} launched successfully")
            return True
        except Exception as e:
            print(f"Failed to launch cluster: {e}")
            return False

    def _get_setup_script(self) -> str:
        """Get setup script for go-judge cluster."""
        return textwrap.dedent("""\
            set -euo pipefail

            # Install Docker
            if ! command -v docker &>/dev/null; then
                curl -fsSL https://get.docker.com | sudo sh
                sudo usermod -aG docker $USER
                sudo systemctl start docker
                sudo systemctl enable docker
            fi

            # Install docker-compose
            if ! command -v docker-compose &>/dev/null; then
                sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" \\
                    -o /usr/local/bin/docker-compose
                sudo chmod +x /usr/local/bin/docker-compose
            fi
        """)

    def _get_run_script(self) -> str:
        """Get run script for go-judge service."""
        return textwrap.dedent("""\
            set -euo pipefail

            # Build and start go-judge service
            echo "Building and starting go-judge..."
            sudo docker-compose up --build -d

            # Wait for service to be ready
            echo "Waiting for judge service to be ready..."
            for i in {1..30}; do
                if curl -s http://localhost:8081/problems >/dev/null 2>&1; then
                    echo "Judge service is ready!"
                    break
                fi
                sleep 2
            done

            # Show status
            echo ""
            echo "=========================================="
            echo "Go-Judge service is running on port 8081"
            echo "=========================================="
            echo ""
            echo "Service started in background. Use 'sudo docker-compose logs -f' to view logs."
        """)

    def _wait_for_service(self, ip: str, timeout: int = 120) -> bool:
        """Wait for the judge service to be ready."""
        url = f"http://{ip}:8081/problems"
        start = time.time()

        while time.time() - start < timeout:
            try:
                response = requests.get(url, timeout=5)
                if response.status_code == 200:
                    return True
            except requests.RequestException:
                pass
            time.sleep(2)

        return False

    def _ensure_cluster(self) -> str:
        """Ensure the cluster is running and return judge URL."""
        if self._judge_url and self._initialized:
            # Verify it's still accessible
            try:
                requests.get(f"{self._judge_url}/problems", timeout=5)
                return self._judge_url
            except requests.RequestException:
                # Cluster may have stopped, re-check
                self._initialized = False

        # Check if cluster is running
        ip = self._get_cluster_ip()

        if ip:
            # Cluster exists, check if service is ready
            print(f"Found existing cluster at {ip}")
            if self._wait_for_service(ip, timeout=30):
                self._judge_url = f"http://{ip}:8081"
                self._initialized = True
                return self._judge_url

        # Need to launch cluster
        if not self._launch_cluster():
            raise RuntimeError("Failed to launch algo-judge cluster")

        # Wait a bit for the service to start after launch
        time.sleep(5)

        # Get IP and wait for service
        ip = self._get_cluster_ip()
        if not ip:
            raise RuntimeError("Could not get cluster IP after launch")

        print(f"Waiting for judge service at {ip}:8081...")
        if not self._wait_for_service(ip, timeout=120):
            raise RuntimeError("Judge service did not become ready")

        self._judge_url = f"http://{ip}:8081"
        self._initialized = True
        print(f"Judge service ready at {self._judge_url}")
        return self._judge_url

    def evaluate(
        self,
        problem_id: str,
        solution_code: str,
        *,
        timeout: Optional[int] = None,
        lang: str = "cpp",
        unbounded: bool = False,
    ) -> EvaluationResult:
        """
        Evaluate a solution using cloud-based go-judge.

        Automatically launches the judge cluster if not running.
        """
        try:
            judge_url = self._ensure_cluster()
        except Exception as e:
            return EvaluationResult(
                problem_id=str(problem_id),
                status=EvaluationStatus.ERROR,
                message=f"Failed to start cloud judge: {e}",
            )

        # Use parent class with the cloud judge URL
        self.judge_url = judge_url
        self.session = requests.Session()
        return super().evaluate(
            problem_id,
            solution_code,
            timeout=timeout,
            lang=lang,
            unbounded=unbounded,
        )

    def evaluate_file(
        self,
        problem_id: str,
        solution_path: Path,
        *,
        timeout: Optional[int] = None,
    ) -> EvaluationResult:
        """Evaluate a solution file using cloud-based go-judge."""
        if not solution_path.exists():
            return EvaluationResult(
                problem_id=str(problem_id),
                status=EvaluationStatus.ERROR,
                message=f"Solution file not found: {solution_path}",
            )

        code = solution_path.read_text(encoding="utf-8")
        lang = "cpp" if solution_path.suffix in [".cpp", ".cc", ".cxx"] else "cpp"
        return self.evaluate(problem_id, code, timeout=timeout, lang=lang)

    def stop_cluster(self) -> bool:
        """Stop the algo-judge cluster."""
        import sky

        try:
            print(f"Stopping cluster {self.CLUSTER_NAME}...")
            request_id = sky.down(self.CLUSTER_NAME)
            sky.stream_and_get(request_id)
            self._initialized = False
            self._judge_url = None
            print(f"Cluster {self.CLUSTER_NAME} stopped")
            return True
        except Exception as e:
            print(f"Failed to stop cluster: {e}")
            return False
