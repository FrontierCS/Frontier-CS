import os
import textwrap

import torch
import triton
import triton.language as tl


@triton.autotune(
    configs=[
        triton.Config({"BLOCK_N": 128}, num_warps=4, num_stages=2),
        triton.Config({"BLOCK_N": 256}, num_warps=4, num_stages=2),
        triton.Config({"BLOCK_N": 512}, num_warps=8, num_stages=2),
        triton.Config({"BLOCK_N": 1024}, num_warps=8, num_stages=2),
        triton.Config({"BLOCK_N": 2048}, num_warps=8, num_stages=2),
        triton.Config({"BLOCK_N": 4096}, num_warps=8, num_stages=2),
    ],
    key=["N"],
)
@triton.jit
def _cross_entropy_rowwise_kernel(
    logits_ptr,  # *f16/f32/bf16 [M, N]
    targets_ptr,  # *i64 [M]
    losses_ptr,  # *f32 [M]
    M: tl.constexpr,  # rows
    N: tl.constexpr,  # cols
    stride_m,  # stride over rows for logits (elements)
    stride_n,  # stride over cols for logits (elements)
    stride_t,  # stride for targets (elements)
    BLOCK_N: tl.constexpr,
):
    row = tl.program_id(0)
    if row >= M:
        return

    row_i64 = row.to(tl.int64)
    stride_m_i64 = stride_m.to(tl.int64)
    stride_n_i64 = stride_n.to(tl.int64)
    base_row_ptr = logits_ptr + row_i64 * stride_m_i64

    # 1) compute max over row for numerical stability
    offs = tl.arange(0, BLOCK_N)
    start = 0
    max_row = tl.full((), -float("inf"), tl.float32)

    while start < N:
        col = start + offs
        mask = col < N
        col_i64 = col.to(tl.int64)
        ptr = base_row_ptr + col_i64 * stride_n_i64
        x = tl.load(ptr, mask=mask, other=0.0)
        x = x.to(tl.float32)
        x = tl.where(mask, x, -float("inf"))
        local_max = tl.max(x, axis=0)
        max_row = tl.maximum(max_row, local_max)
        start += BLOCK_N

    # 2) compute log-sum-exp = log(sum(exp(x - max))) + max
    sum_row = tl.zeros((), dtype=tl.float32)
    start = 0
    while start < N:
        col = start + offs
        mask = col < N
        col_i64 = col.to(tl.int64)
        ptr = base_row_ptr + col_i64 * stride_n_i64
        x = tl.load(ptr, mask=mask, other=0.0)
        x = x.to(tl.float32)
        x = tl.where(mask, x, -float("inf"))
        sum_row += tl.sum(tl.exp(x - max_row), axis=0)
        start += BLOCK_N
    lse = tl.log(sum_row) + max_row

    # 3) gather target logit and compute -log p(target)
    t_idx = tl.load(targets_ptr + row_i64 * stride_t)
    t_idx = t_idx.to(tl.int64)
    target_ptr = base_row_ptr + t_idx * stride_n_i64
    target_val = tl.load(target_ptr).to(tl.float32)

    loss = lse - target_val
    tl.store(losses_ptr + row_i64, loss)


def cross_entropy(logits: torch.Tensor, targets: torch.Tensor) -> torch.Tensor:
    """
    Cross entropy loss computation.

    Args:
        logits: Tensor of shape (M, N) on CUDA
        targets: Long tensor of shape (M,) on CUDA

    Returns:
        losses: Tensor of shape (M,) float32
    """
    if logits.dim() != 2:
        raise ValueError("logits must be a 2D tensor of shape (M, N)")
    if targets.dim() != 1:
        raise ValueError("targets must be a 1D tensor of shape (M,)")

    M, N = logits.shape
    if targets.shape[0] != M:
        raise ValueError("targets length must match batch size M")
    if M == 0:
        return torch.empty((0,), dtype=torch.float32, device=logits.device)

    if not logits.is_cuda or not targets.is_cuda:
        # CPU fallback
        return torch.nn.functional.cross_entropy(
            logits, targets.to(torch.long), reduction="none"
        ).to(torch.float32)

    # Ensure dtypes
    if targets.dtype != torch.long:
        targets = targets.to(torch.long)

    # Strides in elements
    stride_m, stride_n = logits.stride()
    stride_t = targets.stride(0)

    # Output
    out = torch.empty((M,), dtype=torch.float32, device=logits.device)

    # Launch kernel
    grid = (M,)
    _cross_entropy_rowwise_kernel[grid](
        logits,
        targets,
        out,
        M,
        N,
        stride_m,
        stride_n,
        stride_t,
    )
    return out


