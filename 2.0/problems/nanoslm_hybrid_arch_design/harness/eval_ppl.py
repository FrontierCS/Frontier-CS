"""Held-out bits-per-byte evaluation (torch path).

The harness computes cross-entropy from the model's ``logits`` on the HELD-OUT
token stream and returns

    val_bpb = total_nll_nats / (total_val_BYTES * ln 2)

Any loss returned by the model is ignored.

WHY bpb IS THE PRIMARY METRIC (not perplexity):
  * It is tokenizer-independent, which is what makes it comparable across
    architectures and ungameable -- see DESIGN.md §2.
  * It needs no ``exp``. ``val_ppl = exp(mean_ce)`` overflows to ``inf`` for a
    sufficiently bad submission (mean_ce > ~709), turning a merely-poor model
    into a non-finite number the guards then have to special-case. bpb is linear
    in the loss and cannot overflow.

WHY THE DENOMINATOR IS BYTES AND NOT TOKENS -- READ BEFORE EDITING
------------------------------------------------------------------
While the tokenizer was byte-level, 1 token == 1 byte and dividing the summed
NLL by the TOKEN count was accidentally identical to dividing by the byte count.
Under dolma2 BPE the two differ by the compression ratio (~4.4x), and per-token
CE/ln2 is a tokenizer-dependent number: a tokenizer that packs more text per
token raises it for the same model quality. Normalizing that way would destroy
exactly the property bpb was adopted for. So the denominator comes from
``data.val_bytes_for(...)``, which is backed by a byte count measured at
corpus-prep time and asserted present (``data.DataError`` otherwise) rather than
defaulted.

``val_ppl`` is still derived and reported, for human readability only -- it is
no longer the scored quantity, and it remains a PER-TOKEN perplexity (so
``val_ppl != 2**val_bpb`` any more; that identity held only at byte level). It
is computed defensively so a diverged model reports ``inf`` rather than raising.
Determinism knobs (no TF32, deterministic algorithms) are set on the GPU path so
a cached/separate baseline is a valid common-random-numbers partner.
"""

from __future__ import annotations

from dataclasses import dataclass

from .data import DataError, TokenData
from .settings import TaskConfig
from .train import _logits_only


@dataclass
class EvalOutput:
    val_bpb: float          # SCORED quantity: total_nll_nats / (bytes * ln 2)
    val_ppl: float          # derived, per-TOKEN, readability only
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

    # BYTES, not tokens -- see the module docstring. `total_ce` is the SUM of
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
    # Derived for readability only, and PER TOKEN. Guarded: exp overflows above
    # mean_ce ~709, and a diverged submission can get there.
    try:
        val_ppl = math.exp(mean_ce)
    except OverflowError:
        val_ppl = float("inf")
    mean_logit_std = logit_std_accum / max(1, n_batches)
    return EvalOutput(val_bpb, val_ppl, mean_ce, total_tok, mean_logit_std,
                      float(total_bytes))
