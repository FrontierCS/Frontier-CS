import torch
import triton
import triton.language as tl


@triton.jit
def _pass1_lse_kernel(
    X_ptr, W1_ptr, W2_ptr, B1_ptr, B2_ptr,
    LSE1_ptr, LSE2_ptr,
    M, N, K,
    stride_x_m, stride_x_k,
    stride_w_k, stride_w_n,
    BLOCK_M: tl.constexpr, BLOCK_N: tl.constexpr, BLOCK_K: tl.constexpr,
):
    pid_m = tl.program_id(0)
    offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
    mask_m = offs_m < M

    # Running log-sum-exp accumulators per row
    neg_inf = -1e9
    m1 = tl.full((BLOCK_M,), neg_inf, dtype=tl.float32)
    s1 = tl.zeros((BLOCK_M,), dtype=tl.float32)
    m2 = tl.full((BLOCK_M,), neg_inf, dtype=tl.float32)
    s2 = tl.zeros((BLOCK_M,), dtype=tl.float32)

    offs_k_inner = tl.arange(0, BLOCK_K)

    for n0 in range(0, N, BLOCK_N):
        offs_n = n0 + tl.arange(0, BLOCK_N)
        mask_n = offs_n < N

        acc1 = tl.zeros((BLOCK_M, BLOCK_N), dtype=tl.float32)
        acc2 = tl.zeros((BLOCK_M, BLOCK_N), dtype=tl.float32)

        for k0 in range(0, K, BLOCK_K):
            offs_k = k0 + offs_k_inner

            # Load tiles
            x_ptrs = X_ptr + offs_m[:, None] * stride_x_m + offs_k[None, :] * stride_x_k
            x = tl.load(x_ptrs, mask=(mask_m[:, None] & (offs_k[None, :] < K)), other=0.0)

            w1_ptrs = W1_ptr + offs_k[:, None] * stride_w_k + offs_n[None, :] * stride_w_n
            w2_ptrs = W2_ptr + offs_k[:, None] * stride_w_k + offs_n[None, :] * stride_w_n
            w1 = tl.load(w1_ptrs, mask=((offs_k[:, None] < K) & (offs_n[None, :] < N)), other=0.0)
            w2 = tl.load(w2_ptrs, mask=((offs_k[:, None] < K) & (offs_n[None, :] < N)), other=0.0)

            acc1 += tl.dot(x, w1)
            acc2 += tl.dot(x, w2)

        # Add bias
        b1 = tl.load(B1_ptr + offs_n, mask=mask_n, other=0.0)
        b2 = tl.load(B2_ptr + offs_n, mask=mask_n, other=0.0)
        acc1 += b1[None, :]
        acc2 += b2[None, :]

        valid = mask_n[None, :]
        acc1_masked = tl.where(valid, acc1, neg_inf)
        acc2_masked = tl.where(valid, acc2, neg_inf)

        tile_max1 = tl.max(acc1_masked, axis=1)
        tile_max2 = tl.max(acc2_masked, axis=1)

        # sumexp within tile relative to tile_max
        exp1 = tl.exp(acc1_masked - tile_max1[:, None])
        exp2 = tl.exp(acc2_masked - tile_max2[:, None])
        tile_sum1 = tl.sum(exp1, axis=1)
        tile_sum2 = tl.sum(exp2, axis=1)

        # Merge with running
        new_m1 = tl.maximum(m1, tile_max1)
        new_m2 = tl.maximum(m2, tile_max2)
        s1 = s1 * tl.exp(m1 - new_m1) + tile_sum1 * tl.exp(tile_max1 - new_m1)
        s2 = s2 * tl.exp(m2 - new_m2) + tile_sum2 * tl.exp(tile_max2 - new_m2)
        m1 = new_m1
        m2 = new_m2

    # Finalize LSE
    eps = 1e-20
    s1 = tl.maximum(s1, eps)
    s2 = tl.maximum(s2, eps)
    lse1 = tl.log(s1) + m1
    lse2 = tl.log(s2) + m2

    tl.store(LSE1_ptr + offs_m, lse1, mask=mask_m)
    tl.store(LSE2_ptr + offs_m, lse2, mask=mask_m)


