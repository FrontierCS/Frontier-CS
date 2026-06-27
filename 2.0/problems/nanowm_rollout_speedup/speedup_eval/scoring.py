"""Scoring math for nanowm_rollout_speedup (shared by the judge evaluator and
the agent-facing public test; keep the two in sync).

Mirrors the Frontier-CS 2.0 latency-optimization convention (cf.
vllm_llm_serving_optimization): geometric-mean per-clip speedup over a fixed
baseline, mapped through 100*log2, gated by an accuracy guardrail. Here
"accuracy" is rollout fidelity to ground truth (lower LPIPS = better), so the
guardrail penalizes patched LPIPS rising above the baseline's by more than a
tolerance.
"""
from __future__ import annotations

import math


def geometric_mean(values: list[float]) -> float:
    if not values:
        return 0.0
    return math.exp(sum(math.log(max(v, 1e-9)) for v in values) / len(values))


def paired_speedups(baseline_s: dict[str, float], patched_s: dict[str, float]) -> list[float]:
    """Per-clip baseline_seconds / patched_seconds (floored at 0.01)."""
    out: list[float] = []
    for cid, p in patched_s.items():
        b = baseline_s.get(cid)
        if b is None or p <= 0 or b <= 0:
            continue
        out.append(max(b / p, 0.01))
    return out


def score_from_speedup(speedup: float, target: float = 2.0) -> float:
    """Map geomean speedup -> [0, 100], reaching 100 at `target`x. target=2.0
    reproduces the old bare 100*log2(speedup) (saturated at 2x, so everything
    >=2x capped at 100 and became indistinguishable); a larger target keeps a
    gradient across the achievable range."""
    if speedup <= 0:
        return 0.0
    denom = math.log(max(target, 1.0 + 1e-9), 2)
    return max(0.0, min(100.0, 100.0 * math.log(speedup, 2) / denom))


def faithfulness_multiplier(faithfulness_lpips, tolerance: float) -> float:
    """1.0 while the patched rollout frames stay within `tolerance` mean LPIPS of
    the BASELINE rollout frames (a faithful acceleration); decays inverse-
    proportionally beyond that (a different rollout substituted for the baseline).
    `None` (no paired baseline frames, e.g. agent-role cached-baseline path) means
    'not measured' -> no penalty."""
    if faithfulness_lpips is None:
        return 1.0
    f = max(0.0, float(faithfulness_lpips))
    if f <= tolerance:
        return 1.0
    return max(0.0, min(1.0, tolerance / f))


def quality_multiplier(baseline_lpips: float, patched_lpips: float, tolerance: float) -> float:
    """1.0 while patched LPIPS stays within `tolerance` relative of baseline;
    decays inverse-proportionally beyond that. (Lower LPIPS = better, so the
    penalty is on RISES above baseline.)"""
    base = max(baseline_lpips, 1e-9)
    rel_rise = max(0.0, (patched_lpips - baseline_lpips) / base)
    if rel_rise <= tolerance:
        return 1.0
    return max(0.0, min(1.0, tolerance / rel_rise))


def provisional_score(
    baseline_seconds: dict[str, float],
    patched_seconds: dict[str, float],
    baseline_lpips: float,
    patched_lpips: float,
    tolerance: float,
    faithfulness_lpips=None,
    faithfulness_tolerance: float = 0.10,
    speedup_target: float = 2.0,
) -> dict[str, float]:
    speedups = paired_speedups(baseline_seconds, patched_seconds)
    gm = geometric_mean(speedups) if speedups else 0.0
    latency_score = score_from_speedup(gm, target=speedup_target)
    qmult = quality_multiplier(baseline_lpips, patched_lpips, tolerance)
    fmult = faithfulness_multiplier(faithfulness_lpips, faithfulness_tolerance)
    gate = qmult * fmult
    return {
        "geomean_speedup": gm,
        "latency_score": latency_score,
        "quality_multiplier": qmult,
        "faithfulness_multiplier": fmult,
        "faithfulness_lpips": (float(faithfulness_lpips) if faithfulness_lpips is not None else -1.0),
        "score": max(0.0, min(100.0, latency_score * gate)),
        "score_unbounded": max(0.0, 100.0 * math.log(max(gm, 1e-9), 2)) * gate,
        "clips_scored": float(len(speedups)),
    }
