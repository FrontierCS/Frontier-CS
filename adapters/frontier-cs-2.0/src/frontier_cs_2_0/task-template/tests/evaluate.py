#!/usr/bin/env python3
"""Harbor verifier for Frontier-CS 2.0 problems."""

from __future__ import annotations

import importlib.util
import json
import shutil
import sys
import traceback
from pathlib import Path

SOLUTION_PATH = Path("/app/solution.py")
APP_PATH = Path("/app")
SUBMISSION_CONFIG_PATH = Path("/app/submission_config.json")
PROBLEM_EVALUATOR_PATH = Path("/tests/problem_evaluator.py")
REWARD_TXT = Path("/logs/verifier/reward.txt")
REWARD_JSON = Path("/logs/verifier/reward.json")
AGENT_SUBMISSIONS_LOG = Path("/logs/agent/submissions.jsonl")
VERIFIER_SUBMISSIONS_LOG = Path("/logs/verifier/submissions.jsonl")
EVALUATION_JSON = Path("/logs/verifier/evaluation_result.json")


def best_submission() -> dict | None:
    if not AGENT_SUBMISSIONS_LOG.exists():
        return None

    best: dict | None = None
    for line in AGENT_SUBMISSIONS_LOG.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            record = json.loads(line)
            reward = float(record.get("score", 0.0))
        except (TypeError, ValueError, json.JSONDecodeError):
            continue
        if record.get("status") != "done":
            continue
        if best is None or reward > float(best.get("score", 0.0)):
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


def copy_submissions_log() -> None:
    if AGENT_SUBMISSIONS_LOG.exists():
        VERIFIER_SUBMISSIONS_LOG.parent.mkdir(parents=True, exist_ok=True)
        try:
            shutil.copy2(AGENT_SUBMISSIONS_LOG, VERIFIER_SUBMISSIONS_LOG)
        except OSError as exc:
            print(f"WARN: failed to copy submissions.jsonl: {exc}")


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


def normalize_result(result):
    if not isinstance(result, tuple) or len(result) not in (3, 4):
        raise TypeError("evaluator must return (score, score_unbounded, message[, metrics])")
    score = float(result[0])
    score_unbounded = float(result[1])
    message = str(result[2])
    metrics = result[3] if len(result) == 4 else {}
    if not isinstance(metrics, dict):
        raise TypeError("evaluator metrics must be a dict")
    return score, score_unbounded, message, metrics


def load_submission_path() -> Path:
    if not SUBMISSION_CONFIG_PATH.exists():
        return SOLUTION_PATH
    config = json.loads(SUBMISSION_CONFIG_PATH.read_text(encoding="utf-8"))
    if config.get("kind") == "directory":
        return Path(config.get("path") or APP_PATH)
    return Path(config.get("path") or SOLUTION_PATH)


def main() -> None:
    copy_submissions_log()
    best = best_submission()

    def write_best_submission_reward(reason: str) -> bool:
        if best is None:
            return False
        reward = float(best.get("score", 0.0))
        score_raw = best.get("score_raw", reward * 100.0)
        score_unbounded = best.get("score_unbounded", score_raw)
        metrics = best.get("metrics", {})
        if not isinstance(metrics, dict):
            metrics = {}
        print(f"Using best iterative submission after {reason}: reward={reward:.4f}")
        write_reward(
            reward,
            f"Using best iterative submission after {reason}: {best.get('detail', '')}",
            {
                "score": score_raw,
                "score_unbounded": score_unbounded,
                "best_submission_reward": reward,
                "used_best_submission": 1,
                **metrics,
            },
        )
        return True

    solution_path = load_submission_path()
    if not solution_path.exists():
        print(f"ERROR: {solution_path} not found")
        if write_best_submission_reward(f"{solution_path} not found"):
            return
        write_reward(0.0, f"{solution_path} not found")
        return
    if solution_path.is_file() and not solution_path.read_text(encoding="utf-8").strip():
        print("ERROR: /app/solution.py is empty")
        if write_best_submission_reward("solution.py is empty"):
            return
        write_reward(0.0, "solution.py is empty")
        return

    try:
        evaluator = load_problem_evaluator()
        score, score_unbounded, message, metrics = normalize_result(
            evaluator.evaluate(str(solution_path))
        )
        reward = float(score) / 100.0
        if best is not None and float(best.get("score", 0.0)) > reward:
            write_best_submission_reward("final solution scored below best submission")
            return
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
                **metrics,
            },
        )
    except Exception as exc:
        print(traceback.format_exc())
        if write_best_submission_reward(f"final evaluation failed: {exc}"):
            return
        write_reward(0.0, f"Evaluation failed: {exc}")


if __name__ == "__main__":
    main()
