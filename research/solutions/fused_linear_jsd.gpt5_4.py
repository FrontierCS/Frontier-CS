import os
import torch
import triton
import triton.language as tl


@triton.jit
def _pass1_update_kernel(
    X_ptr, W1_ptr, B1_ptr, W2_ptr, B2_ptr,
    m1_ptr, s1_ptr, m2_ptr, s2_ptr,
    M, N, K,
    stride_xm, stride_xk,
    stride_w1k, stride_w1n,
    stride_w2k, stride_w2n,
    n_start,
    BLOCK_M: tl.constexpr, BLOCK_N: tl.constexpr, BLOCK_K: tl.constexpr,
):
    pid_m = tl.program_id(0)
    offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
    offs_n = n_start + tl.arange(0, BLOCK_N)
    offs_k = tl.arange(0, BLOCK_K)

    mask_m = offs_m < M
    mask_n = offs_n < N

    # Accumulate matmul for the tile
    acc1 = tl.zeros((BLOCK_M, BLOCK_N), dtype=tl.float32)
    acc2 = tl.zeros((BLOCK_M, BLOCK_N), dtype=tl.float32)

    k0 = 0
    while k0 < K:
        kk = k0 + offs_k
        mask_x = (offs_m[:, None] < M) & (kk[None, :] < K)
        mask_w = (kk[:, None] < K) & (offs_n[None, :] < N)

        x_ptrs = X_ptr + (offs_m[:, None] * stride_xm + kk[None, :] * stride_xk)
        w1_ptrs = W1_ptr + (kk[:, None] * stride_w1k + offs_n[None, :] * stride_w1n)
        w2_ptrs = W2_ptr + (kk[:, None] * stride_w2k + offs_n[None, :] * stride_w2n)

        a = tl.load(x_ptrs, mask=mask_x, other=0.0)
        b1 = tl.load(w1_ptrs, mask=mask_w, other=0.0)
        b2 = tl.load(w2_ptrs, mask=mask_w, other=0.0)

        acc1 += tl.dot(a, b1)
        acc2 += tl.dot(a, b2)
        k0 += BLOCK_K

    # Add biases
    b1v = tl.load(B1_ptr + offs_n, mask=mask_n, other=0.0)
    b2v = tl.load(B2_ptr + offs_n, mask=mask_n, other=0.0)
    acc1 += b1v[None, :]
    acc2 += b2v[None, :]

    valid_mask = (offs_m[:, None] < M) & (offs_n[None, :] < N)

    neg_inf = -float("inf")

    acc1_masked = tl.where(valid_mask, acc1, neg_inf)
    acc2_masked = tl.where(valid_mask, acc2, neg_inf)

    # Row-wise max for this tile
    tile_max1 = tl.max(acc1_masked, axis=1)
    tile_max2 = tl.max(acc2_masked, axis=1)

    # Load previous m and s
    m1_old = tl.load(m1_ptr + offs_m, mask=mask_m, other=neg_inf)
    s1_old = tl.load(s1_ptr + offs_m, mask=mask_m, other=0.0)
    m2_old = tl.load(m2_ptr + offs_m, mask=mask_m, other=neg_inf)
    s2_old = tl.load(s2_ptr + offs_m, mask=mask_m, other=0.0)

    # Update m and s with streaming log-sum-exp
    new_m1 = tl.maximum(m1_old, tile_max1)
    new_m2 = tl.maximum(m2_old, tile_max2)

    exp_scale1 = tl.exp(m1_old - new_m1)
    exp_scale2 = tl.exp(m2_old - new_m2)

    sum_exp_tile1 = tl.sum(tl.exp(acc1_masked - new_m1[:, None]), axis=1)
    sum_exp_tile2 = tl.sum(tl.exp(acc2_masked - new_m2[:, None]), axis=1)

    new_s1 = s1_old * exp_scale1 + sum_exp_tile1
    new_s2 = s2_old * exp_scale2 + sum_exp_tile2

    tl.store(m1_ptr + offs_m, new_m1, mask=mask_m)
    tl.store(s1_ptr + offs_m, new_s1, mask=mask_m)
    tl.store(m2_ptr + offs_m, new_m2, mask=mask_m)
    tl.store(s2_ptr + offs_m, new_s2, mask=mask_m)


