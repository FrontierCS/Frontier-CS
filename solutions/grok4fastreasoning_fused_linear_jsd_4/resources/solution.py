import torch
import triton
import triton.language as tl
import math

class Solution:
    def solve(self, spec_path: str = None) -> dict:
        code = """
import torch
import triton
import triton.language as tl
import math

@triton.jit
def max_kernel(
    max_buf1_ptr,
    max_buf2_ptr,
    X_ptr,
    W1_ptr,
    B1_ptr,
    W2_ptr,
    B2_ptr,
    M : tl.constexpr,
    K : tl.constexpr,
    N : tl.constexpr,
    stride_xm,
    stride_xk,
    stride_w1k,
    stride_w1n,
    stride_b1,
    stride_w2k,
    stride_w2n,
    stride_b2,
    BLOCK_M : tl.constexpr,
    BLOCK_N : tl.constexpr,
    BLOCK_K : tl.constexpr
):
    pid_m = tl.program_id(0)
    pid_n = tl.program_id(1)
    m_start = pid_m * BLOCK_M
    n_start = pid_n * BLOCK_N
    num_m = tl.minimum(BLOCK_M, M - m_start)
    num_n = tl.minimum(BLOCK_N, N - n_start)
    if num_m <= 0 or num_n <= 0:
        return

    acc1 = tl.zeros((BLOCK_M, BLOCK_N), dtype=tl.float32)
    acc2 = tl.zeros((BLOCK_M, BLOCK_N), dtype=tl.float32)

    k_lo = 0
    while k_lo < K:
        k_hi = tl.minimum(k_lo + BLOCK_K, K)
        offs_m = tl.arange(0, BLOCK_M)
        offs_k = tl.arange(0, BLOCK_K)
        mask_k = offs_k < (k_hi - k_lo)
        x_mask = (offs_m[:, None] < num_m) & mask_k[None, :]
        x_ptr = tl.make_block_ptr(
            base=X_ptr,
            shape=(M, K),
            strides=(stride_xm, stride_xk),
            offset=(m_start, k_lo),
            block_shape=(BLOCK_M, BLOCK_K),
            order=(0, 1)
        )
        x = tl.load(x_ptr, mask=x_mask, other=0.0)
        x_f = x.to(tl.float32)

        # W1
        offs_n = tl.arange(0, BLOCK_N)
        w1_mask = mask_k[:, None] & (offs_n[None, :] < num_n)
        w1_ptr = tl.make_block_ptr(
            base=W1_ptr,
            shape=(K, N),
            strides=(stride_w1k, stride_w1n),
            offset=(k_lo, n_start),
            block_shape=(BLOCK_K, BLOCK_N),
            order=(0, 1)
        )
        w1 = tl.load(w1_ptr, mask=w1_mask, other=0.0)
        w1_f = w1.to(tl.float32)
        partial1 = tl.dot(x_f, w1_f)
        acc1 += partial1

        # W2
        w2_mask = mask_k[:, None] & (offs_n[None, :] < num_n)
        w2_ptr = tl.make_block_ptr(
            base=W2_ptr,
            shape=(K, N),
            strides=(stride_w2k, stride_w2n),
            offset=(k_lo, n_start),
            block_shape=(BLOCK_K, BLOCK_N),
            order=(0, 1)
        )
        w2 = tl.load(w2_ptr, mask=w2_mask, other=0.0)
        w2_f = w2.to(tl.float32)
        partial2 = tl.dot(x_f, w2_f)
        acc2 += partial2

        k_lo += BLOCK_K

    # Add biases
    b1_mask = offs_n < num_n
    b1_slice = tl.load(B1_ptr + n_start + offs_n, mask=b1_mask, other=0.0)
    acc1 += b1_slice[None, :]

    b2_mask = offs_n < num_n
    b2_slice = tl.load(B2_ptr + n_start + offs_n, mask=b2_mask, other=0.0)
    acc2 += b2_slice[None, :]

    # Reduce max for valid
    n_mask = offs_n < num_n
    for i in range(0, num_m):
        valid_acc1 = tl.where(n_mask, acc1[i, :], -10000.0)
        row_max1 = tl.max(valid_acc1)
        tl.atomic_max(max_buf1_ptr + m_start + i, row_max1)

        valid_acc2 = tl.where(n_mask, acc2[i, :], -10000.0)
        row_max2 = tl.max(valid_acc2)
        tl.atomic_max(max_buf2_ptr + m_start + i, row_max2)

@triton.jit
def sum_exp_kernel(
    sum_exp_buf1_ptr,
    sum_exp_buf2_ptr,
    max_buf1_ptr,
    max_buf2_ptr,
    X_ptr,
    W1_ptr,
    B1_ptr,
    W2_ptr,
    B2_ptr,
    M : tl.constexpr,
    K : tl.constexpr,
    N : tl.constexpr,
    stride_xm,
    stride_xk,
    stride_w1k,
    stride_w1n,
    stride_b1,
    stride_w2k,
    stride_w2n,
    stride_b2,
    BLOCK_M : tl.constexpr,
    BLOCK_N : tl.constexpr,
    BLOCK_K : tl.constexpr
):
    pid_m = tl.program_id(0)
    pid_n = tl.program_id(1)
    m_start = pid_m * BLOCK_M
    n_start = pid_n * BLOCK_N
    num_m = tl.minimum(BLOCK_M, M - m_start)
    num_n = tl.minimum(BLOCK_N, N - n_start)
    if num_m <= 0 or num_n <= 0:
        return

    acc1 = tl.zeros((BLOCK_M, BLOCK_N), dtype=tl.float32)
    acc2 = tl.zeros((BLOCK_M, BLOCK_N), dtype=tl.float32)

    k_lo = 0
    while k_lo < K:
        k_hi = tl.minimum(k_lo + BLOCK_K, K)
        offs_m = tl.arange(0, BLOCK_M)
        offs_k = tl.arange(0, BLOCK_K)
        mask_k = offs_k < (k_hi - k_lo)
        x_mask = (offs_m[:, None] < num_m) & mask_k[None, :]
        x_ptr = tl.make_block_ptr(
            base=X_ptr,
            shape=(M, K),
            strides=(stride_xm, stride_xk),
            offset=(m_start, k_lo),
            block_shape=(BLOCK_M, BLOCK_K),
            order=(0, 1)
        )
        x = tl.load(x_ptr, mask=x_mask, other=0.0)
        x_f = x.to(tl.float32)

        offs_n = tl.arange(0, BLOCK_N)
        # W1
        w1_mask = mask_k[:, None] & (offs_n[None, :] < num_n)
        w1_ptr = tl.make_block_ptr(
            base=W1_ptr,
            shape=(K, N),
            strides=(stride_w1k, stride_w1n),
            offset=(k_lo, n_start),
            block_shape=(BLOCK_K, BLOCK_N),
            order=(0, 1)
        )
        w1 = tl.load(w1_ptr, mask=w1_mask, other=0.0)
        w1_f = w1.to(tl.float32)
        partial1 = tl.dot(x_f, w1_f)
        acc1 += partial1

        # W2
        w2_mask = mask_k[:, None] & (offs_n[None, :] < num_n)
        w2_ptr = tl.make_block_ptr(
            base=W2_ptr,
            shape=(K, N),
            strides=(stride_w2k, stride_w2n),
            offset=(k_lo, n_start),
            block_shape=(BLOCK_K, BLOCK_N),
            order=(0, 1)
        )
        w2 = tl.load(w2_ptr, mask=w2_mask, other=0.0)
        w2_f = w2.to(tl.float32)
        partial2 = tl.dot(x_f, w2_f)
        acc2 += partial2

        k_lo += BLOCK_K

    # Add biases
    b1_mask = offs_n < num_n
    b1_slice = tl.load(B1_ptr + n_start + offs_n, mask=b1_mask, other=0.0)
    acc1 += b1_slice[None, :]

    b2_mask = offs_n < num_n
    b2_slice = tl.load(B2_ptr + n_start + offs_n, mask=b2_mask, other=0.0)
    acc2 += b2_slice[None, :]

    # Load max slices
    offs_mm = tl.arange(0, BLOCK_M)
    m_mask = offs_mm < num_m
    max1_slice = tl.load(max_buf1_ptr + m_start + offs_mm, mask=m_mask, other=0.0)
    max2_slice = tl.load(max_buf2_ptr + m_start + offs_mm, mask=m_mask, other=0.0)

    n_mask = offs_n < num_n
    for i in range(0, num_m):
        logp_row = acc1[i, :] - max1_slice[i]
        exp_p_masked = tl.where(n_mask, tl.exp(logp_row), 0.0)
        row_sum_exp1 = tl.sum(exp_p_masked)
        tl.atomic_add(sum_exp_buf1_ptr + m_start + i, row_sum_exp1)

        logq_row = acc2[i, :] - max2_slice[i]
        exp_q_masked = tl.where(n_mask, tl.exp(logq_row), 0.0)
        row_sum_exp2 = tl.sum(exp_q_masked)
        tl.atomic_add(sum_exp_buf2_ptr + m_start + i, row_sum_exp2)

@triton.jit
def jsd_kernel(
    sum_p_logits1_ptr,
    sum_q_logits2_ptr,
    sum_p_logm_ptr,
    sum_q_logm_ptr,
    lse1_ptr,
    lse2_ptr,
    X_ptr,
    W1_ptr,
    B1_ptr,
    W2_ptr,
    B2_ptr,
    M : tl.constexpr,
    K : tl.constexpr,
    N : tl.constexpr,
    stride_xm,
    stride_xk,
    stride_w1k,
    stride_w1n,
    stride_b1,
    stride_w2k,
    stride_w2n,
    stride_b2,
    BLOCK_M : tl.constexpr,
    BLOCK_N : tl.constexpr,
    BLOCK_K : tl.constexpr
):
    pid_m = tl.program_id(0)
    pid_n = tl.program_id(1)
    m_start = pid_m * BLOCK_M
    n_start = pid_n * BLOCK_N
    num_m = tl.minimum(BLOCK_M, M - m_start)
    num_n = tl.minimum(BLOCK_N, N - n_start)
    if num_m <= 0 or num_n <= 0:
        return

    acc1 = tl.zeros((BLOCK_M, BLOCK_N), dtype=tl.float32)
    acc2 = tl.zeros((BLOCK_M, BLOCK_N), dtype=tl.float32)

    k_lo = 0
    while k_lo < K:
        k_hi = tl.minimum(k_lo + BLOCK_K, K)
        offs_m = tl.arange(0, BLOCK_M)
        offs_k = tl.arange(0, BLOCK_K)
        mask_k = offs_k < (k_hi - k_lo)
        x_mask = (offs_m[:, None] < num_m) & mask_k[None, :]
        x_ptr = tl.make_block_ptr(
            base=X_ptr,
            shape=(M, K),
            strides=(stride_xm, stride_xk),
            offset=(m_start, k_lo),
            block_shape=(BLOCK_M, BLOCK_K),
            order=(0, 1)
        )
        x = tl.load(x_ptr, mask=x_mask, other=0.0)
        x_f = x.to(tl.float32)

        offs_n = tl.arange(0, BLOCK_N)
        # W1
        w1_mask = mask_k[:, None] & (offs_n[None, :] < num_n)
        w1_ptr = tl.make_block_ptr(
            base=W1_ptr,
            shape=(K, N),
            strides=(stride_w1k, stride_w1n),
            offset=(k_lo, n_start),
            block_shape=(BLOCK_K, BLOCK_N),
            order=(0, 1)
        )
        w1 = tl.load(w1_ptr, mask=w1_mask, other=0.0)
        w1_f = w1.to(tl.float32)
        partial1 = tl.dot(x_f, w1_f)
        acc1 += partial1

        # W2
        w2_mask = mask_k[:, None] & (offs_n[None, :] < num_n)
        w2_ptr = tl.make_block_ptr(
            base=W2_ptr,
            shape=(K, N),
            strides=(stride_w2k, stride_w2n),
            offset=(k_lo, n_start),
            block_shape=(BLOCK_K, BLOCK_N),
            order=(0, 1)
        )
        w2 = tl.load(w2_ptr, mask=w2_mask, other=0.0)
        w2_f = w2.to(tl.float32)
        partial2 = tl.dot(x_f, w2_f)
        acc2 += partial2

        k_lo += BLOCK_K

    # Add biases
    b1_mask = offs_n < num_n
    b1_slice = tl.load(B1_ptr + n_start + offs_n, mask=b1_mask, other=0.0)
    acc1 += b1_slice[None, :]

    b2_mask = offs_n < num_n
    b2_slice = tl.load(B2_ptr + n_start + offs_n, mask=b2_mask, other=0.0)
    acc2 += b2_slice[None, :]

    # Load lse slices
    offs_mm = tl.arange(0, BLOCK_M)
    m_mask = offs_mm < num_m
    lse1_slice = tl.load(lse1_ptr + m_start + offs_mm, mask=m_mask, other=0.0)
    lse2_slice = tl.load(lse2_ptr + m_start + offs_mm, mask=m_mask, other=0.0)

    n_mask = offs_n < num_n
    for i in range(0, num_m):
        p_row = tl.where(n_mask, tl.exp(acc1[i, :] - lse1_slice[i]), 0.0)
        q_row = tl.where(n_mask, tl.exp(acc2[i, :] - lse2_slice[i]), 0.0)
        mm_row = 0.5 * (p_row + q_row)
        logmm_row = tl.where(mm_row > 0.0, tl.log(mm_row), 0.0)

        contrib_p_logits = tl.sum(p_row * acc1[i, :])
        tl.atomic_add(sum_p_logits1_ptr + m_start + i, contrib_p_logits)

        contrib_q_logits = tl.sum(q_row * acc2[i, :])
        tl.atomic_add(sum_q_logits2_ptr + m_start + i, contrib_q_logits)

        contrib_p_logm = tl.sum(p_row * logmm_row)
        tl.atomic_add(sum_p_logm_ptr + m_start + i, contrib_p_logm)

        contrib_q_logm = tl.sum(q_row * logmm_row)
        tl.atomic_add(sum_q_logm_ptr + m_start + i, contrib_q_logm)

def fused_linear_jsd(X: torch.Tensor, W1: torch.Tensor, B1: torch.Tensor, W2: torch.Tensor, B2: torch.Tensor) -> torch.Tensor:
    X = X.contiguous()
    W1 = W1.contiguous()
    W2 = W2.contiguous()
    B1 = B1.contiguous()
    B2 = B2.contiguous()
    device = X.device
    M, K = X.shape
    N = W1.shape[1]

    BLOCK_M = 128
    BLOCK_N = 128
    BLOCK_K = 64

    num_m_blocks = math.ceil(M / BLOCK_M)
    num_n_blocks = math.ceil(N / BLOCK_N)
    grid = (num_m_blocks, num_n_blocks)

    stride_xm = X.stride(0)
    stride_xk = X.stride(1)
    stride_w1k = W1.stride(0)
    stride_w1n = W1.stride(1)
    stride_b1 = B1.stride(0)
    stride_w2k = W2.stride(0)
    stride_w2n = W2.stride(1)
    stride_b2 = B2.stride(0)

    # Max pass
    max1 = torch.full((M,), -10000.0, dtype=torch.float32, device=device)
    max2 = torch.full((M,), -10000.0, dtype=torch.float32, device=device)
    max_kernel[grid](
        max1,
        max2,
        X,
        W1,
        B1,
        W2,
        B2,
        M,
        K,
        N,
        stride_xm,
        stride_xk,
        stride_w1k,
        stride_w1n,
        stride_b1,
        stride_w2k,
        stride_w2n,
        stride_b2,
        BLOCK_M=BLOCK_M,
        BLOCK_N=BLOCK_N,
        BLOCK_K=BLOCK_K
    )

    # Sum exp pass
    sum_exp1 = torch.zeros((M,), dtype=torch.float32, device=device)
    sum_exp2 = torch.zeros((M,), dtype=torch.float32, device=device)
    sum_exp_kernel[grid](
        sum_exp1,
        sum_exp2,
        max1,
        max2,
        X,
        W1,
        B1,
        W2,
        B2,
        M,
        K,
        N,
        stride_xm,
        stride_xk,
        stride_w1k,
        stride_w1n,
        stride_b1,
        stride_w2k,
        stride_w2n,
        stride_b2,
        BLOCK_M=BLOCK_M,
        BLOCK_N=BLOCK_N,
        BLOCK_K=BLOCK_K
    )

    # Compute LSE
    lse1 = max1 + torch.log(sum_exp1.clamp(min=1e-8))
    lse2 = max2 + torch.log(sum_exp2.clamp(min=1e-8))

    # JSD pass
    sum_p_logits1 = torch.zeros((M,), dtype=torch.float32, device=device)
    sum_q_logits2 = torch.zeros((M,), dtype=torch.float32, device=device)
    sum_p_logm = torch.zeros((M,), dtype=torch.float32, device=device)
    sum_q_logm = torch.zeros((M,), dtype=torch.float32, device=device)
    jsd_kernel[grid](
        sum_p_logits1,
        sum_q_logits2,
        sum_p_logm,
        sum_q_logm,
        lse1,
        lse2,
        X,
        W1,
        B1,
        W2,
        B2,
        M,
        K,
        N,
        stride_xm,
        stride_xk,
        stride_w1k,
        stride_w1n,
        stride_b1,
        stride_w2k,
        stride_w2n,
        stride_b2,
        BLOCK_M=BLOCK_M,
        BLOCK_N=BLOCK_N,
        BLOCK_K=BLOCK_K
    )

    # Compute JSD
    sum_p_logp = sum_p_logits1 - lse1
    sum_q_logq = sum_q_logits2 - lse2
    klp = sum_p_logp - sum_p_logm
    klq = sum_q_logq - sum_q_logm
    output = 0.5 * (klp + klq)
    return output
"""
        return {"code": code}
