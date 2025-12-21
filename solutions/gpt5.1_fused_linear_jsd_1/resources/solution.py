import torch
import triton
import triton.language as tl
import inspect
import sys


@triton.autotune(
    configs=[
        triton.Config({'BLOCK_N': 128, 'BLOCK_K': 32}, num_warps=4, num_stages=2),
        triton.Config({'BLOCK_N': 256, 'BLOCK_K': 32}, num_warps=4, num_stages=2),
        triton.Config({'BLOCK_N': 128, 'BLOCK_K': 64}, num_warps=4, num_stages=3),
        triton.Config({'BLOCK_N': 256, 'BLOCK_K': 64}, num_warps=8, num_stages=3),
    ],
    key=['N', 'K'],
)
@triton.jit
def _lse_kernel(
    X_ptr, W1_ptr, B1_ptr, W2_ptr, B2_ptr,
    logZ1_ptr, logZ2_ptr,
    M, N, K,
    stride_xm, stride_xk,
    stride_w1k, stride_w1n,
    stride_w2k, stride_w2n,
    BLOCK_N: tl.constexpr, BLOCK_K: tl.constexpr,
):
    row = tl.program_id(0)
    if row >= M:
        return

    NEG_INF = -1.0e9
    global_max1 = tl.full((), NEG_INF, dtype=tl.float32)
    global_sum1 = tl.zeros((), dtype=tl.float32)
    global_max2 = tl.full((), NEG_INF, dtype=tl.float32)
    global_sum2 = tl.zeros((), dtype=tl.float32)

    n_start = 0
    while n_start < N:
        offs_n = n_start + tl.arange(0, BLOCK_N)
        mask_n = offs_n < N

        logits1 = tl.zeros((BLOCK_N,), dtype=tl.float32)
        logits2 = tl.zeros((BLOCK_N,), dtype=tl.float32)

        k_start = 0
        while k_start < K:
            offs_k = k_start + tl.arange(0, BLOCK_K)
            mask_k = offs_k < K

            x_ptrs = X_ptr + row * stride_xm + offs_k * stride_xk
            x_segment = tl.load(x_ptrs, mask=mask_k, other=0.0)

            w1_ptrs = W1_ptr + offs_k[:, None] * stride_w1k + offs_n[None, :] * stride_w1n
            w2_ptrs = W2_ptr + offs_k[:, None] * stride_w2k + offs_n[None, :] * stride_w2n
            w1_tile = tl.load(w1_ptrs, mask=mask_k[:, None] & mask_n[None, :], other=0.0)
            w2_tile = tl.load(w2_ptrs, mask=mask_k[:, None] & mask_n[None, :], other=0.0)

            x_mat = tl.reshape(x_segment, (1, BLOCK_K))

            partial1 = tl.dot(x_mat, w1_tile, out_dtype=tl.float32)
            partial2 = tl.dot(x_mat, w2_tile, out_dtype=tl.float32)

            logits1 += partial1[0, :]
            logits2 += partial2[0, :]

            k_start += BLOCK_K

        b1 = tl.load(B1_ptr + offs_n, mask=mask_n, other=0.0)
        b2 = tl.load(B2_ptr + offs_n, mask=mask_n, other=0.0)
        logits1 += b1
        logits2 += b2

        logits1 = tl.where(mask_n, logits1, NEG_INF)
        logits2 = tl.where(mask_n, logits2, NEG_INF)

        tile_max1 = tl.max(logits1, axis=0)
        tile_max2 = tl.max(logits2, axis=0)

        new_max1 = tl.maximum(global_max1, tile_max1)
        exp_prev1 = tl.exp(global_max1 - new_max1)
        exp_tile1 = tl.exp(logits1 - new_max1)
        tile_sum1 = tl.sum(exp_tile1, axis=0)
        global_sum1 = global_sum1 * exp_prev1 + tile_sum1
        global_max1 = new_max1

        new_max2 = tl.maximum(global_max2, tile_max2)
        exp_prev2 = tl.exp(global_max2 - new_max2)
        exp_tile2 = tl.exp(logits2 - new_max2)
        tile_sum2 = tl.sum(exp_tile2, axis=0)
        global_sum2 = global_sum2 * exp_prev2 + tile_sum2
        global_max2 = new_max2

        n_start += BLOCK_N

    logZ1 = global_max1 + tl.log(global_sum1)
    logZ2 = global_max2 + tl.log(global_sum2)

    tl.store(logZ1_ptr + row, logZ1)
    tl.store(logZ2_ptr + row, logZ2)


