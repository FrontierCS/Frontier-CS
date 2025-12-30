import os
import torch
import triton
import triton.language as tl


@triton.jit
def fused_linear_ce_kernel(
    X_ptr, W_ptr, B_ptr, targets_ptr, loss_ptr,
    M, N, K,
    stride_xm, stride_xk,
    stride_wk, stride_wn,
    BLOCK_M: tl.constexpr, BLOCK_N: tl.constexpr, BLOCK_K: tl.constexpr,
):
    pid_m = tl.program_id(0)
    offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
    mask_m = offs_m < M

    # Load targets for each row (int64 -> int32)
    t = tl.load(targets_ptr + offs_m, mask=mask_m, other=0).to(tl.int32)

    # 1) Compute target logits: dot(X[m, :], W[:, t[m]]) + B[t[m]]
    target_acc = tl.zeros((BLOCK_M,), dtype=tl.float32)

    for k_start in range(0, K, BLOCK_K):
        offs_k = k_start + tl.arange(0, BLOCK_K)
        mask_k = offs_k < K

        # X block: shape (BLOCK_M, BLOCK_K)
        x_ptrs = X_ptr + offs_m[:, None] * stride_xm + offs_k[None, :] * stride_xk
        x = tl.load(
            x_ptrs,
            mask=mask_m[:, None] & mask_k[None, :],
            other=0.0,
        ).to(tl.float32)

        # W block for target column per row: shape (BLOCK_M, BLOCK_K)
        # pointer arithmetic: W[k, n] -> k * stride_wk + n * stride_wn
        w_ptrs = W_ptr + offs_k[None, :] * stride_wk + t[:, None] * stride_wn
        w = tl.load(
            w_ptrs,
            mask=mask_m[:, None] & mask_k[None, :],
            other=0.0,
        ).to(tl.float32)

        target_acc += tl.sum(x * w, axis=1)

    # Add bias for target classes
    b_t = tl.load(B_ptr + t, mask=mask_m, other=0.0)
    target_logit = target_acc + b_t

    # 2) Streaming log-sum-exp over all classes via fused matmul
    neg_inf = -1e9
    row_max = tl.full((BLOCK_M,), neg_inf, dtype=tl.float32)
    row_lse = tl.zeros((BLOCK_M,), dtype=tl.float32)

    for n_start in range(0, N, BLOCK_N):
        offs_n = n_start + tl.arange(0, BLOCK_N)
        mask_n = offs_n < N

        # Tile of logits: (BLOCK_M, BLOCK_N)
        logits = tl.zeros((BLOCK_M, BLOCK_N), dtype=tl.float32)

        # Matmul over K dimension
        for k_start in range(0, K, BLOCK_K):
            offs_k = k_start + tl.arange(0, BLOCK_K)
            mask_k = offs_k < K

            # Load X tile (BLOCK_M, BLOCK_K)
            x_ptrs = X_ptr + offs_m[:, None] * stride_xm + offs_k[None, :] * stride_xk
            x = tl.load(
                x_ptrs,
                mask=mask_m[:, None] & mask_k[None, :],
                other=0.0,
            ).to(tl.float16)

            # Load W tile (BLOCK_K, BLOCK_N)
            w_ptrs = W_ptr + offs_k[:, None] * stride_wk + offs_n[None, :] * stride_wn
            w = tl.load(
                w_ptrs,
                mask=mask_k[:, None] & mask_n[None, :],
                other=0.0,
            ).to(tl.float16)

            logits += tl.dot(x, w)

        # Add bias
        b = tl.load(B_ptr + offs_n, mask=mask_n, other=0.0)
        logits += b[None, :]

        # Mask out invalid columns
        logits = tl.where(mask_n[None, :], logits, neg_inf)

        # Streaming log-sum-exp
        tile_max = tl.max(logits, axis=1)
        new_row_max = tl.maximum(row_max, tile_max)

        exp_old = tl.exp(row_max - new_row_max) * row_lse
        exp_new = tl.sum(tl.exp(logits - new_row_max[:, None]), axis=1)

        row_lse = exp_old + exp_new
        row_max = new_row_max

    # Final log-sum-exp
    logsumexp = row_max + tl.log(row_lse)

    # Negative log-likelihood loss per sample
    losses = logsumexp - target_logit

    tl.store(loss_ptr + offs_m, losses, mask=mask_m)


def fused_linear_ce(X: torch.Tensor, W: torch.Tensor, B: torch.Tensor, targets: torch.Tensor) -> torch.Tensor:
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
    K_w, N = W.shape
    assert K_w == K
    assert B.shape[0] == N
    assert targets.shape[0] == M

    losses = torch.empty((M,), dtype=torch.float32, device=X.device)

    BLOCK_M = 16
    BLOCK_N = 128
    BLOCK_K = 64

    grid = (triton.cdiv(M, BLOCK_M),)

    fused_linear_ce_kernel[grid](
        X, W, B, targets, losses,
        M, N, K,
        X.stride(0), X.stride(1),
        W.stride(0), W.stride(1),
        BLOCK_M=BLOCK_M,
        BLOCK_N=BLOCK_N,
        BLOCK_K=BLOCK_K,
        num_warps=4,
        num_stages=3,
    )

    return losses


class Solution:
    def solve(self, spec_path: str = None) -> dict:
        return {"program_path": os.path.abspath(__file__)}