import math
import torch
import triton
import triton.language as tl


@triton.autotune(
    configs=[
        triton.Config({"BLOCK": 256}, num_warps=4, num_stages=2),
        triton.Config({"BLOCK": 512}, num_warps=8, num_stages=2),
        triton.Config({"BLOCK": 1024}, num_warps=8, num_stages=2),
        triton.Config({"BLOCK": 2048}, num_warps=8, num_stages=2),
    ],
    key=["N"],
)
@triton.jit
def _cross_entropy_kernel(
    logits_ptr,
    targets_ptr,
    output_ptr,
    M,
    N,
    stride_m,
    stride_n,
    stride_t,
    BLOCK: tl.constexpr,
    MAX_N: tl.constexpr,
):
    pid_m = tl.program_id(0)
    if pid_m >= M:
        return

    # pointers
    row_base = logits_ptr + pid_m * stride_m

    # load target index for the row (supports strided targets)
    t = tl.load(targets_ptr + pid_m * stride_t)
    t = t.to(tl.int64)

    # compute row-wise max over N using segmented reduction
    offs = tl.arange(0, BLOCK)
    num_segments = (MAX_N + BLOCK - 1) // BLOCK

    row_max = tl.full((), -float("inf"), tl.float32)
    for seg in range(0, num_segments):
        cols = seg * BLOCK + offs
        mask = cols < N
        ptrs = row_base + cols * stride_n
        x = tl.load(ptrs, mask=mask, other=-float("inf"))
        x = x.to(tl.float32)
        seg_max = tl.max(x, axis=0)
        row_max = tl.maximum(row_max, seg_max)

    # compute row-wise sum(exp(x - max))
    sum_exp = tl.zeros((), dtype=tl.float32)
    for seg in range(0, num_segments):
        cols = seg * BLOCK + offs
        mask = cols < N
        ptrs = row_base + cols * stride_n
        x = tl.load(ptrs, mask=mask, other=-float("inf"))
        x = x.to(tl.float32)
        sum_exp += tl.sum(tl.exp(x - row_max), axis=0)

    # load target logit
    # mask to be safe even if targets contain invalid entries; assume valid during evaluation
    t_mask = (t >= 0) & (t < N)
    t_ptr = row_base + t * stride_n
    tgt_val = tl.load(t_ptr, mask=t_mask, other=0.0)
    tgt_val = tgt_val.to(tl.float32)

    # loss = logsumexp - logit[target]
    loss = tl.log(sum_exp) + row_max - tgt_val
    tl.store(output_ptr + pid_m, loss)


def cross_entropy(logits: torch.Tensor, targets: torch.Tensor) -> torch.Tensor:
    """
    Cross entropy loss computation using Triton.

    Args:
        logits: (M, N) tensor (float32/float16/bfloat16) on CUDA
        targets: (M,) tensor (int64 or int32) on same device

    Returns:
        (M,) float32 tensor: per-sample negative log-likelihood loss
    """
    if logits.dim() != 2:
        raise ValueError("logits must be 2D (M, N)")
    if targets.dim() != 1:
        raise ValueError("targets must be 1D (M,)")

    M, N = logits.shape
    if M == 0:
        return torch.empty((0,), device=logits.device, dtype=torch.float32)

    if not logits.is_cuda or not targets.is_cuda:
        # Fallback CPU computation
        return (-torch.log_softmax(logits.float(), dim=-1).gather(-1, targets.view(-1, 1)).squeeze(-1)).to(torch.float32)

    # Ensure dtypes
    logits_f32 = logits.to(torch.float32)
    targets_i64 = targets.to(torch.int64)

    # Allocate output
    out = torch.empty((M,), device=logits.device, dtype=torch.float32)

    # Strides in elements
    stride_m, stride_n = logits_f32.stride()
    stride_t = targets_i64.stride(0)

    # Choose MAX_N as a power-of-two cap not smaller than N to allow compile-time segmented loop
    # Cap MAX_N to a reasonable upper bound to avoid excessive compile-time work
    max_cap = 1 << 15  # 32768
    MAX_N = 1 << (int(N - 1).bit_length())
    if MAX_N > max_cap:
        MAX_N = max_cap
        if N > MAX_N:
            # In extremely large-vocab cases, fall back to PyTorch
            return (-torch.log_softmax(logits_f32, dim=-1).gather(-1, targets_i64.view(-1, 1)).squeeze(-1)).to(torch.float32)

    grid = (M,)

    _cross_entropy_kernel[grid](
        logits_f32,
        targets_i64,
        out,
        M,
        N,
        stride_m,
        stride_n,
        stride_t,
        MAX_N=MAX_N,
    )

    return out


