import torch
import triton
import triton.language as tl


@triton.autotune(
    configs=[
        triton.Config(
            {'BLOCK_N': 64, 'BLOCK_K': 64},
            num_warps=2,
            num_stages=2,
        ),
        triton.Config(
            {'BLOCK_N': 128, 'BLOCK_K': 64},
            num_warps=4,
            num_stages=2,
        ),
        triton.Config(
            {'BLOCK_N': 256, 'BLOCK_K': 64},
            num_warps=8,
            num_stages=2,
        ),
    ],
    key=['N', 'K'],
)
@triton.jit
def fused_linear_ce_kernel(
    X_ptr, W_ptr, B_ptr, T_ptr, Loss_ptr,
    M, N, K,
    stride_xm, stride_xk,
    stride_wk, stride_wn,
    stride_b, stride_t,
    BLOCK_N: tl.constexpr, BLOCK_K: tl.constexpr,
):
    pid_m = tl.program_id(axis=0)
    row = pid_m

    # Guard against out-of-bounds in case grid > M (shouldn't happen if grid=(M,))
    row_mask = row < M
    if not row_mask:
        return

    # Load target index for this row
    target = tl.load(T_ptr + row * stride_t).to(tl.int32)

    # Base pointer to row of X
    x_row_ptr = X_ptr + row * stride_xm

    # Streaming log-sum-exp state
    row_max = -float("inf")
    row_sumexp = tl.zeros((), dtype=tl.float32)
    target_logit = tl.zeros((), dtype=tl.float32)

    n_start = 0
    while n_start < N:
        offs_n = n_start + tl.arange(0, BLOCK_N)
        mask_n = offs_n < N

        # Accumulator for logits in this tile
        acc = tl.zeros((BLOCK_N,), dtype=tl.float32)

        k_start = 0
        while k_start < K:
            offs_k = k_start + tl.arange(0, BLOCK_K)
            mask_k = offs_k < K

            # Load X row slice [BLOCK_K]
            x = tl.load(
                x_row_ptr + offs_k * stride_xk,
                mask=mask_k,
                other=0.0,
            )

            # Load W slice [BLOCK_K, BLOCK_N]
            w_ptrs = W_ptr + offs_k[:, None] * stride_wk + offs_n[None, :] * stride_wn
            w = tl.load(
                w_ptrs,
                mask=mask_k[:, None] & mask_n[None, :],
                other=0.0,
            )

            # Fused dot-product accumulate into fp32
            acc += tl.dot(x, w)

            k_start += BLOCK_K

        # Add bias
        b = tl.load(
            B_ptr + offs_n * stride_b,
            mask=mask_n,
            other=0.0,
        )
        logits = acc + b

        # For masked (out-of-range) columns, set logits to -inf so they don't affect reductions
        logits = tl.where(mask_n, logits, -float("inf"))

        # Tile-wise max
        local_max = tl.max(logits, axis=0)

        # New overall max
        new_row_max = tl.maximum(row_max, local_max)

        # Sum of exp(logits - new_row_max) over this tile
        sumexp_tile = tl.sum(tl.exp(logits - new_row_max), axis=0)

        # Update streaming log-sum-exp state
        row_sumexp = row_sumexp * tl.exp(row_max - new_row_max) + sumexp_tile
        row_max = new_row_max

        # Accumulate target logit if it lies in this tile
        target_mask = offs_n == target
        target_contrib = tl.sum(tl.where(target_mask, logits, 0.0), axis=0)
        target_logit += target_contrib

        n_start += BLOCK_N

    # Final negative log-likelihood for this row
    loss = row_max + tl.log(row_sumexp) - target_logit
    tl.store(Loss_ptr + row, loss)


def fused_linear_ce(
    X: torch.Tensor,
    W: torch.Tensor,
    B: torch.Tensor,
    targets: torch.Tensor,
) -> torch.Tensor:
    """
    Fused linear layer with cross entropy loss computation.

    Args:
        X: (M, K) float16
        W: (K, N) float16
        B: (N,) float32
        targets: (M,) int64

    Returns:
        (M,) float32 negative log-likelihood per sample
    """
    if X.device.type != "cuda":
        # Fallback to PyTorch implementation on CPU or non-CUDA devices
        logits = (X @ W).to(torch.float32) + B
        return torch.nn.functional.cross_entropy(
            logits, targets, reduction="none"
        )

    assert W.device == X.device and B.device == X.device and targets.device == X.device
    assert X.dtype == torch.float16, "X must be float16"
    assert W.dtype == torch.float16, "W must be float16"
    assert B.dtype == torch.float32, "B must be float32"
    assert targets.dtype == torch.long, "targets must be int64 (long)"

    M, K = X.shape
    K_w, N = W.shape
    assert K_w == K, "Incompatible X and W shapes"
    assert B.shape[0] == N, "Incompatible W and B shapes"
    assert targets.shape[0] == M, "Incompatible X and targets shapes"

    # Output tensor
    loss = torch.empty((M,), device=X.device, dtype=torch.float32)

    grid = (M,)

    fused_linear_ce_kernel[grid](
        X, W, B, targets, loss,
        M, N, K,
        X.stride(0), X.stride(1),
        W.stride(0), W.stride(1),
        B.stride(0), targets.stride(0),
    )

    return loss


class Solution:
    def solve(self, spec_path: str = None) -> dict:
        # Provide this file as the kernel program
        return {"program_path": __file__}
