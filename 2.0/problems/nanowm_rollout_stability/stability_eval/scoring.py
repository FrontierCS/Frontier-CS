"""Scoring for nanowm_rollout_stability — the DUAL of the speedup task.

Speedup: minimize wall-clock at iso-quality.  Stability: minimize long-horizon
DRIFT (tail-frame LPIPS-vs-GT) at iso-WALL-CLOCK. Score = relative tail-drift
reduction over the unpatched baseline, gated by a wall-clock guardrail (so drift
can't simply be bought with more compute -- that's the speedup axis).
"""
from __future__ import annotations


def drift_reduction_score(baseline_tail: float, patched_tail: float) -> float:
    """Relative tail-drift reduction, in [0, 100]. 0 if patched is no better."""
    if baseline_tail <= 0:
        return 0.0
    rel = (baseline_tail - patched_tail) / baseline_tail
    return max(0.0, min(100.0, 100.0 * rel))


def wallclock_multiplier(baseline_seconds: float, patched_seconds: float, tolerance: float) -> float:
    """1.0 while patched wall-clock stays within `tolerance` of baseline; decays
    inverse-proportionally beyond (can't buy drift reduction with more compute)."""
    base = max(baseline_seconds, 1e-9)
    rel_over = max(0.0, (patched_seconds - baseline_seconds) / base)
    if rel_over <= tolerance:
        return 1.0
    return max(0.0, min(1.0, tolerance / rel_over))


def provisional_score(baseline_tail, patched_tail, baseline_seconds, patched_seconds, tolerance):
    drift_score = drift_reduction_score(baseline_tail, patched_tail)
    wmult = wallclock_multiplier(baseline_seconds, patched_seconds, tolerance)
    return {
        "tail_drift_reduction": (baseline_tail - patched_tail),
        "rel_reduction_pct": (100.0 * (baseline_tail - patched_tail) / max(baseline_tail, 1e-9)),
        "drift_score": drift_score,
        "wallclock_multiplier": wmult,
        "score": max(0.0, min(100.0, drift_score * wmult)),
        "score_unbounded": max(0.0, drift_score * wmult),
    }
