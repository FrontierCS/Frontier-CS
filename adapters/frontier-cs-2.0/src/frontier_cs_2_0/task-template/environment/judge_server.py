#!/usr/bin/env python3
"""Black-box Frontier-CS 2.0 judge service for Harbor agent submissions."""

from __future__ import annotations

import importlib.util
import json
import os
import sys
import base64
import tarfile
import tempfile
import io
import time
import traceback
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

PROBLEM_EVALUATOR_PATH = Path("/judge/problem_evaluator.py")
MAX_SUBMISSION_BYTES = 30_000_000
MAX_ARCHIVE_BYTES = 20_000_000


def load_problem_evaluator():
    spec = importlib.util.spec_from_file_location(
        "frontier_cs_2_0_problem_evaluator", PROBLEM_EVALUATOR_PATH
    )
    if spec is None or spec.loader is None:
        raise RuntimeError(f"could not load evaluator from {PROBLEM_EVALUATOR_PATH}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


EVALUATOR = None
READY = False
READY_PAYLOAD: dict[str, Any] = {"status": "starting"}


def prepare_evaluator() -> None:
    global EVALUATOR, READY, READY_PAYLOAD
    start = time.time()
    try:
        EVALUATOR = load_problem_evaluator()
        prepare = getattr(EVALUATOR, "prepare", None)
        if callable(prepare):
            payload = prepare()
        else:
            ensure = getattr(EVALUATOR, "_ensure_benchmark", None)
            payload = ensure() if callable(ensure) else {}
        elapsed = time.time() - start
        if not isinstance(payload, dict):
            payload = {}
        READY_PAYLOAD = {
            "status": "ok",
            "ready": True,
            "prepare_seconds": elapsed,
            **payload,
        }
        READY = True
        print(
            "[frontier judge] ready "
            + " ".join(f"{key}={value}" for key, value in READY_PAYLOAD.items()),
            flush=True,
        )
    except Exception as exc:
        READY_PAYLOAD = {
            "status": "error",
            "ready": False,
            "error": str(exc),
        }
        print(traceback.format_exc(), flush=True)


def normalize_result(result: Any) -> tuple[float, float, str, dict[str, Any]]:
    if not isinstance(result, tuple) or len(result) not in (3, 4):
        raise TypeError("evaluator must return (score, score_unbounded, message[, metrics])")
    score = float(result[0])
    score_unbounded = float(result[1])
    message = str(result[2])
    metrics = result[3] if len(result) == 4 else {}
    if not isinstance(metrics, dict):
        raise TypeError("evaluator metrics must be a dict")
    return score, score_unbounded, message, metrics


def evaluate_path(solution_path: Path) -> dict[str, Any]:
    if EVALUATOR is None:
        raise RuntimeError("problem evaluator is not loaded")
    score, score_unbounded, message, metrics = normalize_result(
        EVALUATOR.evaluate(str(solution_path))
    )
    return {
        "status": "done",
        "score": float(score),
        "score_unbounded": float(score_unbounded),
        "message": message,
        "metrics": metrics,
    }


def evaluate_code(code: str) -> dict[str, Any]:
    with tempfile.TemporaryDirectory(prefix="frontier_cs_2_0_submission_") as tmp:
        solution_path = Path(tmp) / "solution.py"
        solution_path.write_text(code, encoding="utf-8")
        return evaluate_path(solution_path)


def is_safe_tar_member(member: tarfile.TarInfo) -> bool:
    path = Path(member.name)
    return not path.is_absolute() and ".." not in path.parts


def evaluate_archive(archive_b64: str) -> dict[str, Any]:
    archive = base64.b64decode(archive_b64.encode("ascii"), validate=True)
    if len(archive) > MAX_ARCHIVE_BYTES:
        raise ValueError("submission archive too large")
    with tempfile.TemporaryDirectory(prefix="frontier_cs_2_0_project_") as tmp:
        root = Path(tmp) / "submission"
        root.mkdir()
        with tarfile.open(fileobj=io.BytesIO(archive), mode="r:gz") as tar:
            members = tar.getmembers()
            if not all(is_safe_tar_member(member) for member in members):
                raise ValueError("unsafe path in submission archive")
            tar.extractall(root)
        return evaluate_path(root)


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
            self._write_json(200 if READY else 503, READY_PAYLOAD)
            return
        self._write_json(404, {"status": "error", "error": "not found"})

    def do_POST(self) -> None:
        if self.path != "/evaluate":
            self._write_json(404, {"status": "error", "error": "not found"})
            return
        if not READY:
            self._write_json(
                503,
                {
                    "status": "error",
                    "score": 0.0,
                    "score_unbounded": 0.0,
                    "message": "judge is not ready",
                    "health": READY_PAYLOAD,
                },
            )
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
            submission_kind = payload.get("submission_kind", "file")
            if submission_kind == "directory":
                archive_b64 = payload.get("archive_b64")
                if not isinstance(archive_b64, str) or not archive_b64:
                    raise ValueError(
                        "directory submission must include archive_b64"
                    )
                self._write_json(200, evaluate_archive(archive_b64))
                return
            code = payload.get("code")
            if not isinstance(code, str) or not code.strip():
                raise ValueError(
                    "file submission must include non-empty string field 'code'"
                )
            self._write_json(200, evaluate_code(code))
        except Exception:
            print(traceback.format_exc(), flush=True)
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
    threading.Thread(target=prepare_evaluator, daemon=True).start()
    server.serve_forever()


if __name__ == "__main__":
    main()
