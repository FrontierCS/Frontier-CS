import os
import textwrap

KERNEL_CODE = textwrap.dedent(
    r"""
    import torch
    import triton
    import triton.language as tl

    @triton.autotune(
        configs=[
            triton.Config({"BLOCK_N": 1024}, num_warps=4, num_stages=4),
            triton.Config({"BLOCK_N": 1024}, num_warps=8, num_stages=4),
            triton.Config({"BLOCK_N": 2048}, num_warps=8, num_stages=3),
        ],
        key=["N"],
    )
    @triton.jit
    def _xent_contig_kernel(
        logits_ptr,
        targets_ptr,
        out_ptr,
        stride_m,
        stride_t,
        N: tl.constexpr,
        BLOCK_N: tl.constexpr,
    ):
        pid = tl.program_id(0)

        row_start = logits_ptr + pid * stride_m
        tl.multiple_of(row_start, 16)

        t = tl.load(targets_ptr + pid * stride_t).to(tl.int32)
        target_logit = tl.load(row_start + t).to(tl.float32)

        gmax = tl.full((), -float("inf"), tl.float32)
        gsum = tl.zeros((), tl.float32)

        num_iters = (N + BLOCK_N - 1) // BLOCK_N
        for i in tl.static_range(0, num_iters):
            offs = i * BLOCK_N + tl.arange(0, BLOCK_N)
            x = tl.load(row_start + offs, mask=offs < N, other=-float("inf")).to(tl.float32)
            bmax = tl.max(x, axis=0)
            new_max = tl.maximum(gmax, bmax)
            gsum = gsum * tl.exp(gmax - new_max) + tl.sum(tl.exp(x - new_max), axis=0)
            gmax = new_max

        lse = tl.log(gsum) + gmax
        loss = lse - target_logit
        tl.store(out_ptr + pid, loss)

    @triton.autotune(
        configs=[
            triton.Config({"BLOCK_N": 512}, num_warps=4, num_stages=4),
            triton.Config({"BLOCK_N": 1024}, num_warps=4, num_stages=4),
            triton.Config({"BLOCK_N": 1024}, num_warps=8, num_stages=4),
        ],
        key=["N"],
    )
    @triton.jit
    def _xent_strided_kernel(
        logits_ptr,
        targets_ptr,
        out_ptr,
        stride_m,
        stride_n,
        stride_t,
        N: tl.constexpr,
        BLOCK_N: tl.constexpr,
    ):
        pid = tl.program_id(0)

        row_start = logits_ptr + pid * stride_m
        t = tl.load(targets_ptr + pid * stride_t).to(tl.int32)
        target_logit = tl.load(row_start + t * stride_n).to(tl.float32)

        gmax = tl.full((), -float("inf"), tl.float32)
        gsum = tl.zeros((), tl.float32)

        num_iters = (N + BLOCK_N - 1) // BLOCK_N
        for i in tl.static_range(0, num_iters):
            offs = i * BLOCK_N + tl.arange(0, BLOCK_N)
            ptrs = row_start + offs * stride_n
            x = tl.load(ptrs, mask=offs < N, other=-float("inf")).to(tl.float32)
            bmax = tl.max(x, axis=0)
            new_max = tl.maximum(gmax, bmax)
            gsum = gsum * tl.exp(gmax - new_max) + tl.sum(tl.exp(x - new_max), axis=0)
            gmax = new_max

        lse = tl.log(gsum) + gmax
        loss = lse - target_logit
        tl.store(out_ptr + pid, loss)

    def cross_entropy(logits: torch.Tensor, targets: torch.Tensor) -> torch.Tensor:
        if logits.ndim != 2:
            raise ValueError(f"logits must be 2D (M, N), got shape={tuple(logits.shape)}")
        if targets.ndim != 1:
            raise ValueError(f"targets must be 1D (M,), got shape={tuple(targets.shape)}")
        if logits.shape[0] != targets.shape[0]:
            raise ValueError(f"M mismatch: logits.shape[0]={logits.shape[0]} vs targets.shape[0]={targets.shape[0]}")
        if not logits.is_cuda or not targets.is_cuda:
            raise ValueError("cross_entropy requires CUDA tensors")
        if targets.dtype not in (torch.int64, torch.int32):
            targets = targets.to(torch.int64)

        M, N = logits.shape
        out = torch.empty((M,), device=logits.device, dtype=torch.float32)

        stride_m = logits.stride(0)
        stride_n = logits.stride(1)
        stride_t = targets.stride(0)

        grid = (M,)
        if stride_n == 1:
            _xent_contig_kernel[grid](
                logits,
                targets,
                out,
                stride_m,
                stride_t,
                N=N,
            )
        else:
            _xent_strided_kernel[grid](
                logits,
                targets,
                out,
                stride_m,
                stride_n,
                stride_t,
                N=N,
            )
        return out
    """
).lstrip()

_exec_globals = {}
exec(KERNEL_CODE, _exec_globals)
cross_entropy = _exec_globals["cross_entropy"]


class Solution:
    def solve(self, spec_path: str = None) -> dict:
        return {"code": KERNEL_CODE}