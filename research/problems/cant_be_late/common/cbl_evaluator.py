"""
Evaluator using the real-cost dataset (first 30% traces per environment).
Provides per-scenario mean/std so the LLM can reason about difficult cases.
"""

import argparse
import glob
import json
import logging
import math
import os
import signal
import sys
from collections import defaultdict
from concurrent.futures import ProcessPoolExecutor, as_completed

import numpy as np

# Local fallback for EvaluationResult to avoid external dependency
try:
    from openevolve.evaluation_result import EvaluationResult  # type: ignore
except Exception:  # pragma: no cover
    try:
        from dataclasses import dataclass
        from typing import Any, Dict

        @dataclass
        class EvaluationResult:  # minimal stub
            metrics: Dict[str, Any]
            artifacts: Dict[str, Any]
    except Exception:
        EvaluationResult = dict  # last‑resort fallback; caller should handle dict

# -----------------------------------------------------------------------------
# Paths / imports
# -----------------------------------------------------------------------------
COMMON_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.join(COMMON_DIR, "cant-be-late-simulator")

# Add common dir to path for sim_worker import
if COMMON_DIR not in sys.path:
    sys.path.insert(0, COMMON_DIR)

from sim_worker import run_single_simulation  # noqa: E402

# -----------------------------------------------------------------------------
# Logging / WANDB
# -----------------------------------------------------------------------------
log_level_name = os.environ.get("CBL_LOG_LEVEL", "INFO").upper()
log_level = getattr(logging, log_level_name, logging.INFO)
logging.basicConfig(level=log_level)
logger = logging.getLogger(__name__)

os.environ.setdefault("WANDB_MODE", "offline")

# -----------------------------------------------------------------------------
# Config
# -----------------------------------------------------------------------------
TRACE_TARGET = 30  # per environment, take up to 30 traces evenly spaced

# ADRS-aligned configuration
ENV_PATHS = [
    "us-west-2a_k80_8",
    "us-west-2b_k80_1",
    "us-west-2b_k80_8",
    "us-west-2a_v100_1",
    "us-west-2a_v100_8",
    "us-west-2b_v100_1",
]

JOB_CONFIGS = [
    {"duration": 48, "deadline": 52},
    {"duration": 48, "deadline": 70},
]

CHANGEOVER_DELAYS = [0.02, 0.05, 0.1]

FAILED_SCORE = -100000.0

MAX_WORKERS = int(os.environ.get('EVALUATOR_MAX_WORKERS', '48'))
FUTURE_TIMEOUT = float(os.environ.get('EVALUATOR_TIMEOUT', '300'))


