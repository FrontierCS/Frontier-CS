#!/usr/bin/env python3
"""Black-box Frontier-CS 2.0 judge service for Harbor agent submissions."""

from __future__ import annotations

import importlib.util
import json
import os
import tempfile
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

PROBLEM_EVALUATOR_PATH = Path("/judge/problem_evaluator.py")
MAX_SUBMISSION_BYTES = 2_000_000


def load_problem_evaluator():
    spec = importlib.util.spec_from_file_location(
        "frontier_cs_2_0_problem_evaluator", PROBLEM_EVALUATOR_PATH
    )
    if spec is None or spec.loader is None:
        raise RuntimeError(f"could not load evaluator from {PROBLEM_EVALUATOR_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


EVALUATOR = load_problem_evaluator()


def evaluate_code(code: str) -> dict[str, Any]:
    with tempfile.TemporaryDirectory(prefix="frontier_cs_2_0_submission_") as tmp:
        solution_path = Path(tmp) / "solution.py"
        solution_path.write_text(code, encoding="utf-8")
        score, score_unbounded, message = EVALUATOR.evaluate(str(solution_path))
    return {
        "status": "done",
        "score": float(score),
        "score_unbounded": float(score_unbounded),
        "message": message,
    }


class JudgeHandler(BaseHTTPRequestHandler):
    server_version = "FrontierCS20Judge/1.0"

    def _write_json(self, status: int, payload: dict[str, Any]) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        if self.path == "/health":
            self._write_json(200, {"status": "ok"})
            return
        self._write_json(404, {"status": "error", "error": "not found"})

    def do_POST(self) -> None:
        if self.path != "/evaluate":
            self._write_json(404, {"status": "error", "error": "not found"})
            return

        try:
            content_length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            self._write_json(400, {"status": "error", "error": "invalid content length"})
            return

        if content_length <= 0:
            self._write_json(400, {"status": "error", "error": "empty request body"})
            return
        if content_length > MAX_SUBMISSION_BYTES:
            self._write_json(413, {"status": "error", "error": "submission too large"})
            return

        try:
            payload = json.loads(self.rfile.read(content_length).decode("utf-8"))
            code = payload.get("code")
            if not isinstance(code, str) or not code.strip():
                raise ValueError("request JSON must include non-empty string field 'code'")
            self._write_json(200, evaluate_code(code))
        except Exception:
            self._write_json(
                200,
                {
                    "status": "error",
                    "score": 0.0,
                    "score_unbounded": 0.0,
                    "message": "evaluation failed",
                },
            )

    def log_message(self, fmt: str, *args: object) -> None:
        return


def main() -> None:
    port = int(os.environ.get("PORT", "8082"))
    server = ThreadingHTTPServer(("0.0.0.0", port), JudgeHandler)
    server.serve_forever()


if __name__ == "__main__":
    main()
