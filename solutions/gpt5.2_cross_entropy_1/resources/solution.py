import os
import torch
import triton
import triton.language as tl


@triton.autotune(
    configs=[
        triton.Config({"BLOCK_N": 512}, num_warps=4, num_stages=3),
        triton.Config({"BLOCK_N": 1024}, num_warps=4, num_stages=3),
        triton.Config({"BLOCK_N": 1024}, num_warps=8, num_stages=2),
        triton.Config({"BLOCK_N": 2048}, num_warps=8, num_stages=2),
    ],
    key=["N"],
)
@triton.jit
def _cross_entropy_kernel(
    logits_ptr,
    targets_ptr,
    out_ptr,
    stride_lm,
    stride_ln,
    stride_out,
    M: tl.constexpr,
    N: tl.constexpr,
    BLOCK_N: tl.constexpr,
):
    pid = tl.program_id(0)
    row = pid
    row_in_bounds = row < M

    row_ptr = logits_ptr + row * stride_lm

    tgt = tl.load(targets_ptr + row, mask=row_in_bounds, other=0).to(tl.int32)
    tgt = tl.maximum(tgt, 0)
    tgt = tl.minimum(tgt, N - 1)
    tgt_logit = tl.load(row_ptr + tgt * stride_ln, mask=row_in_bounds, other=-float("inf")).to(tl.float32)

    offs = tl.arange(0, BLOCK_N)
    m = tl.full((), -float("inf"), tl.float32)
    s = tl.zeros((), tl.float32)

    LOG2E = 1.4426950408889634
    for start in range(0, N, BLOCK_N):
        idx = start + offs
        x = tl.load(row_ptr + idx * stride_ln, mask=row_in_bounds & (idx < N), other=-float("inf")).to(tl.float32)
        m_chunk = tl.max(x, axis=0)
        m_new = tl.maximum(m, m_chunk)
        s = s * tl.math.exp2((m - m_new) * LOG2E) + tl.sum(tl.math.exp2((x - m_new) * LOG2E), axis=0)
        m = m_new

    LN2 = 0.6931471805599453
    lse = tl.math.log2(s) * LN2 + m
    loss = lse - tgt_logit
    tl.store(out_ptr + row * stride_out, loss, mask=row_in_bounds)


def cross_entropy(logits: torch.Tensor, targets: torch.Tensor) -> torch.Tensor:
    if not logits.is_cuda:
        logits_f = logits.float()
        m = torch.logsumexp(logits_f, dim=1)
        t = targets.to(dtype=torch.long)
        gathered = logits_f[torch.arange(logits_f.shape[0], device=logits_f.device), t]
        return (m - gathered).to(torch.float32)

    assert logits.ndim == 2
    assert targets.ndim == 1
    M, N = logits.shape
    assert targets.shape[0] == M

    if targets.dtype != torch.int64:
        targets = targets.to(torch.int64)

    out = torch.empty((M,), device=logits.device, dtype=torch.float32)
    grid = (M,)
    _cross_entropy_kernel[grid](
        logits,
        targets,
        out,
        logits.stride(0),
        logits.stride(1),
        out.stride(0),
        M=M,
        N=N,
    )
    return out


class Solution:
    def solve(self, spec_path: str = None) -> dict:
        return {"program_path": os.path.abspath(__file__)}
