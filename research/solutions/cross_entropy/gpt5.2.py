import os
import sys
import inspect
import textwrap
import torch

try:
    import triton
    import triton.language as tl
except Exception:
    triton = None
    tl = None


if triton is not None:

    @triton.autotune(
        configs=[
            triton.Config({"BLOCK_N": 512}, num_warps=4, num_stages=4),
            triton.Config({"BLOCK_N": 1024}, num_warps=8, num_stages=4),
            triton.Config({"BLOCK_N": 2048}, num_warps=8, num_stages=3),
        ],
        key=["N"],
    )
    @triton.jit
    def _cross_entropy_kernel(
        logits_ptr,
        targets_ptr,
        out_ptr,
        stride_m,
        stride_n,
        stride_t,
        M,
        N: tl.constexpr,
        BLOCK_N: tl.constexpr,
    ):
        pid = tl.program_id(0)
        in_bounds = pid < M

        row_ptr = logits_ptr + pid * stride_m
        tgt = tl.load(targets_ptr + pid * stride_t, mask=in_bounds, other=0).to(tl.int32)

        tgt_logit = tl.load(row_ptr + tgt * stride_n, mask=in_bounds & (tgt >= 0) & (tgt < N), other=-float("inf")).to(
            tl.float32
        )

        m = tl.full((), -float("inf"), tl.float32)
        s = tl.full((), 0.0, tl.float32)

        for start in tl.static_range(0, N, BLOCK_N):
            offs = start + tl.arange(0, BLOCK_N)
            mask = in_bounds & (offs < N)
            x = tl.load(row_ptr + offs * stride_n, mask=mask, other=-float("inf")).to(tl.float32)

            bmax = tl.max(x, axis=0)
            bx = tl.exp(x - bmax)
            bsum = tl.sum(bx, axis=0)

            new_m = tl.maximum(m, bmax)
            s = s * tl.exp(m - new_m) + bsum * tl.exp(bmax - new_m)
            m = new_m

        lse = tl.log(s) + m
        loss = lse - tgt_logit
        tl.store(out_ptr + pid, loss, mask=in_bounds)


def _cross_entropy_torch(logits: torch.Tensor, targets: torch.Tensor) -> torch.Tensor:
    logits_f = logits.float()
    maxv = logits_f.max(dim=1).values
    lse = torch.log(torch.sum(torch.exp(logits_f - maxv[:, None]), dim=1)) + maxv
    tgt = targets.to(torch.long)
    idx = torch.arange(logits.shape[0], device=logits.device)
    tgt_logit = logits_f[idx, tgt]
    return (lse - tgt_logit).to(torch.float32)


def cross_entropy(logits: torch.Tensor, targets: torch.Tensor) -> torch.Tensor:
    if logits.ndim != 2:
        raise ValueError(f"logits must be 2D (M, N), got shape={tuple(logits.shape)}")
    if targets.ndim != 1:
        raise ValueError(f"targets must be 1D (M,), got shape={tuple(targets.shape)}")
    if logits.shape[0] != targets.shape[0]:
        raise ValueError(f"batch mismatch: logits.shape[0]={logits.shape[0]} targets.shape[0]={targets.shape[0]}")

    if (triton is None) or (not logits.is_cuda) or (not targets.is_cuda):
        return _cross_entropy_torch(logits, targets)

    M, N = logits.shape
    out = torch.empty((M,), device=logits.device, dtype=torch.float32)

    stride_m, stride_n = logits.stride()
    stride_t = targets.stride(0)

    grid = (triton.cdiv(M, 1),)
    _cross_entropy_kernel[grid](
        logits,
        targets,
        out,
        stride_m,
        stride_n,
        stride_t,
        M,
        N=N,
    )
    return out


class Solution:
    def solve(self, spec_path: str = None) -> dict:
        try:
            path = __file__
            if path and os.path.exists(path):
                with open(path, "r", encoding="utf-8") as f:
                    return {"code": f.read()}
        except Exception:
            pass
        try:
            src = inspect.getsource(sys.modules[__name__])
            return {"code": textwrap.dedent(src)}
        except Exception:
            return {"code": ""}