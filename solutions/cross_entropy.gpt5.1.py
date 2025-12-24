import os
import sys
import inspect

import torch
import triton
import triton.language as tl


@triton.autotune(
    configs=[
        triton.Config({"BLOCK_SIZE": 64}, num_warps=2),
        triton.Config({"BLOCK_SIZE": 128}, num_warps=4),
        triton.Config({"BLOCK_SIZE": 256}, num_warps=4),
        triton.Config({"BLOCK_SIZE": 512}, num_warps=8),
        triton.Config({"BLOCK_SIZE": 1024}, num_warps=8),
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
    BLOCK_SIZE: tl.constexpr,
):
    pid = tl.program_id(axis=0)
    if pid >= M:
        return

    # Base pointer for this row
    row_logits_ptr = logits_ptr + pid * stride_m

    # Load target index for this row
    tgt = tl.load(targets_ptr + pid)
    tgt = tgt.to(tl.int64)
    tgt = tgt.to(tl.int32)

    # Load logit of the target class (original value, not shifted)
    target_logit = tl.load(row_logits_ptr + tgt * stride_n).to(tl.float32)

    # Streaming log-sum-exp across the row
    offsets = tl.arange(0, BLOCK_SIZE)
    neg_inf = -float("inf")
    max_val = tl.full((), neg_inf, dtype=tl.float32)
    sum_exp = tl.zeros((), dtype=tl.float32)

    for start in range(0, N, BLOCK_SIZE):
        cols = start + offsets
        mask = cols < N
        ptrs = row_logits_ptr + cols * stride_n
        x = tl.load(ptrs, mask=mask, other=neg_inf).to(tl.float32)

        tile_max = tl.max(x, axis=0)
        x_minus_tile_max = x - tile_max
        tile_exp = tl.exp(x_minus_tile_max)
        tile_sum = tl.sum(tile_exp, axis=0)

        new_max = tl.maximum(max_val, tile_max)
        # Combine previous and current tile contributions in a numerically stable way
        sum_exp = sum_exp * tl.exp(max_val - new_max) + tile_sum * tl.exp(tile_max - new_max)
        max_val = new_max

    logsumexp = max_val + tl.log(sum_exp)
    loss = logsumexp - target_logit

    tl.store(output_ptr + pid, loss)


def cross_entropy(logits: torch.Tensor, targets: torch.Tensor) -> torch.Tensor:
    """
    Cross entropy loss computation using a Triton kernel.

    Args:
        logits: Tensor of shape (M, N) on CUDA device
        targets: Tensor of shape (M,) with int64 class indices

    Returns:
        Tensor of shape (M,) with float32 per-sample losses
    """
    if not isinstance(logits, torch.Tensor) or not isinstance(targets, torch.Tensor):
        raise TypeError("logits and targets must be torch.Tensors")

    if logits.dim() != 2:
        raise ValueError("logits must be a 2D tensor of shape (M, N)")
    if targets.dim() != 1:
        raise ValueError("targets must be a 1D tensor of shape (M,)")

    M, N = logits.shape
    if targets.shape[0] != M:
        raise ValueError("targets length must match batch size of logits (M)")

    # CPU fallback
    if logits.device.type != "cuda":
        log_probs = torch.nn.functional.log_softmax(logits, dim=-1)
        loss = -log_probs[torch.arange(M, device=targets.device), targets]
        return loss.to(torch.float32)

    if targets.device != logits.device:
        targets = targets.to(logits.device)

    logits_contig = logits  # we rely on explicit strides, no need to make contiguous
    stride_m, stride_n = logits_contig.stride()

    output = torch.empty((M,), device=logits_contig.device, dtype=torch.float32)

    grid = (M,)

    _cross_entropy_kernel[grid](
        logits_contig,
        targets,
        output,
        M,
        N,
        stride_m,
        stride_n,
    )

    return output


class Solution:
    def solve(self, spec_path: str = None) -> dict:
        # Prefer returning a file path if available
        try:
            path = os.path.abspath(__file__)
            if os.path.exists(path):
                return {"program_path": path}
        except NameError:
            pass
        # Fallback: return the current module's source code
        src = inspect.getsource(sys.modules[__name__])
        return {"code": src}
