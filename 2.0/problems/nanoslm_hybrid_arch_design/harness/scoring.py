"""Scoring: the submission's held-out bits-per-byte, reported raw.

Torch-free and unit-tested on CPU. Shared by the evaluator and the public test
so the agent sees the same math the judge uses.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ScoreResult:
    score: float            # the submission's val_bpb — LOWER IS BETTER
    score_unbounded: float  # identical to score (kept for interface stability)
    rel_improvement: float  # (base_bpb - sub_bpb) / base_bpb — reported only
    abs_bpb_delta: float    # base_bpb - sub_bpb — reported only


# Failure sentinel: with a lower-is-better score, a failed/rejected run must
# NEVER return 0.0 (that would read as a perfect bpb). Finite rather than inf
# so every JSON serializer downstream stays standards-compliant; four orders of
# magnitude above any honest bpb, so it can never be confused for a
# measurement.
FAILURE_SCORE = 9999.0


def score_from_bpb(
    base_bpb: float,
    sub_bpb: float,
) -> ScoreResult:
    """The score IS the submission's held-out bits-per-byte, unscaled.

    LOWER IS BETTER, and there is no clipping, no baseline-relative mapping,
    and no display constant: ``score == sub_bpb``. The former
    ``clip(100 * (base_bpb - sub_bpb) / bpb_score_scale, 0, 100)`` mapping was
    removed deliberately -- the raw measurement is the quantity the
    language-modelling literature quotes, and any rescaling constant attached
    an arbitrary figure to the score's meaning. Consumers that rank runs must
    sort ascending.

    The baseline comparison is still reported (``abs_bpb_delta``,
    ``rel_improvement``) so an operator can read the gain without recomputing
    it, but neither figure participates in the score.
    """
    # Invalid / degenerate values -> the failure sentinel (worst; runner also
    # guards).
    if not (base_bpb > 0.0) or not (sub_bpb > 0.0):
        return ScoreResult(FAILURE_SCORE, FAILURE_SCORE, 0.0, 0.0)
    if not (base_bpb < float("inf")) or not (sub_bpb < float("inf")):
        return ScoreResult(FAILURE_SCORE, FAILURE_SCORE, 0.0, 0.0)

    abs_delta = base_bpb - sub_bpb          # reported for readability only
    rel = abs_delta / base_bpb              # reported for readability only
    return ScoreResult(sub_bpb, sub_bpb, rel, abs_delta)


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
        f"abs_bpb_delta={result.abs_bpb_delta:+.5f}; "
        f"rel_improvement={result.rel_improvement:+.4%}; "
        f"steps={steps}; train_wall_s={wall_seconds:.1f}; "
        f"score={result.score:.5f} (== sub_val_bpb; LOWER is better)"
    )
    if extra:
        msg += f"; note={extra}"
    return msg
