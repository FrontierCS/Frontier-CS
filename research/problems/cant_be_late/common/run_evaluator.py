#!/usr/bin/env python
"""
Common run_evaluator for cant-be-late variants.

Solution interface:
    class Solution(Strategy):
        def solve(self, spec_path: str) -> "Solution":
            # Optional: read spec for configuration
            return self

        def _step(self, last_cluster_type, has_spot) -> ClusterType:
            # Decision logic
            return ClusterType.SPOT if has_spot else ClusterType.ON_DEMAND
"""
import argparse
import inspect
import json
import os
import sys
from pathlib import Path
from typing import Optional

# Common directory paths
COMMON_DIR = Path(__file__).resolve().parent
SIM_ROOT = COMMON_DIR / "cant-be-late-simulator"

# ADRS defaults
ADRS_ENV_PATHS = [
    "us-west-2a_k80_8",
    "us-west-2b_k80_1",
    "us-west-2b_k80_8",
    "us-west-2a_v100_1",
    "us-west-2a_v100_8",
    "us-west-2b_v100_1",
]
ADRS_JOB_CONFIGS = [
    {"duration": 48, "deadline": 52},
    {"duration": 48, "deadline": 70},
]
ADRS_CHANGEOVER_DELAYS = [0.02, 0.05, 0.1]

# Setup paths
if str(COMMON_DIR) not in sys.path:
    sys.path.insert(0, str(COMMON_DIR))
if str(SIM_ROOT) not in sys.path:
    sys.path.insert(0, str(SIM_ROOT))

from cbl_evaluator import evaluate_stage1, evaluate_stage2
from sky_spot.strategies.strategy import Strategy


