import os
import torch
import torch.nn.functional as F
import triton
import triton.language as tl


@triton.autotune(
    configs=[
        triton.Config({'BLOCK_SIZE': 128}, num_warps=4),
        triton.Config({'BLOCK_SIZE': 256}, num_warps=4),
        triton.Config({'BLOCK_SIZE': 512}, num_warps=8),
        triton.Config({'BLOCK_SIZE': 1024}, num_warps=8),
    ],
    key=['N'],
)
@triton.jit
def _cross_entropy_kernel(
    logits_ptr, targets_ptr, loss_ptr,
    M, N,
    stride_logits_m, stride_logits_n,
    stride_targets,
    stride_loss,
    BLOCK_SIZE: tl.constexpr,
):
    row = tl.program_id(0)
    if row >= M:
        return

    row_logits_ptr = logits_ptr + row * stride_logits_m

    # Load target index for this row
    target = tl.load(targets_ptr + row * stride_targets)
    target = target.to(tl.int32)

    cols = tl.arange(0, BLOCK_SIZE)

    # Pass 1: compute row-wise max for numerical stability
    row_max = -float("inf")
    for col_start in range(0, N, BLOCK_SIZE):
        col_idx = col_start + cols
        mask = col_idx < N
        logits = tl.load(
            row_logits_ptr + col_idx * stride_logits_n,
            mask=mask,
            other=-float("inf"),
        )
        block_max = tl.max(logits, axis=0)
        row_max = tl.maximum(row_max, block_max)

    # Pass 2: compute sum(exp(logits - row_max))
    sum_exp = 0.0
    for col_start in range(0, N, BLOCK_SIZE):
        col_idx = col_start + cols
        mask = col_idx < N
        logits = tl.load(
            row_logits_ptr + col_idx * stride_logits_n,
            mask=mask,
            other=-float("inf"),
        )
        logits = logits - row_max
        sum_exp += tl.sum(tl.exp(logits), axis=0)

    logsumexp = row_max + tl.log(sum_exp)

    # Load logit corresponding to target class
    target_logit = tl.load(row_logits_ptr + target * stride_logits_n)

    loss = logsumexp - target_logit
    tl.store(loss_ptr + row * stride_loss, loss)


def cross_entropy(logits: torch.Tensor, targets: torch.Tensor) -> torch.Tensor:
    """
    Cross entropy loss computation.

    Args:
        logits: Tensor of shape (M, N)
        targets: Tensor of shape (M,) with dtype int64

    Returns:
        loss: Tensor of shape (M,) with dtype float32
    """
    if not logits.is_cuda or not targets.is_cuda:
        return F.cross_entropy(logits, targets, reduction='none')

    assert logits.ndim == 2, "logits must be 2D (M, N)"
    M, N = logits.shape
    assert targets.ndim == 1 and targets.shape[0] == M, "targets must be 1D (M,)"

    if logits.dtype != torch.float32:
        logits = logits.float()
    if targets.dtype != torch.int64:
        targets = targets.long()

    if M == 0:
        return torch.empty((0,), dtype=torch.float32, device=logits.device)

    loss = torch.empty((M,), dtype=torch.float32, device=logits.device)

    grid = lambda META: (M,)

    _cross_entropy_kernel[grid](
        logits,
        targets,
        loss,
        M,
        N,
        logits.stride(0),
        logits.stride(1),
        targets.stride(0),
        loss.stride(0),
    )

    return loss


class Solution:
    def solve(self, spec_path: str = None) -> dict:
        return {"program_path": os.path.abspath(__file__)}
