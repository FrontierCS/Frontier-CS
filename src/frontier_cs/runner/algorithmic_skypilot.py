"""
SkyPilot runner for algorithmic problems.

Automatically launches a go-judge VM on cloud and uses it for evaluation.
Uses SkyPilot Python API with sky-judge.yaml configuration.
"""

import logging
import time
from pathlib import Path
from typing import Any, Optional

import requests

from .algorithmic import AlgorithmicRunner
from .base import EvaluationResult, EvaluationStatus

logger = logging.getLogger(__name__)


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
        cloud: Optional[str] = None,
        region: Optional[str] = None,
        keep_cluster: bool = False,
        idle_timeout: Optional[int] = DEFAULT_IDLE_TIMEOUT,
    ):
        """
        Initialize AlgorithmicSkyPilotRunner.

        Args:
            base_dir: Base directory of Frontier-CS repo (auto-detected if None)
            cloud: Cloud provider override (default: use yaml config)
            region: Cloud region override (optional)
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
        # src/frontier_cs/runner/algorithmic_skypilot.py -> repo root
        base = Path(__file__).parents[3]
        if not (base / "algorithmic").is_dir():
            raise RuntimeError(f"algorithmic/ not found in {base}")
        return base

    def _get_yaml_path(self) -> Path:
        """Get path to sky-judge.yaml."""
        return self.base_dir / "algorithmic" / "sky-judge.yaml"

    def _get_cluster_info(self) -> tuple[Optional[str], Any]:
        """Get cluster status and handle.

        Returns:
            Tuple of (status, handle) where status is 'UP', 'STOPPED', etc.
            and handle contains cluster info including head_ip.
        """
        import sky

        try:
            clusters = sky.status(cluster_names=[self.CLUSTER_NAME])
            if clusters:
                record: dict[str, Any] = clusters[0]  # type: ignore[assignment]
                status = record.get("status")
                handle = record.get("handle")
                return (str(status) if status else None, handle)
        except Exception:
            pass
        return (None, None)

    def _get_cluster_status(self) -> Optional[str]:
        """Get the status of the algo-judge cluster."""
        status, _ = self._get_cluster_info()
        return status

    def _get_cluster_ip(self) -> Optional[str]:
        """Get the IP of the algo-judge cluster if running.

        Uses sky.status() to get cluster handle and extract head_ip.
        """
        status, handle = self._get_cluster_info()
        # Status could be string "UP" or enum ClusterStatus.UP
        is_up = status is not None and ("UP" in str(status).upper())
        if is_up and handle is not None:
            # Handle has head_ip attribute
            if hasattr(handle, "head_ip"):
                return handle.head_ip
        return None

    def _is_cluster_running(self) -> bool:
        """Check if the algo-judge cluster is running."""
        status = self._get_cluster_status()
        return status is not None and "UP" in str(status).upper()

    def _launch_cluster(self) -> Optional[str]:
        """Launch the algo-judge cluster using sky-judge.yaml.

        Returns:
            The cluster head IP if successful, None otherwise.
        """
        import sky

        yaml_path = self._get_yaml_path()
        if not yaml_path.exists():
            raise FileNotFoundError(f"sky-judge.yaml not found at {yaml_path}")

        logger.info(f"Launching cluster '{self.CLUSTER_NAME}' from {yaml_path}")

        try:
            task = sky.Task.from_yaml(str(yaml_path))

            # Set absolute path for file_mounts to avoid CWD issues
            algorithmic_dir = str(self.base_dir / "algorithmic")
            task.update_file_mounts({"~/algorithmic": algorithmic_dir})

            if self.cloud or self.region:
                resources = list(task.resources)[0] if task.resources else sky.Resources()
                new_resources = resources.copy(
                    cloud=self.cloud if self.cloud else resources.cloud,
                    region=self.region if self.region else resources.region,
                )
                task.set_resources(new_resources)

            request_id = sky.launch(
                task,
                cluster_name=self.CLUSTER_NAME,
                idle_minutes_to_autostop=self.idle_timeout,
            )
            # stream_and_get returns (job_id, handle) where handle has head_ip
            job_id, handle = sky.stream_and_get(request_id)
            logger.info(f"Cluster '{self.CLUSTER_NAME}' launched successfully")

            # Extract IP from handle
            if handle and hasattr(handle, 'head_ip'):
                return handle.head_ip
            return None
        except Exception as e:
            logger.exception(f"Failed to launch cluster: {e}")
            return None

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

        ip = self._get_cluster_ip()

        if ip:
            logger.info(f"Found existing cluster at {ip}")
            if self._wait_for_service(ip, timeout=30):
                self._judge_url = f"http://{ip}:8081"
                self._initialized = True
                return self._judge_url

        ip = self._launch_cluster()
        if not ip:
            # Fallback: try to get IP from status if launch didn't return it
            # May take a few seconds for cluster to be fully UP
            logger.info("Waiting for cluster IP to become available...")
            for attempt in range(10):
                time.sleep(3)
                ip = self._get_cluster_ip()
                if ip:
                    logger.info(f"Got cluster IP on attempt {attempt + 1}: {ip}")
                    break
        if not ip:
            raise RuntimeError("Could not get cluster IP after launch")

        logger.info(f"Waiting for judge service at {ip}:8081 (timeout: 120s)")
        if not self._wait_for_service(ip, timeout=120):
            raise RuntimeError("Judge service did not become ready after 120s")

        self._judge_url = f"http://{ip}:8081"
        self._initialized = True
        logger.info(f"Judge service ready at {self._judge_url}")
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
        solution_id: Optional[str] = None,
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
            logger.info(f"Stopping cluster '{self.CLUSTER_NAME}'")
            request_id = sky.down(self.CLUSTER_NAME)
            sky.stream_and_get(request_id)
            self._initialized = False
            self._judge_url = None
            logger.info(f"Cluster '{self.CLUSTER_NAME}' stopped")
            return True
        except Exception as e:
            logger.exception(f"Failed to stop cluster: {e}")
            return False
