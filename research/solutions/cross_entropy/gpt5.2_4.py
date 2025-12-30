import os
import math
import torch
import triton
import triton.language as tl


@triton.autotune(
    configs=[
        triton.Config({"BLOCK_N": 1024}, num_warps=8, num_stages=4),
        triton.Config({"BLOCK_N": 2048}, num_warps=8, num_stages=3),
        triton.Config({"BLOCK_N": 512}, num_warps=4, num_stages=4),
        triton.Config({"BLOCK_N": 256}, num_warps=4, num_stages=4),
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
    M: tl.constexpr,
    N: tl.constexpr,
    BLOCK_N: tl.constexpr,
):
    pid = tl.program_id(0)
    if pid >= M:
        return

    row_base = pid * stride_m
    offs = tl.arange(0, BLOCK_N)

    m = tl.full((1,), -float("inf"), tl.float32)
    s = tl.zeros((1,), tl.float32)

    # Online log-sum-exp across blocks
    for start in tl.static_range(0, N, BLOCK_N):
        idx = start + offs
        mask = idx < N
        x = tl.load(logits_ptr + row_base + idx * stride_n, mask=mask, other=-float("inf")).to(tl.float32)
        block_m = tl.max(x, axis=0)
        new_m = tl.maximum(m, block_m)
        s = s * tl.exp(m - new_m) + tl.sum(tl.exp(x - new_m), axis=0)
        m = new_m

    lse = tl.log(s) + m

    t = tl.load(targets_ptr + pid).to(tl.int32)
    t = tl.maximum(0, tl.minimum(t, N - 1))
    xt = tl.load(logits_ptr + row_base + t * stride_n).to(tl.float32)

    loss = lse - xt
    tl.store(out_ptr + pid, loss)


def cross_entropy(logits: torch.Tensor, targets: torch.Tensor) -> torch.Tensor:
    if not (isinstance(logits, torch.Tensor) and isinstance(targets, torch.Tensor)):
        raise TypeError("logits and targets must be torch.Tensors")
    if logits.ndim != 2:
        raise ValueError(f"logits must be 2D (M, N); got {tuple(logits.shape)}")
    if targets.ndim != 1:
        raise ValueError(f"targets must be 1D (M,); got {tuple(targets.shape)}")
    if logits.shape[0] != targets.shape[0]:
        raise ValueError(f"batch size mismatch: logits M={logits.shape[0]} targets M={targets.shape[0]}")

    if logits.numel() == 0:
        return torch.empty((logits.shape[0],), device=logits.device, dtype=torch.float32)

    if not logits.is_cuda:
        # CPU fallback (rare in this eval)
        logits_f = logits.float()
        t = targets.long()
        m = logits_f.max(dim=1).values
        lse = (logits_f - m[:, None]).exp().sum(dim=1).log() + m
        xt = logits_f.gather(1, t[:, None]).squeeze(1)
        return (lse - xt).to(torch.float32)

    if targets.dtype != torch.int64 and targets.dtype != torch.int32:
        targets = targets.to(torch.int64)
    if not targets.is_cuda:
        targets = targets.to(device=logits.device)

    M, N = logits.shape
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
        num_warps=None,
        num_stages=None,
    )
    return out


class Solution:
    def solve(self, spec_path: str = None) -> dict:
        return {"program_path": os.path.abspath(__file__)}