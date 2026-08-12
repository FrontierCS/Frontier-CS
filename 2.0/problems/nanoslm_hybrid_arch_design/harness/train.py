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
import os
import time
from dataclasses import asdict, dataclass

from .data import TokenData
from .settings import TaskConfig


@dataclass
class TrainOutput:
    steps: int
    wall_seconds: float
    final_train_loss: float


def _lr_at(step: int, elapsed: float, cfg: TaskConfig) -> float:
    """Linear step-warmup, then cosine decay over the FULL schedule horizon.

    The decay is a function of ``elapsed / lr_schedule_seconds``, not of a step
    count (wall-clock, so every architecture sees the identical schedule over
    identical time) and not of ``train_seconds`` (the stop time). The horizon
    is deliberately decoupled from the budget: with a short iteration budget
    (e.g. 15 min) the run traverses only the first slice of the full-schedule
    cosine -- i.e. it behaves like the prefix of a long training run, LR still
    near peak at cutoff -- rather than compressing the entire anneal into the
    short budget, which would over-weight the anneal and make short-budget
    rankings unrepresentative of longer training. When
    ``train_seconds == lr_schedule_seconds`` (the original 6 h config) the two
    forms are identical. Warmup stays step-based: its job is stabilizing early
    optimizer state, which is a per-step property.
    """
    if step < cfg.warmup_steps:
        return cfg.learning_rate * (step + 1) / max(1, cfg.warmup_steps)
    frac = min(1.0, max(0.0, elapsed / max(1e-9, cfg.lr_schedule_seconds)))
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


def _maybe_init_wandb(model, cfg: TaskConfig, run_label: str):
    """Opt-in observability sink; returns a wandb run or ``None``.

    Active only when the operator sets ``FRONTIER_NANOSLM_WANDB=1`` (plus a
    valid ``WANDB_API_KEY`` in the environment); no scored path sets it, so
    Harbor runs and the baseline cache are unaffected -- which is why this
    needs no CODE_VERSION bump. Everything is best-effort: any failure
    disables logging rather than touching the run. Init happens before the
    budget timer starts, and the in-loop cost is an async enqueue every
    ``_WANDB_LOG_EVERY`` steps (~1 min apart at production step times), so the
    wall-clock training budget is unaffected.
    """
    if os.environ.get("FRONTIER_NANOSLM_WANDB", "") != "1":
        return None
    try:
        import wandb

        name = "-".join(
            p for p in (
                os.environ.get("FRONTIER_NANOSLM_WANDB_NAME", ""),
                os.environ.get("FRONTIER_NANOSLM_ROLE", ""),
                run_label or type(model).__name__,
            ) if p
        )
        return wandb.init(
            project=os.environ.get(
                "FRONTIER_NANOSLM_WANDB_PROJECT", "nanoslm-hybrid-arch-design"
            ),
            group=os.environ.get("FRONTIER_NANOSLM_WANDB_GROUP") or None,
            name=name or None,
            config={
                **asdict(cfg),
                "run_label": run_label,
                "model_class": type(model).__name__,
            },
        )
    except Exception:
        return None


_WANDB_LOG_EVERY = 20


def train_model(model, data: TokenData, cfg: TaskConfig, device: str,
                run_label: str = "",
                eval_every: float = 0.0, eval_fn=None) -> TrainOutput:
    """``eval_every``/``eval_fn`` (operator experiments only; no scored path
    sets them): call ``eval_fn(model, step, train_elapsed)`` every
    ``eval_every`` seconds of TRAINING time. Time spent inside the hook is
    excluded from the wall-clock budget, so a curve run trains exactly as many
    seconds as a plain run; the hook must leave the model usable (train mode
    is restored here). A raising hook disables itself rather than killing the
    run."""
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

    wb = _maybe_init_wandb(model, cfg, run_label)
    step = 0
    last_loss = float("nan")
    next_eval = eval_every if (eval_every > 0 and eval_fn is not None) else float("inf")
    eval_debt = 0.0   # seconds spent in eval_fn, excluded from the budget
    t0 = time.monotonic()
    try:
        while True:
            elapsed = time.monotonic() - t0 - eval_debt
            if elapsed >= cfg.train_seconds:
                break
            if elapsed >= next_eval:
                _te = time.monotonic()
                try:
                    eval_fn(model, step, elapsed)
                    next_eval += eval_every
                except Exception:
                    next_eval = float("inf")  # sick hook: stop evaluating
                model.train()
                eval_debt += time.monotonic() - _te
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
            # clip_grad_norm_ returns the pre-clip total norm; kept as a GPU
            # tensor and only converted if the wandb branch logs it.
            grad_norm = torch.nn.utils.clip_grad_norm_(
                model.parameters(), cfg.grad_clip)
            opt.step()

            last_loss = step_ce  # sum of per-micro (already /accum) losses = mean CE
            step += 1

            if wb is not None and (step <= 5 or step % _WANDB_LOG_EVERY == 0):
                try:
                    wb.log(
                        {
                            "train/loss": last_loss,
                            "train/lr": lr,
                            "train/grad_norm": float(grad_norm),
                            "train/elapsed_s": elapsed,
                            "train/tokens": step * accum * cfg.batch_size
                            * cfg.block_size,
                        },
                        step=step,
                    )
                except Exception:
                    wb = None  # a sick sink must never touch the run
    finally:
        if wb is not None:
            try:
                wb.finish()
            except Exception:
                pass

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
