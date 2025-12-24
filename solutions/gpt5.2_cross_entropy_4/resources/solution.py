import os
import math
import textwrap

KERNEL_CODE = r'''
import torch
import triton
import triton.language as tl

_LOG2E_F32 = 1.4426950408889634
_LN2_F32 = 0.6931471805599453


@triton.autotune(
    configs=[
        triton.Config({'BLOCK_N': 256}, num_warps=4, num_stages=3),
        triton.Config({'BLOCK_N': 256}, num_warps=8, num_stages=3),
        triton.Config({'BLOCK_N': 512}, num_warps=4, num_stages=3),
        triton.Config({'BLOCK_N': 512}, num_warps=8, num_stages=4),
        triton.Config({'BLOCK_N': 1024}, num_warps=8, num_stages=4),
    ],
    key=['N'],
)
@triton.jit
def _xent_contig_kernel(
    logits_ptr,
    targets_ptr,
    out_ptr,
    stride_t,
    M,
    N: tl.constexpr,
    BLOCK_N: tl.constexpr,
):
    pid = tl.program_id(0)

    # This kernel expects grid=(M,), so pid is always in-bounds.
    row_ptr = logits_ptr + pid * N
    tl.multiple_of(row_ptr, 16)

    m = tl.full((), -float('inf'), tl.float32)
    s = tl.zeros((), tl.float32)

    if N % BLOCK_N == 0:
        for off in tl.static_range(0, N, BLOCK_N):
            cols = off + tl.arange(0, BLOCK_N)
            x = tl.load(row_ptr + cols).to(tl.float32)
            m_block = tl.max(x, axis=0)
            m_new = tl.maximum(m, m_block)
            s = s * tl.exp2((m - m_new) * _LOG2E_F32) + tl.sum(tl.exp2((x - m_new) * _LOG2E_F32), axis=0)
            m = m_new
    else:
        for off in tl.static_range(0, N, BLOCK_N):
            cols = off + tl.arange(0, BLOCK_N)
            mask = cols < N
            x = tl.load(row_ptr + cols, mask=mask, other=-float('inf')).to(tl.float32)
            m_block = tl.max(x, axis=0)
            m_new = tl.maximum(m, m_block)
            s = s * tl.exp2((m - m_new) * _LOG2E_F32) + tl.sum(tl.exp2((x - m_new) * _LOG2E_F32), axis=0)
            m = m_new

    t = tl.load(targets_ptr + pid * stride_t).to(tl.int32)
    x_t = tl.load(row_ptr + t).to(tl.float32)

    loss = tl.log2(s) * _LN2_F32 + m - x_t
    tl.store(out_ptr + pid, loss)


@triton.autotune(
    configs=[
        triton.Config({'BLOCK_N': 256}, num_warps=4, num_stages=3),
        triton.Config({'BLOCK_N': 256}, num_warps=8, num_stages=3),
        triton.Config({'BLOCK_N': 512}, num_warps=4, num_stages=3),
        triton.Config({'BLOCK_N': 512}, num_warps=8, num_stages=4),
        triton.Config({'BLOCK_N': 1024}, num_warps=8, num_stages=4),
    ],
    key=['N'],
)
@triton.jit
def _xent_strided_kernel(
    logits_ptr,
    targets_ptr,
    out_ptr,
    stride_lm,
    stride_ln,
    stride_t,
    M,
    N: tl.constexpr,
    BLOCK_N: tl.constexpr,
):
    pid = tl.program_id(0)

    row_ptr = logits_ptr + pid * stride_lm

    m = tl.full((), -float('inf'), tl.float32)
    s = tl.zeros((), tl.float32)

    if N % BLOCK_N == 0:
        for off in tl.static_range(0, N, BLOCK_N):
            cols = off + tl.arange(0, BLOCK_N)
            x = tl.load(row_ptr + cols * stride_ln).to(tl.float32)
            m_block = tl.max(x, axis=0)
            m_new = tl.maximum(m, m_block)
            s = s * tl.exp2((m - m_new) * _LOG2E_F32) + tl.sum(tl.exp2((x - m_new) * _LOG2E_F32), axis=0)
            m = m_new
    else:
        for off in tl.static_range(0, N, BLOCK_N):
            cols = off + tl.arange(0, BLOCK_N)
            mask = cols < N
            x = tl.load(row_ptr + cols * stride_ln, mask=mask, other=-float('inf')).to(tl.float32)
            m_block = tl.max(x, axis=0)
            m_new = tl.maximum(m, m_block)
            s = s * tl.exp2((m - m_new) * _LOG2E_F32) + tl.sum(tl.exp2((x - m_new) * _LOG2E_F32), axis=0)
            m = m_new

    t = tl.load(targets_ptr + pid * stride_t).to(tl.int32)
    x_t = tl.load(row_ptr + t * stride_ln).to(tl.float32)

    loss = tl.log2(s) * _LN2_F32 + m - x_t
    tl.store(out_ptr + pid, loss)


def cross_entropy(logits: torch.Tensor, targets: torch.Tensor) -> torch.Tensor:
    if logits.dim() != 2:
        raise ValueError("logits must be 2D (M, N)")
    if targets.dim() != 1:
        raise ValueError("targets must be 1D (M,)")
    if logits.shape[0] != targets.shape[0]:
        raise ValueError("batch dimension mismatch")

    M, N = logits.shape
    out = torch.empty((M,), device=logits.device, dtype=torch.float32)

    if M == 0:
        return out

    if (not logits.is_cuda) or (not targets.is_cuda):
        x = logits.to(torch.float32)
        t = targets.to(torch.int64)
        return (torch.logsumexp(x, dim=1) - x.gather(1, t.view(-1, 1)).squeeze(1)).to(torch.float32)

    t = targets
    if t.dtype != torch.int64 and t.dtype != torch.int32:
        t = t.to(torch.int64)

    grid = (M,)
    if logits.is_contiguous() and logits.stride(1) == 1 and logits.stride(0) == N:
        _xent_contig_kernel[grid](
            logits, t, out,
            t.stride(0),
            M,
            N=N,
        )
    else:
        _xent_strided_kernel[grid](
            logits, t, out,
            logits.stride(0), logits.stride(1),
            t.stride(0),
            M,
            N=N,
        )
    return out
'''

exec(KERNEL_CODE, globals())


class Solution:
    def solve(self, spec_path: str = None) -> dict:
        return {"code": KERNEL_CODE}