def build_trace_pool(
    min_required_hours: float,
    env_paths: list[str] = None,
    changeover_delays: list[float] = None,
) -> dict[float, dict[str, list[str]]]:
    """Select trace files per overhead/env with coverage ≥ min_required_hours.

    Note: Trace data is independent of overhead value - we always load from
    the 0.02 trace directory. The overhead config only affects simulation cost.
    """
    env_paths = env_paths or ENV_PATHS
    changeover_delays = changeover_delays or CHANGEOVER_DELAYS

    # Always use 0.02 traces - trace data is independent of overhead config
    TRACE_OVERHEAD = "0.02"

    trace_pool: dict[float, dict[str, list[str]]] = {}
    total_selected = 0

    for overhead in changeover_delays:
        env_map: dict[str, list[str]] = {}
        base_dir = os.path.join(
            PROJECT_ROOT,
            f"data/real/ddl=search+task=48+overhead={TRACE_OVERHEAD}",
            "real",
        )
        if not os.path.isdir(base_dir):
            logger.warning("No trace directory at %s", base_dir)
            trace_pool[overhead] = env_map
            continue

        for env_path in env_paths:
            trace_dir = os.path.join(base_dir, env_path, "traces", "random_start")
            pattern = os.path.join(trace_dir, "*.json")
            matching = sorted(glob.glob(pattern))
            if not matching:
                logger.warning("No traces found for %s (config overhead %.2f)", env_path, overhead)
                env_map[env_path] = []
                continue

            eligible: list[str] = []
            for trace_file in matching:
                try:
                    with open(trace_file, "r", encoding="utf-8") as fh:
                        data = json.load(fh)
                    gap_seconds = data.get("metadata", {}).get("gap_seconds")
                    samples = data.get("data", [])
                    if not gap_seconds or not samples:
                        continue
                    total_hours = len(samples) * gap_seconds / 3600.0
                    if total_hours + 1e-9 < min_required_hours:
                        continue
                    eligible.append(trace_file)
                except Exception as exc:  # pragma: no cover
                    logger.warning("Failed to read trace %s: %s", trace_file, exc)

            if not eligible:
                logger.warning(
                    "No traces ≥ %.2fh for %s (config overhead %.2f)",
                    min_required_hours,
                    env_path,
                    overhead,
                )
                env_map[env_path] = []
                continue

            if len(eligible) > TRACE_TARGET:
                indices = []
                max_idx = len(eligible) - 1
                denom = TRACE_TARGET - 1 if TRACE_TARGET > 1 else 1
                prev = -1
                for j in range(TRACE_TARGET):
                    raw = round(j * max_idx / denom)
                    if raw <= prev:
                        raw = prev + 1
                    if raw > max_idx:
                        raw = max_idx
                    indices.append(raw)
                    prev = raw
                eligible = [eligible[i] for i in indices]
            logger.info(
                "Selected %d traces for %s (config overhead %.2f)",
                len(eligible),
                env_path,
                overhead,
            )
            env_map[env_path] = eligible
            total_selected += len(eligible)

        trace_pool[overhead] = env_map

    logger.info("Total trace selections (≥ %.2fh): %d", min_required_hours, total_selected)
    return trace_pool





def _run_baseline_comparison(selected_traces, eval_configs, max_workers=4):
    """Baseline comparison disabled in this configuration."""
    return None


def _analyze_spot_availability(traces_by_config):
    """Spot availability analysis disabled."""
    return {}

def evaluate_stage1(program_path: str) -> dict:
    try:
        with open(program_path, "r", encoding="utf-8") as fh:
            code = fh.read()
        compile(code, program_path, "exec")
        if "class" not in code or "Strategy" not in code or "_step" not in code:
            return {
                "runs_successfully": 0.0,
                "score": FAILED_SCORE,
                "score_unbounded": FAILED_SCORE,
                "combined_score": FAILED_SCORE,
                "combined_score_unbounded": FAILED_SCORE,
                "error": "Missing Strategy/_step",
            }
        return {"runs_successfully": 1.0}
    except SyntaxError as exc:
        return {
            "runs_successfully": 0.0,
            "score": FAILED_SCORE,
            "score_unbounded": FAILED_SCORE,
            "combined_score": FAILED_SCORE,
            "combined_score_unbounded": FAILED_SCORE,
            "error": f"Syntax error: {exc}",
        }
    except Exception as exc:  # pragma: no cover
        return {
            "runs_successfully": 0.0,
            "score": FAILED_SCORE,
            "score_unbounded": FAILED_SCORE,
            "combined_score": FAILED_SCORE,
            "combined_score_unbounded": FAILED_SCORE,
            "error": str(exc),
        }


