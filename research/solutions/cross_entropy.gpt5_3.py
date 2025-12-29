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
def _cross_entropy_kernel(
    logits_ptr,
    targets_ptr,
    output_ptr,
    M: tl.int32,
    N: tl.int32,
    stride_m: tl.int32,
    stride_n: tl.int32,
    stride_t: tl.int32,
    BLOCK_N: tl.constexpr,
):
    row_id = tl.program_id(0)
    if row_id >= M:
        return

    # Load target index for this row
    t_index = tl.load(targets_ptr + row_id * stride_t).to(tl.int64)

    row_ptr = logits_ptr + row_id * stride_m

    # Load target logit directly
    target_val = tl.load(row_ptr + t_index * stride_n).to(tl.float32)

    # Online log-sum-exp across columns
    m = tl.full([1], -float("inf"), dtype=tl.float32)
    s = tl.zeros([1], dtype=tl.float32)

    offs = tl.arange(0, BLOCK_N)
    for start in range(0, N, BLOCK_N):
        n = start + offs
        mask = n < N
        x = tl.load(row_ptr + n * stride_n, mask=mask, other=-float("inf")).to(tl.float32)
        bmax = tl.max(x, axis=0)
        bsum = tl.sum(tl.exp(x - bmax), axis=0)

        m_new = tl.maximum(m, bmax)
        s = s * tl.exp(m - m_new) + bsum * tl.exp(bmax - m_new)
        m = m_new

    lse = m + tl.log(s)
    loss = lse - target_val
    tl.store(output_ptr + row_id, loss)


def cross_entropy(logits: torch.Tensor, targets: torch.Tensor) -> torch.Tensor:
    if not isinstance(logits, torch.Tensor) or not isinstance(targets, torch.Tensor):
        raise TypeError("logits and targets must be torch.Tensors")
    if logits.ndim != 2:
        raise ValueError("logits must be 2D (M, N)")
    if targets.ndim != 1:
        raise ValueError("targets must be 1D (M,)")
    if logits.shape[0] != targets.shape[0]:
        raise ValueError("Batch size mismatch between logits and targets")

    M, N = logits.shape
    if M == 0 or N == 0:
        return torch.empty((M,), dtype=torch.float32, device=logits.device)

    if not logits.is_cuda or not targets.is_cuda or not torch.cuda.is_available():
        logits_f32 = logits.to(torch.float32)
        t = targets.to(torch.long)
        lse = torch.logsumexp(logits_f32, dim=1)
        tgt = logits_f32.gather(1, t.view(-1, 1)).squeeze(1)
        return lse - tgt

    if targets.dtype != torch.long:
        targets = targets.to(torch.long)

    out = torch.empty((M,), dtype=torch.float32, device=logits.device)

    stride_m, stride_n = logits.stride()
    stride_t = targets.stride(0)

    grid = (M,)

    _cross_entropy_kernel[grid](
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
        code = r'''
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
def _cross_entropy_kernel(
    logits_ptr,
    targets_ptr,
    output_ptr,
    M: tl.int32,
    N: tl.int32,
    stride_m: tl.int32,
    stride_n: tl.int32,
    stride_t: tl.int32,
    BLOCK_N: tl.constexpr,
):
    row_id = tl.program_id(0)
    if row_id >= M:
        return

    t_index = tl.load(targets_ptr + row_id * stride_t).to(tl.int64)
    row_ptr = logits_ptr + row_id * stride_m
    target_val = tl.load(row_ptr + t_index * stride_n).to(tl.float32)

    m = tl.full([1], -float("inf"), dtype=tl.float32)
    s = tl.zeros([1], dtype=tl.float32)

    offs = tl.arange(0, BLOCK_N)
    for start in range(0, N, BLOCK_N):
        n = start + offs
        mask = n < N
        x = tl.load(row_ptr + n * stride_n, mask=mask, other=-float("inf")).to(tl.float32)
        bmax = tl.max(x, axis=0)
        bsum = tl.sum(tl.exp(x - bmax), axis=0)

        m_new = tl.maximum(m, bmax)
        s = s * tl.exp(m - m_new) + bsum * tl.exp(bmax - m_new)
        m = m_new

    lse = m + tl.log(s)
    loss = lse - target_val
    tl.store(output_ptr + row_id, loss)


def cross_entropy(logits: torch.Tensor, targets: torch.Tensor) -> torch.Tensor:
    if not isinstance(logits, torch.Tensor) or not isinstance(targets, torch.Tensor):
        raise TypeError("logits and targets must be torch.Tensors")
    if logits.ndim != 2:
        raise ValueError("logits must be 2D (M, N)")
    if targets.ndim != 1:
        raise ValueError("targets must be 1D (M,)")
    if logits.shape[0] != targets.shape[0]:
        raise ValueError("Batch size mismatch between logits and targets")

    M, N = logits.shape
    if M == 0 or N == 0:
        return torch.empty((M,), dtype=torch.float32, device=logits.device)

    if not logits.is_cuda or not targets.is_cuda or not torch.cuda.is_available():
        logits_f32 = logits.to(torch.float32)
        t = targets.to(torch.long)
        lse = torch.logsumexp(logits_f32, dim=1)
        tgt = logits_f32.gather(1, t.view(-1, 1)).squeeze(1)
        return lse - tgt

    if targets.dtype != torch.long:
        targets = targets.to(torch.long)

    out = torch.empty((M,), dtype=torch.float32, device=logits.device)

    stride_m, stride_n = logits.stride()
    stride_t = targets.stride(0)

    grid = (M,)

    _cross_entropy_kernel[grid](
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
        return {"code": code}