class Solution:
    def solve(self, spec_path: str = None) -> dict:
        code = textwrap.dedent(
            '''
            import torch
            import triton
            import triton.language as tl

            @triton.autotune(
                configs=[
                    triton.Config({"BLOCK_N": 128}, num_warps=4, num_stages=2),
                    triton.Config({"BLOCK_N": 256}, num_warps=4, num_stages=2),
                    triton.Config({"BLOCK_N": 512}, num_warps=8, num_stages=2),
                    triton.Config({"BLOCK_N": 1024}, num_warps=8, num_stages=2),
                    triton.Config({"BLOCK_N": 2048}, num_warps=8, num_stages=2),
                    triton.Config({"BLOCK_N": 4096}, num_warps=8, num_stages=2),
                ],
                key=["N"],
            )
            @triton.jit
            def _cross_entropy_rowwise_kernel(
                logits_ptr,  # *f16/f32/bf16 [M, N]
                targets_ptr,  # *i64 [M]
                losses_ptr,  # *f32 [M]
                M: tl.constexpr,  # rows
                N: tl.constexpr,  # cols
                stride_m,  # stride over rows for logits (elements)
                stride_n,  # stride over cols for logits (elements)
                stride_t,  # stride for targets (elements)
                BLOCK_N: tl.constexpr,
            ):
                row = tl.program_id(0)
                if row >= M:
                    return

                row_i64 = row.to(tl.int64)
                stride_m_i64 = stride_m.to(tl.int64)
                stride_n_i64 = stride_n.to(tl.int64)
                base_row_ptr = logits_ptr + row_i64 * stride_m_i64

                # 1) compute max over row for numerical stability
                offs = tl.arange(0, BLOCK_N)
                start = 0
                max_row = tl.full((), -float("inf"), tl.float32)

                while start < N:
                    col = start + offs
                    mask = col < N
                    col_i64 = col.to(tl.int64)
                    ptr = base_row_ptr + col_i64 * stride_n_i64
                    x = tl.load(ptr, mask=mask, other=0.0)
                    x = x.to(tl.float32)
                    x = tl.where(mask, x, -float("inf"))
                    local_max = tl.max(x, axis=0)
                    max_row = tl.maximum(max_row, local_max)
                    start += BLOCK_N

                # 2) compute log-sum-exp
                sum_row = tl.zeros((), dtype=tl.float32)
                start = 0
                while start < N:
                    col = start + offs
                    mask = col < N
                    col_i64 = col.to(tl.int64)
                    ptr = base_row_ptr + col_i64 * stride_n_i64
                    x = tl.load(ptr, mask=mask, other=0.0)
                    x = x.to(tl.float32)
                    x = tl.where(mask, x, -float("inf"))
                    sum_row += tl.sum(tl.exp(x - max_row), axis=0)
                    start += BLOCK_N
                lse = tl.log(sum_row) + max_row

                # 3) gather target logit and compute -log p(target)
                t_idx = tl.load(targets_ptr + row_i64 * stride_t)
                t_idx = t_idx.to(tl.int64)
                target_ptr = base_row_ptr + t_idx * stride_n_i64
                target_val = tl.load(target_ptr).to(tl.float32)

                loss = lse - target_val
                tl.store(losses_ptr + row_i64, loss)


            def cross_entropy(logits: torch.Tensor, targets: torch.Tensor) -> torch.Tensor:
                if logits.dim() != 2:
                    raise ValueError("logits must be a 2D tensor of shape (M, N)")
                if targets.dim() != 1:
                    raise ValueError("targets must be a 1D tensor of shape (M,)")

                M, N = logits.shape
                if targets.shape[0] != M:
                    raise ValueError("targets length must match batch size M")
                if M == 0:
                    return torch.empty((0,), dtype=torch.float32, device=logits.device)

                if not logits.is_cuda or not targets.is_cuda:
                    return torch.nn.functional.cross_entropy(
                        logits, targets.to(torch.long), reduction="none"
                    ).to(torch.float32)

                if targets.dtype != torch.long:
                    targets = targets.to(torch.long)

                stride_m, stride_n = logits.stride()
                stride_t = targets.stride(0)

                out = torch.empty((M,), dtype=torch.float32, device=logits.device)

                grid = (M,)
                _cross_entropy_rowwise_kernel[grid](
                    logits,
                    targets,
                    out,
                    M,
                    N,
                    stride_m,
                    stride_n,
                    stride_t,
                )
                return out
            '''
        ).strip()
        return {"code": code}