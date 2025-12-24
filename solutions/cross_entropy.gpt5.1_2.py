import os
import torch
import torch.nn.functional as F
import triton
import triton.language as tl


@triton.autotune(
    configs=[
        triton.Config({'BLOCK_SIZE': 128}, num_warps=4, num_stages=3),
        triton.Config({'BLOCK_SIZE': 256}, num_warps=4, num_stages=3),
        triton.Config({'BLOCK_SIZE': 512}, num_warps=8, num_stages=3),
        triton.Config({'BLOCK_SIZE': 1024}, num_warps=8, num_stages=4),
    ],
    key=['N'],
)
@triton.jit
def _cross_entropy_kernel(
    logits_ptr,  # *f32 / *f16 / *bf16
    targets_ptr,  # *i64
    losses_ptr,  # *f32
    stride_lm, stride_ln,
    stride_tm,
    M,
    N: tl.constexpr,
    BLOCK_SIZE: tl.constexpr,
):
    row_id = tl.program_id(0)
    if row_id >= M:
        return

    offs = tl.arange(0, BLOCK_SIZE)
    row_start = row_id * stride_lm

    # 1. Compute row-wise max for numerical stability
    max_val = -float('inf')
    for start_n in tl.static_range(0, N, BLOCK_SIZE):
        cols = start_n + offs
        mask = cols < N
        logits = tl.load(
            logits_ptr + row_start + cols * stride_ln,
            mask=mask,
            other=-float('inf'),
        )
        logits = logits.to(tl.float32)
        curr_max = tl.max(logits, axis=0)
        max_val = tl.maximum(max_val, curr_max)

    # 2. Compute log-sum-exp using the max
    sum_exp = 0.0
    for start_n in tl.static_range(0, N, BLOCK_SIZE):
        cols = start_n + offs
        mask = cols < N
        logits = tl.load(
            logits_ptr + row_start + cols * stride_ln,
            mask=mask,
            other=-float('inf'),
        )
        logits = logits.to(tl.float32)
        logits = logits - max_val
        exp_logits = tl.exp(logits)
        sum_exp += tl.sum(exp_logits, axis=0)

    log_denom = tl.log(sum_exp) + max_val

    # 3. Gather logit corresponding to the target class
    target_idx = tl.load(targets_ptr + row_id * stride_tm)
    target_idx = target_idx.to(tl.int64)
    target_logit = tl.load(logits_ptr + row_start + target_idx * stride_ln)
    target_logit = target_logit.to(tl.float32)

    loss = log_denom - target_logit
    tl.store(losses_ptr + row_id, loss)


def cross_entropy(logits: torch.Tensor, targets: torch.Tensor) -> torch.Tensor:
    """
    Cross entropy loss computation using a Triton kernel.

    Args:
        logits: Tensor of shape (M, N) on CUDA device
        targets: Tensor of shape (M,) with int64 class indices

    Returns:
        Tensor of shape (M,) with float32 losses.
    """
    if not isinstance(logits, torch.Tensor) or not isinstance(targets, torch.Tensor):
        raise TypeError("logits and targets must be torch.Tensors")

    if logits.ndim != 2:
        raise ValueError("logits must be 2D (M, N)")
    if targets.ndim != 1:
        raise ValueError("targets must be 1D (M,)")

    M, N = logits.shape
    if targets.shape[0] != M:
        raise ValueError("targets length must match logits batch dimension")

    # Fallback to PyTorch implementation on CPU
    if not logits.is_cuda or not targets.is_cuda:
        return F.cross_entropy(logits, targets.long(), reduction='none').to(torch.float32)

    if targets.dtype != torch.long:
        targets = targets.long()

    # Ensure reasonably good memory layout
    if not logits.is_contiguous():
        logits = logits.contiguous()
    if not targets.is_contiguous():
        targets = targets.contiguous()

    # Allocate output
    losses = torch.empty((M,), device=logits.device, dtype=torch.float32)

    stride_lm, stride_ln = logits.stride()
    stride_tm = targets.stride(0)

    grid = (M,)

    _cross_entropy_kernel[grid](
        logits,
        targets,
        losses,
        stride_lm,
        stride_ln,
        stride_tm,
        M,
        N,
    )

    return losses


class Solution:
    def solve(self, spec_path: str = None) -> dict:
        return {"program_path": os.path.abspath(__file__)}