@triton.autotune(
    configs=[
        triton.Config({'BLOCK_N': 128, 'BLOCK_K': 32}, num_warps=4, num_stages=2),
        triton.Config({'BLOCK_N': 256, 'BLOCK_K': 32}, num_warps=4, num_stages=2),
        triton.Config({'BLOCK_N': 128, 'BLOCK_K': 64}, num_warps=4, num_stages=3),
        triton.Config({'BLOCK_N': 256, 'BLOCK_K': 64}, num_warps=8, num_stages=3),
    ],
    key=['N', 'K'],
)
@triton.jit
def _jsd_kernel(
    X_ptr, W1_ptr, B1_ptr, W2_ptr, B2_ptr,
    logZ1_ptr, logZ2_ptr,
    out_ptr,
    M, N, K,
    stride_xm, stride_xk,
    stride_w1k, stride_w1n,
    stride_w2k, stride_w2n,
    BLOCK_N: tl.constexpr, BLOCK_K: tl.constexpr,
):
    row = tl.program_id(0)
    if row >= M:
        return

    logZ1 = tl.load(logZ1_ptr + row)
    logZ2 = tl.load(logZ2_ptr + row)

    HP = tl.zeros((), dtype=tl.float32)
    HQ = tl.zeros((), dtype=tl.float32)
    HM = tl.zeros((), dtype=tl.float32)

    EPS = 1.0e-12

    n_start = 0
    while n_start < N:
        offs_n = n_start + tl.arange(0, BLOCK_N)
        mask_n = offs_n < N

        logits1 = tl.zeros((BLOCK_N,), dtype=tl.float32)
        logits2 = tl.zeros((BLOCK_N,), dtype=tl.float32)

        k_start = 0
        while k_start < K:
            offs_k = k_start + tl.arange(0, BLOCK_K)
            mask_k = offs_k < K

            x_ptrs = X_ptr + row * stride_xm + offs_k * stride_xk
            x_segment = tl.load(x_ptrs, mask=mask_k, other=0.0)

            w1_ptrs = W1_ptr + offs_k[:, None] * stride_w1k + offs_n[None, :] * stride_w1n
            w2_ptrs = W2_ptr + offs_k[:, None] * stride_w2k + offs_n[None, :] * stride_w2n
            w1_tile = tl.load(w1_ptrs, mask=mask_k[:, None] & mask_n[None, :], other=0.0)
            w2_tile = tl.load(w2_ptrs, mask=mask_k[:, None] & mask_n[None, :], other=0.0)

            x_mat = tl.reshape(x_segment, (1, BLOCK_K))

            partial1 = tl.dot(x_mat, w1_tile, out_dtype=tl.float32)
            partial2 = tl.dot(x_mat, w2_tile, out_dtype=tl.float32)

            logits1 += partial1[0, :]
            logits2 += partial2[0, :]

            k_start += BLOCK_K

        b1 = tl.load(B1_ptr + offs_n, mask=mask_n, other=0.0)
        b2 = tl.load(B2_ptr + offs_n, mask=mask_n, other=0.0)
        logits1 += b1
        logits2 += b2

        l1_shift = logits1 - logZ1
        l2_shift = logits2 - logZ2

        p = tl.exp(l1_shift)
        q = tl.exp(l2_shift)

        p = tl.where(mask_n, p, 0.0)
        q = tl.where(mask_n, q, 0.0)

        m = 0.5 * (p + q)
        m_safe = tl.where(mask_n, tl.maximum(m, EPS), 1.0)
        logm = tl.log(m_safe)

        HP_tile = -tl.sum(p * l1_shift, axis=0)
        HQ_tile = -tl.sum(q * l2_shift, axis=0)
        HM_tile = -tl.sum(m * logm, axis=0)

        HP += HP_tile
        HQ += HQ_tile
        HM += HM_tile

        n_start += BLOCK_N

    jsd = HM - 0.5 * HP - 0.5 * HQ
    tl.store(out_ptr + row, jsd)


def fused_linear_jsd(X: torch.Tensor, W1: torch.Tensor, B1: torch.Tensor, W2: torch.Tensor, B2: torch.Tensor) -> torch.Tensor:
    if not (X.is_cuda and W1.is_cuda and W2.is_cuda and B1.is_cuda and B2.is_cuda):
        raise ValueError("All inputs must be CUDA tensors")

    if X.dtype != torch.float16 or W1.dtype != torch.float16 or W2.dtype != torch.float16:
        raise ValueError("X, W1, and W2 must be float16 tensors")

    if B1.dtype != torch.float32 or B2.dtype != torch.float32:
        raise ValueError("B1 and B2 must be float32 tensors")

    M, K = X.shape
    K1, N = W1.shape
    K2, N2 = W2.shape

    if K1 != K or K2 != K or N2 != N:
        raise ValueError("Shape mismatch between X, W1, and W2")

    if B1.numel() != N or B2.numel() != N:
        raise ValueError("Bias size must match output features (N)")

    device = X.device

    logZ1 = torch.empty(M, dtype=torch.float32, device=device)
    logZ2 = torch.empty(M, dtype=torch.float32, device=device)
    out = torch.empty(M, dtype=torch.float32, device=device)

    grid = (M,)

    _lse_kernel[grid](
        X, W1, B1, W2, B2,
        logZ1, logZ2,
        M, N, K,
        X.stride(0), X.stride(1),
        W1.stride(0), W1.stride(1),
        W2.stride(0), W2.stride(1),
    )

    _jsd_kernel[grid](
        X, W1, B1, W2, B2,
        logZ1, logZ2,
        out,
        M, N, K,
        X.stride(0), X.stride(1),
        W1.stride(0), W1.stride(1),
        W2.stride(0), W2.stride(1),
    )

    return out


class Solution:
    def solve(self, spec_path: str = None) -> dict:
        module = sys.modules[__name__]
        source = inspect.getsource(module)
        return {"code": source}
