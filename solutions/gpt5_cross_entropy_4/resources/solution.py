import torch
import triton
import triton.language as tl


@triton.autotune(
    configs=[
        triton.Config({"BLOCK_N": 64}, num_warps=2, num_stages=2),
        triton.Config({"BLOCK_N": 128}, num_warps=4, num_stages=2),
        triton.Config({"BLOCK_N": 256}, num_warps=4, num_stages=2),
        triton.Config({"BLOCK_N": 512}, num_warps=8, num_stages=2),
        triton.Config({"BLOCK_N": 1024}, num_warps=8, num_stages=2),
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
    targets_stride,
    BLOCK_N: tl.constexpr,
):
    row_id = tl.program_id(0)
    if row_id >= M:
        return

    # Base pointers
    row_ptr = logits_ptr + row_id * stride_m

    # Prepare iteration across columns
    offs_n = tl.arange(0, BLOCK_N)

    # First pass: compute row-wise max for numerical stability
    x_ptrs = row_ptr + offs_n * stride_n
    row_max = tl.full([1], -float("inf"), dtype=tl.float32)
    for start_n in range(0, N, BLOCK_N):
        mask = offs_n + start_n < N
        x = tl.load(x_ptrs, mask=mask, other=-float("inf"))
        x = x.to(tl.float32)
        tile_max = tl.max(x, axis=0)
        row_max = tl.maximum(row_max, tile_max)
        x_ptrs += BLOCK_N * stride_n

    # Load target index and target logit
    t = tl.load(targets_ptr + row_id * targets_stride).to(tl.int64)
    tgt_logit = tl.load(row_ptr + t * stride_n).to(tl.float32)

    # Second pass: compute sum(exp(x - row_max))
    x_ptrs = row_ptr + offs_n * stride_n
    sum_exp = tl.zeros([1], dtype=tl.float32)
    for start_n in range(0, N, BLOCK_N):
        mask = offs_n + start_n < N
        x = tl.load(x_ptrs, mask=mask, other=-float("inf"))
        x = x.to(tl.float32) - row_max
        expx = tl.exp(x)
        sum_exp += tl.sum(expx, axis=0)
        x_ptrs += BLOCK_N * stride_n

    lse = row_max + tl.log(sum_exp)
    loss = lse - tgt_logit
    tl.store(losses_ptr + row_id, loss)


def cross_entropy(logits: torch.Tensor, targets: torch.Tensor) -> torch.Tensor:
    if logits.dim() != 2:
        raise ValueError("logits must be a 2D tensor of shape (M, N)")
    if targets.dim() != 1 or targets.shape[0] != logits.shape[0]:
        raise ValueError("targets must be a 1D tensor with length equal to logits.shape[0]")
    if not logits.is_cuda or not targets.is_cuda:
        # Fallback to PyTorch if tensors are not on CUDA
        with torch.no_grad():
            lse = torch.logsumexp(logits.float(), dim=1)
            tgt = logits[torch.arange(logits.shape[0], device=logits.device), targets]
            return (lse - tgt).float()

    M, N = logits.shape
    if M == 0 or N == 0:
        return torch.empty((M,), dtype=torch.float32, device=logits.device)

    logits_contig = logits
    targets_contig = targets

    # Ensure dtype compatibility; computations are in float32
    out = torch.empty((M,), dtype=torch.float32, device=logits.device)

    stride_m = logits_contig.stride(0)
    stride_n = logits_contig.stride(1)
    targets_stride = targets_contig.stride(0)

    grid = (triton.cdiv(M, 1),)

    _cross_entropy_kernel[grid](
        logits_contig,
        targets_contig,
        out,
        M,
        N,
        stride_m,
        stride_n,
        targets_stride,
    )
    return out


class Solution:
    def solve(self, spec_path: str = None) -> dict:
        code = '''
import torch
import triton
import triton.language as tl


@triton.autotune(
    configs=[
        triton.Config({"BLOCK_N": 64}, num_warps=2, num_stages=2),
        triton.Config({"BLOCK_N": 128}, num_warps=4, num_stages=2),
        triton.Config({"BLOCK_N": 256}, num_warps=4, num_stages=2),
        triton.Config({"BLOCK_N": 512}, num_warps=8, num_stages=2),
        triton.Config({"BLOCK_N": 1024}, num_warps=8, num_stages=2),
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
    targets_stride,
    BLOCK_N: tl.constexpr,
):
    row_id = tl.program_id(0)
    if row_id >= M:
        return

    # Base pointers
    row_ptr = logits_ptr + row_id * stride_m

    # Prepare iteration across columns
    offs_n = tl.arange(0, BLOCK_N)

    # First pass: compute row-wise max for numerical stability
    x_ptrs = row_ptr + offs_n * stride_n
    row_max = tl.full([1], -float("inf"), dtype=tl.float32)
    for start_n in range(0, N, BLOCK_N):
        mask = offs_n + start_n < N
        x = tl.load(x_ptrs, mask=mask, other=-float("inf"))
        x = x.to(tl.float32)
        tile_max = tl.max(x, axis=0)
        row_max = tl.maximum(row_max, tile_max)
        x_ptrs += BLOCK_N * stride_n

    # Load target index and target logit
    t = tl.load(targets_ptr + row_id * targets_stride).to(tl.int64)
    tgt_logit = tl.load(row_ptr + t * stride_n).to(tl.float32)

    # Second pass: compute sum(exp(x - row_max))
    x_ptrs = row_ptr + offs_n * stride_n
    sum_exp = tl.zeros([1], dtype=tl.float32)
    for start_n in range(0, N, BLOCK_N):
        mask = offs_n + start_n < N
        x = tl.load(x_ptrs, mask=mask, other=-float("inf"))
        x = x.to(tl.float32) - row_max
        expx = tl.exp(x)
        sum_exp += tl.sum(expx, axis=0)
        x_ptrs += BLOCK_N * stride_n

    lse = row_max + tl.log(sum_exp)
    loss = lse - tgt_logit
    tl.store(losses_ptr + row_id, loss)


def cross_entropy(logits: torch.Tensor, targets: torch.Tensor) -> torch.Tensor:
    if logits.dim() != 2:
        raise ValueError("logits must be a 2D tensor of shape (M, N)")
    if targets.dim() != 1 or targets.shape[0] != logits.shape[0]:
        raise ValueError("targets must be a 1D tensor with length equal to logits.shape[0]")
    if not logits.is_cuda or not targets.is_cuda:
        # Fallback to PyTorch if tensors are not on CUDA
        with torch.no_grad():
            lse = torch.logsumexp(logits.float(), dim=1)
            tgt = logits[torch.arange(logits.shape[0], device=logits.device), targets]
            return (lse - tgt).float()

    M, N = logits.shape
    if M == 0 or N == 0:
        return torch.empty((M,), dtype=torch.float32, device=logits.device)

    logits_contig = logits
    targets_contig = targets

    # Ensure dtype compatibility; computations are in float32
    out = torch.empty((M,), dtype=torch.float32, device=logits.device)

    stride_m = logits_contig.stride(0)
    stride_n = logits_contig.stride(1)
    targets_stride = targets_contig.stride(0)

    grid = (triton.cdiv(M, 1),)

    _cross_entropy_kernel[grid](
        logits_contig,
        targets_contig,
        out,
        M,
        N,
        stride_m,
        stride_n,
        targets_stride,
    )
    return out
'''
        return {"code": code}
