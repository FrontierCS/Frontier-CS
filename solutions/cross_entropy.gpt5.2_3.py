import os
import math
import torch
import triton
import triton.language as tl


@triton.autotune(
    configs=[
        triton.Config({"BLOCK_N": 512}, num_warps=4, num_stages=3),
        triton.Config({"BLOCK_N": 1024}, num_warps=8, num_stages=3),
        triton.Config({"BLOCK_N": 2048}, num_warps=8, num_stages=2),
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
    if row >= M:
        return

    row_ptr = logits_ptr + row * stride_m
    t = tl.load(targets_ptr + row).to(tl.int32)
    logit_t = tl.load(row_ptr + t * stride_n, mask=t < N, other=-float("inf")).to(tl.float32)

    m = tl.full((), -float("inf"), tl.float32)
    s = tl.full((), 0.0, tl.float32)

    offs = tl.arange(0, BLOCK_N)
    for start in tl.static_range(0, N, BLOCK_N):
        cols = start + offs
        x = tl.load(row_ptr + cols * stride_n, mask=cols < N, other=-float("inf")).to(tl.float32)

        block_max = tl.max(x, axis=0)
        new_m = tl.maximum(m, block_max)
        s = s * tl.exp(m - new_m) + tl.sum(tl.exp(x - new_m), axis=0)
        m = new_m

    lse = m + tl.log(s)
    loss = lse - logit_t
    tl.store(out_ptr + row, loss)


def cross_entropy(logits: torch.Tensor, targets: torch.Tensor) -> torch.Tensor:
    if not logits.is_cuda or not targets.is_cuda:
        raise ValueError("cross_entropy: logits and targets must be CUDA tensors")
    if logits.ndim != 2:
        raise ValueError("cross_entropy: logits must be 2D (M, N)")
    if targets.ndim != 1:
        raise ValueError("cross_entropy: targets must be 1D (M,)")
    M, N = logits.shape
    if targets.shape[0] != M:
        raise ValueError("cross_entropy: targets.shape[0] must equal logits.shape[0]")
    if targets.dtype != torch.int64 and targets.dtype != torch.int32:
        targets = targets.to(torch.int64)

    out = torch.empty((M,), device=logits.device, dtype=torch.float32)

    stride_m = logits.stride(0)
    stride_n = logits.stride(1)

    grid = (M,)
    _cross_entropy_kernel[grid](
        logits,
        targets,
        out,
        stride_m=stride_m,
        stride_n=stride_n,
        M=M,
        N=N,
    )
    return out


class Solution:
    def solve(self, spec_path: str = None) -> dict:
        return {"program_path": os.path.abspath(__file__)}
