import sys
import torch
import triton
import triton.language as tl


@triton.jit
def _lse_kernel(
    X_ptr,
    W1_ptr,
    B1_ptr,
    W2_ptr,
    B2_ptr,
    LSE1_ptr,
    LSE2_ptr,
    M, N, K,
    stride_xm, stride_xk,
    stride_w1k, stride_w1n,
    stride_w2k, stride_w2n,
    BLOCK_N: tl.constexpr,
    BLOCK_K: tl.constexpr,
):
    pid_m = tl.program_id(axis=0)
    # Each program handles one row of X
    x_row_ptr = X_ptr + pid_m * stride_xm

    # Initialize running max and sumexp for log-sum-exp
    m1 = tl.full((), -float("inf"), dtype=tl.float32)
    s1 = tl.zeros((), dtype=tl.float32)
    m2 = tl.full((), -float("inf"), dtype=tl.float32)
    s2 = tl.zeros((), dtype=tl.float32)

    offs_n = tl.arange(0, BLOCK_N)

    n_start = 0
    while n_start < N:
        n_offsets = n_start + offs_n
        n_mask = n_offsets < N

        logits1 = tl.zeros((BLOCK_N,), dtype=tl.float32)
        logits2 = tl.zeros((BLOCK_N,), dtype=tl.float32)

        offs_k = tl.arange(0, BLOCK_K)
        k_start = 0
        while k_start < K:
            k_offsets = k_start + offs_k
            k_mask = k_offsets < K

            x_ptrs = x_row_ptr + k_offsets * stride_xk
            x = tl.load(x_ptrs, mask=k_mask, other=0.0)
            x = x.to(tl.float32)
            x = x[:, None]  # (BLOCK_K, 1)

            w1_ptrs = W1_ptr + k_offsets[:, None] * stride_w1k + n_offsets[None, :] * stride_w1n
            w2_ptrs = W2_ptr + k_offsets[:, None] * stride_w2k + n_offsets[None, :] * stride_w2n
            w_mask = k_mask[:, None] & n_mask[None, :]

            w1 = tl.load(w1_ptrs, mask=w_mask, other=0.0).to(tl.float32)
            w2 = tl.load(w2_ptrs, mask=w_mask, other=0.0).to(tl.float32)

            logits1 += tl.sum(x * w1, axis=0)
            logits2 += tl.sum(x * w2, axis=0)

            k_start += BLOCK_K

        b1 = tl.load(B1_ptr + n_offsets, mask=n_mask, other=0.0)
        b2 = tl.load(B2_ptr + n_offsets, mask=n_mask, other=0.0)
        logits1 += b1
        logits2 += b2

        neg_inf = -float("inf")
        logits1 = tl.where(n_mask, logits1, neg_inf)
        logits2 = tl.where(n_mask, logits2, neg_inf)

        tile_max1 = tl.max(logits1, axis=0)
        tile_max2 = tl.max(logits2, axis=0)

        new_m1 = tl.maximum(m1, tile_max1)
        new_m2 = tl.maximum(m2, tile_max2)

        s1 = s1 * tl.exp(m1 - new_m1) + tl.sum(tl.exp(logits1 - new_m1), axis=0)
        s2 = s2 * tl.exp(m2 - new_m2) + tl.sum(tl.exp(logits2 - new_m2), axis=0)

        m1 = new_m1
        m2 = new_m2

        n_start += BLOCK_N

    lse1 = m1 + tl.log(s1)
    lse2 = m2 + tl.log(s2)

    tl.store(LSE1_ptr + pid_m, lse1)
    tl.store(LSE2_ptr + pid_m, lse2)


