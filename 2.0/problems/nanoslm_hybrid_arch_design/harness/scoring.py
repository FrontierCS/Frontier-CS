"""Scoring: tempered per-byte likelihood; perfect fit = 100, reference = 70.

Torch-free and unit-tested on CPU. Shared by the evaluator and the public test
so the agent sees the same math the judge uses.

The map is information-theoretic, smooth over the WHOLE domain, and
single-parameter::

    p     = 2 ** (-val_bpb)              # geometric-mean per-byte probability
    score = 100 * p ** GAMMA
          = 100 * 2 ** (-GAMMA * val_bpb)

a TEMPERED likelihood: the score is a fixed power of the probability the model
assigns to the held-out text, with GAMMA pinned by two anchors -- a PERFECT
fit (val_bpb 0, probability 1/byte) scores exactly 100, and the measured
reference solution scores exactly ``REF_ANCHOR_SCORE`` (70). HIGHER IS
BETTER. Consequences worth knowing:

  * There is NO interior clip: the formula attains 100 only at val_bpb = 0,
    the curve is strictly decreasing and smooth everywhere else, and the
    [0, 100] clamp below is a numerical safety net the curve never touches
    for real bpb >= 0. (An input of EXACTLY 0 or below is routed to
    FAILURE_SCORE by the validity guard instead -- deliberate: no honest
    measurement can be <= 0, and the 0.4 min_plausible_bpb leakage floor
    rejects anything close long before scoring, so "perfect fit scores 100"
    is a property of the curve, not a reachable code path.)
  * log2(score/100) is linear in bpb: the score halves every 1/GAMMA (~3.02)
    bits per byte, and score ratios depend only on bpb differences.
  * Failures score 0 (see ``FAILURE_SCORE``), and a degenerate/huge bpb decays
    to ~0 through the same exponential -- no special-casing needed.
  * The anchor constants are scoring conventions, NOT training knobs: they are
    deliberately absent from ``settings._FINGERPRINT_KEYS`` so recalibrating
    them never invalidates a cached baseline.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

# Measured val_bpb of reference.py under the CURRENT locked config
# (train_seconds=900, full-horizon LR, 2B corpus; final-role CRN pair,
# measured 2026-08-09: reference 1.55484 @264 steps, paired baseline
# 1.58648 @327 steps -> baseline scores ~69.5 under this anchor).
# Re-measure and update when a fingerprinted knob changes.
REF_ANCHOR_BPB = 1.55484
REF_ANCHOR_SCORE = 70.0

# Tempering exponent, pinned by the anchors (0 bpb -> 100,
# REF_ANCHOR_BPB -> REF_ANCHOR_SCORE).
GAMMA = math.log2(100.0 / REF_ANCHOR_SCORE) / REF_ANCHOR_BPB


@dataclass
class ScoreResult:
    score: float            # 100 * 2**(-GAMMA * sub_bpb) — smooth (0, 100], HIGHER IS BETTER
    score_unbounded: float  # identical on the valid domain (the clamp never binds, bpb >= 0)
    rel_improvement: float  # (base_bpb - sub_bpb) / base_bpb — reported only
    abs_bpb_delta: float    # base_bpb - sub_bpb — reported only


# Failed / rejected / degenerate runs. 0.0 is unambiguously the worst value
# now that the score is higher-is-better on [0, 100].
FAILURE_SCORE = 0.0


def _clip(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, x))


def score_from_bpb(
    base_bpb: float,
    sub_bpb: float,
) -> ScoreResult:
    """Map the submission's held-out bits-per-byte to the [0, 100] score.

    See the module docstring for the map and its properties. The baseline
    comparison (``abs_bpb_delta``, ``rel_improvement``) is still reported so an
    operator can read the gain without recomputing it, but the baseline does
    not participate in the score -- only the fixed reference anchor does.
    """
    # Invalid / degenerate values -> failure (runner also guards).
    if not (base_bpb > 0.0) or not (sub_bpb > 0.0):
        return ScoreResult(FAILURE_SCORE, FAILURE_SCORE, 0.0, 0.0)
    if not (base_bpb < float("inf")) or not (sub_bpb < float("inf")):
        return ScoreResult(FAILURE_SCORE, FAILURE_SCORE, 0.0, 0.0)

    unbounded = 100.0 * (2.0 ** (-GAMMA * sub_bpb))
    bounded = _clip(unbounded, 0.0, 100.0)  # inert for bpb >= 0; safety only
    abs_delta = base_bpb - sub_bpb          # reported for readability only
    rel = abs_delta / base_bpb              # reported for readability only
    return ScoreResult(bounded, unbounded, rel, abs_delta)


def format_message(
    base_bpb: float,
    sub_bpb: float,
    result: ScoreResult,
    *,
    steps: int,
    wall_seconds: float,
    train_block_size: int = 0,
    extra: str = "",
) -> str:
    """Public feedback string — metrics only, no submission stdout/tracebacks."""
    ctx = f"train_ctx={train_block_size}; " if train_block_size else ""
    msg = (
        f"base_val_bpb={base_bpb:.5f}; sub_val_bpb={sub_bpb:.5f}; "
        f"abs_bpb_delta={result.abs_bpb_delta:+.5f}; "
        f"rel_improvement={result.rel_improvement:+.4%}; "
        f"steps={steps}; {ctx}train_wall_s={wall_seconds:.1f}; "
        f"score={result.score:.4f} (100*2^(-GAMMA*bpb), smooth; perfect=100, "
        f"reference=70; HIGHER is better)"
    )
    if extra:
        msg += f"; note={extra}"
    return msg
