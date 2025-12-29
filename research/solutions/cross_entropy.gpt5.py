import torch
import triton
import triton.language as tl


@triton.autotune(
    configs=[
        triton.Config({'BLOCK_N': 128}, num_warps=4, num_stages=2),
        triton.Config({'BLOCK_N': 256}, num_warps=4, num_stages=2),
        triton.Config({'BLOCK_N': 512}, num_warps=8, num_stages=2),
        triton.Config({'BLOCK_N': 1024}, num_warps=8, num_stages=2),
    ],
    key=['N'],
)
@triton.jit
def _cross_entropy_kernel(
    logits_ptr,  # *f32 | *f16 | *bf16
    targets_ptr,  # *i64
    out_ptr,  # *f32
    M: tl.constexpr,
    N: tl.constexpr,
    stride_m,  # stride along rows for logits
    stride_n,  # stride along cols for logits
    target_stride,  # stride for targets
    out_stride,  # stride for output
    BLOCK_N: tl.constexpr,
):
    row = tl.program_id(0)
    # Guard against out-of-bounds launch
    if row >= M:
        return

    # Base pointers for this row
    row_ptr = logits_ptr + row * stride_m

    # Load target class index for this row
    t_idx = tl.load(targets_ptr + row * target_stride, mask=True, other=0).to(tl.int64)
    # Gather target logit
    t_logit = tl.load(row_ptr + t_idx * stride_n, mask=True, other=0).to(tl.float32)

    # Online log-sum-exp reduction across the row
    m = tl.full((), -float('inf'), tl.float32)  # running max
    s = tl.zeros((), tl.float32)  # running sum of exp(x - m)
    offs = tl.arange(0, BLOCK_N)

    col = 0
    while col < N:
        idx = col + offs
        mask = idx < N
        x = tl.load(row_ptr + idx * stride_n, mask=mask, other=0)
        x = x.to(tl.float32)
        # Apply mask by setting -inf to invalid lanes
        x = tl.where(mask, x, -float('inf'))
        block_max = tl.max(x, axis=0)
        new_m = tl.maximum(m, block_max)
        # Rescale previous sum to new max and add current block contribution
        s = s * tl.exp(m - new_m) + tl.sum(tl.exp(x - new_m), axis=0)
        m = new_m
        col += BLOCK_N

    # Final log-sum-exp
    lse = tl.log(s) + m
    loss = lse - t_logit

    # Store result
    tl.store(out_ptr + row * out_stride, loss)


def cross_entropy(logits: torch.Tensor, targets: torch.Tensor) -> torch.Tensor:
    """
    Cross entropy loss computation.

    Args:
        logits: Tensor of shape (M, N) on CUDA device. Supports float32/float16/bfloat16.
        targets: Tensor of shape (M,) with dtype int64 on CUDA device.

    Returns:
        Tensor of shape (M,) with dtype float32.
    """
    assert logits.is_cuda and targets.is_cuda, "Inputs must be CUDA tensors"
    assert logits.ndim == 2, "logits must be 2D (M, N)"
    assert targets.ndim == 1 and targets.shape[0] == logits.shape[0], "targets must be 1D with length M"
    M, N = logits.shape

    # Ensure targets are int64
    if targets.dtype != torch.int64:
        targets = targets.to(torch.int64)

    out = torch.empty((M,), device=logits.device, dtype=torch.float32)

    grid = (M,)

    _cross_entropy_kernel[grid](
        logits,
        targets,
        out,
        M,
        N,
        logits.stride(0),
        logits.stride(1),
        targets.stride(0),
        out.stride(0),
    )
    return out


class Solution:
    def solve(self, spec_path: str = None) -> dict:
        code = '''
import torch
import triton
import triton.language as tl


@triton.autotune(
    configs=[
        triton.Config({'BLOCK_N': 128}, num_warps=4, num_stages=2),
        triton.Config({'BLOCK_N': 256}, num_warps=4, num_stages=2),
        triton.Config({'BLOCK_N': 512}, num_warps=8, num_stages=2),
        triton.Config({'BLOCK_N': 1024}, num_warps=8, num_stages=2),
    ],
    key=['N'],
)
@triton.jit
def _cross_entropy_kernel(
    logits_ptr,  # *f32 | *f16 | *bf16
    targets_ptr,  # *i64
    out_ptr,  # *f32
    M: tl.constexpr,
    N: tl.constexpr,
    stride_m,  # stride along rows for logits
    stride_n,  # stride along cols for logits
    target_stride,  # stride for targets
    out_stride,  # stride for output
    BLOCK_N: tl.constexpr,
):
    row = tl.program_id(0)
    if row >= M:
        return

    row_ptr = logits_ptr + row * stride_m

    t_idx = tl.load(targets_ptr + row * target_stride, mask=True, other=0).to(tl.int64)
    t_logit = tl.load(row_ptr + t_idx * stride_n, mask=True, other=0).to(tl.float32)

    m = tl.full((), -float('inf'), tl.float32)
    s = tl.zeros((), tl.float32)

    offs = tl.arange(0, BLOCK_N)
    col = 0
    while col < N:
        idx = col + offs
        mask = idx < N
        x = tl.load(row_ptr + idx * stride_n, mask=mask, other=0)
        x = x.to(tl.float32)
        x = tl.where(mask, x, -float('inf'))
        block_max = tl.max(x, axis=0)
        new_m = tl.maximum(m, block_max)
        s = s * tl.exp(m - new_m) + tl.sum(tl.exp(x - new_m), axis=0)
        m = new_m
        col += BLOCK_N

    lse = tl.log(s) + m
    loss = lse - t_logit

    tl.store(out_ptr + row * out_stride, loss)


def cross_entropy(logits: torch.Tensor, targets: torch.Tensor) -> torch.Tensor:
    assert logits.is_cuda and targets.is_cuda, "Inputs must be CUDA tensors"
    assert logits.ndim == 2, "logits must be 2D (M, N)"
    assert targets.ndim == 1 and targets.shape[0] == logits.shape[0], "targets must be 1D with length M"
    M, N = logits.shape

    if targets.dtype != torch.int64:
        targets = targets.to(torch.int64)

    out = torch.empty((M,), device=logits.device, dtype=torch.float32)

    grid = (M,)

    _cross_entropy_kernel[grid](
        logits,
        targets,
        out,
        M,
        N,
        logits.stride(0),
        logits.stride(1),
        targets.stride(0),
        out.stride(0),
    )
    return out
'''
        return {"code": code}