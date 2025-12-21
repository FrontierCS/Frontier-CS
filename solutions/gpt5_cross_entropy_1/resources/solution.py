import torch
import torch.nn.functional as F
import triton
import triton.language as tl


@triton.autotune(
    configs=[
        triton.Config({'BLOCK_N': 128}, num_warps=2, num_stages=2),
        triton.Config({'BLOCK_N': 256}, num_warps=4, num_stages=2),
        triton.Config({'BLOCK_N': 512}, num_warps=4, num_stages=3),
        triton.Config({'BLOCK_N': 1024}, num_warps=8, num_stages=3),
        triton.Config({'BLOCK_N': 2048}, num_warps=8, num_stages=4),
        triton.Config({'BLOCK_N': 4096}, num_warps=16, num_stages=4),
    ],
    key=['N'],
)
@triton.jit
def _cross_entropy_kernel(
    logits_ptr,
    targets_ptr,
    output_ptr,
    M: tl.constexpr,
    N: tl.constexpr,
    stride_m,
    stride_n,
    stride_tgt,
    stride_out,
    BLOCK_N: tl.constexpr,
):
    row = tl.program_id(0)
    if row >= M:
        return

    row_i64 = row.to(tl.int64)

    # Base pointers for this row
    row_base_ptr = logits_ptr + row_i64 * stride_m
    out_ptr = output_ptr + row_i64 * stride_out

    # Load target index for this row
    tgt_idx = tl.load(targets_ptr + row_i64 * stride_tgt)
    # Cast to 64-bit for pointer arithmetic
    tgt_idx_i64 = tgt_idx.to(tl.int64)

    # Streaming log-sum-exp across tiles
    m_curr = tl.full((), -float('inf'), tl.float32)
    s_curr = tl.zeros((), tl.float32)

    col_start = 0
    offs = tl.arange(0, BLOCK_N)
    while col_start < N:
        n = col_start + offs
        mask = n < N
        # Load as the source dtype then cast to float32 for math
        x = tl.load(row_base_ptr + n.to(tl.int64) * stride_n, mask=mask, other=-float('inf'))
        x = x.to(tl.float32)
        m_block = tl.max(x, axis=0)
        x_exp = tl.exp(x - m_block)
        s_block = tl.sum(x_exp, axis=0)

        m_new = tl.maximum(m_curr, m_block)
        # s_curr*exp(m_curr-m_new) + s_block*exp(m_block-m_new)
        s_new = s_curr * tl.exp(m_curr - m_new) + s_block * tl.exp(m_block - m_new)

        m_curr = m_new
        s_curr = s_new

        col_start += BLOCK_N

    logsumexp = m_curr + tl.log(s_curr)

    # Load target logit value
    tgt_val = tl.load(row_base_ptr + tgt_idx_i64 * stride_n).to(tl.float32)

    loss = logsumexp - tgt_val
    tl.store(out_ptr, loss)


def cross_entropy(logits: torch.Tensor, targets: torch.Tensor) -> torch.Tensor:
    if logits.dim() != 2:
        raise ValueError("logits must be 2D (M, N)")
    if targets.dim() != 1:
        raise ValueError("targets must be 1D (M,)")

    M, N = logits.shape
    if targets.shape[0] != M:
        raise ValueError("targets length must match logits' first dimension")

    if not logits.is_cuda or not targets.is_cuda:
        # Fallback to PyTorch on CPU or non-CUDA tensors
        loss = -F.log_softmax(logits, dim=-1).gather(-1, targets.to(torch.long).unsqueeze(-1)).squeeze(-1)
        return loss.to(torch.float32)

    if logits.dtype not in (torch.float16, torch.bfloat16, torch.float32):
        logits = logits.to(torch.float32)

    if targets.dtype != torch.long and targets.dtype != torch.int64:
        targets = targets.to(torch.long)

    # Prepare output
    out = torch.empty((M,), device=logits.device, dtype=torch.float32)

    stride_m = logits.stride(0)
    stride_n = logits.stride(1)
    stride_tgt = targets.stride(0)
    stride_out = out.stride(0)

    grid = (M,)

    _cross_entropy_kernel[grid](
        logits,
        targets,
        out,
        M,
        N,
        stride_m,
        stride_n,
        stride_tgt,
        stride_out,
    )
    return out


