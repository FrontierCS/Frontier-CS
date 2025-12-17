#!/usr/bin/env python
"""
Common run_evaluator for cant-be-late variants.
Handles solution loading, artifact parsing, and score normalization.
"""
import argparse
import importlib.util
import json
import os
import sys
from pathlib import Path
from types import ModuleType
from typing import Any, Optional

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

# Setup path for cbl_evaluator import
if str(COMMON_DIR) not in sys.path:
    sys.path.insert(0, str(COMMON_DIR))

from cbl_evaluator import evaluate_stage1, evaluate_stage2


def load_solution_module(solution_path: Path) -> ModuleType:
    """Load solution.py as a module."""
    if not solution_path.exists():
        raise FileNotFoundError(f"solution.py not found at {solution_path}")
    spec = importlib.util.spec_from_file_location("submitted_solution", solution_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Failed to load spec for {solution_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def materialize_artifact(result: Any, artifact_path: Path) -> Path:
    """Convert solution output to artifact file."""
    artifact_path.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(result, dict):
        with artifact_path.open("w", encoding="utf-8") as fout:
            json.dump(result, fout)
        return artifact_path
    if isinstance(result, str):
        is_possible_path = len(result) < 4096 and '\n' not in result
        if is_possible_path:
            candidate = Path(result)
            try:
                if candidate.is_file():
                    with artifact_path.open("w", encoding="utf-8") as fout:
                        json.dump({"program_path": str(candidate.resolve())}, fout)
                    return artifact_path
            except OSError:
                pass
        with artifact_path.open("w", encoding="utf-8") as fout:
            fout.write(result)
        return artifact_path
    raise TypeError(
        f"Solution.solve() must return dict/path-string/code-string; got {type(result)!r}."
    )


def evaluate_artifact(
    artifact_path: str,
    env_paths: Optional[list] = None,
    job_configs: Optional[list] = None,
    changeover_delays: Optional[list] = None,
) -> dict:
    """Evaluate a strategy artifact; return payload with score and metrics."""
    artifact_path = os.path.abspath(artifact_path)

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
    sys.path.insert(0, str(SIM_ROOT))
    try:
        from sky_spot.utils import DEVICE_COSTS, COST_K  # type: ignore
    except Exception as e:
        raise RuntimeError(f"Failed to import simulator pricing utils: {e}") from e

    # Parse artifact to get program path
    try:
        with open(artifact_path, "r", encoding="utf-8") as f:
            content = f.read().strip()
    except Exception as e:
        raise RuntimeError(f"Error reading artifact {artifact_path}: {e}") from e

    program_path = None
    try:
        obj = json.loads(content)
        if isinstance(obj, dict):
            if obj.get("program_path"):
                pp = obj["program_path"].strip()
                program_path = pp if os.path.isabs(pp) else os.path.abspath(pp)
            elif obj.get("code"):
                code = obj["code"]
                program_path = os.path.abspath("./solution_env/_submitted_program.py")
                os.makedirs(os.path.dirname(program_path), exist_ok=True)
                with open(program_path, "w", encoding="utf-8") as out:
                    out.write(code)
    except Exception:
        pass

    if program_path is None and os.path.exists(content):
        program_path = content if os.path.isabs(content) else os.path.abspath(content)

    if program_path is None:
        program_path = os.path.abspath("./solution_env/_submitted_program.py")
        os.makedirs(os.path.dirname(program_path), exist_ok=True)
        with open(program_path, "w", encoding="utf-8") as out:
            out.write(content)

    # Stage 1: syntax check
    stage1_result = evaluate_stage1(program_path)
    if stage1_result.get("runs_successfully", 0) != 1.0:
        return {"score": 0, "avg_cost": 0, "error": stage1_result.get("error", "Stage 1 failed")}

    # Stage 2: full evaluation
    try:
        result = evaluate_stage2(
            program_path,
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
        return {"score": 0, "avg_cost": avg_cost, "od_anchor": None, "spot_anchor": None}

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
        return {"score": 0, "avg_cost": avg_cost, "od_anchor": None, "spot_anchor": None}

    od_anchor = od_sum / total_weight
    spot_anchor = spot_sum / total_weight
    denom = od_anchor - spot_anchor
    if denom <= 1e-9:
        return {"score": 0, "avg_cost": avg_cost, "od_anchor": od_anchor, "spot_anchor": spot_anchor}

    norm = (od_anchor - avg_cost) / denom
    norm = max(0.0, min(1.0, norm))
    score = round(norm * 100)
    return {
        "score": score,
        "avg_cost": avg_cost,
        "od_anchor": od_anchor,
        "spot_anchor": spot_anchor,
        "scenario_count": total_weight,
    }


def evaluate(solution_path: Path, spec_path: Path) -> dict:
    """Full evaluation: load solution, run solve(), evaluate artifact."""
    # Setup sky_spot path for solution imports
    if str(SIM_ROOT) not in sys.path:
        sys.path.insert(0, str(SIM_ROOT))

    module = load_solution_module(solution_path)
    if not hasattr(module, "Solution"):
        raise AttributeError("solution.py must define a 'Solution' class")
    SolutionCls = module.Solution
    solution_obj = SolutionCls()
    if not hasattr(solution_obj, "solve"):
        raise AttributeError("Solution class must define a 'solve' method")
    result = solution_obj.solve(str(spec_path))
    artifact_path = Path("./output_ans").resolve()
    materialize_artifact(result, artifact_path)
    return evaluate_artifact(str(artifact_path))


def main(resources_dir: str, default_solution: str = "../../execution_env/solution_env/solution.py"):
    """CLI entry point."""
    parser = argparse.ArgumentParser(description="Evaluate cant-be-late solution")
    parser.add_argument("--solution", default=default_solution, help="Path to solution.py")
    parser.add_argument("--spec", default=str(Path(resources_dir) / "submission_spec.json"))
    args = parser.parse_args()

    try:
        payload = evaluate(Path(args.solution).resolve(), Path(args.spec).resolve())
    except Exception as e:
        print(json.dumps({"error": str(e), "score": 0}))
        raise
    print(json.dumps(payload))
