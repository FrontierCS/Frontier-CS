import torch
import triton
import triton.language as tl

KERNEL_SRC = """
import torch
import triton
import triton.language as tl

EPS = 1e-12


@triton.autotune(
    configs=[
        triton.Config(
            {'BLOCK_M': 16, 'BLOCK_N': 128, 'BLOCK_K': 32},
            num_warps=4,
            num_stages=3,
        ),
        triton.Config(
            {'BLOCK_M': 32, 'BLOCK_N': 64, 'BLOCK_K': 32},
            num_warps=4,
            num_stages=3,
        ),
        triton.Config(
            {'BLOCK_M': 64, 'BLOCK_N': 64, 'BLOCK_K': 32},
            num_warps=8,
            num_stages=3,
        ),
    ],
    key=['M', 'N', 'K'],
)
@triton.jit
def _fused_linear_jsd_kernel(
    X_ptr, W1_ptr, B1_ptr, W2_ptr, B2_ptr, Out_ptr,
    M, N, K,
    stride_xm, stride_xk,
    stride_w1k, stride_w1n,
    stride_w2k, stride_w2n,
    BLOCK_M: tl.constexpr, BLOCK_N: tl.constexpr, BLOCK_K: tl.constexpr,
):
    pid_m = tl.program_id(0)
    offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
    mask_m = offs_m < M

    # Initialize running log-sum-exp statistics for both logits
    max1 = tl.full((BLOCK_M,), -float('inf'), dtype=tl.float32)
    sum1 = tl.zeros((BLOCK_M,), dtype=tl.float32)
    max2 = tl.full((BLOCK_M,), -float('inf'), dtype=tl.float32)
    sum2 = tl.zeros((BLOCK_M,), dtype=tl.float32)

    # ============================
    # Pass 1: compute logZ1, logZ2
    # ============================
    n = 0
    while n < N:
        offs_n = n + tl.arange(0, BLOCK_N)
        mask_n = offs_n < N

        # Accumulators for logits block
        acc1 = tl.zeros((BLOCK_M, BLOCK_N), dtype=tl.float32)
        acc2 = tl.zeros((BLOCK_M, BLOCK_N), dtype=tl.float32)

        k = 0
        while k < K:
            offs_k = k + tl.arange(0, BLOCK_K)
            mask_k = offs_k < K

            # Load X block: [BLOCK_M, BLOCK_K]
            x_ptrs = X_ptr + (
                offs_m[:, None] * stride_xm +
                offs_k[None, :] * stride_xk
            )
            x = tl.load(
                x_ptrs,
                mask=mask_m[:, None] & mask_k[None, :],
                other=0.0,
            )
            x = x.to(tl.float16)

            # Load W1 and W2 blocks: [BLOCK_K, BLOCK_N]
            w1_ptrs = W1_ptr + (
                offs_k[:, None] * stride_w1k +
                offs_n[None, :] * stride_w1n
            )
            w2_ptrs = W2_ptr + (
                offs_k[:, None] * stride_w2k +
                offs_n[None, :] * stride_w2n
            )
            w_mask = mask_k[:, None] & mask_n[None, :]

            w1 = tl.load(w1_ptrs, mask=w_mask, other=0.0)
            w2 = tl.load(w2_ptrs, mask=w_mask, other=0.0)
            w1 = w1.to(tl.float16)
            w2 = w2.to(tl.float16)

            acc1 += tl.dot(x, w1, out_dtype=tl.float32)
            acc2 += tl.dot(x, w2, out_dtype=tl.float32)

            k += BLOCK_K

        # Add biases
        b1 = tl.load(B1_ptr + offs_n, mask=mask_n, other=0.0)
        b2 = tl.load(B2_ptr + offs_n, mask=mask_n, other=0.0)

        logits1 = acc1 + b1[None, :]
        logits2 = acc2 + b2[None, :]

        # Mask out-of-bounds rows/cols with -inf so they don't affect max/sum
        mask_block = mask_m[:, None] & mask_n[None, :]
        logits1 = tl.where(mask_block, logits1, -float('inf'))
        logits2 = tl.where(mask_block, logits2, -float('inf'))

        # Per-row maximum over this block
        block_max1 = tl.max(logits1, axis=1)
        block_max2 = tl.max(logits2, axis=1)

        new_max1 = tl.maximum(max1, block_max1)
        new_max2 = tl.maximum(max2, block_max2)

        # Update running sum of exp(logits - new_max)
        exp1 = tl.exp(logits1 - new_max1[:, None])
        exp2 = tl.exp(logits2 - new_max2[:, None])

        sum_block1 = tl.sum(exp1, axis=1)
        sum_block2 = tl.sum(exp2, axis=1)

        old_scaled1 = tl.exp(max1 - new_max1) * sum1
        old_scaled2 = tl.exp(max2 - new_max2) * sum2

        sum1 = old_scaled1 + sum_block1
        sum2 = old_scaled2 + sum_block2
        max1 = new_max1
        max2 = new_max2

        n += BLOCK_N

    # Final log partition functions
    logZ1 = max1 + tl.log(sum1 + EPS)
    logZ2 = max2 + tl.log(sum2 + EPS)

    # ============================
    # Pass 2: accumulate JSD
    # ============================
    jsd_row = tl.zeros((BLOCK_M,), dtype=tl.float32)

    n = 0
    while n < N:
        offs_n = n + tl.arange(0, BLOCK_N)
        mask_n = offs_n < N

        acc1 = tl.zeros((BLOCK_M, BLOCK_N), dtype=tl.float32)
        acc2 = tl.zeros((BLOCK_M, BLOCK_N), dtype=tl.float32)

        k = 0
        while k < K:
            offs_k = k + tl.arange(0, BLOCK_K)
            mask_k = offs_k < K

            x_ptrs = X_ptr + (
                offs_m[:, None] * stride_xm +
                offs_k[None, :] * stride_xk
            )
            x = tl.load(
                x_ptrs,
                mask=mask_m[:, None] & mask_k[None, :],
                other=0.0,
            )
            x = x.to(tl.float16)

            w1_ptrs = W1_ptr + (
                offs_k[:, None] * stride_w1k +
                offs_n[None, :] * stride_w1n
            )
            w2_ptrs = W2_ptr + (
                offs_k[:, None] * stride_w2k +
                offs_n[None, :] * stride_w2n
            )
            w_mask = mask_k[:, None] & mask_n[None, :]

            w1 = tl.load(w1_ptrs, mask=w_mask, other=0.0)
            w2 = tl.load(w2_ptrs, mask=w_mask, other=0.0)
            w1 = w1.to(tl.float16)
            w2 = w2.to(tl.float16)

            acc1 += tl.dot(x, w1, out_dtype=tl.float32)
            acc2 += tl.dot(x, w2, out_dtype=tl.float32)

            k += BLOCK_K

        b1 = tl.load(B1_ptr + offs_n, mask=mask_n, other=0.0)
        b2 = tl.load(B2_ptr + offs_n, mask=mask_n, other=0.0)

        logits1 = acc1 + b1[None, :]
        logits2 = acc2 + b2[None, :]

        mask_block = mask_m[:, None] & mask_n[None, :]
        logits1 = tl.where(mask_block, logits1, -float('inf'))
        logits2 = tl.where(mask_block, logits2, -float('inf'))

        s1 = logits1 - logZ1[:, None]
        s2 = logits2 - logZ2[:, None]

        # Probabilities P and Q; zero for masked positions
        P = tl.where(mask_block, tl.exp(s1), 0.0)
        Q = tl.where(mask_block, tl.exp(s2), 0.0)

        M_prob = 0.5 * (P + Q) + EPS
        logM = tl.log(M_prob)

        jsd_tile = 0.5 * (P * (s1 - logM) + Q * (s2 - logM))

        jsd_row += tl.sum(jsd_tile, axis=1)

        n += BLOCK_N

    tl.store(Out_ptr + offs_m, jsd_row, mask=mask_m)


def fused_linear_jsd(X: torch.Tensor,
                     W1: torch.Tensor,
                     B1: torch.Tensor,
                     W2: torch.Tensor,
                     B2: torch.Tensor) -> torch.Tensor:
    \"""
    Fused linear layers with Jensen-Shannon Divergence computation.

    Args:
        X:  (M, K) float16
        W1: (K, N) float16
        B1: (N,)   float32
        W2: (K, N) float16
        B2: (N,)   float32

    Returns:
        (M,) float32 tensor of JSD values.
    \"""
    assert X.is_cuda and W1.is_cuda and W2.is_cuda and B1.is_cuda and B2.is_cuda
    assert X.dtype == torch.float16
    assert W1.dtype == torch.float16 and W2.dtype == torch.float16
    assert B1.dtype == torch.float32 and B2.dtype == torch.float32

    M, K = X.shape
    K1, N = W1.shape
    K2, N2 = W2.shape
    assert K1 == K and K2 == K and N2 == N
    assert B1.numel() == N and B2.numel() == N

    out = torch.empty((M,), device=X.device, dtype=torch.float32)

    stride_xm, stride_xk = X.stride()
    stride_w1k, stride_w1n = W1.stride()
    stride_w2k, stride_w2n = W2.stride()

    grid = lambda META: (triton.cdiv(M, META['BLOCK_M']),)

    _fused_linear_jsd_kernel[grid](
        X, W1, B1, W2, B2, out,
        M, N, K,
        stride_xm, stride_xk,
        stride_w1k, stride_w1n,
        stride_w2k, stride_w2n,
    )

    return out
"""

exec(KERNEL_SRC, globals())


class Solution:
    def solve(self, spec_path: str = None) -> dict:
        return {"code": KERNEL_SRC}