#!/usr/bin/env python3
"""Iterative submission helper for Frontier-CS 2.0 Harbor tasks."""

from __future__ import annotations

import json
import os
import sys
import time
import traceback
import uuid
import base64
import io
import tarfile
from datetime import datetime, timezone
from pathlib import Path

import requests

SOLUTION_PATH = Path("/app/solution.py")
SUBMISSION_CONFIG_PATH = Path("/app/submission_config.json")
SUBMISSIONS_LOG = Path("/logs/agent/submissions.jsonl")
JUDGE_URL = os.environ.get("JUDGE_URL", "http://judge:8082").rstrip("/")
JUDGE_TIMEOUT_SECONDS = int(os.environ.get("JUDGE_TIMEOUT_SECONDS", "10800"))


def load_submission_config() -> dict:
    if not SUBMISSION_CONFIG_PATH.exists():
        return {"kind": "file", "path": str(SOLUTION_PATH), "exclude": []}
    return json.loads(SUBMISSION_CONFIG_PATH.read_text(encoding="utf-8"))


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
    deadline = time.time() + JUDGE_TIMEOUT_SECONDS
    last_error: Exception | None = None
    printed_waiting = False
    while time.time() < deadline:
        try:
            response = requests.get(f"{JUDGE_URL}/health", timeout=5)
        except Exception as exc:
            last_error = exc
            if not printed_waiting:
                print("[submit] waiting for judge service", flush=True)
                printed_waiting = True
            time.sleep(1)
            continue

        try:
            payload = response.json()
        except Exception:
            payload = {}
        if payload.get("status") == "error":
            raise RuntimeError(f"judge setup failed: {payload.get('error') or payload}")
        if response.status_code == 200:
            prepare_seconds = payload.get("prepare_seconds")
            suffix = (
                f" prepare_seconds={float(prepare_seconds):.2f}"
                if isinstance(prepare_seconds, (int, float))
                else ""
            )
            print(f"[submit] judge ready{suffix}", flush=True)
            return
        if not printed_waiting:
            print("[submit] waiting for judge to finish environment setup", flush=True)
            printed_waiting = True
        time.sleep(1)
    raise RuntimeError(f"judge service is not ready at {JUDGE_URL}: {last_error}")


def should_exclude(path: Path, root: Path, exclude: list[str]) -> bool:
    rel = path.relative_to(root).as_posix()
    parts = set(path.relative_to(root).parts)
    for pattern in exclude:
        pattern = str(pattern).strip("/")
        if not pattern:
            continue
        if rel == pattern or rel.startswith(pattern + "/") or pattern in parts:
            return True
    return False


def make_directory_archive(root: Path, exclude: list[str]) -> tuple[str, int]:
    buf = io.BytesIO()
    file_count = 0
    with tarfile.open(fileobj=buf, mode="w:gz") as tar:
        for path in sorted(root.rglob("*")):
            if should_exclude(path, root, exclude):
                continue
            if path.is_file():
                tar.add(path, arcname=path.relative_to(root).as_posix())
                file_count += 1
    return base64.b64encode(buf.getvalue()).decode("ascii"), file_count


def evaluate_with_judge(payload: dict) -> tuple[float, float, str, dict]:
    wait_for_judge()
    response = requests.post(
        f"{JUDGE_URL}/evaluate",
        json=payload,
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
        dict(payload.get("metrics", {}) or {}),
    )


def main() -> int:
    config = load_submission_config()
    submission_kind = str(config.get("kind", "file"))
    default_path = str(config.get("path") or SOLUTION_PATH)
    solution_path = Path(sys.argv[1] if len(sys.argv) > 1 else default_path)
    exclude = list(config.get("exclude", []) or [])
    sub_uuid = str(uuid.uuid4())
    code_chars = 0
    file_count = 0

    log_record(
        {
            "submission_uuid": sub_uuid,
            "ts": now_iso(),
            "status": "started",
            "solution_path": str(solution_path),
            "submission_kind": submission_kind,
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

    if submission_kind == "directory":
        if not solution_path.is_dir():
            msg = f"Submission path {solution_path} is not a directory"
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
        archive_b64, file_count = make_directory_archive(solution_path, exclude)
        code_chars = sum(
            p.stat().st_size
            for p in solution_path.rglob("*")
            if p.is_file() and not should_exclude(p, solution_path, exclude)
        )
        judge_payload = {
            "submission_kind": "directory",
            "archive_b64": archive_b64,
        }
    else:
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
        judge_payload = {"submission_kind": "file", "code": code}

    try:
        start = time.time()
        score, score_unbounded, message, metrics = evaluate_with_judge(judge_payload)
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
                "file_count": file_count,
                "metrics": metrics,
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
        if metrics:
            metric_text = " ".join(
                f"{key}={value}" for key, value in sorted(metrics.items())
            )
            print(f"[submit] metrics: {metric_text}")
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
