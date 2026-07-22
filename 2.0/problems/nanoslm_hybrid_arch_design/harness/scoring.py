"""Scoring: Absolute held-out bits-per-byte gain over the locked baseline.

Torch-free and unit-tested on CPU. Shared by the evaluator and the public test
so the agent sees the same math the judge uses.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ScoreResult:
    score: float            # bounded [0, 100] reported to Harbor
    score_unbounded: float  # keeps rewarding past 100
    rel_improvement: float  # (base_bpb - sub_bpb) / base_bpb — reported only
    abs_bpb_delta: float    # base_bpb - sub_bpb — the scored quantity


def _clip(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, x))


def score_from_bpb(
    base_bpb: float,
    sub_bpb: float,
    bpb_score_scale: float,
) -> ScoreResult:
    """Map a submission's held-out bits-per-byte to a [0, 100] score.

    Lower ``sub_bpb`` is better. The measurement is the absolute gain::

        gain  = base_bpb - sub_bpb          # bits per byte
        score = clip(100 * gain / bpb_score_scale, 0, 100)

    The baseline architecture (``sub_bpb == base_bpb``) scores 0, and a
    submission worse than the baseline scores 0.

    What ``bpb_score_scale`` is, and what it is not
    -----------------------------------------------
    It is a display convention and it is arbitrary by design. Its one necessary
    job is to map bits-per-byte into the 0-100 range Harbor expects: Harbor
    computes ``reward = score / 100``, so a raw ``gain`` of 0.05 bpb would
    surface as reward 0.0005 -- indistinguishable from zero for every
    submission. That is the whole reason the constant exists.

    It is not a calibrated definition of "what counts as a full win". No such
    number has been measured, and presenting an arbitrary constant as a target
    would (a) attach the score's meaning to a figure nobody determined and
    (b) throw away information at the clip, where a submission at 2x the scale
    scores the same 100 as one exactly at it. ``score_unbounded`` is therefore
    the un-clipped value and an operator should read it whenever the bounded
    score pins at 100.

    The one weak requirement that does remain is discrimination: set far too
    large and every submission pins at 0, far too small and every submission
    pins at 100. That is a much weaker condition than calibration and can be set
    from a single real-corpus run.

    Why absolute and not relative
    -----------------------------
    Absolute bpb is the unit the language-modelling literature quotes, so a
    result is directly comparable to published numbers; it is linear in
    cross-entropy, so equal absolute gains are equal information gains, and
    gains compose roughly additively. The cost is that it is not scale-free: the
    same absolute gain is roughly twice as hard at ``base_bpb`` 1.5 as at 2.9,
    so the operating point matters. ``rel_improvement`` is
    still computed and reported so an operator can see the relative figure
    without recomputing it.
    """
    # Invalid / degenerate values -> zero (defensive; runner also guards).
    if not (base_bpb > 0.0) or not (sub_bpb > 0.0):
        return ScoreResult(0.0, 0.0, 0.0, 0.0)
    if not (base_bpb < float("inf")) or not (sub_bpb < float("inf")):
        return ScoreResult(0.0, 0.0, 0.0, 0.0)
    if bpb_score_scale <= 0.0:
        raise ValueError("bpb_score_scale must be positive")

    abs_delta = base_bpb - sub_bpb          # the scored measurement
    rel = abs_delta / base_bpb              # reported for readability only
    unbounded = 100.0 * abs_delta / bpb_score_scale
    bounded = _clip(unbounded, 0.0, 100.0)
    # No credit for tying or losing to the baseline.
    if abs_delta <= 0.0:
        bounded = 0.0
    return ScoreResult(bounded, unbounded, rel, abs_delta)


def format_message(
    base_bpb: float,
    sub_bpb: float,
    result: ScoreResult,
    *,
    steps: int,
    wall_seconds: float,
    extra: str = "",
) -> str:
    """Public feedback string — metrics only, no submission stdout/tracebacks.

    Reports both the scored absolute gain and the relative figure: only the
    Scored quantity changed to absolute, and an operator should not have to
    recompute the other one.
    """
    msg = (
        f"base_val_bpb={base_bpb:.5f}; sub_val_bpb={sub_bpb:.5f}; "
        f"abs_bpb_delta={result.abs_bpb_delta:+.5f}; "   # Scored
        f"rel_improvement={result.rel_improvement:+.4%}; "
        f"steps={steps}; train_wall_s={wall_seconds:.1f}; "
        f"score={result.score:.4f}; score_unbounded={result.score_unbounded:.4f}"
    )
    if extra:
        msg += f"; note={extra}"
    return msg
