#!/usr/bin/env python3
"""Harbor verifier for Frontier-CS 2.0 problems."""

from __future__ import annotations

import base64
import io
import json
import os
import shutil
import tarfile
import time
import traceback
import uuid
from pathlib import Path
from urllib import error, request

SOLUTION_PATH = Path("/app/solution.py")
APP_PATH = Path("/app")
SUBMISSION_CONFIG_PATH = Path("/app/submission_config.json")
REWARD_TXT = Path("/logs/verifier/reward.txt")
REWARD_JSON = Path("/logs/verifier/reward.json")
JUDGE_SUBMISSIONS_LOG = Path("/logs/judge/submissions.jsonl")
JUDGE_READY_LOG = Path("/logs/judge/judge_ready.json")
VERIFIER_SUBMISSIONS_LOG = Path("/logs/verifier/submissions.jsonl")
VERIFIER_JUDGE_READY_LOG = Path("/logs/verifier/judge_ready.json")
EVALUATION_JSON = Path("/logs/verifier/evaluation_result.json")
JUDGE_URL = os.environ.get("JUDGE_URL", "http://judge:8082").rstrip("/")
JUDGE_TIMEOUT_SECONDS = int(os.environ.get("JUDGE_TIMEOUT_SECONDS", "10800"))


def submission_reward(record: dict) -> float | None:
    try:
        return float(record.get("score", 0.0)) / 100.0
    except (TypeError, ValueError):
        return None


def best_submission() -> dict | None:
    submissions_log = (
        VERIFIER_SUBMISSIONS_LOG
        if VERIFIER_SUBMISSIONS_LOG.exists()
        else JUDGE_SUBMISSIONS_LOG
    )
    if not submissions_log.exists():
        return None

    best: dict | None = None
    for line in submissions_log.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            record = json.loads(line)
            reward = submission_reward(record)
            if reward is None:
                continue
        except json.JSONDecodeError:
            continue
        if record.get("submission_role", "agent") != "agent":
            continue
        if record.get("status") != "done":
            continue
        best_reward = submission_reward(best) if best is not None else None
        if best is None or best_reward is None or reward > best_reward:
            best = record
    return best


def write_reward(reward: float, detail: str = "", extra: dict | None = None) -> None:
    REWARD_TXT.parent.mkdir(parents=True, exist_ok=True)
    reward = max(0.0, min(1.0, float(reward)))
    REWARD_TXT.write_text(str(reward), encoding="utf-8")
    payload = {"reward": reward}
    sidecar = {"reward": reward, "detail": detail}
    if extra:
        for key, value in extra.items():
            if isinstance(value, (int, float)) and not isinstance(value, bool):
                payload[key] = value
            sidecar[key] = value
    REWARD_JSON.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    EVALUATION_JSON.write_text(json.dumps(sidecar, indent=2), encoding="utf-8")


def copy_judge_artifacts() -> None:
    records: list[dict] = []
    try:
        with request.urlopen(f"{JUDGE_URL}/submissions", timeout=5) as response:
            payload = json.loads(response.read().decode("utf-8"))
        http_records = payload.get("submissions", [])
        if isinstance(http_records, list):
            records.extend(record for record in http_records if isinstance(record, dict))
    except Exception as exc:
        print(f"WARN: failed to fetch judge submissions: {exc}")

    if JUDGE_SUBMISSIONS_LOG.exists():
        try:
            with JUDGE_SUBMISSIONS_LOG.open("r", encoding="utf-8") as src:
                for line in src:
                    try:
                        record = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    if isinstance(record, dict):
                        records.append(record)
        except OSError as exc:
            print(f"WARN: failed to copy submissions.jsonl: {exc}")

    seen: set[str] = set()
    VERIFIER_SUBMISSIONS_LOG.parent.mkdir(parents=True, exist_ok=True)
    with VERIFIER_SUBMISSIONS_LOG.open("w", encoding="utf-8") as dst:
        for record in records:
            if record.get("submission_role", "agent") != "agent":
                continue
            key = str(record.get("submission_uuid") or json.dumps(record, sort_keys=True))
            if key in seen:
                continue
            seen.add(key)
            dst.write(json.dumps(record, ensure_ascii=False) + "\n")

    if JUDGE_READY_LOG.exists():
        VERIFIER_JUDGE_READY_LOG.parent.mkdir(parents=True, exist_ok=True)
        try:
            shutil.copy2(JUDGE_READY_LOG, VERIFIER_JUDGE_READY_LOG)
        except OSError as exc:
            print(f"WARN: failed to copy judge_ready.json: {exc}")


def load_submission_config() -> dict:
    if not SUBMISSION_CONFIG_PATH.exists():
        return {"kind": "file", "path": str(SOLUTION_PATH), "exclude": []}
    return json.loads(SUBMISSION_CONFIG_PATH.read_text(encoding="utf-8"))


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