@triton.jit
def _pass2_update_kernel(
    X_ptr, W1_ptr, B1_ptr, W2_ptr, B2_ptr,
    lse1_ptr, lse2_ptr,
    out_ptr,
    M, N, K,
    stride_xm, stride_xk,
    stride_w1k, stride_w1n,
    stride_w2k, stride_w2n,
    n_start,
    BLOCK_M: tl.constexpr, BLOCK_N: tl.constexpr, BLOCK_K: tl.constexpr,
):
    pid_m = tl.program_id(0)
    offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
    offs_n = n_start + tl.arange(0, BLOCK_N)
    offs_k = tl.arange(0, BLOCK_K)

    mask_m = offs_m < M
    mask_n = offs_n < N

    # Matmul accumulators
    acc1 = tl.zeros((BLOCK_M, BLOCK_N), dtype=tl.float32)
    acc2 = tl.zeros((BLOCK_M, BLOCK_N), dtype=tl.float32)

    k0 = 0
    while k0 < K:
        kk = k0 + offs_k
        mask_x = (offs_m[:, None] < M) & (kk[None, :] < K)
        mask_w = (kk[:, None] < K) & (offs_n[None, :] < N)

        x_ptrs = X_ptr + (offs_m[:, None] * stride_xm + kk[None, :] * stride_xk)
        w1_ptrs = W1_ptr + (kk[:, None] * stride_w1k + offs_n[None, :] * stride_w1n)
        w2_ptrs = W2_ptr + (kk[:, None] * stride_w2k + offs_n[None, :] * stride_w2n)

        a = tl.load(x_ptrs, mask=mask_x, other=0.0)
        b1 = tl.load(w1_ptrs, mask=mask_w, other=0.0)
        b2 = tl.load(w2_ptrs, mask=mask_w, other=0.0)

        acc1 += tl.dot(a, b1)
        acc2 += tl.dot(a, b2)
        k0 += BLOCK_K

    # Add biases
    b1v = tl.load(B1_ptr + offs_n, mask=mask_n, other=0.0)
    b2v = tl.load(B2_ptr + offs_n, mask=mask_n, other=0.0)
    acc1 += b1v[None, :]
    acc2 += b2v[None, :]

    valid_mask = (offs_m[:, None] < M) & (offs_n[None, :] < N)

    # Load LSE values per row
    lse1 = tl.load(lse1_ptr + offs_m, mask=mask_m, other=0.0)
    lse2 = tl.load(lse2_ptr + offs_m, mask=mask_m, other=0.0)

    # Compute logP, logQ
    logP = acc1 - lse1[:, None]
    logQ = acc2 - lse2[:, None]

    # Stable computation of logM = log(0.5 * (exp(logP) + exp(logQ)))
    # m_pair per element
    # For invalid positions, set m_pair = 0 to avoid -inf - -inf
    mpair = tl.where(valid_mask, tl.maximum(logP, logQ), 0.0)
    z1 = tl.where(valid_mask, tl.exp(logP - mpair), 0.0)
    z2 = tl.where(valid_mask, tl.exp(logQ - mpair), 0.0)
    ln2 = 0.6931471805599453
    logM = tl.where(valid_mask, mpair + tl.log(z1 + z2) - ln2, 0.0)

    P = tl.where(valid_mask, tl.exp(logP), 0.0)
    Q = tl.where(valid_mask, tl.exp(logQ), 0.0)

    contrib = P * (logP - logM) + Q * (logQ - logM)

    row_sum = tl.sum(contrib, axis=1)

    # Accumulate into output: out += 0.5 * row_sum
    out_old = tl.load(out_ptr + offs_m, mask=mask_m, other=0.0)
    out_new = out_old + 0.5 * row_sum
    tl.store(out_ptr + offs_m, out_new, mask=mask_m)


