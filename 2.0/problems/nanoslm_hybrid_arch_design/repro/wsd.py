"""WSD-S learning-rate schedule (warmup - stable - decay with periodic resets).

Paper (arXiv:2604.03444, Section 4.1): a WSD-S schedule that is token-agnostic
-- the LR at step t does not depend on the total token budget T. "We decay the
learning rate for 5% of the training tokens to 0 at each of the five Chinchilla
factors to obtain the trained checkpoint for that factor." Between factors the
LR resets back to the stable peak (the '-S' = periodic reset), so a single long
run yields checkpoints at 0.5x/1x/2x/4x/8x Chinchilla.

Refs: Hu et al. 2024 (MiniCPM WSD); Wen et al. 2025b (river-valley view of WSD).

Two schedule shapes here:
  * ``lr_wsd``: single warmup -> stable -> terminal 5% decay-to-0. Used for a
    fixed-budget run (e.g. the 1x-Chinchilla smoke).
  * ``lr_wsd_s``: the periodic-reset variant. Given the ordered list of
    decay-endpoint steps (the Chinchilla factors), it produces a checkpoint at
    each: warmup once, hold at peak, and for the last ``decay_frac`` of the span
    BEFORE each endpoint, decay to 0; immediately after an endpoint, jump back
    to peak. Evaluate/snapshot AT each endpoint step.

Decay shape: the WSD "river-valley" analysis (Wen et al.) favours a 1-sqrt decay
over linear; we use 1 - sqrt(progress), which spends more steps near the low LR.
Set ``decay_shape='linear'`` for a plain linear ramp to 0.
"""

from __future__ import annotations

import math


def _decay_mult(progress: float, shape: str) -> float:
    """LR multiplier in [0,1] as decay progresses 0->1 (1 at start, 0 at end)."""
    progress = min(1.0, max(0.0, progress))
    if shape == "linear":
        return 1.0 - progress
    # '1-sqrt' (river-valley): stays high then drops fast near the end.
    return 1.0 - math.sqrt(progress)


def lr_wsd(step: int, *, peak_lr: float, total_steps: int, warmup_steps: int,
           decay_frac: float = 0.05, decay_shape: str = "1-sqrt") -> float:
    """Single warmup -> stable -> terminal decay-to-0 over the last ``decay_frac``."""
    if step < warmup_steps:
        return peak_lr * (step + 1) / max(1, warmup_steps)
    decay_steps = max(1, int(round(decay_frac * total_steps)))
    decay_start = total_steps - decay_steps
    if step < decay_start:
        return peak_lr
    progress = (step - decay_start) / decay_steps
    return peak_lr * _decay_mult(progress, decay_shape)


def lr_wsd_s(step: int, *, peak_lr: float, endpoints: list[int], warmup_steps: int,
             decay_frac: float = 0.05, decay_shape: str = "1-sqrt") -> float:
    """Periodic-reset WSD-S. ``endpoints`` = sorted decay-endpoint steps.

    For each consecutive span (prev_endpoint, endpoint], the last ``decay_frac``
    of the span decays to 0; the rest holds at peak (after the one-time warmup).
    Snapshot the model exactly AT each endpoint step to get that factor's ckpt.
    """
    if step < warmup_steps:
        return peak_lr * (step + 1) / max(1, warmup_steps)
    prev = 0
    for end in endpoints:
        if step <= end:
            span = end - prev
            decay_steps = max(1, int(round(decay_frac * span)))
            decay_start = end - decay_steps
            if step < decay_start:
                return peak_lr
            progress = (step - decay_start) / decay_steps
            return peak_lr * _decay_mult(progress, decay_shape)
        prev = end
    return 0.0  # past the final endpoint


if __name__ == "__main__":
    # Sanity checks.
    P, T, W = 2e-3, 1000, 50
    assert abs(lr_wsd(0, peak_lr=P, total_steps=T, warmup_steps=W) - P / W) < 1e-12
    assert abs(lr_wsd(W, peak_lr=P, total_steps=T, warmup_steps=W) - P) < 1e-12      # stable
    assert abs(lr_wsd(940, peak_lr=P, total_steps=T, warmup_steps=W) - P) < 1e-9     # still stable (decay=last 50)
    assert lr_wsd(999, peak_lr=P, total_steps=T, warmup_steps=W) < P                 # decaying
    assert abs(lr_wsd(T, peak_lr=P, total_steps=T, warmup_steps=W)) < 1e-9           # ~0 at end
    # WSD-S: peak restored right after an endpoint.
    eps = [500, 1000]
    assert abs(lr_wsd_s(600, peak_lr=P, endpoints=eps, warmup_steps=W) - P) < 1e-9   # reset to peak after 500
    assert lr_wsd_s(500, peak_lr=P, endpoints=eps, warmup_steps=W) < P               # decayed at endpoint 500
    print("WSD / WSD-S schedule self-check OK")
    for s in (0, 25, 50, 500, 900, 950, 975, 1000):
        print(f"  step {s:4d}  lr={lr_wsd(s, peak_lr=P, total_steps=T, warmup_steps=W):.3e}")
