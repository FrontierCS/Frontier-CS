#!/usr/bin/env python3
from __future__ import annotations

import argparse
import importlib.util
import json
import os
import sys
import time
import traceback
import uuid
from datetime import datetime, timezone
from pathlib import Path

import requests
import numpy as np

SOLUTION_PATH = Path("/app/solution.py")
SUBMISSIONS_LOG = Path("/logs/agent/submissions.jsonl")
JUDGE_URL = os.environ.get("JUDGE_URL", "http://judge:8082").rstrip("/")
JUDGE_TIMEOUT_SECONDS = int(os.environ.get("JUDGE_TIMEOUT_SECONDS", "10800"))


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def log_record(record: dict) -> None:
    SUBMISSIONS_LOG.parent.mkdir(parents=True, exist_ok=True)
    with SUBMISSIONS_LOG.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


def wait_for_judge() -> None:
    deadline = time.time() + 120
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


def fetch_info() -> dict:
    wait_for_judge()
    response = requests.get(f"{JUDGE_URL}/info", timeout=JUDGE_TIMEOUT_SECONDS)
    response.raise_for_status()
    payload = response.json()
    if payload.get("status") != "ok":
        raise RuntimeError(str(payload.get("error") or payload))
    return payload["info"]


def load_solution_module(solution_path: Path):
    module_name = f"bboplace_agent_solution_{uuid.uuid4().hex}"
    spec = importlib.util.spec_from_file_location(module_name, solution_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"could not load solution from {solution_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def solution_output(module, info: dict):
    if hasattr(module, "solve"):
        return module.solve(info)
    if hasattr(module, "generate"):
        return module.generate(info)
    if hasattr(module, "CANDIDATES"):
        return module.CANDIDATES
    if hasattr(module, "CANDIDATE"):
        return module.CANDIDATE
    raise RuntimeError("solution must define solve(info), generate(info), CANDIDATES, or CANDIDATE")


def normalize_candidates(value, info: dict) -> np.ndarray:
    if isinstance(value, dict):
        value = value.get("candidates", value.get("candidate"))
    arr = np.asarray(value, dtype=float)
    if arr.ndim == 1:
        arr = arr.reshape(1, -1)
    if arr.ndim != 2:
        raise ValueError(f"candidate output must be 1D or 2D, got shape {arr.shape}")
    dim = int(info["dim"])
    if arr.shape[1] != dim:
        raise ValueError(f"candidate dimension mismatch: expected {dim}, got {arr.shape[1]}")
    max_candidates = int(info.get("max_candidates_per_submission", 256))
    if arr.shape[0] < 1:
        raise ValueError("at least one candidate is required")
    if arr.shape[0] > max_candidates:
        raise ValueError(f"too many candidates: max {max_candidates}, got {arr.shape[0]}")
    if not np.all(np.isfinite(arr)):
        raise ValueError("candidate values must be finite")
    return arr


def validate_bounds(candidates: np.ndarray, info: dict) -> None:
    placer = info["placer"]
    eps = 1e-9
    if placer == "mgo":
        node_cnt = int(info["node_cnt"])
        n_grid_x = float(info["n_grid_x"])
        n_grid_y = float(info["n_grid_y"])
        if np.any(candidates[:, :node_cnt] < -eps) or np.any(candidates[:, :node_cnt] > n_grid_x + eps):
            raise ValueError(f"mgo x-grid coordinates must be in [0, {n_grid_x}]")
        if np.any(candidates[:, node_cnt:] < -eps) or np.any(candidates[:, node_cnt:] > n_grid_y + eps):
            raise ValueError(f"mgo y-grid coordinates must be in [0, {n_grid_y}]")
    elif placer == "sp":
        upper = float(info["node_cnt"])
        if np.any(candidates < -eps) or np.any(candidates > upper + eps):
            raise ValueError(f"sp coordinates must be in [0, {upper}]")
    elif "xl" in info and "xu" in info:
        xl = np.asarray(info["xl"], dtype=float)
        xu = np.asarray(info["xu"], dtype=float)
        if np.any(candidates < xl - eps) or np.any(candidates > xu + eps):
            raise ValueError("candidate is outside evaluator bounds")


def candidates_from_solution(solution_path: Path, info: dict) -> list[list[float]]:
    module = load_solution_module(solution_path)
    candidates = normalize_candidates(solution_output(module, info), info)
    validate_bounds(candidates, info)
    return candidates.tolist()


def evaluate_with_judge(candidates: list[list[float]], submission_uuid: str) -> dict:
    wait_for_judge()
    response = requests.post(
        f"{JUDGE_URL}/evaluate",
        json={"candidates": candidates, "submission_uuid": submission_uuid},
        timeout=JUDGE_TIMEOUT_SECONDS,
    )
    response.raise_for_status()
    return response.json()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("solution_path", nargs="?", default=str(SOLUTION_PATH))
    parser.add_argument("--info", action="store_true", help="Print exact task metadata")
    args = parser.parse_args()

    try:
        if args.info:
            print(json.dumps(fetch_info(), indent=2))
            return 0

        solution_path = Path(args.solution_path)
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
            raise FileNotFoundError(f"Solution file {solution_path} does not exist")
        code = solution_path.read_text(encoding="utf-8")
        code_chars = len(code)
        if not code.strip():
            raise ValueError(f"Solution file {solution_path} is empty")

        start = time.time()
        info = fetch_info()
        candidates = candidates_from_solution(solution_path, info)
        payload = evaluate_with_judge(candidates, sub_uuid)
        elapsed_seconds = time.time() - start
        if payload.get("status") != "done":
            raise RuntimeError(str(payload.get("message") or payload.get("error") or payload))

        record = {
            "submission_uuid": sub_uuid,
            "ts": now_iso(),
            "status": "done",
            "reward": float(payload.get("reward", 0.0)),
            "hpwl": payload.get("hpwl"),
            "overlap_rate": payload.get("overlap_rate"),
            "candidate_index": payload.get("candidate_index"),
            "n_candidates": payload.get("n_candidates"),
            "elapsed_seconds": elapsed_seconds,
            "code_chars": code_chars,
        }
        log_record(record)

        print(f"[submit] uuid={sub_uuid}")
        print(
            "[submit] status=done "
            f"reward={record['reward']:.6f} "
            f"hpwl={record['hpwl']} "
            f"overlap={record['overlap_rate']} "
            f"candidates={record['n_candidates']} "
            f"code_chars={code_chars}"
        )
        return 0
    except Exception as exc:
        detail = traceback.format_exc()
        print(detail, file=sys.stderr)
        log_record(
            {
                "submission_uuid": locals().get("sub_uuid", str(uuid.uuid4())),
                "ts": now_iso(),
                "status": "error",
                "error": str(exc),
                "detail": detail,
                "code_chars": locals().get("code_chars", 0),
            }
        )
        return 5


if __name__ == "__main__":
    sys.exit(main())
