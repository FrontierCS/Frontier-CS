import torch
import triton
import triton.language as tl
import math
from typing import Dict

class Solution:
    def solve(self, spec_path: str = None) -> Dict[str, str]:
        code = """
import torch
import triton
import triton.language as tl

@triton.autotune(
    configs=[
        triton.Config({'BLOCK_N': 1024}, num_stages=4),
        triton.Config({'BLOCK_N': 512}, num_stages=2),
        triton.Config({'BLOCK_N': 256}, num_stages=1),
    ],
    key=['N'],
)
@triton.jit
def cross_entropy_kernel(
    losses_ptr, logits_ptr, targets_ptr,
    M, N,
    stride_logits_m, stride_logits_n,
    stride_targets,
    BLOCK_N: tl.constexpr
):
    row = tl.program_id(0)
    if row >= M:
        return

    target_ptr = targets_ptr + row * stride_targets
    target = tl.load(target_ptr)

    # First pass: compute max_logit
    max_logit = -1e20
    for start in range(0, N, BLOCK_N):
        offsets = tl.arange(0, BLOCK_N)
        mask = (start + offsets) < N
        row_start_ptr = logits_ptr + row * stride_logits_m + start * stride_logits_n
        col_ptrs = row_start_ptr + offsets * stride_logits_n
        block = tl.load(col_ptrs, mask=mask, other=-1e20)
        block_max = tl.max(block, axis=0)
        max_logit = tl.maximum(max_logit, block_max)

    # Load target_logit
    target_offset = target * stride_logits_n
    target_logit_ptr = logits_ptr + row * stride_logits_m + target_offset
    target_logit = tl.load(target_logit_ptr)

    # Second pass: compute sum_exp
    sum_exp = 0.0
    for start in range(0, N, BLOCK_N):
        offsets = tl.arange(0, BLOCK_N)
        mask = (start + offsets) < N
        row_start_ptr = logits_ptr + row * stride_logits_m + start * stride_logits_n
        col_ptrs = row_start_ptr + offsets * stride_logits_n
        block = tl.load(col_ptrs, mask=mask, other=-1e20)
        block = block - max_logit
        exp_block = tl.exp(block)
        sum_exp += tl.sum(exp_block, axis=0)

    lse = max_logit + tl.log(sum_exp)
    log_prob = target_logit - lse
    loss = -log_prob
    tl.store(losses_ptr + row, loss)


def cross_entropy(logits: torch.Tensor, targets: torch.Tensor) -> torch.Tensor:
    assert logits.dim() == 2, "logits must be 2D"
    assert targets.dim() == 1, "targets must be 1D"
    M, N = logits.shape
    assert targets.shape[0] == M, "batch size mismatch"
    assert targets.max() < N and targets.min() >= 0, "invalid targets"

    losses = torch.empty(M, dtype=torch.float32, device=logits.device, requires_grad=False)

    if M == 0:
        return losses

    stride_logits_m = logits.stride(0)
    stride_logits_n = logits.stride(1)
    stride_targets = targets.stride(0)

    grid = (M,)
    cross_entropy_kernel[grid](
        losses, logits, targets,
        M, N,
        stride_logits_m, stride_logits_n,
        stride_targets,
    )
    return losses
"""
        return {"code": code}