@triton.jit
def _pass2_jsd_kernel(
    X_ptr, W1_ptr, W2_ptr, B1_ptr, B2_ptr,
    LSE1_ptr, LSE2_ptr,
    OUT_ptr,
    M, N, K,
    stride_x_m, stride_x_k,
    stride_w_k, stride_w_n,
    BLOCK_M: tl.constexpr, BLOCK_N: tl.constexpr, BLOCK_K: tl.constexpr,
):
    pid_m = tl.program_id(0)
    offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
    mask_m = offs_m < M

    lse1 = tl.load(LSE1_ptr + offs_m, mask=mask_m, other=0.0)
    lse2 = tl.load(LSE2_ptr + offs_m, mask=mask_m, other=0.0)

    sum_plogp = tl.zeros((BLOCK_M,), dtype=tl.float32)
    sum_qlogq = tl.zeros((BLOCK_M,), dtype=tl.float32)
    sum_mlogm = tl.zeros((BLOCK_M,), dtype=tl.float32)

    offs_k_inner = tl.arange(0, BLOCK_K)
    eps = 1e-20

    for n0 in range(0, N, BLOCK_N):
        offs_n = n0 + tl.arange(0, BLOCK_N)
        mask_n = offs_n < N

        acc1 = tl.zeros((BLOCK_M, BLOCK_N), dtype=tl.float32)
        acc2 = tl.zeros((BLOCK_M, BLOCK_N), dtype=tl.float32)

        for k0 in range(0, K, BLOCK_K):
            offs_k = k0 + offs_k_inner

            x_ptrs = X_ptr + offs_m[:, None] * stride_x_m + offs_k[None, :] * stride_x_k
            x = tl.load(x_ptrs, mask=(mask_m[:, None] & (offs_k[None, :] < K)), other=0.0)

            w1_ptrs = W1_ptr + offs_k[:, None] * stride_w_k + offs_n[None, :] * stride_w_n
            w2_ptrs = W2_ptr + offs_k[:, None] * stride_w_k + offs_n[None, :] * stride_w_n
            w1 = tl.load(w1_ptrs, mask=((offs_k[:, None] < K) & (offs_n[None, :] < N)), other=0.0)
            w2 = tl.load(w2_ptrs, mask=((offs_k[:, None] < K) & (offs_n[None, :] < N)), other=0.0)

            acc1 += tl.dot(x, w1)
            acc2 += tl.dot(x, w2)

        b1 = tl.load(B1_ptr + offs_n, mask=(offs_n < N), other=0.0)
        b2 = tl.load(B2_ptr + offs_n, mask=(offs_n < N), other=0.0)
        acc1 += b1[None, :]
        acc2 += b2[None, :]

        # Compute probabilities
        shift1 = acc1 - lse1[:, None]
        shift2 = acc2 - lse2[:, None]

        valid = (offs_n < N)[None, :]
        # Zero out invalid columns
        shift1 = tl.where(valid, shift1, -1e9)
        shift2 = tl.where(valid, shift2, -1e9)

        p = tl.exp(shift1)
        q = tl.exp(shift2)

        # p*log p and q*log q
        plogp = p * shift1
        qlogq = q * shift2

        sum_plogp += tl.sum(plogp, axis=1)
        sum_qlogq += tl.sum(qlogq, axis=1)

        # m*log m for M = 0.5*(p+q)
        m = 0.5 * (p + q)
        m = tl.where(valid, m, 0.0)
        m_log_m = m * tl.log(tl.maximum(m, eps))
        sum_mlogm += tl.sum(m_log_m, axis=1)

    jsd = 0.5 * sum_plogp + 0.5 * sum_qlogq - sum_mlogm
    tl.store(OUT_ptr + offs_m, jsd, mask=mask_m)