def load_and_validate_solution(solution_path: Path, spec_path: Path) -> Path:
    """
    Load solution, validate it's a Strategy with required methods, return the path.

    The solution.py file must define:
        class Solution(Strategy):
            def solve(self, spec_path): ...
            def _step(self, last_cluster_type, has_spot): ...
    """
    import importlib.util

    if not solution_path.exists():
        raise FileNotFoundError(f"solution.py not found at {solution_path}")

    spec = importlib.util.spec_from_file_location("submitted_solution", solution_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Failed to load spec for {solution_path}")

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    if not hasattr(module, "Solution"):
        raise AttributeError("solution.py must define a 'Solution' class")

    SolutionCls = module.Solution

    # Validate it's a Strategy subclass
    if not issubclass(SolutionCls, Strategy):
        raise TypeError("Solution must inherit from sky_spot.strategies.strategy.Strategy")

    # Validate it has solve method
    if not hasattr(SolutionCls, "solve") or not callable(getattr(SolutionCls, "solve")):
        raise AttributeError("Solution must implement solve(self, spec_path)")

    # Validate it has _step method
    if not hasattr(SolutionCls, "_step") or not callable(getattr(SolutionCls, "_step")):
        raise AttributeError("Solution must implement _step(self, last_cluster_type, has_spot)")

    # Note: solve() is NOT called here - it will be called by sim_worker with runtime config
    # Return the solution path - workers will load the Solution class directly
    return solution_path


def evaluate_solution(
    solution_path: Path,
    env_paths: Optional[list] = None,
    job_configs: Optional[list] = None,
    changeover_delays: Optional[list] = None,
) -> dict:
    """Evaluate a Solution (Strategy subclass); return payload with score and metrics."""
    solution_path_str = str(solution_path.resolve())

    env_paths = env_paths or ADRS_ENV_PATHS
    job_configs = job_configs or ADRS_JOB_CONFIGS
    changeover_delays = changeover_delays or ADRS_CHANGEOVER_DELAYS

    data_root = SIM_ROOT / "data"
    if not data_root.exists():
        raise RuntimeError(
            "Dataset not found. Please ensure real_traces.tar.gz has been extracted under "
            "common/cant-be-late-simulator/data/."
        )

    # Import pricing utils from simulator
    try:
        from sky_spot.utils import DEVICE_COSTS, COST_K
    except Exception as e:
        raise RuntimeError(f"Failed to import simulator pricing utils: {e}") from e

    # Stage 1: syntax/import check
    stage1_result = evaluate_stage1(solution_path_str)
    if stage1_result.get("runs_successfully", 0) != 1.0:
        return {"score": 0, "score_unbounded": 0, "avg_cost": 0, "error": stage1_result.get("error", "Stage 1 failed")}

    # Stage 2: full evaluation
    try:
        result = evaluate_stage2(
            solution_path_str,
            env_paths,
            job_configs,
            changeover_delays,
        )
    except Exception as e:
        raise RuntimeError(f"Error running evaluator: {e}") from e

    if isinstance(result, dict):
        metrics = result.get("metrics", {})
        artifacts = result.get("artifacts", {})
    else:
        metrics = getattr(result, "metrics", {})
        artifacts = getattr(result, "artifacts", {})

    avg_cost = float(metrics.get("avg_cost", 0.0))
    scen_json = artifacts.get("scenario_stats_json")

    if not scen_json:
        return {"score": 0, "score_unbounded": 0, "avg_cost": avg_cost, "od_anchor": None, "spot_anchor": None}

    try:
        scenario_stats = json.loads(scen_json)
    except Exception as e:
        raise RuntimeError(f"Error parsing scenario_stats_json: {e}") from e

    # Calculate normalized score
    total_weight = 0.0
    od_sum = 0.0
    spot_sum = 0.0

    for _, item in scenario_stats.items():
        env_path = item.get("env_path", "")
        duration = float(item.get("duration", 0))
        count = float(item.get("count", 0))
        if duration <= 0 or count <= 0 or not env_path:
            continue

        parts = env_path.split("_")
        device = None
        if len(parts) >= 3:
            device = f"{parts[-2]}_{parts[-1]}"
        if device not in DEVICE_COSTS:
            for cand in DEVICE_COSTS.keys():
                if cand in env_path:
                    device = cand
                    break
        od_price = DEVICE_COSTS.get(device)
        if od_price is None:
            continue
        spot_price = float(od_price) / float(COST_K)
        od_sum += float(od_price) * duration * count
        spot_sum += float(spot_price) * duration * count
        total_weight += count

    if total_weight <= 0 or od_sum <= 0:
        return {"score": 0, "score_unbounded": 0, "avg_cost": avg_cost, "od_anchor": None, "spot_anchor": None}

    od_anchor = od_sum / total_weight
    spot_anchor = spot_sum / total_weight
    denom = od_anchor - spot_anchor
    if denom <= 1e-9:
        return {"score": 0, "score_unbounded": 0, "avg_cost": avg_cost, "od_anchor": od_anchor, "spot_anchor": spot_anchor}

    norm_unbounded = (od_anchor - avg_cost) / denom
    norm = max(0.0, min(1.0, norm_unbounded))
    score_unbounded = norm_unbounded * 100
    score = round(norm * 100)
    return {
        "score": score,
        "score_unbounded": score_unbounded,
        "avg_cost": avg_cost,
        "od_anchor": od_anchor,
        "spot_anchor": spot_anchor,
        "scenario_count": total_weight,
    }


def evaluate(
    solution_path: Path,
    spec_path: Path,
    env_paths: Optional[list] = None,
    job_configs: Optional[list] = None,
    changeover_delays: Optional[list] = None,
) -> dict:
    """Full evaluation: load solution, validate, run simulations."""
    # Validate solution and call solve() for initialization
    validated_path = load_and_validate_solution(solution_path, spec_path)

    # Run evaluation
    return evaluate_solution(
        validated_path,
        env_paths=env_paths,
        job_configs=job_configs,
        changeover_delays=changeover_delays,
    )


def main(
    resources_dir: str,
    default_solution: str = "../../execution_env/solution_env/solution.py",
    env_paths: Optional[list] = None,
    job_configs: Optional[list] = None,
    changeover_delays: Optional[list] = None,
):
    """CLI entry point."""
    parser = argparse.ArgumentParser(description="Evaluate cant-be-late solution")
    parser.add_argument("--solution", default=default_solution, help="Path to solution.py")
    parser.add_argument("--spec", default=str(Path(resources_dir) / "submission_spec.json"))
    args = parser.parse_args()

    try:
        payload = evaluate(
            Path(args.solution).resolve(),
            Path(args.spec).resolve(),
            env_paths=env_paths,
            job_configs=job_configs,
            changeover_delays=changeover_delays,
        )
    except Exception as e:
        print(json.dumps({"error": str(e), "score": 0}))
        raise
    print(json.dumps(payload))
