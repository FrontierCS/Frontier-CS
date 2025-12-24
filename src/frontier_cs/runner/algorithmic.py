"""
Runner for algorithmic problems using the judge server.
"""

import time
from pathlib import Path
from typing import Optional

import requests

from .base import Runner, EvaluationResult, EvaluationStatus


class AlgorithmicRunner(Runner):
    """
    Runner for algorithmic problems.

    Submits solutions to the judge server (go-judge) and polls for results.
    """

    DEFAULT_JUDGE_URL = "http://localhost:8081"
    DEFAULT_POLL_INTERVAL = 2  # seconds

    def __init__(
        self,
        judge_url: str = DEFAULT_JUDGE_URL,
        poll_interval: float = DEFAULT_POLL_INTERVAL,
    ):
        self.judge_url = judge_url.rstrip("/")
        self.poll_interval = poll_interval
        self.session = requests.Session()

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
            unbounded: If True, use unbounded score (without clipping)

        Returns:
            EvaluationResult with score and status
        """
        pid = str(problem_id)
        start_time = time.time()

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
        result = self._poll_result(sid, timeout)
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
            return EvaluationResult(
                problem_id=pid,
                status=EvaluationStatus.ERROR,
                message=result.get("message", "Unknown error"),
                logs=result.get("logs"),
                duration_seconds=duration,
            )

        # Use unbounded score if requested and available
        score = result.get("scoreUnbounded" if unbounded else "score", 0.0)
        
        # Create result with both scores if available
        eval_result = EvaluationResult(
            problem_id=pid,
            score=score,
            status=EvaluationStatus.SUCCESS,
            duration_seconds=duration,
            metadata=result,
        )
        
        # Add unbounded score as attribute if available
        if "scoreUnbounded" in result:
            eval_result.score_unbounded = result["scoreUnbounded"]
        
        return eval_result

    def evaluate_file(
        self,
        problem_id: str,
        solution_path: Path,
        *,
        timeout: Optional[int] = None,
        solution_id: Optional[str] = None,
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
        return self.evaluate(problem_id, code, timeout=timeout, lang=lang)

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
        timeout: Optional[int] = None,
    ) -> Optional[dict]:
        """Poll for evaluation result."""
        start = time.time()

        while True:
            if timeout and (time.time() - start) > timeout:
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