@triton.jit
def _jsd_kernel(
    X_ptr,
    W1_ptr,
    B1_ptr,
    W2_ptr,
    B2_ptr,
    LSE1_ptr,
    LSE2_ptr,
    OUT_ptr,
    M, N, K,
    stride_xm, stride_xk,
    stride_w1k, stride_w1n,
    stride_w2k, stride_w2n,
    BLOCK_N: tl.constexpr,
    BLOCK_K: tl.constexpr,
):
    pid_m = tl.program_id(axis=0)
    x_row_ptr = X_ptr + pid_m * stride_xm

    lse1 = tl.load(LSE1_ptr + pid_m)
    lse2 = tl.load(LSE2_ptr + pid_m)

    jsd_acc = tl.zeros((), dtype=tl.float32)

    offs_n = tl.arange(0, BLOCK_N)
    offs_k = tl.arange(0, BLOCK_K)

    LOG2 = 0.6931471805599453  # log(2)

    n_start = 0
    while n_start < N:
        n_offsets = n_start + offs_n
        n_mask = n_offsets < N

        logits1 = tl.zeros((BLOCK_N,), dtype=tl.float32)
        logits2 = tl.zeros((BLOCK_N,), dtype=tl.float32)

        k_start = 0
        while k_start < K:
            k_offsets = k_start + offs_k
            k_mask = k_offsets < K

            x_ptrs = x_row_ptr + k_offsets * stride_xk
            x = tl.load(x_ptrs, mask=k_mask, other=0.0)
            x = x.to(tl.float32)
            x = x[:, None]

            w1_ptrs = W1_ptr + k_offsets[:, None] * stride_w1k + n_offsets[None, :] * stride_w1n
            w2_ptrs = W2_ptr + k_offsets[:, None] * stride_w2k + n_offsets[None, :] * stride_w2n
            w_mask = k_mask[:, None] & n_mask[None, :]

            w1 = tl.load(w1_ptrs, mask=w_mask, other=0.0).to(tl.float32)
            w2 = tl.load(w2_ptrs, mask=w_mask, other=0.0).to(tl.float32)

            logits1 += tl.sum(x * w1, axis=0)
            logits2 += tl.sum(x * w2, axis=0)

            k_start += BLOCK_K

        b1 = tl.load(B1_ptr + n_offsets, mask=n_mask, other=0.0)
        b2 = tl.load(B2_ptr + n_offsets, mask=n_mask, other=0.0)
        logits1 += b1
        logits2 += b2

        # For invalid positions, any finite value is fine since we will mask contributions to zero.
        logits1 = tl.where(n_mask, logits1, 0.0)
        logits2 = tl.where(n_mask, logits2, 0.0)

        u = logits1 - lse1  # log P
        v = logits2 - lse2  # log Q

        exp_u = tl.exp(u)
        exp_v = tl.exp(v)

        max_uv = tl.maximum(u, v)
        sum_exp = tl.exp(u - max_uv) + tl.exp(v - max_uv)
        log_m = max_uv + tl.log(sum_exp) - LOG2  # log M

        kl_p_m = exp_u * (u - log_m)
        kl_q_m = exp_v * (v - log_m)

        contrib = 0.5 * (kl_p_m + kl_q_m)
        contrib = tl.where(n_mask, contrib, 0.0)

        jsd_acc += tl.sum(contrib, axis=0)

        n_start += BLOCK_N

    tl.store(OUT_ptr + pid_m, jsd_acc)


def fused_linear_jsd(X: torch.Tensor, W1: torch.Tensor, B1: torch.Tensor, W2: torch.Tensor, B2: torch.Tensor) -> torch.Tensor:
    """
    Fused linear layers with Jensen-Shannon Divergence computation.
    """
    assert X.is_cuda and W1.is_cuda and W2.is_cuda and B1.is_cuda and B2.is_cuda
    assert X.dtype == torch.float16
    assert W1.dtype == torch.float16 and W2.dtype == torch.float16
    assert B1.dtype == torch.float32 and B2.dtype == torch.float32

    Xc = X.contiguous()
    W1c = W1.contiguous()
    W2c = W2.contiguous()
    B1c = B1.contiguous()
    B2c = B2.contiguous()

    M, K = Xc.shape
    K1, N = W1c.shape
    K2, N2 = W2c.shape
    assert K1 == K and K2 == K and N2 == N

    if M == 0:
        return torch.empty((0,), dtype=torch.float32, device=X.device)

    device = Xc.device
    lse1 = torch.empty((M,), dtype=torch.float32, device=device)
    lse2 = torch.empty((M,), dtype=torch.float32, device=device)
    out = torch.empty((M,), dtype=torch.float32, device=device)

    BLOCK_N = 128
    BLOCK_K = 32

    grid = (M,)

    _lse_kernel[grid](
        Xc, W1c, B1c, W2c, B2c,
        lse1, lse2,
        M, N, K,
        Xc.stride(0), Xc.stride(1),
        W1c.stride(0), W1c.stride(1),
        W2c.stride(0), W2c.stride(1),
        BLOCK_N=BLOCK_N,
        BLOCK_K=BLOCK_K,
        num_warps=4,
        num_stages=2,
    )

    _jsd_kernel[grid](
        Xc, W1c, B1c, W2c, B2c,
        lse1, lse2, out,
        M, N, K,
        Xc.stride(0), Xc.stride(1),
        W1c.stride(0), W1c.stride(1),
        W2c.stride(0), W2c.stride(1),
        BLOCK_N=BLOCK_N,
        BLOCK_K=BLOCK_K,
        num_warps=4,
        num_stages=2,
    )

    return out


class Solution:
    def solve(self, spec_path: str = None) -> dict:
        module_name = __name__
        code = f"""import torch
import triton
import triton.language as tl
try:
    from {module_name} import fused_linear_jsd
except ImportError:
    from __main__ import fused_linear_jsd
"""
        return {"code": code}
