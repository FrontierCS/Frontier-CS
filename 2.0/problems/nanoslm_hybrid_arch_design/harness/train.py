"""Locked training loop (torch path).

The optimizer, LR schedule, weight-decay grouping, gradient accumulation, data
order, gradient clipping, and the wall-clock cutoff are all fixed here so the
task measures *architecture*, not training tricks. The harness computes the
cross-entropy loss from the model's logits and ignores any loss the model
returns.

Each optimizer step accumulates ``cfg.grad_accum`` micro-batches of
``cfg.batch_size`` sequences, for an effective batch of
``batch_size * grad_accum`` at the peak activation memory of a single
micro-batch.

Timing note: wall-clock is measured by ``time.monotonic`` inside the harness
(never by the model). Training stops at the first optimizer step whose start
exceeds ``cfg.train_seconds``. ``max_train_seconds`` is an infrastructure
backstop (the Modal function timeout / orchestrator), not a loop condition: a
between-step check could never fire before the ``train_seconds`` one, and it
could not interrupt a hung step anyway.
"""

from __future__ import annotations

import math
import time
from dataclasses import dataclass

from .data import TokenData
from .settings import TaskConfig


@dataclass
class TrainOutput:
    steps: int
    wall_seconds: float
    final_train_loss: float


def _lr_at(step: int, elapsed: float, cfg: TaskConfig) -> float:
    """Linear step-warmup, then cosine decay over the wall-clock budget.

    The decay is a function of ``elapsed / train_seconds``, not of a step
    count. The stop condition is wall-clock, so a step horizon cannot be known
    in advance, and any fixed guess hands different effective schedules to arms
    with different throughput: a fast arm (short context, cheap mixer) overruns
    the guess and trains most of its budget flat at ``min_lr``, while a slow
    arm never finishes the decay -- which is known to cost real validation
    loss. That would let the score partly measure schedule luck rather than
    architecture, the exact confound the locked recipe exists to remove.
    Time-based decay gives every architecture the identical schedule over the
    identical budget. Warmup stays step-based: its job is stabilizing early
    optimizer state, which is a per-step property, and at 100 steps it is a
    negligible slice of the budget.
    """
    if step < cfg.warmup_steps:
        return cfg.learning_rate * (step + 1) / max(1, cfg.warmup_steps)
    frac = min(1.0, max(0.0, elapsed / max(1e-9, cfg.train_seconds)))
    coeff = 0.5 * (1.0 + math.cos(math.pi * frac))
    return cfg.min_lr + coeff * (cfg.learning_rate - cfg.min_lr)


def _param_groups(model, cfg: TaskConfig):
    """No weight decay on 1-D params (norms, biases). 2-D params -- including
    the (tied) embedding table -- are decayed, nanoGPT-style."""
    decay, no_decay = [], []
    for _, p in model.named_parameters():
        if not p.requires_grad:
            continue
        (decay if p.dim() >= 2 else no_decay).append(p)
    return [
        {"params": decay, "weight_decay": cfg.weight_decay},
        {"params": no_decay, "weight_decay": 0.0},
    ]


def _cross_entropy(logits, targets):
    import torch.nn.functional as F

    B, T, V = logits.shape
    return F.cross_entropy(
        logits.reshape(B * T, V).float(), targets.reshape(B * T)
    )


def train_model(model, data: TokenData, cfg: TaskConfig, device: str) -> TrainOutput:
    import torch

    model.to(device)
    model.train()
    opt = torch.optim.AdamW(
        _param_groups(model, cfg),
        lr=cfg.learning_rate,
        betas=(cfg.beta1, cfg.beta2),
    )
    use_amp = device.startswith("cuda")
    autocast = (
        torch.autocast(device_type="cuda", dtype=torch.bfloat16)
        if use_amp
        else _nullcontext()
    )

    step = 0
    last_loss = float("nan")
    t0 = time.monotonic()
    while True:
        elapsed = time.monotonic() - t0
        if elapsed >= cfg.train_seconds:
            break
        # (max_train_seconds is enforced by the Modal function timeout, not
        # here: train_seconds always breaks first between steps, and no
        # between-step check can interrupt a hung step.)

        lr = _lr_at(step, elapsed, cfg)
        for pg in opt.param_groups:
            pg["lr"] = lr

        # Gradient accumulation: grad_accum micro-batches of cfg.batch_size make
        # one optimizer step (effective batch = batch_size * grad_accum) while
        # peak activation memory stays at a single micro-batch. cfg.block_size is
        # this arm's training context (run_arm passes a per-arm cfg); evaluation
        # is at cfg.eval_block_size regardless -- see data.val_windows.
        accum = max(1, int(cfg.grad_accum))
        opt.zero_grad(set_to_none=True)
        step_ce = 0.0
        for micro in range(accum):
            # Distinct deterministic micro-batch, identical across arms (CRN):
            # keyed by (step * accum + micro) so an optimizer step's micro-batches
            # never repeat and both arms see the same data. accum == 1 reproduces
            # the pre-accumulation key exactly.
            x, y = data.batch(step * accum + micro, device, cfg.block_size)
            with autocast:
                logits = _logits_only(model(x))
                loss = _cross_entropy(logits, y) / accum  # harness-owned loss
            loss.backward()
            step_ce += float(loss.detach().float().item())
        torch.nn.utils.clip_grad_norm_(model.parameters(), cfg.grad_clip)
        opt.step()

        last_loss = step_ce  # sum of per-micro (already /accum) losses = mean CE
        step += 1

    if device.startswith("cuda"):
        import torch as _t

        _t.cuda.synchronize()
    return TrainOutput(
        steps=step, wall_seconds=time.monotonic() - t0, final_train_loss=last_loss
    )


def _logits_only(out):
    """Accept either ``logits`` or ``(logits, loss)``; keep only logits."""
    if isinstance(out, (tuple, list)):
        return out[0]
    return out


class _nullcontext:
    def __enter__(self):
        return None

    def __exit__(self, *a):
        return False