def evaluate_stage2(
    program_path: str,
    env_paths: list[str] = None,
    job_configs: list[dict] = None,
    changeover_delays: list[float] = None,
) -> EvaluationResult | dict:
    program_path = os.path.abspath(program_path)

    env_paths = env_paths or ENV_PATHS
    job_configs = job_configs or JOB_CONFIGS
    changeover_delays = changeover_delays or CHANGEOVER_DELAYS

    min_required_hours = max(job_config["deadline"] for job_config in job_configs)
    trace_pool = build_trace_pool(min_required_hours, env_paths, changeover_delays)

    total_traces = sum(
        len(traces)
        for env_map in trace_pool.values()
        for traces in env_map.values()
    )
    if total_traces == 0:
        return {
            "runs_successfully": 0.0,
            "score": 0.0,
            "score_unbounded": 0.0,
            "combined_score": FAILED_SCORE,
            "combined_score_unbounded": FAILED_SCORE,
            "error": "No trace files found",
        }

    eval_configs = [
        {"duration": job["duration"], "deadline": job["deadline"], "overhead": delay}
        for job in job_configs
        for delay in changeover_delays
    ]
    logger.info(
        "Testing on %d traces with %d configs",
        total_traces,
        len(eval_configs),
    )

    all_trace_paths = [
        trace
        for env_map in trace_pool.values()
        for traces in env_map.values()
        for trace in traces
    ]

    scenario_costs: dict[str, list[float]] = defaultdict(list)
    trace_infos: dict[str, list[dict]] = defaultdict(list)
    all_costs: list[float] = []
    total_evaluations = 0

    max_workers = min(MAX_WORKERS, os.cpu_count() or MAX_WORKERS)
    executor_kwargs = {}
    try:
        import multiprocessing

        if hasattr(multiprocessing, "get_context"):
            executor_kwargs["mp_context"] = multiprocessing.get_context("fork")
    except Exception:  # pragma: no cover
        pass

    executor = ProcessPoolExecutor(max_workers=max_workers, **executor_kwargs)
    future_to_info = {}

    all_warnings: list[str] = []
    all_errors: list[str] = []
    traces_by_config: dict[str, list[dict]] = defaultdict(list)

    old_sigint = old_sigterm = None
    try:
        try:
            old_sigint = signal.signal(signal.SIGINT, signal.SIG_IGN)
            old_sigterm = signal.signal(signal.SIGTERM, signal.SIG_IGN)
        except ValueError:
            old_sigint = old_sigterm = None

        for config in eval_configs:
            overhead = config["overhead"]
            env_map = trace_pool.get(overhead, {})
            if not env_map:
                logger.warning("No traces selected for overhead %.2f", overhead)
                continue

            for env_path, trace_list in env_map.items():
                if not trace_list:
                    logger.warning(
                        "No eligible traces for %s at overhead %.2f",
                        env_path,
                        overhead,
                    )
                    continue

                for trace_file in trace_list:
                    future = executor.submit(
                        run_single_simulation,
                        program_path,
                        trace_file,
                        config,
                    )
                    future_to_info[future] = (env_path, trace_file, config)
                    total_evaluations += 1

        logger.info("Total evaluations: %d", total_evaluations)

        if total_evaluations == 0:
            executor.shutdown(wait=False, cancel_futures=True)
            return {
                "runs_successfully": 0.0,
                "score": 0.0,
                "score_unbounded": 0.0,
                "combined_score": FAILED_SCORE,
                "combined_score_unbounded": FAILED_SCORE,
                "error": "No evaluations scheduled (trace pool empty)",
            }

        for future in as_completed(future_to_info):
            env_path, trace_file, config = future_to_info[future]
            try:
                result = future.result(timeout=FUTURE_TIMEOUT)
                if not (isinstance(result, (list, tuple)) and len(result) >= 2):
                    raise RuntimeError("Worker returned malformed result")

                success, cost = result[0], result[1]
                error_msg = result[2] if len(result) > 2 else ""
                trace_name = (
                    os.path.basename(os.path.dirname(trace_file))
                    + "/"
                    + os.path.splitext(os.path.basename(trace_file))[0]
                )
                if success:
                    all_costs.append(cost)
                    key = (
                        f"{env_path}|d{config['duration']}_dl{config['deadline']}_o{config['overhead']}"
                    )
                    scenario_costs[key].append(cost)
                    trace_infos[key].append(
                        {
                            "trace_name": trace_name,
                            "cost": cost,
                            "config": config,
                        }
                    )
                    traces_by_config[key].append(
                        {
                            "trace_name": trace_name,
                            "trace_file": trace_file,
                        }
                    )
                    logger.info(
                        "✓ %s (d=%d, dl=%d, o=%.2f): $%.2f",
                        trace_name,
                        config["duration"],
                        config["deadline"],
                        config["overhead"],
                        cost,
                    )
                else:
                    logger.error(
                        "Simulation failed: %s (d=%d, dl=%d, o=%.2f) -> %s",
                        trace_name,
                        config["duration"],
                        config["deadline"],
                        config["overhead"],
                        error_msg,
                    )
                    for pending in future_to_info:
                        pending.cancel()
                    executor.shutdown(wait=False, cancel_futures=True)
                    return {
                        "runs_successfully": 0.0,
                        "score": 0.0,
                        "score_unbounded": 0.0,
                        "combined_score": FAILED_SCORE,
                        "combined_score_unbounded": FAILED_SCORE,
                        "error": f"Not all runs successful: {error_msg}",
                    }
            except Exception as exc:  # pragma: no cover
                for pending in future_to_info:
                    pending.cancel()
                executor.shutdown(wait=False, cancel_futures=True)
                return {
                    "runs_successfully": 0.0,
                    "score": 0.0,
                    "score_unbounded": 0.0,
                    "combined_score": FAILED_SCORE,
                    "combined_score_unbounded": FAILED_SCORE,
                    "error": str(exc),
                }
    finally:
        if old_sigint is not None:
            signal.signal(signal.SIGINT, old_sigint)
        if old_sigterm is not None:
            signal.signal(signal.SIGTERM, old_sigterm)
        executor.shutdown(wait=True)

    avg_cost = float(np.mean(all_costs)) if all_costs else 0.0
    std_cost = float(np.std(all_costs)) if all_costs else 0.0
    score_unbounded = -avg_cost
    score = score_unbounded
    combined_score_unbounded = score_unbounded - 0.25 * std_cost
    combined_score = combined_score_unbounded

    logger.info("All %d simulations completed successfully!", len(all_costs))
    logger.info("Average cost: $%.2f", avg_cost)
    logger.info("Score (negative cost): %.2f", score)

    scenario_stats = {}
    for key, costs in scenario_costs.items():
        env_path, rest = key.split("|", 1)
        parts = rest.split("_")
        duration = int(parts[0][1:])
        deadline = int(parts[1][2:])
        overhead = float(parts[2][1:])
        scenario_stats[key] = {
            "env_path": env_path,
            "duration": duration,
            "deadline": deadline,
            "overhead": overhead,
            "avg": float(np.mean(costs)),
            "std": float(np.std(costs)) if len(costs) > 1 else 0.0,
            "count": len(costs),
        }

    worst = sorted(scenario_stats.values(), key=lambda x: x["avg"], reverse=True)[:5]
    lines = ["Worst scenarios (mean cost high → needs work):"]
    for item in worst:
        lines.append(
            f"- {item['env_path']} d={item['duration']} dl={item['deadline']} o={item['overhead']:.2f}: "
            f"avg=${item['avg']:.2f}, std=${item['std']:.2f}, n={item['count']}"
        )
    artifact_text = "\n".join(lines)

    metrics = {
        "runs_successfully": 1.0,
        "score": score,
        "score_unbounded": score_unbounded,
        "combined_score": combined_score,
        "combined_score_unbounded": combined_score_unbounded,
        "avg_cost": avg_cost,
        "cost_std": std_cost,
        "scenario_stats": scenario_stats,
    }

    # Analyze availability and baseline comparisons
    availability_stats = _analyze_spot_availability(traces_by_config)
    baseline_stats = _run_baseline_comparison(all_trace_paths, eval_configs)

    artifacts = {
        "scenario_summary": artifact_text,
        "scenario_stats_json": json.dumps(scenario_stats, ensure_ascii=False),
    }
    if availability_stats:
        artifacts["availability_stats_json"] = json.dumps(availability_stats, ensure_ascii=False)
    if baseline_stats:
        artifacts["baseline_stats_json"] = json.dumps(baseline_stats, ensure_ascii=False)

    return EvaluationResult(metrics=metrics, artifacts=artifacts)


def evaluate(_program_path: str) -> dict:
    raise NotImplementedError("Use cascade evaluation")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("program_path", type=str, default="initial_program.py", nargs="?")
    args = parser.parse_args()
    result = evaluate_stage2(args.program_path)
    if isinstance(result, dict):
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        payload = {
            'metrics': result.metrics,
            'artifacts': result.artifacts,
        }
        print(json.dumps(payload, indent=2, ensure_ascii=False))