def fused_linear_jsd(X: torch.Tensor, W1: torch.Tensor, B1: torch.Tensor, W2: torch.Tensor, B2: torch.Tensor) -> torch.Tensor:
    """
    Fused linear layers with Jensen-Shannon Divergence computation.
    Args:
        X: (M, K) float16 CUDA
        W1: (K, N) float16 CUDA
        B1: (N,) float32 CUDA
        W2: (K, N) float16 CUDA
        B2: (N,) float32 CUDA
    Returns:
        (M,) float32 CUDA tensor with JSD per sample
    """
    assert X.is_cuda and W1.is_cuda and W2.is_cuda and B1.is_cuda and B2.is_cuda
    assert X.dtype == torch.float16
    assert W1.dtype == torch.float16 and W2.dtype == torch.float16
    assert B1.dtype == torch.float32 and B2.dtype == torch.float32
    M, K = X.shape
    K1, N = W1.shape
    K2, N2 = W2.shape
    assert K1 == K and K2 == K and N2 == N
    assert B1.numel() == N and B2.numel() == N

    # Allocate temporary buffers
    device = X.device
    m1 = torch.full((M,), float("-inf"), dtype=torch.float32, device=device)
    s1 = torch.zeros((M,), dtype=torch.float32, device=device)
    m2 = torch.full((M,), float("-inf"), dtype=torch.float32, device=device)
    s2 = torch.zeros((M,), dtype=torch.float32, device=device)

    # Tuning parameters
    BLOCK_M = 32
    BLOCK_N = 128
    BLOCK_K = 32
    num_warps = 8
    num_stages = 4

    grid = lambda META: (triton.cdiv(M, META["BLOCK_M"]),)

    # Pass 1: stream over N blocks to compute LSE for both logits
    for n_start in range(0, N, BLOCK_N):
        _pass1_update_kernel[grid](
            X, W1, B1, W2, B2,
            m1, s1, m2, s2,
            M, N, K,
            X.stride(0), X.stride(1),
            W1.stride(0), W1.stride(1),
            W2.stride(0), W2.stride(1),
            n_start,
            BLOCK_M=BLOCK_M, BLOCK_N=BLOCK_N, BLOCK_K=BLOCK_K,
            num_warps=num_warps, num_stages=num_stages
        )

    # Compute LSE values
    lse1 = torch.log(s1) + m1
    lse2 = torch.log(s2) + m2

    # Pass 2: compute JSD accumulation using the LSE values
    out = torch.zeros((M,), dtype=torch.float32, device=device)
    for n_start in range(0, N, BLOCK_N):
        _pass2_update_kernel[grid](
            X, W1, B1, W2, B2,
            lse1, lse2, out,
            M, N, K,
            X.stride(0), X.stride(1),
            W1.stride(0), W1.stride(1),
            W2.stride(0), W2.stride(1),
            n_start,
            BLOCK_M=BLOCK_M, BLOCK_N=BLOCK_N, BLOCK_K=BLOCK_K,
            num_warps=num_warps, num_stages=num_stages
        )

    return out


class Solution:
    def solve(self, spec_path: str = None) -> dict:
        code = inspect.getsource(triton)  # dummy to ensure import in the output code string
        program_code = (
            "import torch\n"
            "import triton\n"
            "import triton.language as tl\n\n"
            + inspect.getsource(_pass1_update_kernel)
            + "\n\n"
            + inspect.getsource(_pass2_update_kernel)
            + "\n\n"
            + inspect.getsource(fused_linear_jsd)
        )
        return {"code": program_code}