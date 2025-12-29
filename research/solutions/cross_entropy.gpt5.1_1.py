import torch
import torch.nn.functional as F
import triton
import triton.language as tl
import inspect
import sys


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
    logits_ptr,
    targets_ptr,
    loss_ptr,
    M,
    N,
    stride_m,
    stride_n,
    stride_targets,
    stride_loss,
    BLOCK_SIZE: tl.constexpr,
):
    pid_m = tl.program_id(axis=0)
    if pid_m >= M:
        return

    # Base pointer to the row
    row_logits_ptr = logits_ptr + pid_m * stride_m

    # Load target index for this row
    target = tl.load(targets_ptr + pid_m * stride_targets)
    # Cast to same int type as offsets
    target = target.to(tl.int32)

    # First block: initialize row_max, row_sum, target_logit
    col_start = 0
    offs = col_start + tl.arange(0, BLOCK_SIZE)
    mask = offs < N
    ptrs = row_logits_ptr + offs * stride_n
    logits = tl.load(ptrs, mask=mask, other=-float('inf'))
    logits_f32 = logits.to(tl.float32)

    row_max = tl.max(logits_f32, axis=0)
    exp_block = tl.exp(logits_f32 - row_max)
    row_sum = tl.sum(exp_block, axis=0)

    is_target = offs == target
    target_logit = tl.sum(logits_f32 * is_target.to(tl.float32), axis=0)

    col_start += BLOCK_SIZE

    # Process remaining blocks
    while col_start < N:
        offs = col_start + tl.arange(0, BLOCK_SIZE)
        mask = offs < N
        ptrs = row_logits_ptr + offs * stride_n
        logits = tl.load(ptrs, mask=mask, other=-float('inf'))
        logits_f32 = logits.to(tl.float32)

        block_max = tl.max(logits_f32, axis=0)
        exp_block = tl.exp(logits_f32 - block_max)
        block_sum = tl.sum(exp_block, axis=0)

        new_max = tl.maximum(row_max, block_max)
        exp_prev = tl.exp(row_max - new_max) * row_sum
        exp_cur = tl.exp(block_max - new_max) * block_sum
        row_sum = exp_prev + exp_cur
        row_max = new_max

        is_target = offs == target
        target_logit += tl.sum(logits_f32 * is_target.to(tl.float32), axis=0)

        col_start += BLOCK_SIZE

    logsumexp = tl.log(row_sum) + row_max
    loss = logsumexp - target_logit
    tl.store(loss_ptr + pid_m * stride_loss, loss.to(tl.float32))


def cross_entropy(logits: torch.Tensor, targets: torch.Tensor) -> torch.Tensor:
    """
    Cross entropy loss computation.

    Args:
        logits: Tensor of shape (M, N)
        targets: Tensor of shape (M,)

    Returns:
        Tensor of shape (M,) with dtype float32
    """
    if logits.dim() != 2:
        raise ValueError("logits must be a 2D tensor of shape (M, N)")
    if targets.dim() != 1:
        raise ValueError("targets must be a 1D tensor of shape (M,)")

    M, N = logits.shape
    if targets.shape[0] != M:
        raise ValueError("targets length must match logits batch size (M)")

    if not logits.is_cuda or not targets.is_cuda:
        # Fallback to PyTorch implementation on CPU or mismatched device
        return F.cross_entropy(logits, targets, reduction='none').to(torch.float32)

    # Ensure targets are contiguous for stride correctness
    if not targets.is_contiguous():
        targets = targets.contiguous()

    device = logits.device
    out = torch.empty((M,), device=device, dtype=torch.float32)

    stride_m, stride_n = logits.stride()
    stride_targets = targets.stride(0)
    stride_loss = out.stride(0)

    grid = lambda META: (M,)

    _cross_entropy_kernel[grid](
        logits,
        targets,
        out,
        M,
        N,
        stride_m,
        stride_n,
        stride_targets,
        stride_loss,
    )

    return out


class Solution:
    def solve(self, spec_path: str = None) -> dict:
        module = sys.modules[__name__]
        code = inspect.getsource(module)
        return {"code": code}