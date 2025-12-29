import torch
import triton
import triton.language as tl
import torch.nn.functional as F


@triton.autotune(
    configs=[
        triton.Config({'BLOCK_SIZE': 64}, num_warps=2),
        triton.Config({'BLOCK_SIZE': 128}, num_warps=2),
        triton.Config({'BLOCK_SIZE': 256}, num_warps=4),
        triton.Config({'BLOCK_SIZE': 512}, num_warps=4),
        triton.Config({'BLOCK_SIZE': 1024}, num_warps=8),
    ],
    key=['N'],
)
@triton.jit
def _cross_entropy_kernel(
    logits_ptr,       # *f32
    targets_ptr,      # *i64 or *i32
    losses_ptr,       # *f32
    M,                # int32
    N,                # int32
    stride_m,         # int32
    stride_n,         # int32
    stride_targets,   # int32
    BLOCK_SIZE: tl.constexpr,
):
    row_id = tl.program_id(axis=0)
    # Each program handles one row, assume grid = (M,)
    # Compute pointer to the beginning of this row in logits
    row_logits_ptr = logits_ptr + row_id * stride_m

    # Load target index for this row
    t = tl.load(targets_ptr + row_id * stride_targets)
    t = t.to(tl.int32)

    neg_inf = -float("inf")
    m = tl.full((), neg_inf, tl.float32)
    s = tl.zeros((), tl.float32)

    offs = tl.arange(0, BLOCK_SIZE)
    col_start = tl.zeros((), tl.int32)

    # Streaming log-sum-exp over the row
    while col_start < N:
        cols = col_start + offs
        mask = cols < N
        x = tl.load(
            row_logits_ptr + cols * stride_n,
            mask=mask,
            other=neg_inf,
        )
        block_max = tl.max(x, axis=0)
        new_m = tl.maximum(m, block_max)
        exp_scale = tl.exp(m - new_m)
        s = s * exp_scale + tl.sum(tl.exp(x - new_m), axis=0)
        m = new_m
        col_start += BLOCK_SIZE

    lse = m + tl.log(s)

    # Load the logit corresponding to the target index
    target_logit = tl.load(row_logits_ptr + t * stride_n)

    loss = lse - target_logit
    tl.store(losses_ptr + row_id, loss)


def cross_entropy(logits: torch.Tensor, targets: torch.Tensor) -> torch.Tensor:
    """
    Cross entropy loss computation using Triton.

    Args:
        logits: (M, N) float tensor on CUDA
        targets: (M,) long tensor of class indices on same device

    Returns:
        (M,) float32 tensor of per-sample losses
    """
    if logits.dim() != 2:
        raise ValueError(f"logits must be 2D (M, N), got shape {tuple(logits.shape)}")
    if targets.dim() != 1:
        raise ValueError(f"targets must be 1D (M,), got shape {tuple(targets.shape)}")
    if logits.size(0) != targets.size(0):
        raise ValueError("First dimension of logits and targets must match")

    M, N = logits.shape

    # CPU or non-CUDA fallback: use PyTorch implementation
    if logits.device.type != "cuda":
        log_probs = F.log_softmax(logits, dim=-1)
        idx = torch.arange(M, device=logits.device)
        loss = -log_probs[idx, targets]
        return loss.to(torch.float32)

    if targets.device != logits.device:
        raise ValueError("logits and targets must be on the same device")

    # Use float32 for computation for numerical stability
    if logits.dtype != torch.float32:
        logits_f = logits.float()
    else:
        logits_f = logits

    stride_m, stride_n = logits_f.stride()
    stride_targets = targets.stride(0)

    losses = torch.empty(M, device=logits.device, dtype=torch.float32)

    _cross_entropy_kernel[(M,)](
        logits_f,
        targets,
        losses,
        M,
        N,
        stride_m,
        stride_n,
        stride_targets,
    )

    return losses


class Solution:
    def solve(self, spec_path: str = None) -> dict:
        import inspect
        import sys

        module = sys.modules[__name__]
        src = inspect.getsource(module)
        return {"code": src}