#!/usr/bin/env python3
from __future__ import annotations

import json
import shutil
from pathlib import Path
from urllib import request

SOLUTION_PATH = Path("/app/solution.py")
REWARD_TXT = Path("/logs/verifier/reward.txt")
REWARD_JSON = Path("/logs/verifier/reward.json")
EVALUATION_JSON = Path("/logs/verifier/evaluation_result.json")
AGENT_SUBMISSIONS_LOG = Path("/logs/agent/submissions.jsonl")
VERIFIER_SUBMISSIONS_LOG = Path("/logs/verifier/submissions.jsonl")
JUDGE_URL = "http://judge:8082"


def best_submission() -> dict | None:
    records: list[dict] = []
    try:
        with request.urlopen(f"{JUDGE_URL}/submissions", timeout=5) as response:
            payload = json.loads(response.read().decode("utf-8"))
        http_records = payload.get("submissions", [])
        if isinstance(http_records, list):
            records.extend(record for record in http_records if isinstance(record, dict))
    except Exception as exc:
        print(f"WARN: failed to fetch judge submissions: {exc}")

    seen: set[str] = set()
    best: dict | None = None
    VERIFIER_SUBMISSIONS_LOG.parent.mkdir(parents=True, exist_ok=True)
    with VERIFIER_SUBMISSIONS_LOG.open("w", encoding="utf-8") as dst:
        for record in records:
            key = str(record.get("submission_uuid") or json.dumps(record, sort_keys=True))
            if key in seen:
                continue
            seen.add(key)
            dst.write(json.dumps(record, ensure_ascii=False) + "\n")
            if record.get("status") != "done":
                continue
            try:
                reward = float(record.get("reward", 0.0))
            except (TypeError, ValueError):
                continue
            if best is None or reward > float(best.get("reward", 0.0)):
                best = record
    return best


def copy_agent_submissions_log() -> None:
    if AGENT_SUBMISSIONS_LOG.exists():
        target = Path("/logs/verifier/agent_submissions.jsonl")
        target.parent.mkdir(parents=True, exist_ok=True)
        try:
            shutil.copy2(AGENT_SUBMISSIONS_LOG, target)
        except OSError as exc:
            print(f"WARN: failed to copy agent submissions log: {exc}")


def write_reward(reward: float, detail: str = "", extra: dict | None = None) -> None:
    REWARD_TXT.parent.mkdir(parents=True, exist_ok=True)
    reward = max(0.0, float(reward))
    REWARD_TXT.write_text(str(reward), encoding="utf-8")
    numeric_payload = {"reward": reward, "score": reward}
    sidecar = {"reward": reward, "detail": detail}
    if extra:
        for key, value in extra.items():
            if isinstance(value, (int, float)) and not isinstance(value, bool):
                numeric_payload[key] = value
            sidecar[key] = value
    REWARD_JSON.write_text(json.dumps(numeric_payload, indent=2), encoding="utf-8")
    EVALUATION_JSON.write_text(json.dumps(sidecar, indent=2), encoding="utf-8")


def write_best_submission_reward(best: dict | None, reason: str) -> bool:
    if best is None:
        return False
    reward = float(best.get("reward", 0.0))
    print(f"Using best iterative submission after {reason}: reward={reward:.6f}")
    write_reward(
        reward,
        f"Using best iterative submission after {reason}",
        {
            "hpwl": best.get("hpwl"),
            "overlap_rate": best.get("overlap_rate"),
            "best_submission_reward": reward,
            "used_best_submission": 1,
        },
    )
    return True


def main() -> None:
    copy_agent_submissions_log()
    best = best_submission()

    if not SOLUTION_PATH.exists():
        print("ERROR: /app/solution.py not found")
        if write_best_submission_reward(best, "solution.py not found"):
            return
        write_reward(0.0, "solution.py not found")
        return
    if not SOLUTION_PATH.read_text(encoding="utf-8", errors="replace").strip():
        print("ERROR: /app/solution.py is empty")
        if write_best_submission_reward(best, "solution.py is empty"):
            return
        write_reward(0.0, "solution.py is empty")
        return

    if write_best_submission_reward(best, "final scoring uses judge-scored iterative submissions"):
        return
    write_reward(0.0, "No successful judge-scored iterative submission found")


if __name__ == "__main__":
    main()
