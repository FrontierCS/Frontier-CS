import os
import textwrap
import torch
import triton
import triton.language as tl


@triton.autotune(
    configs=[
        triton.Config({"BLOCK_N": 256}, num_warps=4, num_stages=3),
        triton.Config({"BLOCK_N": 512}, num_warps=4, num_stages=3),
        triton.Config({"BLOCK_N": 1024}, num_warps=8, num_stages=4),
        triton.Config({"BLOCK_N": 2048}, num_warps=8, num_stages=4),
    ],
    key=["N"],
)
@triton.jit
def _cross_entropy_kernel(
    logits_ptr,
    targets_ptr,
    out_ptr,
    stride_m: tl.constexpr,
    stride_n: tl.constexpr,
    M,
    N: tl.constexpr,
    BLOCK_N: tl.constexpr,
):
    row = tl.program_id(0)
    row_mask = row < M

    t = tl.load(targets_ptr + row, mask=row_mask, other=0).to(tl.int32)

    m = tl.full([], -float("inf"), tl.float32)
    s = tl.zeros([], dtype=tl.float32)

    offs = tl.arange(0, BLOCK_N)
    row_base = logits_ptr + row * stride_m

    for start in tl.static_range(0, N, BLOCK_N):
        cols = start + offs
        col_mask = cols < N
        mask = row_mask & col_mask
        x = tl.load(row_base + cols * stride_n, mask=mask, other=-float("inf")).to(tl.float32)

        block_max = tl.max(x, axis=0)
        new_m = tl.maximum(m, block_max)
        s = s * tl.exp(m - new_m) + tl.sum(tl.exp(x - new_m), axis=0)
        m = new_m

    logsumexp = tl.log(s) + m

    t_mask = row_mask & (t >= 0) & (t < N)
    logit_t = tl.load(row_base + t * stride_n, mask=t_mask, other=0.0).to(tl.float32)

    loss = logsumexp - logit_t
    tl.store(out_ptr + row, loss, mask=row_mask)


def cross_entropy(logits: torch.Tensor, targets: torch.Tensor) -> torch.Tensor:
    if not isinstance(logits, torch.Tensor) or not isinstance(targets, torch.Tensor):
        raise TypeError("logits and targets must be torch.Tensor")
    if logits.ndim != 2:
        raise ValueError(f"logits must be 2D (M, N); got shape {tuple(logits.shape)}")
    if targets.ndim != 1:
        raise ValueError(f"targets must be 1D (M,); got shape {tuple(targets.shape)}")
    if logits.shape[0] != targets.shape[0]:
        raise ValueError(f"Batch mismatch: logits.shape[0]={logits.shape[0]} targets.shape[0]={targets.shape[0]}")

    M, N = logits.shape
    if M == 0:
        return torch.empty((0,), device=logits.device, dtype=torch.float32)

    if not logits.is_cuda:
        # CPU fallback
        logsumexp = torch.logsumexp(logits.to(torch.float32), dim=1)
        idx = targets.to(torch.long).clamp(0, N - 1).view(-1, 1)
        logit_t = logits.to(torch.float32).gather(1, idx).squeeze(1)
        return (logsumexp - logit_t).to(torch.float32)

    if targets.dtype != torch.int64:
        targets_i64 = targets.to(torch.int64)
    else:
        targets_i64 = targets

    out = torch.empty((M,), device=logits.device, dtype=torch.float32)

    stride_m, stride_n = logits.stride(0), logits.stride(1)

    grid = (triton.cdiv(M, 1),)
    _cross_entropy_kernel[grid](
        logits,
        targets_i64,
        out,
        stride_m=stride_m,
        stride_n=stride_n,
        M=M,
        N=N,
    )
    return out


_KERNEL_CODE = textwrap.dedent(
    r"""
    import torch
    import triton
    import triton.language as tl


    @triton.autotune(
        configs=[
            triton.Config({"BLOCK_N": 256}, num_warps=4, num_stages=3),
            triton.Config({"BLOCK_N": 512}, num_warps=4, num_stages=3),
            triton.Config({"BLOCK_N": 1024}, num_warps=8, num_stages=4),
            triton.Config({"BLOCK_N": 2048}, num_warps=8, num_stages=4),
        ],
        key=["N"],
    )
    @triton.jit
    def _cross_entropy_kernel(
        logits_ptr,
        targets_ptr,
        out_ptr,
        stride_m: tl.constexpr,
        stride_n: tl.constexpr,
        M,
        N: tl.constexpr,
        BLOCK_N: tl.constexpr,
    ):
        row = tl.program_id(0)
        row_mask = row < M

        t = tl.load(targets_ptr + row, mask=row_mask, other=0).to(tl.int32)

        m = tl.full([], -float("inf"), tl.float32)
        s = tl.zeros([], dtype=tl.float32)

        offs = tl.arange(0, BLOCK_N)
        row_base = logits_ptr + row * stride_m

        for start in tl.static_range(0, N, BLOCK_N):
            cols = start + offs
            col_mask = cols < N
            mask = row_mask & col_mask
            x = tl.load(row_base + cols * stride_n, mask=mask, other=-float("inf")).to(tl.float32)

            block_max = tl.max(x, axis=0)
            new_m = tl.maximum(m, block_max)
            s = s * tl.exp(m - new_m) + tl.sum(tl.exp(x - new_m), axis=0)
            m = new_m

        logsumexp = tl.log(s) + m

        t_mask = row_mask & (t >= 0) & (t < N)
        logit_t = tl.load(row_base + t * stride_n, mask=t_mask, other=0.0).to(tl.float32)

        loss = logsumexp - logit_t
        tl.store(out_ptr + row, loss, mask=row_mask)


    def cross_entropy(logits: torch.Tensor, targets: torch.Tensor) -> torch.Tensor:
        if not isinstance(logits, torch.Tensor) or not isinstance(targets, torch.Tensor):
            raise TypeError("logits and targets must be torch.Tensor")
        if logits.ndim != 2:
            raise ValueError(f"logits must be 2D (M, N); got shape {tuple(logits.shape)}")
        if targets.ndim != 1:
            raise ValueError(f"targets must be 1D (M,); got shape {tuple(targets.shape)}")
        if logits.shape[0] != targets.shape[0]:
            raise ValueError(f"Batch mismatch: logits.shape[0]={logits.shape[0]} targets.shape[0]={targets.shape[0]}")

        M, N = logits.shape
        if M == 0:
            return torch.empty((0,), device=logits.device, dtype=torch.float32)

        if not logits.is_cuda:
            logsumexp = torch.logsumexp(logits.to(torch.float32), dim=1)
            idx = targets.to(torch.long).clamp(0, N - 1).view(-1, 1)
            logit_t = logits.to(torch.float32).gather(1, idx).squeeze(1)
            return (logsumexp - logit_t).to(torch.float32)

        if targets.dtype != torch.int64:
            targets_i64 = targets.to(torch.int64)
        else:
            targets_i64 = targets

        out = torch.empty((M,), device=logits.device, dtype=torch.float32)

        stride_m, stride_n = logits.stride(0), logits.stride(1)

        grid = (triton.cdiv(M, 1),)
        _cross_entropy_kernel[grid](
            logits,
            targets_i64,
            out,
            stride_m=stride_m,
            stride_n=stride_n,
            M=M,
            N=N,
        )
        return out
    """
).lstrip()


class Solution:
    def solve(self, spec_path: str = None) -> dict:
        return {"code": _KERNEL_CODE}