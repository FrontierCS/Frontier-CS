import torch
import triton
import triton.language as tl


@triton.autotune(
    configs=[
        triton.Config({"BLOCK_SIZE": 128}, num_warps=4, num_stages=2),
        triton.Config({"BLOCK_SIZE": 256}, num_warps=4, num_stages=2),
        triton.Config({"BLOCK_SIZE": 512}, num_warps=8, num_stages=2),
        triton.Config({"BLOCK_SIZE": 1024}, num_warps=8, num_stages=2),
        triton.Config({"BLOCK_SIZE": 2048}, num_warps=8, num_stages=2),
    ],
    key=["N"],
)
@triton.jit
def _cross_entropy_kernel(
    logits_ptr,
    targets_ptr,
    losses_ptr,
    M,
    N,
    stride_m,
    stride_n,
    t_stride,
    BLOCK_SIZE: tl.constexpr,
):
    pid = tl.program_id(0)
    if pid >= M:
        return

    # Pointers to the start of the row
    row_ptr = logits_ptr + pid * stride_m

    # Load target index for this row
    t = tl.load(targets_ptr + pid * t_stride)
    t = t.to(tl.int64)

    # Running log-sum-exp with online update
    m = tl.full((), -float("inf"), tl.float32)
    s = tl.zeros((), dtype=tl.float32)
    val_t = tl.zeros((), dtype=tl.float32)

    offs = tl.arange(0, BLOCK_SIZE)
    start = 0
    while start < N:
        cols = start + offs
        mask = cols < N

        x = tl.load(row_ptr + cols * stride_n, mask=mask, other=-float("inf"))
        x_f32 = x.to(tl.float32)

        # Online log-sum-exp update
        tile_max = tl.max(x_f32, axis=0)
        m_new = tl.maximum(m, tile_max)
        s = s * tl.exp(m - m_new) + tl.sum(tl.exp(x_f32 - m_new), axis=0)
        m = m_new

        # Accumulate target logit
        tmask = cols.to(tl.int64) == t
        val_t += tl.sum(tl.where(tmask, x_f32, 0.0), axis=0)

        start += BLOCK_SIZE

    loss = (m + tl.log(s)) - val_t
    tl.store(losses_ptr + pid, loss)


def cross_entropy(logits: torch.Tensor, targets: torch.Tensor) -> torch.Tensor:
    if logits.ndim != 2:
        raise ValueError("logits must be a 2D tensor of shape (M, N)")
    if targets.ndim != 1:
        raise ValueError("targets must be a 1D tensor of shape (M,)")

    if not logits.is_cuda:
        raise ValueError("logits must be on CUDA device")
    device = logits.device

    M, N = logits.shape
    if targets.shape[0] != M:
        raise ValueError("targets length must match batch size M")

    # Ensure targets are on device and int64
    if targets.device != device or targets.dtype != torch.long:
        targets = targets.to(device=device, dtype=torch.long, non_blocking=True)

    # Output tensor
    out = torch.empty(M, device=device, dtype=torch.float32)

    stride_m = logits.stride(0)
    stride_n = logits.stride(1)
    t_stride = targets.stride(0)

    grid = (M,)
    _cross_entropy_kernel[grid](
        logits,
        targets,
        out,
        M,
        N,
        stride_m,
        stride_n,
        t_stride,
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
        triton.Config({"BLOCK_SIZE": 128}, num_warps=4, num_stages=2),
        triton.Config({"BLOCK_SIZE": 256}, num_warps=4, num_stages=2),
        triton.Config({"BLOCK_SIZE": 512}, num_warps=8, num_stages=2),
        triton.Config({"BLOCK_SIZE": 1024}, num_warps=8, num_stages=2),
        triton.Config({"BLOCK_SIZE": 2048}, num_warps=8, num_stages=2),
    ],
    key=["N"],
)
@triton.jit
def _cross_entropy_kernel(
    logits_ptr,
    targets_ptr,
    losses_ptr,
    M,
    N,
    stride_m,
    stride_n,
    t_stride,
    BLOCK_SIZE: tl.constexpr,
):
    pid = tl.program_id(0)
    if pid >= M:
        return

    row_ptr = logits_ptr + pid * stride_m

    t = tl.load(targets_ptr + pid * t_stride)
    t = t.to(tl.int64)

    m = tl.full((), -float("inf"), tl.float32)
    s = tl.zeros((), dtype=tl.float32)
    val_t = tl.zeros((), dtype=tl.float32)

    offs = tl.arange(0, BLOCK_SIZE)
    start = 0
    while start < N:
        cols = start + offs
        mask = cols < N

        x = tl.load(row_ptr + cols * stride_n, mask=mask, other=-float("inf"))
        x_f32 = x.to(tl.float32)

        tile_max = tl.max(x_f32, axis=0)
        m_new = tl.maximum(m, tile_max)
        s = s * tl.exp(m - m_new) + tl.sum(tl.exp(x_f32 - m_new), axis=0)
        m = m_new

        tmask = cols.to(tl.int64) == t
        val_t += tl.sum(tl.where(tmask, x_f32, 0.0), axis=0)

        start += BLOCK_SIZE

    loss = (m + tl.log(s)) - val_t
    tl.store(losses_ptr + pid, loss)


def cross_entropy(logits: torch.Tensor, targets: torch.Tensor) -> torch.Tensor:
    if logits.ndim != 2:
        raise ValueError("logits must be a 2D tensor of shape (M, N)")
    if targets.ndim != 1:
        raise ValueError("targets must be a 1D tensor of shape (M,)")

    if not logits.is_cuda:
        raise ValueError("logits must be on CUDA device")
    device = logits.device

    M, N = logits.shape
    if targets.shape[0] != M:
        raise ValueError("targets length must match batch size M")

    if targets.device != device or targets.dtype != torch.long:
        targets = targets.to(device=device, dtype=torch.long, non_blocking=True)

    out = torch.empty(M, device=device, dtype=torch.float32)

    stride_m = logits.stride(0)
    stride_n = logits.stride(1)
    t_stride = targets.stride(0)

    grid = (M,)
    _cross_entropy_kernel[grid](
        logits,
        targets,
        out,
        M,
        N,
        stride_m,
        stride_n,
        t_stride,
    )
    return out
'''
        return {"code": code}
