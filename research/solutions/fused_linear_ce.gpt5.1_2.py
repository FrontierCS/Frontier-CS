import os
import torch
import triton
import triton.language as tl


@triton.jit
def _cross_entropy_kernel(
    logits_ptr,  # pointer to [M, N] float16
    bias_ptr,    # pointer to [N] float32
    targets_ptr, # pointer to [M] int64
    out_ptr,     # pointer to [M] float32
    M, N,
    stride_lm, stride_ln,
    BLOCK_N: tl.constexpr,
):
    pid_m = tl.program_id(0)
    if pid_m >= M:
        return

    # Offsets along the class dimension
    offs_n = tl.arange(0, BLOCK_N)

    # Pointer to the start of the current row in logits
    row_logits_ptr = logits_ptr + pid_m * stride_lm

    # Load target index for this row
    t = tl.load(targets_ptr + pid_m)
    t = t.to(tl.int32)

    # First pass: compute row-wise max over logits + bias
    row_max = -float("inf")
    col_start = 0
    while col_start < N:
        cols = col_start + offs_n
        mask = cols < N

        # Load logits (float16) and cast to float32
        l = tl.load(
            row_logits_ptr + cols * stride_ln,
            mask=mask,
            other=0.0,
        ).to(tl.float32)

        # Load bias (float32)
        b = tl.load(
            bias_ptr + cols,
            mask=mask,
            other=0.0,
        )

        z = l + b
        z = tl.where(mask, z, -float("inf"))
        tile_max = tl.max(z, axis=0)
        row_max = tl.maximum(row_max, tile_max)

        col_start += BLOCK_N

    # Second pass: compute sumexp and gather target logit
    sum_exp = 0.0
    logit_t = 0.0
    col_start = 0
    while col_start < N:
        cols = col_start + offs_n
        mask = cols < N

        l = tl.load(
            row_logits_ptr + cols * stride_ln,
            mask=mask,
            other=0.0,
        ).to(tl.float32)

        b = tl.load(
            bias_ptr + cols,
            mask=mask,
            other=0.0,
        )

        z = l + b
        z = tl.where(mask, z, -float("inf"))

        exp_vals = tl.exp(z - row_max)
        exp_vals = tl.where(mask, exp_vals, 0.0)
        sum_exp += tl.sum(exp_vals, axis=0)

        is_target = cols == t
        target_vals = tl.where(is_target, z, 0.0)
        logit_t += tl.sum(target_vals, axis=0)

        col_start += BLOCK_N

    # Avoid log(0)
    sum_exp = tl.maximum(sum_exp, 1e-20)
    loss = row_max + tl.log(sum_exp) - logit_t
    tl.store(out_ptr + pid_m, loss)


def fused_linear_ce(
    X: torch.Tensor, W: torch.Tensor, B: torch.Tensor, targets: torch.Tensor
) -> torch.Tensor:
    """
    Fused linear layer with cross entropy loss computation.

    Args:
        X: Input tensor of shape (M, K) - input features (float16)
        W: Weight tensor of shape (K, N) - weight matrix (float16)
        B: Bias tensor of shape (N,) - bias vector (float32)
        targets: Target tensor of shape (M,) - target class indices (int64)

    Returns:
        Output tensor of shape (M,) - negative log-likelihood loss per sample (float32)
    """
    assert X.is_cuda and W.is_cuda and B.is_cuda and targets.is_cuda
    assert X.dtype == torch.float16
    assert W.dtype == torch.float16
    assert B.dtype == torch.float32
    assert targets.dtype == torch.long

    M, K = X.shape
    K2, N = W.shape
    assert K == K2
    assert B.numel() == N
    assert targets.numel() == M

    # Use cuBLAS via torch.matmul for the linear layer
    logits = torch.matmul(X, W)  # (M, N), float16

    # Prepare output tensor
    out = torch.empty(M, device=X.device, dtype=torch.float32)

    stride_lm, stride_ln = logits.stride()

    BLOCK_N = 128
    grid = (M,)

    _cross_entropy_kernel[grid](
        logits,
        B,
        targets,
        out,
        M,
        N,
        stride_lm,
        stride_ln,
        BLOCK_N=BLOCK_N,
        num_warps=4,
        num_stages=2,
    )

    return out


class Solution:
    def solve(self, spec_path: str = None) -> dict:
        return {"program_path": os.path.abspath(__file__)}