class Solution:
    def solve(self, spec_path: str = None) -> dict:
        code = '''
import torch
import torch.nn.functional as F
import triton
import triton.language as tl


@triton.autotune(
    configs=[
        triton.Config({'BLOCK_N': 128}, num_warps=2, num_stages=2),
        triton.Config({'BLOCK_N': 256}, num_warps=4, num_stages=2),
        triton.Config({'BLOCK_N': 512}, num_warps=4, num_stages=3),
        triton.Config({'BLOCK_N': 1024}, num_warps=8, num_stages=3),
        triton.Config({'BLOCK_N': 2048}, num_warps=8, num_stages=4),
        triton.Config({'BLOCK_N': 4096}, num_warps=16, num_stages=4),
    ],
    key=['N'],
)
@triton.jit
def _cross_entropy_kernel(
    logits_ptr,
    targets_ptr,
    output_ptr,
    M: tl.constexpr,
    N: tl.constexpr,
    stride_m,
    stride_n,
    stride_tgt,
    stride_out,
    BLOCK_N: tl.constexpr,
):
    row = tl.program_id(0)
    if row >= M:
        return

    row_i64 = row.to(tl.int64)

    row_base_ptr = logits_ptr + row_i64 * stride_m
    out_ptr = output_ptr + row_i64 * stride_out

    tgt_idx = tl.load(targets_ptr + row_i64 * stride_tgt)
    tgt_idx_i64 = tgt_idx.to(tl.int64)

    m_curr = tl.full((), -float('inf'), tl.float32)
    s_curr = tl.zeros((), tl.float32)

    col_start = 0
    offs = tl.arange(0, BLOCK_N)
    while col_start < N:
        n = col_start + offs
        mask = n < N
        x = tl.load(row_base_ptr + n.to(tl.int64) * stride_n, mask=mask, other=-float('inf'))
        x = x.to(tl.float32)
        m_block = tl.max(x, axis=0)
        x_exp = tl.exp(x - m_block)
        s_block = tl.sum(x_exp, axis=0)

        m_new = tl.maximum(m_curr, m_block)
        s_new = s_curr * tl.exp(m_curr - m_new) + s_block * tl.exp(m_block - m_new)

        m_curr = m_new
        s_curr = s_new

        col_start += BLOCK_N

    logsumexp = m_curr + tl.log(s_curr)
    tgt_val = tl.load(row_base_ptr + tgt_idx_i64 * stride_n).to(tl.float32)

    loss = logsumexp - tgt_val
    tl.store(out_ptr, loss)


def cross_entropy(logits: torch.Tensor, targets: torch.Tensor) -> torch.Tensor:
    if logits.dim() != 2:
        raise ValueError("logits must be 2D (M, N)")
    if targets.dim() != 1:
        raise ValueError("targets must be 1D (M,)")

    M, N = logits.shape
    if targets.shape[0] != M:
        raise ValueError("targets length must match logits' first dimension")

    if not logits.is_cuda or not targets.is_cuda:
        loss = -F.log_softmax(logits, dim=-1).gather(-1, targets.to(torch.long).unsqueeze(-1)).squeeze(-1)
        return loss.to(torch.float32)

    if logits.dtype not in (torch.float16, torch.bfloat16, torch.float32):
        logits = logits.to(torch.float32)

    if targets.dtype != torch.long and targets.dtype != torch.int64:
        targets = targets.to(torch.long)

    out = torch.empty((M,), device=logits.device, dtype=torch.float32)

    stride_m = logits.stride(0)
    stride_n = logits.stride(1)
    stride_tgt = targets.stride(0)
    stride_out = out.stride(0)

    grid = (M,)

    _cross_entropy_kernel[grid](
        logits,
        targets,
        out,
        M,
        N,
        stride_m,
        stride_n,
        stride_tgt,
        stride_out,
    )
    return out
'''
        return {"code": code}
