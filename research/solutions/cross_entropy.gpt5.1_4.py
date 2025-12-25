import torch
import triton
import triton.language as tl


@triton.autotune(
    configs=[
        triton.Config({"BLOCK_SIZE": 128, "MAX_TILES": 64}, num_warps=2),
        triton.Config({"BLOCK_SIZE": 256, "MAX_TILES": 64}, num_warps=4),
        triton.Config({"BLOCK_SIZE": 512, "MAX_TILES": 32}, num_warps=4),
        triton.Config({"BLOCK_SIZE": 1024, "MAX_TILES": 16}, num_warps=8),
    ],
    key=["N"],
)
@triton.jit
def _cross_entropy_kernel(
    logits_ptr,
    targets_ptr,
    loss_ptr,
    M,
    N,
    stride_m,
    stride_n,
    stride_targets,
    stride_loss,
    BLOCK_SIZE: tl.constexpr,
    MAX_TILES: tl.constexpr,
):
    row = tl.program_id(0)
    if row >= M:
        return

    row_logits_ptr = logits_ptr + row * stride_m

    target_idx = tl.load(targets_ptr + row * stride_targets)
    target_idx = target_idx.to(tl.int32)

    offsets = tl.arange(0, BLOCK_SIZE)

    m = -float("inf")
    s = 0.0
    logit_target = 0.0

    for tile in tl.static_range(0, MAX_TILES):
        cols = tile * BLOCK_SIZE + offsets
        mask = cols < N

        x = tl.load(row_logits_ptr + cols * stride_n, mask=mask, other=-float("inf"))
        x = x.to(tl.float32)

        is_target = (cols == target_idx) & mask
        logit_target += tl.sum(tl.where(is_target, x, 0.0), axis=0)

        x_max = tl.max(x, axis=0)
        new_m = tl.maximum(m, x_max)
        s = s * tl.exp(m - new_m) + tl.sum(tl.exp(x - new_m), axis=0)
        m = new_m

    log_sum_exp = tl.log(s) + m
    loss = log_sum_exp - logit_target

    tl.store(loss_ptr + row * stride_loss, loss)


def cross_entropy(logits: torch.Tensor, targets: torch.Tensor) -> torch.Tensor:
    if logits.ndim != 2:
        raise ValueError("logits must be 2D (M, N)")
    if not logits.is_cuda:
        raise ValueError("logits must be a CUDA tensor")

    M, N = logits.shape

    if M == 0 or N == 0:
        return torch.empty((M,), device=logits.device, dtype=torch.float32)

    if logits.dtype not in (torch.float16, torch.bfloat16, torch.float32):
        logits = logits.float()

    if not targets.is_cuda or targets.device != logits.device:
        targets = targets.to(device=logits.device, non_blocking=True)
    if targets.dtype != torch.int64:
        targets = targets.long()
    if targets.ndim != 1 or targets.shape[0] != M:
        raise ValueError("targets must be 1D with length equal to batch size (M)")

    losses = torch.empty((M,), device=logits.device, dtype=torch.float32)

    stride_m, stride_n = logits.stride()
    stride_targets = targets.stride(0)
    stride_loss = losses.stride(0)

    grid = (M,)

    _cross_entropy_kernel[grid](
        logits,
        targets,
        losses,
        M,
        N,
        stride_m,
        stride_n,
        stride_targets,
        stride_loss,
    )

    return losses


class Solution:
    def solve(self, spec_path: str = None) -> dict:
        return {"program_path": __file__}