def fused_linear_jsd(X: torch.Tensor, W1: torch.Tensor, B1: torch.Tensor, W2: torch.Tensor, B2: torch.Tensor) -> torch.Tensor:
    """
    Fused linear layers with Jensen-Shannon Divergence computation.
    
    Args:
        X: (M, K), float16
        W1: (K, N), float16
        B1: (N,), float32
        W2: (K, N), float16
        B2: (N,), float32
    
    Returns:
        (M,), float32
    """
    assert X.is_cuda and W1.is_cuda and W2.is_cuda and B1.is_cuda and B2.is_cuda
    assert X.dtype == torch.float16 and W1.dtype == torch.float16 and W2.dtype == torch.float16
    assert B1.dtype == torch.float32 and B2.dtype == torch.float32
    M, K = X.shape
    K_w1, N = W1.shape
    K_w2, N2 = W2.shape
    assert K_w1 == K and K_w2 == K and N2 == N
    assert B1.shape[0] == N and B2.shape[0] == N

    device = X.device
    lse1 = torch.empty((M,), dtype=torch.float32, device=device)
    lse2 = torch.empty((M,), dtype=torch.float32, device=device)
    out = torch.empty((M,), dtype=torch.float32, device=device)

    # Strides in elements
    stride_x_m, stride_x_k = X.stride()
    stride_w1_k, stride_w1_n = W1.stride()
    # For W2, assume same layout
    stride_w2_k, stride_w2_n = W2.stride()
    assert stride_w1_k == stride_w2_k and stride_w1_n == stride_w2_n, "W1 and W2 must have same strides"

    # Choose tile sizes heuristically
    BLOCK_M = 32
    BLOCK_N = 128 if N >= 512 else 64
    BLOCK_K = 64 if (K % 64 == 0) else 32
    num_warps = 4 if BLOCK_N <= 128 else 8
    num_stages = 3

    grid = (triton.cdiv(M, BLOCK_M),)

    _pass1_lse_kernel[grid](
        X, W1, W2, B1, B2,
        lse1, lse2,
        M, N, K,
        stride_x_m, stride_x_k,
        stride_w1_k, stride_w1_n,
        BLOCK_M=BLOCK_M, BLOCK_N=BLOCK_N, BLOCK_K=BLOCK_K,
        num_warps=num_warps, num_stages=num_stages
    )

    _pass2_jsd_kernel[grid](
        X, W1, W2, B1, B2,
        lse1, lse2,
        out,
        M, N, K,
        stride_x_m, stride_x_k,
        stride_w1_k, stride_w1_n,
        BLOCK_M=BLOCK_M, BLOCK_N=BLOCK_N, BLOCK_K=BLOCK_K,
        num_warps=num_warps, num_stages=num_stages
    )

    return out


