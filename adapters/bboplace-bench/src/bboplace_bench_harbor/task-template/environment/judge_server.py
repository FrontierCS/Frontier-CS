#!/usr/bin/env python3
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

from bboplace_runtime import (
    build_evaluator,
    evaluate_candidates,
    exact_problem_info,
    load_json,
)

TASK_INFO = load_json(os.environ.get("BBOPLACE_TASK_INFO", "/judge/task_info.json"))
REPO_DIR = Path(os.environ.get("BBOPLACE_REPO", "/opt/bboplace-bench"))
JUDGE_SUBMISSIONS_LOG = Path("/logs/judge/submissions.jsonl")
MAX_SUBMISSION_BYTES = 30_000_000
EVALUATOR = None


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def log_submission(record: dict[str, Any]) -> None:
    JUDGE_SUBMISSIONS_LOG.parent.mkdir(parents=True, exist_ok=True)
    with JUDGE_SUBMISSIONS_LOG.open("a", encoding="utf-8") as f:
        f.write(json.dumps({"ts": now_iso(), **record}, ensure_ascii=False) + "\n")


def read_submissions() -> list[dict[str, Any]]:
    if not JUDGE_SUBMISSIONS_LOG.exists():
        return []
    records: list[dict[str, Any]] = []
    for line in JUDGE_SUBMISSIONS_LOG.read_text(encoding="utf-8", errors="replace").splitlines():
        if not line.strip():
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(record, dict):
            records.append(record)
    return records


def get_evaluator():
    global EVALUATOR
    if EVALUATOR is None:
        EVALUATOR = build_evaluator(REPO_DIR, TASK_INFO)
    return EVALUATOR


def evaluate_candidate_payload(candidates: Any) -> dict[str, Any]:
    evaluator = get_evaluator()
    return evaluate_candidates(evaluator, TASK_INFO, candidates)


class JudgeHandler(BaseHTTPRequestHandler):
    server_version = "BBOPlaceJudge/1.0"

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
        if self.path == "/info":
            try:
                info = exact_problem_info(get_evaluator(), TASK_INFO, include_full_bounds=False)
                self._write_json(200, {"status": "ok", "info": info})
            except Exception as exc:
                self._write_json(200, {"status": "error", "error": str(exc)})
            return
        if self.path == "/submissions":
            self._write_json(200, {"status": "ok", "submissions": read_submissions()})
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
            submission_uuid = str(payload.get("submission_uuid") or "")
            if "candidates" not in payload:
                raise ValueError("request JSON must include field 'candidates'")
            result = evaluate_candidate_payload(payload["candidates"])
            log_submission(
                {
                    "submission_uuid": submission_uuid,
                    "status": result.get("status", "done"),
                    "reward": result.get("reward", 0.0),
                    "hpwl": result.get("hpwl"),
                    "overlap_rate": result.get("overlap_rate"),
                    "candidate_index": result.get("candidate_index"),
                    "n_candidates": result.get("n_candidates"),
                }
            )
            self._write_json(200, result)
        except Exception as exc:
            log_submission(
                {
                    "submission_uuid": locals().get("submission_uuid", ""),
                    "status": "error",
                    "error": str(exc),
                }
            )
            self._write_json(
                200,
                {
                    "status": "error",
                    "reward": 0.0,
                    "hpwl": None,
                    "message": str(exc),
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