def wait_for_judge() -> None:
    deadline = time.time() + JUDGE_TIMEOUT_SECONDS
    last_error: Exception | None = None
    while time.time() < deadline:
        try:
            with request.urlopen(f"{JUDGE_URL}/health", timeout=5) as response:
                payload = json.loads(response.read().decode("utf-8"))
            if payload.get("status") == "error":
                raise RuntimeError(f"judge setup failed: {payload.get('error') or payload}")
            return
        except error.HTTPError as exc:
            try:
                payload = json.loads(exc.read().decode("utf-8"))
            except Exception:
                payload = {}
            if payload.get("status") == "error":
                raise RuntimeError(f"judge setup failed: {payload.get('error') or payload}")
            last_error = exc
            time.sleep(1)
        except RuntimeError:
            raise
        except Exception as exc:
            last_error = exc
            time.sleep(1)
    raise RuntimeError(f"judge service is not ready at {JUDGE_URL}: {last_error}")


def post_json(url: str, payload: dict) -> dict:
    body = json.dumps(payload).encode("utf-8")
    req = request.Request(
        url,
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with request.urlopen(req, timeout=JUDGE_TIMEOUT_SECONDS) as response:
            return json.loads(response.read().decode("utf-8"))
    except error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"judge HTTP {exc.code}: {detail}") from exc


def build_judge_payload(solution_path: Path, config: dict) -> dict:
    submission_kind = str(config.get("kind", "file"))
    exclude = list(config.get("exclude", []) or [])
    submission_uuid = str(uuid.uuid4())

    if submission_kind == "directory":
        archive_b64, _ = make_directory_archive(solution_path, exclude)
        return {
            "submission_kind": "directory",
            "submission_uuid": submission_uuid,
            "submission_role": "final",
            "archive_b64": archive_b64,
        }

    return {
        "submission_kind": "file",
        "submission_uuid": submission_uuid,
        "submission_role": "final",
        "code": solution_path.read_text(encoding="utf-8"),
    }


def evaluate_with_judge(payload: dict) -> dict:
    wait_for_judge()
    result = post_json(f"{JUDGE_URL}/evaluate", payload)
    if result.get("status") != "done":
        raise RuntimeError(str(result.get("message") or result.get("error") or result))
    return result


def load_submission_path(config: dict) -> Path:
    if config.get("kind") == "directory":
        return Path(config.get("path") or APP_PATH)
    return Path(config.get("path") or SOLUTION_PATH)


def write_result(result: dict) -> None:
    score = float(result.get("score", 0.0))
    score_unbounded = float(result.get("score_unbounded", score))
    message = str(result.get("message", ""))
    metrics = result.get("metrics", {})
    if not isinstance(metrics, dict):
        metrics = {}
    reward = score / 100.0
    print(message)
    print(f"Score: {score}/100 (reward: {reward:.4f})")
    if score_unbounded != score:
        print(f"Unbounded score: {score_unbounded}")
    write_reward(
        reward,
        message,
        {
            "score": score,
            "score_unbounded": score_unbounded,
            "raw_result": result,
            **metrics,
        },
    )


def main() -> None:
    copy_judge_artifacts()
    best = best_submission()

    def write_best_submission_reward(reason: str) -> bool:
        if best is None:
            return False
        score_raw = float(best.get("score", 0.0))
        reward = score_raw / 100.0
        score_unbounded = float(best.get("score_unbounded", score_raw))
        metrics = best.get("metrics", {})
        if not isinstance(metrics, dict):
            metrics = {}
        print(f"Using best iterative submission after {reason}: reward={reward:.4f}")
        write_reward(
            reward,
            f"Using best iterative submission after {reason}: {best.get('message', '')}",
            {
                "score": score_raw,
                "score_unbounded": score_unbounded,
                "best_submission_reward": reward,
                "used_best_submission": 1,
                **metrics,
            },
        )
        return True

    try:
        config = load_submission_config()
        solution_path = load_submission_path(config)
        if not solution_path.exists():
            print(f"ERROR: {solution_path} not found")
            if write_best_submission_reward(f"{solution_path} not found"):
                return
            write_reward(0.0, f"{solution_path} not found")
            return
        if solution_path.is_file() and not solution_path.read_text(encoding="utf-8").strip():
            print(f"ERROR: {solution_path} is empty")
            if write_best_submission_reward(f"{solution_path} is empty"):
                return
            write_reward(0.0, f"{solution_path} is empty")
            return

        final_result = evaluate_with_judge(build_judge_payload(solution_path, config))
        copy_judge_artifacts()
        final_reward = float(final_result.get("score", 0.0)) / 100.0
        best_reward = submission_reward(best) if best is not None else None
        if best_reward is not None and best_reward > final_reward:
            write_best_submission_reward("final solution scored below best submission")
            return
        write_result(final_result)
    except Exception as exc:
        print(traceback.format_exc())
        copy_judge_artifacts()
        if write_best_submission_reward(f"final evaluation failed: {exc}"):
            return
        write_reward(0.0, f"Evaluation failed: {exc}")


if __name__ == "__main__":
    main()