class Solution:
    def solve(self, spec_path: str = None) -> dict:
        code = '''
import torch
import triton
import triton.language as tl


@triton.jit
def _pass1_lse_kernel(
    X_ptr, W1_ptr, W2_ptr, B1_ptr, B2_ptr,
    LSE1_ptr, LSE2_ptr,
    M, N, K,
    stride_x_m, stride_x_k,
    stride_w_k, stride_w_n,
    BLOCK_M: tl.constexpr, BLOCK_N: tl.constexpr, BLOCK_K: tl.constexpr,
):
    pid_m = tl.program_id(0)
    offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
    mask_m = offs_m < M

    # Running log-sum-exp accumulators per row
    neg_inf = -1e9
    m1 = tl.full((BLOCK_M,), neg_inf, dtype=tl.float32)
    s1 = tl.zeros((BLOCK_M,), dtype=tl.float32)
    m2 = tl.full((BLOCK_M,), neg_inf, dtype=tl.float32)
    s2 = tl.zeros((BLOCK_M,), dtype=tl.float32)

    offs_k_inner = tl.arange(0, BLOCK_K)

    for n0 in range(0, N, BLOCK_N):
        offs_n = n0 + tl.arange(0, BLOCK_N)
        mask_n = offs_n < N

        acc1 = tl.zeros((BLOCK_M, BLOCK_N), dtype=tl.float32)
        acc2 = tl.zeros((BLOCK_M, BLOCK_N), dtype=tl.float32)

        for k0 in range(0, K, BLOCK_K):
            offs_k = k0 + offs_k_inner

            # Load tiles
            x_ptrs = X_ptr + offs_m[:, None] * stride_x_m + offs_k[None, :] * stride_x_k
            x = tl.load(x_ptrs, mask=(mask_m[:, None] & (offs_k[None, :] < K)), other=0.0)

            w1_ptrs = W1_ptr + offs_k[:, None] * stride_w_k + offs_n[None, :] * stride_w_n
            w2_ptrs = W2_ptr + offs_k[:, None] * stride_w_k + offs_n[None, :] * stride_w_n
            w1 = tl.load(w1_ptrs, mask=((offs_k[:, None] < K) & (offs_n[None, :] < N)), other=0.0)
            w2 = tl.load(w2_ptrs, mask=((offs_k[:, None] < K) & (offs_n[None, :] < N)), other=0.0)

            acc1 += tl.dot(x, w1)
            acc2 += tl.dot(x, w2)

        # Add bias
        b1 = tl.load(B1_ptr + offs_n, mask=mask_n, other=0.0)
        b2 = tl.load(B2_ptr + offs_n, mask=mask_n, other=0.0)
        acc1 += b1[None, :]
        acc2 += b2[None, :]

        valid = mask_n[None, :]
        acc1_masked = tl.where(valid, acc1, neg_inf)
        acc2_masked = tl.where(valid, acc2, neg_inf)

        tile_max1 = tl.max(acc1_masked, axis=1)
        tile_max2 = tl.max(acc2_masked, axis=1)

        # sumexp within tile relative to tile_max
        exp1 = tl.exp(acc1_masked - tile_max1[:, None])
        exp2 = tl.exp(acc2_masked - tile_max2[:, None])
        tile_sum1 = tl.sum(exp1, axis=1)
        tile_sum2 = tl.sum(exp2, axis=1)

        # Merge with running
        new_m1 = tl.maximum(m1, tile_max1)
        new_m2 = tl.maximum(m2, tile_max2)
        s1 = s1 * tl.exp(m1 - new_m1) + tile_sum1 * tl.exp(tile_max1 - new_m1)
        s2 = s2 * tl.exp(m2 - new_m2) + tile_sum2 * tl.exp(tile_max2 - new_m2)
        m1 = new_m1
        m2 = new_m2

    # Finalize LSE
    eps = 1e-20
    s1 = tl.maximum(s1, eps)
    s2 = tl.maximum(s2, eps)
    lse1 = tl.log(s1) + m1
    lse2 = tl.log(s2) + m2

    tl.store(LSE1_ptr + offs_m, lse1, mask=mask_m)
    tl.store(LSE2_ptr + offs_m, lse2, mask=mask_m)


@triton.jit
def _pass2_jsd_kernel(
    X_ptr, W1_ptr, W2_ptr, B1_ptr, B2_ptr,
    LSE1_ptr, LSE2_ptr,
    OUT_ptr,
    M, N, K,
    stride_x_m, stride_x_k,
    stride_w_k, stride_w_n,
    BLOCK_M: tl.constexpr, BLOCK_N: tl.constexpr, BLOCK_K: tl.constexpr,
):
    pid_m = tl.program_id(0)
    offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
    mask_m = offs_m < M

    lse1 = tl.load(LSE1_ptr + offs_m, mask=mask_m, other=0.0)
    lse2 = tl.load(LSE2_ptr + offs_m, mask=mask_m, other=0.0)

    sum_plogp = tl.zeros((BLOCK_M,), dtype=tl.float32)
    sum_qlogq = tl.zeros((BLOCK_M,), dtype=tl.float32)
    sum_mlogm = tl.zeros((BLOCK_M,), dtype=tl.float32)

    offs_k_inner = tl.arange(0, BLOCK_K)
    eps = 1e-20

    for n0 in range(0, N, BLOCK_N):
        offs_n = n0 + tl.arange(0, BLOCK_N)
        mask_n = offs_n < N

        acc1 = tl.zeros((BLOCK_M, BLOCK_N), dtype=tl.float32)
        acc2 = tl.zeros((BLOCK_M, BLOCK_N), dtype=tl.float32)

        for k0 in range(0, K, BLOCK_K):
            offs_k = k0 + offs_k_inner

            x_ptrs = X_ptr + offs_m[:, None] * stride_x_m + offs_k[None, :] * stride_x_k
            x = tl.load(x_ptrs, mask=(mask_m[:, None] & (offs_k[None, :] < K)), other=0.0)

            w1_ptrs = W1_ptr + offs_k[:, None] * stride_w_k + offs_n[None, :] * stride_w_n
            w2_ptrs = W2_ptr + offs_k[:, None] * stride_w_k + offs_n[None, :] * stride_w_n
            w1 = tl.load(w1_ptrs, mask=((offs_k[:, None] < K) & (offs_n[None, :] < N)), other=0.0)
            w2 = tl.load(w2_ptrs, mask=((offs_k[:, None] < K) & (offs_n[None, :] < N)), other=0.0)

            acc1 += tl.dot(x, w1)
            acc2 += tl.dot(x, w2)

        b1 = tl.load(B1_ptr + offs_n, mask=(offs_n < N), other=0.0)
        b2 = tl.load(B2_ptr + offs_n, mask=(offs_n < N), other=0.0)
        acc1 += b1[None, :]
        acc2 += b2[None, :]

        # Compute probabilities
        shift1 = acc1 - lse1[:, None]
        shift2 = acc2 - lse2[:, None]

        valid = (offs_n < N)[None, :]
        shift1 = tl.where(valid, shift1, -1e9)
        shift2 = tl.where(valid, shift2, -1e9)

        p = tl.exp(shift1)
        q = tl.exp(shift2)

        # p*log p and q*log q
        plogp = p * shift1
        qlogq = q * shift2

        sum_plogp += tl.sum(plogp, axis=1)
        sum_qlogq += tl.sum(qlogq, axis=1)

        # m*log m for M = 0.5*(p+q)
        m = 0.5 * (p + q)
        m = tl.where(valid, m, 0.0)
        m_log_m = m * tl.log(tl.maximum(m, eps))
        sum_mlogm += tl.sum(m_log_m, axis=1)

    jsd = 0.5 * sum_plogp + 0.5 * sum_qlogq - sum_mlogm
    tl.store(OUT_ptr + offs_m, jsd, mask=mask_m)


def fused_linear_jsd(X: torch.Tensor, W1: torch.Tensor, B1: torch.Tensor, W2: torch.Tensor, B2: torch.Tensor) -> torch.Tensor:
    """
    Fused linear layers with Jensen-Shannon Divergence computation.
    
    Args:
        X: (M, K), float16
        W1: (K, N), float16
        B1: (N,), float32
        W2: (K, N), float16
        B2: (N,), float32
    
    Returns:
        (M,), float32
    """
    assert X.is_cuda and W1.is_cuda and W2.is_cuda and B1.is_cuda and B2.is_cuda
    assert X.dtype == torch.float16 and W1.dtype == torch.float16 and W2.dtype == torch.float16
    assert B1.dtype == torch.float32 and B2.dtype == torch.float32
    M, K = X.shape
    K_w1, N = W1.shape
    K_w2, N2 = W2.shape
    assert K_w1 == K and K_w2 == K and N2 == N
    assert B1.shape[0] == N and B2.shape[0] == N

    device = X.device
    lse1 = torch.empty((M,), dtype=torch.float32, device=device)
    lse2 = torch.empty((M,), dtype=torch.float32, device=device)
    out = torch.empty((M,), dtype=torch.float32, device=device)

    # Strides in elements
    stride_x_m, stride_x_k = X.stride()
    stride_w1_k, stride_w1_n = W1.stride()
    stride_w2_k, stride_w2_n = W2.stride()
    assert stride_w1_k == stride_w2_k and stride_w1_n == stride_w2_n, "W1 and W2 must have same strides"

    # Choose tile sizes heuristically
    BLOCK_M = 32
    BLOCK_N = 128 if N >= 512 else 64
    BLOCK_K = 64 if (K % 64 == 0) else 32
    num_warps = 4 if BLOCK_N <= 128 else 8
    num_stages = 3

    grid = (triton.cdiv(M, BLOCK_M),)

    _pass1_lse_kernel[grid](
        X, W1, W2, B1, B2,
        lse1, lse2,
        M, N, K,
        stride_x_m, stride_x_k,
        stride_w1_k, stride_w1_n,
        BLOCK_M=BLOCK_M, BLOCK_N=BLOCK_N, BLOCK_K=BLOCK_K,
        num_warps=num_warps, num_stages=num_stages
    )

    _pass2_jsd_kernel[grid](
        X, W1, W2, B1, B2,
        lse1, lse2,
        out,
        M, N, K,
        stride_x_m, stride_x_k,
        stride_w1_k, stride_w1_n,
        BLOCK_M=BLOCK_M, BLOCK_N=BLOCK_N, BLOCK_K=BLOCK_K,
        num_warps=num_warps, num_stages=num_stages
    )

    return out
'''
        return {"code": code}