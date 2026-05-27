#!/usr/bin/env python3
"""Iterative submission helper for Frontier-CS Harbor tasks.

The agent runs this whenever it wants to test the solution against the
graded judge. Each call:

1. Writes a `started` record to /logs/agent/submissions.jsonl (so we know the
   call existed even if everything downstream fails).
2. POSTs /app/solution.cpp (or the first arg) to the judge sidecar.
3. Polls until the judge returns done/error.
4. Writes a `done`/`error` record with the same submission_uuid, then prints
   a concise score + feedback summary so the agent sees it on stdout.

Exit code semantics:
- 0: judge returned a result (score may be low — that's still success).
- 2: solution file missing / empty.
- 3: judge submit request failed.
- 4: judge polling timed out.
- 5: unexpected runtime error.

The post-hoc analysis joins submissions.jsonl with the agent's trajectory
file by ordinal to attach tokens_so_far. See ../../../../../analysis/.
"""
from __future__ import annotations

import json
import os
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

import requests

JUDGE_URL = os.environ.get("JUDGE_URL", "http://judge:8081")
PROBLEM_ID = os.environ.get("PROBLEM_ID", "")
SUBMISSIONS_LOG = Path("/logs/agent/submissions.jsonl")
POLL_INTERVAL = 2.0
MAX_POLL_TIME = float(os.environ.get("SUBMIT_MAX_POLL_TIME", "600"))


def now_iso() -> str:
    return (
        datetime.now(timezone.utc)
        .isoformat(timespec="milliseconds")
        .replace("+00:00", "Z")
    )


def log_record(record: dict) -> None:
    SUBMISSIONS_LOG.parent.mkdir(parents=True, exist_ok=True)
    with SUBMISSIONS_LOG.open("a") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


def main() -> int:
    solution_path = Path(sys.argv[1] if len(sys.argv) > 1 else "/app/solution.cpp")
    sub_uuid = str(uuid.uuid4())
    code_chars = 0

    log_record(
        {
            "submission_uuid": sub_uuid,
            "ts": now_iso(),
            "status": "started",
            "problem_id": PROBLEM_ID,
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

    code = solution_path.read_text()
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
        r = requests.post(
            f"{JUDGE_URL}/submit",
            files={"code": ("solution.cpp", code)},
            data={"pid": PROBLEM_ID, "lang": "cpp"},
            timeout=30,
        )
        r.raise_for_status()
        sid = r.json()["sid"]
    except Exception as exc:
        msg = f"Submit request failed: {exc}"
        print(f"[submit] ERROR: {msg}", file=sys.stderr)
        log_record(
            {
                "submission_uuid": sub_uuid,
                "ts": now_iso(),
                "status": "error",
                "error": msg,
            }
        )
        return 3

    print(f"[submit] uuid={sub_uuid} sid={sid} pid={PROBLEM_ID} evaluating...")

    start = time.time()
    result: dict | None = None
    while time.time() - start < MAX_POLL_TIME:
        try:
            r = requests.get(f"{JUDGE_URL}/result/{sid}", timeout=10)
            if r.status_code == 200:
                data = r.json()
                if data.get("status") in ("done", "error"):
                    result = data
                    break
        except Exception:
            pass
        time.sleep(POLL_INTERVAL)

    if result is None:
        msg = f"Polling timed out after {MAX_POLL_TIME}s"
        print(f"[submit] ERROR: {msg}", file=sys.stderr)
        log_record(
            {
                "submission_uuid": sub_uuid,
                "ts": now_iso(),
                "status": "error",
                "sid": sid,
                "error": msg,
            }
        )
        return 4

    score_raw = result.get("score") or 0.0
    try:
        score = float(score_raw) / 100.0
    except (TypeError, ValueError):
        score = 0.0
    status = result.get("status", "unknown")
    detail = result.get("message") or result.get("detail") or ""

    log_record(
        {
            "submission_uuid": sub_uuid,
            "ts": now_iso(),
            "status": status,
            "sid": sid,
            "score": score,
            "score_raw": score_raw,
            "detail": detail,
            "raw_result": result,
            "code_chars": code_chars,
        }
    )

    print(f"[submit] uuid={sub_uuid} sid={sid}")
    print(
        f"[submit] status={status} score={score:.4f} "
        f"(raw={score_raw}/100) code_chars={code_chars}"
    )
    if detail:
        snippet = detail if len(detail) <= 500 else detail[:500] + "..."
        print(f"[submit] detail: {snippet}")
    cases = result.get("cases") or result.get("results") or []
    if isinstance(cases, list) and cases:
        passed = sum(
            1
            for c in cases
            if isinstance(c, dict) and (c.get("score") or 0) > 0
        )
        print(f"[submit] cases: {passed}/{len(cases)} passed")

    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        sys.exit(130)
    except Exception as exc:
        print(f"[submit] FATAL: {exc!r}", file=sys.stderr)
        sys.exit(5)
