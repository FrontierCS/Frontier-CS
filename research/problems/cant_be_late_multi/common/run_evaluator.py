#!/usr/bin/env python3
"""
Common run_evaluator for cant-be-late-multi variants.

Solution interface:
    class Solution(MultiRegionStrategy):
        def solve(self, spec_path: str) -> "Solution":
            # Read spec for configuration, initialize strategy
            return self

        def _step(self, last_cluster_type, has_spot) -> ClusterType:
            # Decision logic at each simulation step
            return ClusterType.SPOT if has_spot else ClusterType.ON_DEMAND
"""
import argparse
import json
import logging
import os
import sys
from pathlib import Path
from typing import Dict, List, Optional

# Common directory paths
COMMON_DIR = Path(__file__).resolve().parent
SIM_ROOT = COMMON_DIR / "cant-be-late-simulator"

# Setup paths
if str(COMMON_DIR) not in sys.path:
    sys.path.insert(0, str(COMMON_DIR))
if str(SIM_ROOT) not in sys.path:
    sys.path.insert(0, str(SIM_ROOT))

from __init__ import (
    TASK_DURATION_HOURS,
    STAGE_1_SCENARIO,
    TIMEOUT_SECONDS,
    WORST_POSSIBLE_SCORE,
)
from sim_worker import run_single_simulation, _load_strategy_class, SimulationFailure
from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import COSTS, ClusterType

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

os.environ.setdefault("WANDB_MODE", "disabled")


