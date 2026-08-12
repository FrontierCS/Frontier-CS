"""Held-out bits-per-byte evaluation (torch path).

The harness computes cross-entropy from the model's ``logits`` on the held-out
token stream and returns

    val_bpb = total_nll_nats / (total_val_BYTES * ln 2)

Any loss returned by the model is ignored.

Why bpb is the primary metric (not perplexity):
  * It is tokenizer-independent, which is what makes it comparable across
    architectures and ungameable.
  * It needs no ``exp``. ``val_ppl = exp(mean_ce)`` overflows to ``inf`` for a
    sufficiently bad submission (mean_ce > ~709), turning a merely-poor model
    into a non-finite number the guards then have to special-case. bpb is linear
    in the loss and cannot overflow.
"""

from __future__ import annotations

from dataclasses import dataclass

from .data import DataError, TokenData
from .settings import TaskConfig
from .train import _logits_only


@dataclass
class EvalOutput:
    val_bpb: float          # Scored quantity: total_nll_nats / (bytes * ln 2)
    val_ppl: float          # derived, per-token, readability only
    val_ce_nats: float      # mean per-token CE
    n_tokens: int
    mean_abs_logit_std: float  # degeneracy signal (near-constant logits -> ~0)
    n_bytes: float = 0.0    # denominator actually used for val_bpb


def set_determinism(cfg: TaskConfig) -> None:
    import torch

    try:
        torch.use_deterministic_algorithms(True, warn_only=True)
    except Exception:
        pass
    if torch.cuda.is_available():
        torch.backends.cudnn.deterministic = True
        torch.backends.cudnn.benchmark = False
        torch.backends.cuda.matmul.allow_tf32 = False
        torch.backends.cudnn.allow_tf32 = False
    torch.manual_seed(cfg.seed)


def evaluate_perplexity(model, data: TokenData, cfg: TaskConfig, device: str) -> EvalOutput:
    import math

    import torch
    import torch.nn.functional as F

    model.eval()
    total_ce = 0.0
    total_tok = 0
    logit_std_accum = 0.0
    n_batches = 0

    with torch.no_grad():
        for x, y in data.val_windows(device):
            logits = _logits_only(model(x)).float()
            B, T, V = logits.shape
            ce = F.cross_entropy(
                logits.reshape(B * T, V), y.reshape(B * T), reduction="sum"
            )
            total_ce += float(ce.item())
            total_tok += B * T
            # degeneracy probe: spread of the logits across vocab
            logit_std_accum += float(logits.std(dim=-1).mean().item())
            n_batches += 1

    if total_tok == 0:
        return EvalOutput(float("inf"), float("inf"), float("inf"), 0, 0.0, 0.0)

    # Bytes, not tokens. `total_ce` is the sum of
    # NLL in nats over every scored target token, so this is exactly
    # total_nll / (bytes * ln 2).
    total_bytes = data.val_bytes_for(total_tok)
    if not (total_bytes > 0.0):
        raise DataError(
            "held-out byte count is zero/unavailable; refusing to normalize "
            "bits-per-byte by a token count (see harness/eval_ppl.py)"
        )
    val_bpb = total_ce / (total_bytes * math.log(2.0))

    mean_ce = total_ce / total_tok
    # Derived for readability only, and per token. Guarded: exp overflows above
    # mean_ce ~709, and a diverged submission can get there.
    try:
        val_ppl = math.exp(mean_ce)
    except OverflowError:
        val_ppl = float("inf")
    mean_logit_std = logit_std_accum / max(1, n_batches)
    return EvalOutput(val_bpb, val_ppl, mean_ce, total_tok, mean_logit_std,
                      float(total_bytes))
