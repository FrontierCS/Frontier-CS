import os
import torch
import triton
import triton.language as tl


@triton.autotune(
    configs=[
        triton.Config({"BLOCK_N": 128, "TILES_PER_ROW": 64}, num_warps=4, num_stages=2),
        triton.Config({"BLOCK_N": 256, "TILES_PER_ROW": 32}, num_warps=4, num_stages=2),
        triton.Config({"BLOCK_N": 512, "TILES_PER_ROW": 16}, num_warps=8, num_stages=2),
        triton.Config({"BLOCK_N": 1024, "TILES_PER_ROW": 8}, num_warps=8, num_stages=2),
    ],
    key=["N"],
)
@triton.jit
def _cross_entropy_kernel(
    logits_ptr,
    targets_ptr,
    output_ptr,
    M,
    N,
    stride_m,
    stride_n,
    BLOCK_N: tl.constexpr,
    TILES_PER_ROW: tl.constexpr,
):
    row = tl.program_id(0)
    if row >= M:
        return

    row_offset = row * stride_m

    # First pass: compute per-row maximum for numerical stability
    row_max = -float("inf")
    for tile in tl.static_range(0, TILES_PER_ROW):
        col_start = tile * BLOCK_N
        offs = col_start + tl.arange(0, BLOCK_N)
        mask = offs < N
        ptrs = logits_ptr + row_offset + offs * stride_n
        x = tl.load(ptrs, mask=mask, other=-float("inf"))
        x = x.to(tl.float32)
        tile_max = tl.max(x, axis=0)
        row_max = tl.maximum(row_max, tile_max)

    # Second pass: compute sum(exp(logits - row_max))
    exp_sum = 0.0
    for tile in tl.static_range(0, TILES_PER_ROW):
        col_start = tile * BLOCK_N
        offs = col_start + tl.arange(0, BLOCK_N)
        mask = offs < N
        ptrs = logits_ptr + row_offset + offs * stride_n
        x = tl.load(ptrs, mask=mask, other=-float("inf"))
        x = x.to(tl.float32)
        exp_block = tl.exp(x - row_max)
        exp_sum += tl.sum(exp_block, axis=0)

    # Logit of the target class
    target_idx = tl.load(targets_ptr + row)
    target_idx = target_idx.to(tl.int32)
    target_ptr = logits_ptr + row_offset + target_idx * stride_n
    logit_target = tl.load(target_ptr)
    logit_target = logit_target.to(tl.float32)

    logsumexp = row_max + tl.log(exp_sum)
    loss = logsumexp - logit_target

    tl.store(output_ptr + row, loss)


def cross_entropy(logits: torch.Tensor, targets: torch.Tensor) -> torch.Tensor:
    """
    Cross entropy loss computation.

    Args:
        logits: Tensor of shape (M, N) - logits for M samples and N classes
        targets: Tensor of shape (M,) - target class indices (int64)

    Returns:
        Tensor of shape (M,) - negative log-likelihood loss for each sample
    """
    if logits.ndim != 2:
        raise ValueError(f"logits must be 2D (M, N), got shape {logits.shape}")
    if targets.ndim != 1:
        raise ValueError(f"targets must be 1D (M,), got shape {targets.shape}")
    if logits.shape[0] != targets.shape[0]:
        raise ValueError(
            f"Batch size mismatch: logits.shape[0]={logits.shape[0]}, targets.shape[0]={targets.shape[0]}"
        )
    if not logits.is_cuda or not targets.is_cuda:
        raise ValueError("Both logits and targets must be CUDA tensors")

    M, N = logits.shape
    stride_m, stride_n = logits.stride()

    # Ensure targets are of integer type
    if targets.dtype != torch.long:
        targets_tensor = targets.to(torch.long)
    else:
        targets_tensor = targets

    output = torch.empty(M, device=logits.device, dtype=torch.float32)

    grid = (M,)
    _cross_entropy_kernel[grid](
        logits,
        targets_tensor,
        output,
        M,
        N,
        stride_m,
        stride_n,
    )

    return output


class Solution:
    def solve(self, spec_path: str = None) -> dict:
        return {"program_path": os.path.abspath(__file__)}