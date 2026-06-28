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


def wallclock_multiplier_from_rel(rel_over: float, tolerance: float, grace: float = 0.02) -> float:
    """Wall-clock guardrail credit given the RELATIVE over-budget (patched vs
    baseline gen time). The task is ISO-WALL-CLOCK drift reduction, so credit DECAYS
    as gen time rises -- NOT a flat 1.0 plateau up to +tolerance (which let drift be
    bought with up to `tolerance` extra compute for free, contradicting the premise).
    A small `grace` absorbs sub-effect timing jitter; past it the credit decays
    smoothly as mult = 1/(1 + (rel_over-grace)/tolerance): ~0.556 at `tolerance` over
    parity, exactly 0.5 at `grace+tolerance`, and ->0 beyond. A speedup (rel_over<=0)
    keeps full credit."""
    rel_over = max(0.0, rel_over)
    if rel_over <= grace:
        return 1.0
    x = (rel_over - grace) / max(tolerance, 1e-9)
    return max(0.0, min(1.0, 1.0 / (1.0 + x)))


def wallclock_multiplier(baseline_seconds: float, patched_seconds: float, tolerance: float) -> float:
    base = max(baseline_seconds, 1e-9)
    return wallclock_multiplier_from_rel((patched_seconds - baseline_seconds) / base, tolerance)


def provisional_score(baseline_tail, patched_tail, baseline_seconds, patched_seconds, tolerance,
                      wallclock_rel_over=None):
    drift_score = drift_reduction_score(baseline_tail, patched_tail)
    # Prefer the clip-weighted mean of PER-CHUNK over-budget ratios (each measured on
    # ONE board) when the fan-out provides it -- fairer than a ratio of gen_seconds
    # SUMMED across heterogeneous H100 boards; else fall back to the summed-time ratio.
    if wallclock_rel_over is not None:
        rel_over = max(0.0, float(wallclock_rel_over))
    else:
        base = max(baseline_seconds, 1e-9)
        rel_over = max(0.0, (patched_seconds - baseline_seconds) / base)
    wmult = wallclock_multiplier_from_rel(rel_over, tolerance)
    return {
        "tail_drift_reduction": (baseline_tail - patched_tail),
        "rel_reduction_pct": (100.0 * (baseline_tail - patched_tail) / max(baseline_tail, 1e-9)),
        "drift_score": drift_score,
        "wallclock_rel_over": rel_over,
        "wallclock_multiplier": wmult,
        "score": max(0.0, min(100.0, drift_score * wmult)),
        # Unlike the speedup task (whose 100*log2(speedup) is genuinely uncapped
        # beyond 2x), a RELATIVE drift reduction is intrinsically in [0, 100]
        # (patched_tail in [0, baseline_tail]), so score_unbounded == score by
        # construction. Kept for a uniform (score, score_unbounded) return shape
        # across the two tasks.
        "score_unbounded": max(0.0, min(100.0, drift_score * wmult)),
    }
