"""Orchestration (torch path): train + eval one arm, and CRN-pair two arms.

Isolation model mirrors ``nanowm``: the judge/Modal boundary separates this code
from the agent workspace ``/app``; the submitted ``model.py`` is imported here
only after the static policy gate (evaluator) passes. All dynamic guards that the
static scan cannot see live in this module.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import Callable

from . import baseline_model
from .data import DataError, TokenData
from .eval_ppl import EvalOutput, evaluate_perplexity, set_determinism
from .model_config import ModelConfig
from .settings import TaskConfig
from .train import TrainOutput, train_model


class GuardError(Exception):
    """Raised when a submission trips a dynamic guard -> score 0, public reason."""


@dataclass
class ArmMetrics:
    val_bpb: float          # Scored quantity
    val_ppl: float          # derived, readability only
    steps: int
    wall_seconds: float
    n_params: int
    train_block_size: int = 0       # context this arm actually trained at
    warmup_seconds: float = 0.0     # time absorbed outside the timed window
    warmup_error: str = ""          # "" when warmup completed cleanly
    eval: EvalOutput = field(repr=False, default=None)


def load_factory(module) -> Callable:
    fn = getattr(module, "build_model", None)
    if callable(fn):
        return fn
    cls = getattr(module, "NanoSLM", None)
    if cls is not None:
        return lambda config: cls(config)
    raise GuardError("model.py must define build_model(config) or class NanoSLM")


# --------------------------------------------------------------------------- #
# Agent-controlled training context.
#
# A submission declares it with a module-level ``BLOCK_SIZE`` int in model.py.
# That is deliberately the whole protocol: no new required entrypoint, and the
# existing build_model(config) / class NanoSLM contract is untouched, so a
# submission that says nothing keeps training at the judge's 8192 default.
#
# The evaluation context is never negotiable -- see settings.eval_block_size.
# --------------------------------------------------------------------------- #
MIN_TRAIN_BLOCK = 256


def _is_power_of_two(n: int) -> bool:
    return n > 0 and (n & (n - 1)) == 0


def resolve_train_block_size(module, cfg: TaskConfig) -> int:
    """Training context for `module`: its ``BLOCK_SIZE``, else the cfg default.

    Enforced as a GuardError (public message), exactly like the param cap:

      * power of two -- kernels, chunkwise mixers and mask caches all assume it,
        and it keeps the space small enough to reason about;
      * >= 256 -- below that the context degenerates and a "language model"
        stops modelling anything the 8192-wide evaluation rewards;
      * <= eval_block_size (8192) -- training longer than the scoring window
        buys nothing measurable and only costs memory and steps.
    """
    raw = getattr(module, "BLOCK_SIZE", None)
    if raw is None:
        return int(cfg.block_size)
    if isinstance(raw, bool) or not isinstance(raw, int):
        raise GuardError(
            f"model.py BLOCK_SIZE must be an int, got {type(raw).__name__}"
        )
    hi = int(cfg.eval_block_size)
    if not (MIN_TRAIN_BLOCK <= raw <= hi) or not _is_power_of_two(raw):
        raise GuardError(
            f"model.py BLOCK_SIZE={raw} is out of range: the training context "
            f"must be a power of two in [{MIN_TRAIN_BLOCK}, {hi}] "
            f"(evaluation is always at {hi})"
        )
    return int(raw)


def _model_config(cfg: TaskConfig, device: str) -> ModelConfig:
    return ModelConfig(
        vocab_size=cfg.vocab_size,
        block_size=cfg.block_size,          # per-arm training context
        eval_block_size=cfg.eval_block_size,  # fixed scoring context
        train_seconds_hint=cfg.train_seconds,
        param_cap_hint=cfg.param_cap,
        device_hint="cuda" if device.startswith("cuda") else device,
    )


def _count_params(model) -> int:
    return sum(p.numel() for p in model.parameters() if p.requires_grad)


def _param_snapshot(model):
    import torch

    with torch.no_grad():
        return torch.cat([p.detach().reshape(-1).float().cpu() for p in model.parameters()])


def _warmup(model, data: TokenData, cfg: TaskConfig, device: str):
    """Compile/autotune kernels before the wall-clock timer starts.

    This is required for a fair fixed-wall-clock comparison, not an
    optimization. Triton JIT-compiles per shape on first use, so fla's
    GatedDeltaNet pays a large first-forward cost while torch's SDPA path pays
    essentially none.

    Left inside the timed window, an fla-based hybrid would spend a chunk of its
    budget T compiling while a pure-attention arm spent none -- so the score
    would partly measure compilation rather than throughput, and the smaller T
    is the worse the distortion.

    Three things this must match about ``train_model``, or it warms kernels the
    training loop never calls and the JIT cost lands inside the timer anyway:

      1. Device. The factories (``baseline_model.build_model``, the submission's)
         construct on CPU; only ``train_model`` calls ``model.to(device)``. So
         warmup moves the model to ``device`` here and reports errors rather than
         swallowing them: an earlier version ran before the move and silently
         no-op'd on a device mismatch, letting fla's entire Triton compile land
         in step 0.
      2. Dtype. ``train_model`` runs under ``torch.autocast(bfloat16)``. Triton
         autotunes per dtype, so an fp32 warmup warms the wrong kernels.
      3. The optimizer step. ``clip_grad_norm_`` and AdamW's foreach/fused
         kernels are first-call-compiled too, so warmup takes a real step and
         then restores the parameters, leaving training bit-identical to a run
         that never warmed up.

    Two iterations, not one: Triton autotuning picks a config on the first call
    and can still recompile on the second. The second is ~ms once warm.

    Fourth thing, added with the agent-controlled training context: the
    training and evaluation shapes can now differ. Warming only the
    training shape leaves every eval-shape kernel cold for a submission that
    trained at, say, 2048 -- and Triton autotunes per shape, so that is a fresh
    compile of tens of seconds. It does not currently land inside the scored
    window (``train_model`` stops its timer before ``evaluate_perplexity`` is
    called), so this is not a scoring bug today; it is warmed here anyway
    because (a) it is a real cost against the container/`max_train_seconds`
    budget, (b) it makes the property robust to any future reordering rather
    than accidental, and (c) it surfaces an eval-shape failure (a model whose
    buffers were sized at the training context and cannot run at 8192) here,
    BEFORE the training budget is spent. The eval warm mirrors
    ``eval_ppl.evaluate_perplexity`` exactly: ``model.eval()``, ``no_grad``,
    and no autocast -- evaluation runs in fp32, so warming it under bfloat16
    would warm the wrong kernels again.

    Error handling is split by shape, deliberately:

      * Training-shape errors are captured and returned in
        ``ArmMetrics.warmup_error``, never raised -- a genuinely broken model
        must fail in the real training loop where the guards can classify it
        (OOM vs shape error vs ...), and a warmup hiccup must not reject a
        model the real loop could have trained.
      * Eval-shape errors -- reached only when the training shape already ran
        cleanly, so the model itself works -- are definitive: a model that
        cannot run at ``eval_block_size`` can only ever score 0, and letting it
        train first burns the full ``train_seconds`` of H100 to find that out.
        These raise ``GuardError`` here, with the same classification the
        post-training guard in ``run_arm`` would have produced.
    """
    import time

    import torch

    t0 = time.monotonic()
    err = ""
    try:
        model.to(device)
        model.train()
        autocast = (
            torch.autocast(device_type="cuda", dtype=torch.bfloat16)
            if device.startswith("cuda")
            else _nullctx()
        )
        # Snapshot so the warmup optimizer step leaves no trace on training.
        saved = [p.detach().clone() for p in model.parameters()]
        opt = torch.optim.AdamW(model.parameters(), lr=0.0)

        for i in range(2):
            # cfg.block_size here is the arm's training context (run_arm passes
            # a per-arm cfg), so this warms the shape train_model will use.
            x, y = data.batch(i, device, cfg.block_size)   # same API train.py uses
            with autocast:
                out = model(x)
                logits = out[0] if isinstance(out, tuple) else out
                loss = torch.nn.functional.cross_entropy(
                    logits.reshape(-1, logits.size(-1)).float(), y.reshape(-1)
                )
            opt.zero_grad(set_to_none=True)
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), cfg.grad_clip)
            opt.step()

        with torch.no_grad():
            for p, s in zip(model.parameters(), saved):
                p.copy_(s)
        model.zero_grad(set_to_none=True)
        del saved, opt
    except Exception as exc:
        # Training-shape failure: record and let the real training loop
        # classify it (see the docstring). The eval-shape warm is skipped --
        # with the training shape already broken, its failure would say nothing
        # about the eval context specifically.
        err = f"{type(exc).__name__}: {exc}"[:300]
        return round(time.monotonic() - t0, 2), err

    # Eval-shape warm: [1, eval_block_size] in eval mode, no_grad, fp32 --
    # exactly how evaluate_perplexity will call the model. Uses the first
    # real held-out window so the shape and dtype match to the element; it
    # runs under no_grad and takes no optimizer step, so it cannot influence
    # any parameter or leak the held-out stream into training.
    #
    # Failure here is a fast-fail (see the docstring): the training shape ran
    # cleanly two iterations ago, so an exception now means the model cannot
    # run at the fixed scoring context -- it can only ever score 0, and the
    # only question is whether it finds that out now or after train_seconds of
    # GPU time. Classified exactly like the post-training eval guard in
    # run_arm, so the public message is identical either way.
    try:
        model.eval()
        with torch.no_grad():
            first = next(iter(data.val_windows(device)), None)
            if first is not None:
                for _ in range(2):
                    out = model(first[0])
                    _ = out[0] if isinstance(out, tuple) else out
                del out
            del first
        model.train()

        if device.startswith("cuda"):
            torch.cuda.synchronize()
            torch.cuda.empty_cache()
    except (GuardError, DataError):
        raise
    except Exception as exc:
        msg = str(exc).lower()
        if "out of memory" in msg:
            raise GuardError(
                f"evaluation ran out of GPU memory at context "
                f"{cfg.eval_block_size}"
            )
        raise GuardError(
            f"evaluation failed at context {cfg.eval_block_size} "
            f"(trained at {cfg.block_size}): {type(exc).__name__}. Buffers sized "
            f"off config.block_size must still work at config.eval_block_size"
        )

    return round(time.monotonic() - t0, 2), err


class _nullctx:
    def __enter__(self):
        return None

    def __exit__(self, *a):
        return False


def run_arm(factory: Callable, data: TokenData, cfg: TaskConfig, device: str,
            train_block_size: int | None = None) -> ArmMetrics:
    """Instantiate -> guard params -> train -> eval -> guard training/degeneracy.

    ``train_block_size`` is this arm's training context (default: cfg's). It is
    threaded through as a per-arm ``cfg`` so that every consumer -- the model
    config handed to the factory, ``_warmup``, and ``train_model`` -- sees one
    consistent value. ``cfg.eval_block_size`` is untouched by it, so evaluation
    stays at 8192 for every arm.
    """
    import torch

    if train_block_size is not None and int(train_block_size) != int(cfg.block_size):
        cfg = replace(cfg, block_size=int(train_block_size))

    set_determinism(cfg)
    try:
        model = factory(_model_config(cfg, device))
    except GuardError:
        raise
    except Exception as exc:
        raise GuardError(f"model construction failed: {type(exc).__name__}")

    if not isinstance(model, torch.nn.Module):
        raise GuardError("factory did not return a torch.nn.Module")

    n_params = _count_params(model)
    if n_params <= 0:
        raise GuardError("model has no trainable parameters")
    if n_params > cfg.param_cap:
        raise GuardError(f"model exceeds param cap ({n_params} > {cfg.param_cap})")

    # Compile both arms, uniformly, in the harness.
    #
    # Two reasons, and the second is a correctness issue:
    #
    # 1. Throughput. The chunkwise linear mixer is unfused eager PyTorch and is
    #    dominated by kernel-launch overhead, so it loses to SDPA's single fused
    #    flash-attention kernel despite doing a fraction of the FLOPs.
    #    Compilation fuses the elementwise work and is what makes a linear mixer
    #    competitive at all here.
    #
    # 2. Fairness. `torch.compile()` is explicitly allowed in submissions
    #    (policy.py). If the harness did not compile, a submission could take
    #    the baseline architecture unchanged, wrap it in torch.compile, gain
    #    wall-clock and score well with zero architectural insight -- the same
    #    kernel-mismatch confound that fla created, by another route. Compiling
    #    both arms here removes compilation as a lever and puts the comparison
    #    back on architecture.
    #
    # Failures fall back to eager: a submitted architecture may contain
    # something inductor cannot trace, and that should cost throughput, not be
    # a hard rejection.
    # Default off. The fairness argument above is real and unresolved, but
    # compilation measured worse than eager on the chunkwise mixer (inductor
    # almost certainly graph-breaks on the chunk loop's data-dependent state),
    # and its interaction with fla's Triton kernels is unvalidated. Re-enable
    # only after measuring both arms with it.
    if getattr(cfg, "compile_model", False):
        try:
            model = torch.compile(model)
        except Exception:
            pass

    # Warm kernels outside the timed window -- see _warmup. This now also
    # absorbs inductor's compilation, which is the whole reason it must precede
    # the timer.
    warmup_seconds, warmup_error = _warmup(model, data, cfg, device)

    before = _param_snapshot(model)
    try:
        tout: TrainOutput = train_model(model, data, cfg, device)
    except (GuardError, DataError):
        raise
    except Exception as exc:
        # `Exception`, not `RuntimeError`: a malformed architecture can raise
        # anything mid-training -- torch raised ValueError for a kernel dtype
        # mismatch, IndexError for an overrun table -- and an uncaught type
        # here escapes classification entirely, surfacing as a misleading
        # environment_error at the judge instead of a submission fault.
        msg = str(exc).lower()
        if "out of memory" in msg:
            raise GuardError("training ran out of GPU memory")
        raise GuardError(f"training runtime error: {type(exc).__name__}")

    if tout.steps <= 0:
        raise GuardError("model completed zero optimizer steps in the budget")

    after = _param_snapshot(model)
    if before.numel() == after.numel():
        mean_abs_delta = float((after - before).abs().mean().item())
        if mean_abs_delta < cfg.min_param_delta:
            raise GuardError("parameters did not change during training (not trained)")

    # A new failure mode, since the training and evaluation contexts can differ:
    # a model whose buffers were sized off the training context
    # trains happily and then blows up at eval, where T is always
    # eval_block_size. Left unclassified that surfaced as a bare
    # "submission_error: RuntimeError" with no hint about the cause, so it is
    # turned into a GuardError naming both contexts.
    # `Exception`, not `RuntimeError`: the commonest form of this bug is a
    # positional embedding table indexed past its end, which torch raises as an
    # IndexError, not a RuntimeError. Catching only RuntimeError let exactly the
    # failure this guard exists for escape unclassified. DataError is re-raised
    # untouched -- a missing held-out byte count is a judge-side asset problem
    # and must not be reported as a submission fault.
    try:
        eout = evaluate_perplexity(model, data, cfg, device)
    except (GuardError, DataError):
        raise
    except Exception as exc:
        msg = str(exc).lower()
        if "out of memory" in msg:
            raise GuardError(
                f"evaluation ran out of GPU memory at context "
                f"{cfg.eval_block_size}"
            )
        raise GuardError(
            f"evaluation failed at context {cfg.eval_block_size} "
            f"(trained at {cfg.block_size}): {type(exc).__name__}. Buffers sized "
            f"off config.block_size must still work at config.eval_block_size"
        )
    # Guard on bpb, the scored quantity. bpb cannot overflow the way exp(ce)
    # can, so this catches a diverged model as a large-but-finite bpb rather
    # than relying on an inf that only appears past mean_ce ~709.
    if not (eout.val_bpb > 0.0) or eout.val_bpb == float("inf"):
        raise GuardError("evaluation produced a non-finite bits-per-byte")
    if eout.mean_abs_logit_std < 1e-4:
        raise GuardError("model produced near-constant logits (degenerate)")
    # Plausibility floor (see settings.min_plausible_bpb): the static policy
    # gate is defense in depth, not proof, and a submission that evaded it and
    # memorized the held-out stream would land near zero. No honest model at
    # this scale and budget can approach the floor, so below it the measurement
    # is treated as leakage, not brilliance. Applied to both arms uniformly;
    # the baseline sits several times above it.
    floor = float(getattr(cfg, "min_plausible_bpb", 0.0))
    if floor > 0.0 and eout.val_bpb < floor:
        raise GuardError(
            f"bits-per-byte {eout.val_bpb:.4f} is below the plausibility "
            f"floor ({floor}); flagged as presumed held-out leakage"
        )

    return ArmMetrics(
        val_bpb=eout.val_bpb,
        val_ppl=eout.val_ppl,
        steps=tout.steps,
        wall_seconds=tout.wall_seconds,
        n_params=n_params,
        train_block_size=int(cfg.block_size),
        warmup_seconds=warmup_seconds,
        warmup_error=warmup_error,
        eval=eout,
    )


def baseline_factory() -> Callable:
    return baseline_model.build_model


def baseline_block_size(cfg: TaskConfig) -> int:
    """Training context of the locked arm.

    Read through the same ``BLOCK_SIZE`` protocol a submission uses, from
    ``baseline_model``, which declares 8192 explicitly rather than inheriting a
    default. The locked arm's context must be unambiguous and must not move if
    ``TaskConfig.block_size`` (now only the submission-facing default) is ever
    retuned -- and it is what makes the fingerprint-keyed baseline cache valid
    across submissions with different training contexts.
    """
    return resolve_train_block_size(baseline_model, cfg)


def run_pair(submission_module, cfg: TaskConfig, device: str):
    """Scored path: train baseline + submission back-to-back on one GPU (CRN)."""
    # Resolve (and range-guard) the submission's training context before
    # spending a baseline run on it: an out-of-range BLOCK_SIZE should cost the
    # judge nothing.
    sub_block = resolve_train_block_size(submission_module, cfg)
    data = TokenData(cfg)
    base = run_arm(baseline_factory(), data, cfg, device, baseline_block_size(cfg))
    sub = run_arm(load_factory(submission_module), data, cfg, device, sub_block)
    return base, sub
