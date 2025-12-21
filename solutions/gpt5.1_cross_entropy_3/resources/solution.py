import os
import torch
import triton
import triton.language as tl


@triton.autotune(
    configs=[
        triton.Config({'BLOCK_N': 64}, num_warps=2, num_stages=2),
        triton.Config({'BLOCK_N': 128}, num_warps=4, num_stages=2),
        triton.Config({'BLOCK_N': 256}, num_warps=4, num_stages=3),
        triton.Config({'BLOCK_N': 512}, num_warps=8, num_stages=3),
        triton.Config({'BLOCK_N': 1024}, num_warps=8, num_stages=4),
    ],
    key=['N'],
)
@triton.jit
def _cross_entropy_kernel(
    logits_ptr,        # *f16 / *bf16 / *f32
    targets_ptr,       # *i64
    loss_ptr,          # *f32
    M,                 # number of rows
    stride_logits_m,
    stride_logits_n,
    stride_targets_m,
    stride_loss_m,
    N: tl.constexpr,   # number of classes (compile-time for better perf)
    BLOCK_N: tl.constexpr,
):
    row_id = tl.program_id(0)

    # Pointers to this row
    row_logits_ptr = logits_ptr + row_id * stride_logits_m

    # Load target index for this row
    target_idx = tl.load(targets_ptr + row_id * stride_targets_m)
    target_idx = target_idx.to(tl.int32)

    # First pass: compute max logit for numerical stability
    offs_n = tl.arange(0, BLOCK_N)
    row_max = -float('inf')
    for start_n in range(0, N, BLOCK_N):
        n_idx = start_n + offs_n
        mask = n_idx < N
        logits = tl.load(
            row_logits_ptr + n_idx * stride_logits_n,
            mask=mask,
            other=-float('inf'),
        )
        logits = logits.to(tl.float32)
        cur_max = tl.max(logits, axis=0)
        row_max = tl.maximum(row_max, cur_max)

    # Second pass: compute sum(exp(logits - max))
    row_sum = 0.0
    for start_n in range(0, N, BLOCK_N):
        n_idx = start_n + offs_n
        mask = n_idx < N
        logits = tl.load(
            row_logits_ptr + n_idx * stride_logits_n,
            mask=mask,
            other=-float('inf'),
        )
        logits = logits.to(tl.float32)
        logits = logits - row_max
        exp_logits = tl.exp(logits)
        row_sum += tl.sum(exp_logits, axis=0)

    # Load logit at target index
    target_logit = tl.load(row_logits_ptr + target_idx * stride_logits_n)
    target_logit = target_logit.to(tl.float32)

    # Compute loss: -log softmax at target = logsumexp - target_logit
    loss_val = (tl.log(row_sum) + row_max) - target_logit

    # Store loss
    tl.store(loss_ptr + row_id * stride_loss_m, loss_val)


def cross_entropy(logits: torch.Tensor, targets: torch.Tensor) -> torch.Tensor:
    """
    Cross entropy loss computation using Triton.

    Args:
        logits: Tensor of shape (M, N) on CUDA
        targets: Tensor of shape (M,) with int64 class indices on same device

    Returns:
        Tensor of shape (M,) containing per-sample negative log-likelihood loss (float32)
    """
    if logits.ndim != 2:
        raise ValueError(f"logits must be 2D (M, N), got shape {tuple(logits.shape)}")
    if targets.ndim != 1:
        raise ValueError(f"targets must be 1D (M,), got shape {tuple(targets.shape)}")
    if logits.size(0) != targets.size(0):
        raise ValueError("logits and targets must have matching first dimension")

    M, N = logits.shape

    # Handle empty input early
    if M == 0:
        return logits.new_empty((0,), dtype=torch.float32)

    # Fallback for non-CUDA tensors or if Triton is not usable
    if not logits.is_cuda or not targets.is_cuda:
        log_probs = torch.nn.functional.log_softmax(logits.float(), dim=-1)
        arange_m = torch.arange(M, device=logits.device)
        return -log_probs[arange_m, targets]

    # Ensure dtype compatibility: computations in float32, but we support f16/bf16/f32 inputs
    logits_tensor = logits
    targets_tensor = targets

    loss = torch.empty(M, device=logits_tensor.device, dtype=torch.float32)

    stride_logits_m, stride_logits_n = logits_tensor.stride()
    stride_targets_m = targets_tensor.stride(0)
    stride_loss_m = loss.stride(0)

    grid = lambda META: (M,)

    _cross_entropy_kernel[grid](
        logits_tensor,
        targets_tensor,
        loss,
        M,
        stride_logits_m,
        stride_logits_n,
        stride_targets_m,
        stride_loss_m,
        N=N,
    )

    return loss


class Solution:
    def solve(self, spec_path: str = None) -> dict:
        # Provide this very file as the program path so the evaluator can
        # import `cross_entropy` from it.
        return {"program_path": os.path.abspath(__file__)}
