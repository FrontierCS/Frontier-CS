"""Scoring math shared with the agent-facing public test.

The judge's authoritative scorer lives in the task evaluator; these helpers
mirror it so the public test shows a provisional score consistent with how the
judge grades. Keep the two in sync.

Two changes vs a naive geomean-speedup score:

* Per-instance speedup is clamped to ``[1/cap, cap]`` and a patched instance that
  *failed* (errored / early-exited, hence a tiny latency) is counted as a
  regression (``1/cap``), not a giant speedup — so "fail fast" cannot game the
  metric (audit finding: uncapped geomean inflation).
* The final score blends two workloads (SWE-bench + BFCL) by configurable
  weights, each gated by its own accuracy guardrail. BFCL's baseline accuracy is
  non-zero, so its guardrail is live.
"""

from __future__ import annotations

import math
from typing import Iterable


def geometric_mean(values: list[float]) -> float:
    if not values:
        return 0.0
    return math.exp(sum(math.log(max(value, 1e-9)) for value in values) / len(values))


def paired_speedups(
    baseline: dict[str, float],
    patched: dict[str, float],
    *,
    cap: float = 8.0,
    failed_ids: Iterable[str] = (),
) -> list[float]:
    cap = max(1.0001, cap)
    floor = 1.0 / cap
    failed = set(failed_ids)
    speedups: list[float] = []
    for instance_id, patched_value in patched.items():
        base_value = baseline.get(instance_id)
        if base_value is None or base_value <= 0:
            continue
        if instance_id in failed or patched_value <= 0:
            # Patched request failed; do not let its tiny latency read as a win.
            speedups.append(floor)
            continue
        speedups.append(max(floor, min(cap, base_value / patched_value)))
    return speedups


def score_from_speedup(speedup: float) -> float:
    if speedup <= 0:
        return 0.0
    return max(0.0, min(100.0, 100.0 * math.log(speedup, 2)))


def accuracy_multiplier(
    baseline_accuracy: float,
    patched_accuracy: float,
    tolerance: float,
    abs_tolerance: float = 0.05,
) -> float:
    # No penalty if the accuracy drop is within EITHER the relative tolerance OR
    # the absolute tolerance. resolve_rate over a finite instance slice is a
    # coarse, high-variance signal (a 1-2 instance swing on 50 ~ a big relative
    # drop), so the absolute floor keeps small, likely-noise drops from being
    # over-penalized while still catching real quality regressions.
    abs_drop = max(0.0, baseline_accuracy - patched_accuracy)
    base = max(baseline_accuracy, 1e-9)
    rel_drop = max(0.0, abs_drop / base)
    if abs_drop <= abs_tolerance or rel_drop <= tolerance:
        return 1.0
    return max(0.0, min(1.0, tolerance / rel_drop))


def workload_score(
    baseline_latency: dict[str, float],
    patched_latency: dict[str, float],
    baseline_accuracy: float,
    patched_accuracy: float,
    tolerance: float,
    *,
    cap: float = 8.0,
    failed_ids: Iterable[str] = (),
    abs_tolerance: float = 0.05,
) -> dict[str, float]:
    """Latency-speedup score for one workload, gated by its accuracy guardrail."""
    speedups = paired_speedups(baseline_latency, patched_latency, cap=cap, failed_ids=failed_ids)
    gm = geometric_mean(speedups) if speedups else 0.0
    latency_score = score_from_speedup(gm)
    acc_mult = accuracy_multiplier(baseline_accuracy, patched_accuracy, tolerance, abs_tolerance)
    return {
        "latency_geomean_speedup": gm,
        "latency_score": latency_score,
        "accuracy_multiplier": acc_mult,
        "score": max(0.0, min(100.0, latency_score * acc_mult)),
        "instances_scored": float(len(speedups)),
    }


def blend(swe_score: float, bfcl_score: float, weights: tuple[float, float]) -> float:
    w_swe, w_bfcl = weights
    return max(0.0, min(100.0, w_swe * swe_score + w_bfcl * bfcl_score))


def provisional_score(
    baseline_latency: dict[str, float],
    patched_latency: dict[str, float],
    baseline_accuracy: float,
    patched_accuracy: float,
    tolerance: float,
    *,
    cap: float = 8.0,
    abs_tolerance: float = 0.05,
    baseline_bfcl_latency: dict[str, float] | None = None,
    patched_bfcl_latency: dict[str, float] | None = None,
    baseline_bfcl_accuracy: float = 0.0,
    patched_bfcl_accuracy: float = 0.0,
    weights: tuple[float, float] = (0.5, 0.5),
) -> dict[str, float]:
    swe = workload_score(
        baseline_latency, patched_latency, baseline_accuracy, patched_accuracy, tolerance,
        cap=cap, abs_tolerance=abs_tolerance,
    )
    has_bfcl = bool(patched_bfcl_latency)
    if has_bfcl:
        bfcl = workload_score(
            baseline_bfcl_latency or {}, patched_bfcl_latency or {},
            baseline_bfcl_accuracy, patched_bfcl_accuracy, tolerance,
            cap=cap, abs_tolerance=abs_tolerance,
        )
        use_weights = weights
    else:
        bfcl = {"latency_geomean_speedup": 0.0, "latency_score": 0.0,
                "accuracy_multiplier": 1.0, "score": 0.0, "instances_scored": 0.0}
        use_weights = (1.0, 0.0)
    return {
        "swe_latency_geomean_speedup": swe["latency_geomean_speedup"],
        "swe_score": swe["score"],
        "bfcl_latency_geomean_speedup": bfcl["latency_geomean_speedup"],
        "bfcl_score": bfcl["score"],
        "bfcl_accuracy_multiplier": bfcl["accuracy_multiplier"],
        "score": blend(swe["score"], bfcl["score"], use_weights),
    }
