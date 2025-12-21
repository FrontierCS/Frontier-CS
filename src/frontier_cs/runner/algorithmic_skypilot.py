"""
SkyPilot runner for algorithmic problems.

Automatically launches a go-judge VM on cloud and uses it for evaluation.
"""

import subprocess
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

    def __init__(
        self,
        base_dir: Optional[Path] = None,
        cloud: str = "gcp",
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
            Path(__file__).parents[4],
            Path.cwd(),
            Path.cwd().parent,
        ]
        for candidate in candidates:
            if (candidate / "algorithmic").is_dir() and (candidate / "pyproject.toml").exists():
                return candidate
        raise RuntimeError("Could not find Frontier-CS base directory")

    def _get_cluster_ip(self) -> Optional[str]:
        """Get the IP of the algo-judge cluster if running."""
        try:
            result = subprocess.run(
                ["sky", "status", "--ip", self.CLUSTER_NAME],
                capture_output=True,
                text=True,
                timeout=30,
            )
            if result.returncode == 0:
                ip = result.stdout.strip()
                if ip and not ip.startswith("No"):
                    return ip
        except (subprocess.TimeoutExpired, Exception):
            pass
        return None

    def _is_cluster_running(self) -> bool:
        """Check if the algo-judge cluster is running."""
        try:
            result = subprocess.run(
                ["sky", "status", self.CLUSTER_NAME],
                capture_output=True,
                text=True,
                timeout=30,
            )
            return "UP" in result.stdout
        except (subprocess.TimeoutExpired, Exception):
            return False

    def _launch_cluster(self) -> bool:
        """Launch the algo-judge cluster."""
        yaml_path = self.base_dir / "algorithmic" / "sky-judge.yaml"
        if not yaml_path.exists():
            raise FileNotFoundError(f"sky-judge.yaml not found at {yaml_path}")

        cmd = [
            "sky", "launch", "-c", self.CLUSTER_NAME,
            str(yaml_path),
            "-y",  # auto-confirm
        ]

        if self.idle_timeout is not None:
            cmd.extend(["--idle-minutes-to-autostop", str(self.idle_timeout)])

        try:
            # Launch in background-ish mode (don't wait for logs to finish)
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=600,  # 10 minutes max for launch
            )
            return result.returncode == 0
        except subprocess.TimeoutExpired:
            return False

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
            if self._wait_for_service(ip, timeout=10):
                self._judge_url = f"http://{ip}:8081"
                self._initialized = True
                return self._judge_url

        # Need to launch cluster
        print(f"Launching {self.CLUSTER_NAME} cluster on {self.cloud}...")
        if not self._launch_cluster():
            raise RuntimeError("Failed to launch algo-judge cluster")

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