def load_and_validate_solution(solution_path: Path, spec_path: Path) -> Path:
    """
    Load solution, validate it's a MultiRegionStrategy with required methods.

    The solution.py file must define:
        class Solution(MultiRegionStrategy):
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

    # Validate it's a MultiRegionStrategy subclass
    if not issubclass(SolutionCls, MultiRegionStrategy):
        raise TypeError("Solution must inherit from sky_spot.strategies.multi_strategy.MultiRegionStrategy")

    # Validate it has solve method
    if not hasattr(SolutionCls, "solve") or not callable(getattr(SolutionCls, "solve")):
        raise AttributeError("Solution must implement solve(self, spec_path)")

    # Validate it has _step method
    if not hasattr(SolutionCls, "_step") or not callable(getattr(SolutionCls, "_step")):
        raise AttributeError("Solution must implement _step(self, last_cluster_type, has_spot)")

    return solution_path


def evaluate_stage1(
    solution_path: Path,
    data_path: str,
    deadline_hours: float,
    restart_overhead_hours: float,
) -> Dict:
    """Stage 1: Quick check to see if the program can run without crashing."""
    logger.info(f"--- Stage 1: Quick Check for {solution_path.name} ---")

    try:
        trace_files = [
            os.path.join(data_path, region, STAGE_1_SCENARIO["traces"][0])
            for region in STAGE_1_SCENARIO["regions"]
        ]

        if not all(os.path.exists(p) for p in trace_files):
            return {
                "runs_successfully": 0.0,
                "combined_score": WORST_POSSIBLE_SCORE,
                "error": f"Missing trace files for Stage 1: {trace_files}."
            }

        config = {
            "deadline": deadline_hours,
            "duration": TASK_DURATION_HOURS,
            "overhead": restart_overhead_hours,
        }

        success, cost, error = run_single_simulation(
            str(solution_path), trace_files, config
        )

        if success:
            logger.info("Stage 1 PASSED.")
            return {"runs_successfully": 1.0}
        else:
            logger.warning(f"Stage 1 FAILED. Reason: {error}")
            return {
                "runs_successfully": 0.0,
                "combined_score": WORST_POSSIBLE_SCORE,
                "error": error,
            }

    except Exception as e:
        import traceback
        tb = traceback.format_exc()
        logger.error(f"Stage 1 evaluator itself failed: {tb}")
        return {
            "runs_successfully": 0.0,
            "combined_score": WORST_POSSIBLE_SCORE,
            "error": "Evaluator script failure",
            "traceback": tb
        }


def evaluate_stage2(
    solution_path: Path,
    data_path: str,
    scenarios: List[Dict],
    deadline_hours: float,
    restart_overhead_hours: float,
) -> Dict:
    """Stage 2: Full evaluation across all test scenarios."""
    logger.info(f"--- Stage 2: Full Evaluation for {solution_path.name} ---")

    scenario_costs = []
    last_error = "No scenarios were successfully evaluated in Stage 2."

    config = {
        "deadline": deadline_hours,
        "duration": TASK_DURATION_HOURS,
        "overhead": restart_overhead_hours,
    }

    for scenario in scenarios:
        scenario_name = scenario["name"]
        total_scenario_cost = 0
        successful_runs_in_scenario = 0

        logger.info(f"--- Evaluating Scenario: {scenario_name} ---")

        for trace_file_name in scenario["traces"]:
            trace_files = [
                os.path.join(data_path, region, trace_file_name)
                for region in scenario["regions"]
            ]

            if not all(os.path.exists(p) for p in trace_files):
                last_error = f"Missing trace files for {scenario_name}, trace {trace_file_name}."
                logger.warning(last_error)
                continue

            success, cost, error = run_single_simulation(
                str(solution_path), trace_files, config
            )

            if not success:
                last_error = f"Error in scenario '{scenario_name}': {error}"
                break

            total_scenario_cost += cost
            successful_runs_in_scenario += 1

        if successful_runs_in_scenario > 0:
            average_scenario_cost = total_scenario_cost / successful_runs_in_scenario
            scenario_costs.append(average_scenario_cost)
            logger.info(f"Scenario '{scenario_name}' Average Cost: ${average_scenario_cost:.2f}")
        else:
            scenario_costs.append(float('inf'))
            logger.warning(f"Scenario '{scenario_name}' failed completely. Last error: {last_error}")

    valid_costs = [c for c in scenario_costs if c != float('inf')]
    if not valid_costs:
        logger.error(f"All Stage 2 evaluation scenarios failed. Last error: {last_error}")
        return {
            "runs_successfully": 1.0,
            "cost": float('inf'),
            "combined_score": WORST_POSSIBLE_SCORE,
            "error": last_error
        }

    final_average_cost = sum(valid_costs) / len(valid_costs)

    logger.info("--- Evaluation Summary ---")
    logger.info(f"Final Average Cost across all scenarios: ${final_average_cost:.2f}")

    # Normalized scoring
    od_anchor = COSTS[ClusterType.ON_DEMAND] * TASK_DURATION_HOURS
    spot_anchor = COSTS[ClusterType.SPOT] * TASK_DURATION_HOURS

    denom = od_anchor - spot_anchor
    normalized = (od_anchor - final_average_cost) / denom
    score = max(0.0, min(1.0, normalized)) * 100

    logger.info(f"Final Normalized Score: {score:.2f}")

    return {
        "runs_successfully": 1.0,
        "score": round(score, 2),
        "avg_cost": final_average_cost,
        "od_anchor": od_anchor,
        "spot_anchor": spot_anchor
    }


def evaluate_solution(
    solution_path: Path,
    spec_path: Path,
    scenarios: List[Dict],
    deadline_hours: float,
    restart_overhead_hours: float,
) -> dict:
    """Evaluate a Solution; return payload with score and metrics."""
    data_path = str(SIM_ROOT / "data" / "converted_multi_region_aligned")

    # Validate solution
    load_and_validate_solution(solution_path, spec_path)

    # Run cascade evaluation
    stage1_result = evaluate_stage1(
        solution_path, data_path, deadline_hours, restart_overhead_hours
    )

    if stage1_result.get("runs_successfully", 0.0) > 0:
        stage2_result = evaluate_stage2(
            solution_path, data_path, scenarios, deadline_hours, restart_overhead_hours
        )
        return stage2_result
    else:
        return stage1_result


def main(
    resources_dir: str,
    scenarios: List[Dict],
    deadline_hours: float,
    restart_overhead_hours: float,
    default_solution: str = "../../execution_env/solution_env/solution.py",
) -> None:
    """Entry point for variant evaluators."""
    parser = argparse.ArgumentParser(description="Evaluate cant-be-late-multi solution")
    parser.add_argument(
        "--solution",
        default=default_solution,
        help="Path to contestant solution.py",
    )
    parser.add_argument(
        "--spec",
        default=str(Path(resources_dir) / "submission_spec.json"),
        help="Path to submission spec (passed to Solution.solve)",
    )
    args = parser.parse_args()

    solution_path = Path(args.solution).resolve()
    spec_path = Path(args.spec).resolve()

    try:
        payload = evaluate_solution(
            solution_path,
            spec_path,
            scenarios,
            deadline_hours,
            restart_overhead_hours,
        )
    except Exception as e:
        import traceback
        print(json.dumps({"error": str(e), "score": 0, "traceback": traceback.format_exc()}))
        raise
    else:
        print(json.dumps(payload))
        # Format: "score score_unbounded" (space-separated) for batch runner
        score = payload.get("score", 0)
        score_unbounded = payload.get("score_unbounded", score)
        print(f"{score} {score_unbounded}")


if __name__ == "__main__":
    # For direct testing with default settings
    from __init__ import HIGH_AVAILABILITY_SCENARIOS, TIGHT_DEADLINE, LARGE_OVERHEAD
    main(
        str(COMMON_DIR.parent / "high_availability_tight_deadline_large_overhead" / "resources"),
        scenarios=HIGH_AVAILABILITY_SCENARIOS,
        deadline_hours=TIGHT_DEADLINE,
        restart_overhead_hours=LARGE_OVERHEAD,
    )
