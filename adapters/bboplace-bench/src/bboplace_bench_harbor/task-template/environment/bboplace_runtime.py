from __future__ import annotations

import importlib.util
import json
import os
import sys
import uuid
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import numpy as np

REWARD_SCALE = 100000.0


def load_json(path: str | Path) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def hpwl_to_reward(hpwl: float) -> float:
    if not np.isfinite(hpwl) or hpwl < 0:
        return 0.0
    return float(1.0 / (1.0 + hpwl / REWARD_SCALE))


def prepare_repo(repo_dir: str | Path) -> Path:
    repo = Path(repo_dir)
    for path in (repo, repo / "src", repo / "thirdparty", repo / "thirdparty" / "dreamplace"):
        if path.exists() and str(path) not in sys.path:
            sys.path.insert(0, str(path))
    os.environ["PYTHONPATH"] = os.pathsep.join(sys.path)
    return repo


def build_evaluator(repo_dir: str | Path, task_info: dict):
    repo = prepare_repo(repo_dir)
    cwd = os.getcwd()
    os.chdir(repo)
    try:
        try:
            import ray

            ray.init = lambda *args, **kwargs: None
        except Exception:
            pass

        from src.evaluator import Evaluator

        args = SimpleNamespace(
            placer=task_info["placer"],
            benchmark=task_info["benchmark"],
            eval_gp_hpwl=bool(task_info.get("eval_gp_hpwl", False)),
            seed=int(task_info.get("seed", 1)),
            n_cpu_max=1,
            use_wandb=False,
            error_redirect=False,
        )
        return Evaluator(args)
    finally:
        os.chdir(cwd)


def exact_problem_info(evaluator, task_info: dict, *, include_full_bounds: bool = False) -> dict:
    info = dict(task_info)
    dim = int(evaluator.n_dim)
    info["dim"] = dim
    info["n_dim"] = dim
    info["node_cnt"] = int(getattr(evaluator.placer.placedb, "node_cnt", 0))
    info["canvas_width"] = float(getattr(evaluator.placer.placedb, "canvas_width", 0.0))
    info["canvas_height"] = float(getattr(evaluator.placer.placedb, "canvas_height", 0.0))

    placer = task_info["placer"]
    if placer == "mgo":
        info["bounds_kind"] = "mgo_repeated_grid"
        info["n_grid_x"] = int(evaluator.args.n_grid_x)
        info["n_grid_y"] = int(evaluator.args.n_grid_y)
        info["bounds_summary"] = {
            "first_node_cnt_dimensions": [0.0, float(evaluator.args.n_grid_x)],
            "last_node_cnt_dimensions": [0.0, float(evaluator.args.n_grid_y)],
        }
    elif placer == "sp":
        info["bounds_kind"] = "sp_repeated_rank"
        info["bounds_summary"] = {
            "all_dimensions": [0.0, float(info["node_cnt"])],
        }
    else:
        info["bounds_kind"] = "explicit"
        include_full_bounds = True

    if include_full_bounds:
        xl = np.asarray(evaluator.xl, dtype=float)
        xu = np.asarray(evaluator.xu, dtype=float)
        info["xl"] = xl.tolist()
        info["xu"] = xu.tolist()
    return info


def load_solution_module(solution_path: str | Path):
    path = Path(solution_path)
    module_name = f"bboplace_solution_{uuid.uuid4().hex}"
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"could not load solution from {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def solution_output(module: Any, info: dict):
    if hasattr(module, "solve"):
        return module.solve(info)
    if hasattr(module, "generate"):
        return module.generate(info)
    if hasattr(module, "CANDIDATES"):
        return module.CANDIDATES
    if hasattr(module, "CANDIDATE"):
        return module.CANDIDATE
    raise RuntimeError("solution must define solve(info), generate(info), CANDIDATES, or CANDIDATE")


def generate_candidates_from_solution(
    solution_path: str | Path, info: dict, *, max_candidates: int
) -> np.ndarray:
    module = load_solution_module(solution_path)
    candidates = normalize_candidates(
        solution_output(module, info),
        int(info["dim"]),
        max_candidates=max_candidates,
    )
    validate_bounds(candidates, info)
    return candidates


def normalize_candidates(value: Any, dim: int, *, max_candidates: int) -> np.ndarray:
    if isinstance(value, dict):
        value = value.get("candidates", value.get("candidate"))
    arr = np.asarray(value, dtype=float)
    if arr.ndim == 1:
        arr = arr.reshape(1, -1)
    if arr.ndim != 2:
        raise ValueError(f"candidate output must be 1D or 2D, got shape {arr.shape}")
    if arr.shape[1] != dim:
        raise ValueError(f"candidate dimension mismatch: expected {dim}, got {arr.shape[1]}")
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


def evaluate_candidates(evaluator, task_info: dict, candidates: Any) -> dict:
    info = exact_problem_info(evaluator, task_info, include_full_bounds=False)
    candidates = normalize_candidates(
        candidates,
        int(info["dim"]),
        max_candidates=int(task_info.get("max_candidates_per_submission", 256)),
    )
    validate_bounds(candidates, info)

    hpwl_values, overlap_values, _macro_positions = evaluator.placer.evaluate(candidates)
    records = []
    for idx, (hpwl, overlap) in enumerate(zip(hpwl_values, overlap_values)):
        hpwl = float(hpwl)
        overlap = float(overlap)
        records.append(
            {
                "candidate_index": idx,
                "hpwl": hpwl,
                "overlap_rate": overlap,
                "reward": hpwl_to_reward(hpwl),
            }
        )
    best = min(records, key=lambda record: record["hpwl"])
    return {
        "status": "done",
        "reward": best["reward"],
        "hpwl": best["hpwl"],
        "overlap_rate": best["overlap_rate"],
        "candidate_index": best["candidate_index"],
        "n_candidates": len(records),
        "records": records,
        "problem_info": {
            key: info[key]
            for key in (
                "benchmark",
                "benchmark_base",
                "benchmark_type",
                "placer",
                "dim",
                "node_cnt",
                "bounds_kind",
                "bounds_summary",
                "n_grid_x",
                "n_grid_y",
            )
            if key in info
        },
    }


def evaluate_solution_code(evaluator, task_info: dict, solution_path: str | Path) -> dict:
    info = exact_problem_info(evaluator, task_info, include_full_bounds=False)
    candidates = generate_candidates_from_solution(
        solution_path,
        info,
        max_candidates=int(task_info.get("max_candidates_per_submission", 256)),
    )
    return evaluate_candidates(evaluator, task_info, candidates)
