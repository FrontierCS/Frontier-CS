"""
Runner for algorithmic problems using the judge server.
"""

import logging
import os
import subprocess
import threading
import time
from pathlib import Path
from typing import Optional

import requests

from .base import Runner, EvaluationResult, EvaluationStatus

logger = logging.getLogger(__name__)


class AlgorithmicRunner(Runner):
    """
    Runner for algorithmic problems.

    Submits solutions to the judge server (go-judge) and polls for results.
    Automatically starts the judge via docker-compose if not running.
    """

    DEFAULT_JUDGE_URL = "http://localhost:8081"
    DEFAULT_POLL_INTERVAL = 2  # seconds

    # Class-level lock to prevent multiple threads from starting judge simultaneously
    _startup_lock = threading.Lock()

    def __init__(
        self,
        judge_url: str = DEFAULT_JUDGE_URL,
        poll_interval: float = DEFAULT_POLL_INTERVAL,
        base_dir: Optional[Path] = None,
        problems_dir: Optional[Path] = None,
        auto_start: bool = True,
    ):
        self.judge_url = judge_url.rstrip("/")
        self.poll_interval = poll_interval
        self.session = requests.Session()
        self.base_dir = base_dir or self._find_base_dir()
        self.problems_dir = problems_dir  # Not used directly, but stored for consistency
        self.auto_start = auto_start
        self._judge_started = False

    def _find_base_dir(self) -> Path:
        """Find the Frontier-CS base directory."""
        # src/frontier_cs/runner/algorithmic.py -> repo root
        base = Path(__file__).parents[3]
        if not (base / "algorithmic").is_dir():
            raise RuntimeError(f"algorithmic/ not found in {base}")
        return base

    def _is_judge_available(self) -> bool:
        """Check if judge server is available."""
        try:
            response = self.session.get(f"{self.judge_url}/problems", timeout=5)
            return response.status_code == 200
        except requests.RequestException:
            return False

    def _start_judge(self) -> bool:
        """Start judge server via docker compose."""
        compose_dir = self.base_dir / "algorithmic"
        compose_file = compose_dir / "docker-compose.yml"

        if not compose_file.exists():
            logger.error(f"docker-compose.yml not found: {compose_file}")
            return False

        # Build docker compose command
        cmd = ["docker", "compose", "up", "-d"]

        # Build environment with optional problems_dir override
        env = None
        if self.problems_dir:
            problems_path = Path(self.problems_dir).resolve()
            logger.info(f"Using problems from: {problems_path}")
            env = os.environ.copy()
            env["PROBLEMS_DIR"] = str(problems_path)

        logger.info(f"Starting judge server in {compose_dir}")
        try:
            result = subprocess.run(
                cmd,
                cwd=compose_dir,
                capture_output=True,
                text=True,
                timeout=120,
                env=env,
            )
            if result.returncode != 0:
                logger.error(f"docker compose failed: {result.stderr.strip()}")
                return False
            logger.info("docker compose started successfully")
            return True
        except subprocess.TimeoutExpired:
            logger.error("docker compose timed out after 120s")
            return False
        except FileNotFoundError:
            logger.error("docker command not found - is Docker installed?")
            return False

    def _wait_for_judge(self, timeout: int = 60) -> bool:
        """Wait for judge server to become available."""
        logger.info(f"Waiting for judge server at {self.judge_url} (timeout: {timeout}s)")
        start = time.time()
        while time.time() - start < timeout:
            if self._is_judge_available():
                elapsed = time.time() - start
                logger.info(f"Judge server ready ({elapsed:.1f}s)")
                return True
            time.sleep(2)
        logger.error(f"Judge server not ready after {timeout}s")
        return False

    def _ensure_judge(self) -> bool:
        """Ensure judge server is running, start if needed."""
        # Fast path: already started or available
        if self._judge_started or self._is_judge_available():
            self._judge_started = True
            return True

        # Use lock to prevent multiple threads from starting judge simultaneously
        with self._startup_lock:
            # Double-check after acquiring lock (another thread may have started it)
            if self._judge_started or self._is_judge_available():
                self._judge_started = True
                return True

            logger.info(f"Judge server not available at {self.judge_url}")

            if not self.auto_start:
                logger.error("auto_start disabled, cannot start judge automatically")
                return False

            if not self._start_judge():
                logger.error("Failed to start judge server")
                return False

            if not self._wait_for_judge():
                logger.error("Judge server failed to become ready")
                return False

            self._judge_started = True
            logger.info("Judge server is now running")
            return True

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
        Evaluate a solution for an algorithmic problem.

        Args:
            problem_id: Problem ID (numeric string or int)
            solution_code: C++ solution code
            timeout: Optional timeout in seconds
            lang: Programming language (default: cpp)
            unbounded: Deprecated for storage. Both bounded and unbounded scores
                       are always stored (score and score_unbounded fields).

        Returns:
            EvaluationResult with score and status
        """
        pid = str(problem_id)
        start_time = time.time()

        # Ensure judge is running
        if not self._ensure_judge():
            return EvaluationResult(
                problem_id=pid,
                status=EvaluationStatus.ERROR,
                message=f"Judge server at {self.judge_url} not available. "
                        f"Run 'docker compose up -d' in algorithmic/ or use --skypilot",
            )

        # Check for empty code
        if not solution_code or not solution_code.strip():
            return EvaluationResult(
                problem_id=pid,
                status=EvaluationStatus.ERROR,
                message="Empty code submission - please provide valid code",
            )

        # Submit solution
        sid = self._submit(pid, solution_code, lang)
        if sid is None:
            return EvaluationResult(
                problem_id=pid,
                status=EvaluationStatus.ERROR,
                message="Submission failed - judge server may be unavailable",
            )

        # Poll for result
        effective_timeout = timeout or self.DEFAULT_TIMEOUT
        result = self._poll_result(sid, effective_timeout)
        duration = time.time() - start_time

        if result is None:
            return EvaluationResult(
                problem_id=pid,
                status=EvaluationStatus.TIMEOUT,
                message=f"Evaluation timed out after {timeout}s",
                duration_seconds=duration,
            )

        status = result.get("status", "")
        if status == "error":
            # Build error message with available info
            error_msg = result.get("message") or result.get("error") or "Unknown error"
            logs = result.get("logs") or result.get("stderr") or ""
            if not result.get("message") and logs:
                # If no message but has logs, include first line of logs in message
                first_line = logs.strip().split("\n")[0][:200]
                error_msg = f"{error_msg}: {first_line}"
            return EvaluationResult(
                problem_id=pid,
                status=EvaluationStatus.ERROR,
                message=error_msg,
                logs=logs,
                duration_seconds=duration,
            )

        # Get both bounded and unbounded scores
        bounded_score = result.get("score", 0.0)
        unbounded_score = result.get("scoreUnbounded")

        # Always store bounded in score, unbounded in score_unbounded
        return EvaluationResult(
            problem_id=pid,
            score=bounded_score,
            score_unbounded=unbounded_score,
            status=EvaluationStatus.SUCCESS,
            duration_seconds=duration,
            metadata=result,
        )

    def evaluate_file(
        self,
        problem_id: str,
        solution_path: Path,
        *,
        timeout: Optional[int] = None,
        solution_id: Optional[str] = None,
        unbounded: bool = True,
    ) -> EvaluationResult:
        """Evaluate a solution file."""
        if not solution_path.exists():
            return EvaluationResult(
                problem_id=str(problem_id),
                status=EvaluationStatus.ERROR,
                message=f"Solution file not found: {solution_path}",
            )

        code = solution_path.read_text(encoding="utf-8")
        lang = "cpp" if solution_path.suffix in [".cpp", ".cc", ".cxx"] else "cpp"
        return self.evaluate(problem_id, code, timeout=timeout, lang=lang, unbounded=unbounded)

    def _submit(self, pid: str, code: str, lang: str) -> Optional[str]:
        """Submit solution to judge server."""
        ext = ".cpp" if lang == "cpp" else f".{lang}"
        files = {"code": (f"solution{ext}", code)}
        data = {"pid": pid, "lang": lang}

        try:
            response = self.session.post(
                f"{self.judge_url}/submit",
                files=files,
                data=data,
                timeout=30,
            )
            response.raise_for_status()
            return response.json().get("sid")
        except requests.RequestException:
            return None

    def _poll_result(
        self,
        sid: str,
        timeout: int,
    ) -> Optional[dict]:
        """Poll for evaluation result."""
        start = time.time()

        while True:
            if (time.time() - start) > timeout:
                return None

            try:
                response = self.session.get(
                    f"{self.judge_url}/result/{sid}",
                    timeout=10,
                )

                if response.status_code == 404:
                    time.sleep(self.poll_interval)
                    continue

                response.raise_for_status()
                result = response.json()

                if result.get("status") in ["done", "error"]:
                    return result

                time.sleep(self.poll_interval)

            except requests.RequestException:
                time.sleep(self.poll_interval)

    def list_problems(self) -> list:
        """List all available algorithmic problems."""
        try:
            response = self.session.get(f"{self.judge_url}/problems", timeout=10)
            response.raise_for_status()
            return response.json()
        except requests.RequestException:
            return []

    def get_problem_statement(self, problem_id: str) -> Optional[str]:
        """Get problem statement."""
        try:
            response = self.session.get(
                f"{self.judge_url}/problem/{problem_id}/statement",
                timeout=10,
            )
            response.raise_for_status()
            return response.text
        except requests.RequestException:
            return None