class Solution:
    def solve(self, spec_path: str = None) -> dict:
        code = '''
import math
import torch
import triton
import triton.language as tl


@triton.autotune(
    configs=[
        triton.Config({"BLOCK": 256}, num_warps=4, num_stages=2),
        triton.Config({"BLOCK": 512}, num_warps=8, num_stages=2),
        triton.Config({"BLOCK": 1024}, num_warps=8, num_stages=2),
        triton.Config({"BLOCK": 2048}, num_warps=8, num_stages=2),
    ],
    key=["N"],
)
@triton.jit
def _cross_entropy_kernel(
    logits_ptr,
    targets_ptr,
    output_ptr,
    M,
    N,
    stride_m,
    stride_n,
    stride_t,
    BLOCK: tl.constexpr,
    MAX_N: tl.constexpr,
):
    pid_m = tl.program_id(0)
    if pid_m >= M:
        return

    row_base = logits_ptr + pid_m * stride_m

    t = tl.load(targets_ptr + pid_m * stride_t)
    t = t.to(tl.int64)

    offs = tl.arange(0, BLOCK)
    num_segments = (MAX_N + BLOCK - 1) // BLOCK

    row_max = tl.full((), -float("inf"), tl.float32)
    for seg in range(0, num_segments):
        cols = seg * BLOCK + offs
        mask = cols < N
        ptrs = row_base + cols * stride_n
        x = tl.load(ptrs, mask=mask, other=-float("inf"))
        x = x.to(tl.float32)
        seg_max = tl.max(x, axis=0)
        row_max = tl.maximum(row_max, seg_max)

    sum_exp = tl.zeros((), dtype=tl.float32)
    for seg in range(0, num_segments):
        cols = seg * BLOCK + offs
        mask = cols < N
        ptrs = row_base + cols * stride_n
        x = tl.load(ptrs, mask=mask, other=-float("inf"))
        x = x.to(tl.float32)
        sum_exp += tl.sum(tl.exp(x - row_max), axis=0)

    t_mask = (t >= 0) & (t < N)
    t_ptr = row_base + t * stride_n
    tgt_val = tl.load(t_ptr, mask=t_mask, other=0.0)
    tgt_val = tgt_val.to(tl.float32)

    loss = tl.log(sum_exp) + row_max - tgt_val
    tl.store(output_ptr + pid_m, loss)


def cross_entropy(logits: torch.Tensor, targets: torch.Tensor) -> torch.Tensor:
    if logits.dim() != 2:
        raise ValueError("logits must be 2D (M, N)")
    if targets.dim() != 1:
        raise ValueError("targets must be 1D (M,)")

    M, N = logits.shape
    if M == 0:
        return torch.empty((0,), device=logits.device, dtype=torch.float32)

    if not logits.is_cuda or not targets.is_cuda:
        return (-torch.log_softmax(logits.float(), dim=-1).gather(-1, targets.view(-1, 1)).squeeze(-1)).to(torch.float32)

    logits_f32 = logits.to(torch.float32)
    targets_i64 = targets.to(torch.int64)

    out = torch.empty((M,), device=logits.device, dtype=torch.float32)

    stride_m, stride_n = logits_f32.stride()
    stride_t = targets_i64.stride(0)

    max_cap = 1 << 15  # 32768
    MAX_N = 1 << (int(N - 1).bit_length())
    if MAX_N > max_cap:
        MAX_N = max_cap
        if N > MAX_N:
            return (-torch.log_softmax(logits_f32, dim=-1).gather(-1, targets_i64.view(-1, 1)).squeeze(-1)).to(torch.float32)

    grid = (M,)

    _cross_entropy_kernel[grid](
        logits_f32,
        targets_i64,
        out,
        M,
        N,
        stride_m,
        stride_n,
        stride_t,
        MAX_N=MAX_N,
    )

    return out
'''
        return {"code": code}