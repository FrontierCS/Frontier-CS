#!/usr/bin/env python3
"""Iterative submission helper for Frontier-CS 2.0 Harbor tasks."""

from __future__ import annotations

import json
import os
import sys
import time
import traceback
import uuid
from datetime import datetime, timezone
from pathlib import Path

import requests

SOLUTION_PATH = Path("/app/solution.py")
SUBMISSIONS_LOG = Path("/logs/agent/submissions.jsonl")
JUDGE_URL = os.environ.get("JUDGE_URL", "http://judge:8082").rstrip("/")
JUDGE_TIMEOUT_SECONDS = int(os.environ.get("JUDGE_TIMEOUT_SECONDS", "10800"))


def now_iso() -> str:
    return (
        datetime.now(timezone.utc)
        .isoformat(timespec="milliseconds")
        .replace("+00:00", "Z")
    )


def log_record(record: dict) -> None:
    SUBMISSIONS_LOG.parent.mkdir(parents=True, exist_ok=True)
    with SUBMISSIONS_LOG.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


def wait_for_judge() -> None:
    deadline = time.time() + 60
    last_error: Exception | None = None
    while time.time() < deadline:
        try:
            response = requests.get(f"{JUDGE_URL}/health", timeout=5)
            if response.status_code == 200:
                return
        except Exception as exc:
            last_error = exc
        time.sleep(1)
    raise RuntimeError(f"judge service is not ready at {JUDGE_URL}: {last_error}")


def evaluate_with_judge(code: str) -> tuple[float, float, str]:
    wait_for_judge()
    response = requests.post(
        f"{JUDGE_URL}/evaluate",
        json={"code": code},
        timeout=JUDGE_TIMEOUT_SECONDS,
    )
    response.raise_for_status()
    payload = response.json()
    if payload.get("status") != "done":
        raise RuntimeError(str(payload.get("message") or payload.get("error") or payload))
    return (
        float(payload.get("score", 0.0)),
        float(payload.get("score_unbounded", payload.get("score", 0.0))),
        str(payload.get("message", "")),
    )


def main() -> int:
    solution_path = Path(sys.argv[1] if len(sys.argv) > 1 else SOLUTION_PATH)
    sub_uuid = str(uuid.uuid4())
    code_chars = 0

    log_record(
        {
            "submission_uuid": sub_uuid,
            "ts": now_iso(),
            "status": "started",
            "solution_path": str(solution_path),
            "code_chars": code_chars,
        }
    )

    if not solution_path.exists():
        msg = f"Solution file {solution_path} does not exist"
        print(f"[submit] ERROR: {msg}", file=sys.stderr)
        log_record(
            {
                "submission_uuid": sub_uuid,
                "ts": now_iso(),
                "status": "error",
                "error": msg,
            }
        )
        return 2

    code = solution_path.read_text(encoding="utf-8")
    code_chars = len(code)
    if not code.strip():
        msg = f"Solution file {solution_path} is empty"
        print(f"[submit] ERROR: {msg}", file=sys.stderr)
        log_record(
            {
                "submission_uuid": sub_uuid,
                "ts": now_iso(),
                "status": "error",
                "error": msg,
                "code_chars": code_chars,
            }
        )
        return 2

    try:
        start = time.time()
        score, score_unbounded, message = evaluate_with_judge(code)
        elapsed_seconds = time.time() - start
        reward = float(score) / 100.0

        log_record(
            {
                "submission_uuid": sub_uuid,
                "ts": now_iso(),
                "status": "done",
                "score": reward,
                "score_raw": score,
                "score_unbounded": score_unbounded,
                "elapsed_seconds": elapsed_seconds,
                "detail": message,
                "code_chars": code_chars,
            }
        )

        print(f"[submit] uuid={sub_uuid}")
        print(
            f"[submit] status=done score={reward:.4f} "
            f"(raw={score}/100) code_chars={code_chars}"
        )
        if score_unbounded != score:
            print(f"[submit] unbounded={score_unbounded}")
        if message:
            snippet = message if len(message) <= 800 else message[:800] + "..."
            print(f"[submit] detail: {snippet}")
        return 0
    except Exception as exc:
        detail = traceback.format_exc()
        print(detail, file=sys.stderr)
        log_record(
            {
                "submission_uuid": sub_uuid,
                "ts": now_iso(),
                "status": "error",
                "error": str(exc),
                "detail": detail,
                "code_chars": code_chars,
            }
        )
        return 5


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        sys.exit(130)
