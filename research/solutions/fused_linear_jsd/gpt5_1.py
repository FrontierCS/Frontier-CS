import torch
import triton
import triton.language as tl
import math


class Solution:
    def solve(self, spec_path: str = None) -> dict:
        code = r'''
import torch
import triton
import triton.language as tl
import math


@triton.jit
def _jsd_from_logits_kernel(
    L1_ptr, L2_ptr,
    M, N,
    stride_l1_m, stride_l1_n,
    stride_l2_m, stride_l2_n,
    OUT_ptr,
    BLOCK_M: tl.constexpr,
    BLOCK_N: tl.constexpr,
    EPS: tl.constexpr,
):
    pid_m = tl.program_id(0)
    offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
    mask_m = offs_m < M

    # Initialize running stats for branch 1 and 2
    neg_inf = -float('inf')
    m1 = tl.full((BLOCK_M,), neg_inf, tl.float32)
    m2 = tl.full((BLOCK_M,), neg_inf, tl.float32)
    s1 = tl.zeros((BLOCK_M,), tl.float32)
    s2 = tl.zeros((BLOCK_M,), tl.float32)
    t1 = tl.zeros((BLOCK_M,), tl.float32)
    t2 = tl.zeros((BLOCK_M,), tl.float32)

    # Pointers row base
    row_ptrs_l1 = L1_ptr + offs_m[:, None] * stride_l1_m
    row_ptrs_l2 = L2_ptr + offs_m[:, None] * stride_l2_m

    # Pass 1: streaming log-sum-exp and weighted sums t1/t2
    n_start = 0
    while n_start < N:
        offs_n = n_start + tl.arange(0, BLOCK_N)
        mask_n = offs_n < N
        mask = mask_m[:, None] & mask_n[None, :]

        ptrs1 = row_ptrs_l1 + offs_n[None, :] * stride_l1_n
        ptrs2 = row_ptrs_l2 + offs_n[None, :] * stride_l2_n

        l1 = tl.load(ptrs1, mask=mask, other=neg_inf)
        l2 = tl.load(ptrs2, mask=mask, other=neg_inf)

        # Row-wise maxima for this tile
        rmax1 = tl.max(l1, axis=1)
        rmax2 = tl.max(l2, axis=1)

        # Update streaming lse for branch 1
        m1_new = tl.maximum(m1, rmax1)
        scale1 = tl.exp(m1 - m1_new)
        l1_shift = l1 - m1_new[:, None]
        exp_l1_shift = tl.exp(l1_shift)
        s1 = s1 * scale1 + tl.sum(exp_l1_shift, axis=1)
        # weighted sum with original logits (not shifted)
        t1 = t1 * scale1 + tl.sum(exp_l1_shift * l1, axis=1)
        m1 = m1_new

        # Update streaming lse for branch 2
        m2_new = tl.maximum(m2, rmax2)
        scale2 = tl.exp(m2 - m2_new)
        l2_shift = l2 - m2_new[:, None]
        exp_l2_shift = tl.exp(l2_shift)
        s2 = s2 * scale2 + tl.sum(exp_l2_shift, axis=1)
        t2 = t2 * scale2 + tl.sum(exp_l2_shift * l2, axis=1)
        m2 = m2_new

        n_start += BLOCK_N

    # Final LSE and SP, SQ
    # Guard invalid rows by setting A/B to 0 to avoid NaNs in next pass
    # A = LSE1, B = LSE2
    log_s1 = tl.log(s1 + EPS)
    log_s2 = tl.log(s2 + EPS)
    A = m1 + log_s1
    B = m2 + log_s2

    # S_P = sum P*log P = t1/s1 - A
    inv_s1 = 1.0 / (s1 + EPS)
    inv_s2 = 1.0 / (s2 + EPS)
    SP = t1 * inv_s1 - A
    SQ = t2 * inv_s2 - B

    # For invalid rows, set A/B to 0 and SP/SQ to 0 so computations are benign
    A = tl.where(mask_m, A, 0.0)
    B = tl.where(mask_m, B, 0.0)
    SP = tl.where(mask_m, SP, 0.0)
    SQ = tl.where(mask_m, SQ, 0.0)

    # Pass 2: accumulate sum_n ( (P+Q) * log(P+Q) )
    sMq = tl.zeros((BLOCK_M,), tl.float32)

    n_start = 0
    while n_start < N:
        offs_n = n_start + tl.arange(0, BLOCK_N)
        mask_n = offs_n < N
        mask = mask_m[:, None] & mask_n[None, :]

        ptrs1 = row_ptrs_l1 + offs_n[None, :] * stride_l1_n
        ptrs2 = row_ptrs_l2 + offs_n[None, :] * stride_l2_n

        l1 = tl.load(ptrs1, mask=mask, other=neg_inf)
        l2 = tl.load(ptrs2, mask=mask, other=neg_inf)

        LP = l1 - A[:, None]
        LQ = l2 - B[:, None]

        p = tl.exp(LP)
        q = tl.exp(LQ)
        y = p + q
        # y*log(y) with safe epsilon
        yS = y * tl.log(y + EPS)

        sMq += tl.sum(yS, axis=1)

        n_start += BLOCK_N

    # JSD = 0.5 * (SP + SQ - sMq) + ln(2)
    ln2 = 0.6931471805599453
    jsd = 0.5 * (SP + SQ - sMq) + ln2

    # Store
    tl.store(OUT_ptr + offs_m, jsd, mask=mask_m)


def fused_linear_jsd(X: torch.Tensor, W1: torch.Tensor, B1: torch.Tensor, W2: torch.Tensor, B2: torch.Tensor) -> torch.Tensor:
    """
    Fused linear layers with Jensen-Shannon Divergence computation.

    Args:
        X: Input tensor of shape (M, K) - input features (float16)
        W1: Weight tensor of shape (K, N) - first weight matrix (float16)
        B1: Bias tensor of shape (N,) - first bias vector (float32)
        W2: Weight tensor of shape (K, N) - second weight matrix (float16)
        B2: Bias tensor of shape (N,) - second bias vector (float32)

    Returns:
        Output tensor of shape (M,) - Jensen-Shannon Divergence per sample (float32)
    """
    assert X.is_cuda and W1.is_cuda and W2.is_cuda and B1.is_cuda and B2.is_cuda, "All tensors must be on CUDA"
    assert X.dim() == 2 and W1.dim() == 2 and W2.dim() == 2, "X, W1, W2 must be 2D"
    assert B1.dim() == 1 and B2.dim() == 1, "B1, B2 must be 1D"
    M, K = X.shape
    K1, N = W1.shape
    K2, N2 = W2.shape
    assert K == K1 == K2, "K dimensions must match"
    assert N == N2 == B1.shape[0] == B2.shape[0], "N dimensions must match"

    # Ensure dtypes
    if X.dtype != torch.float16:
        X = X.to(torch.float16)
    if W1.dtype != torch.float16:
        W1 = W1.to(torch.float16)
    if W2.dtype != torch.float16:
        W2 = W2.to(torch.float16)
    if B1.dtype != torch.float32:
        B1 = B1.to(torch.float32)
    if B2.dtype != torch.float32:
        B2 = B2.to(torch.float32)

    # Compute logits via cuBLAS (fp16 matmul) then upcast and add bias
    # Using contiguous for better memory access in kernel
    logits1 = (X @ W1).to(torch.float32)
    logits1.add_(B1)
    logits1 = logits1.contiguous()

    logits2 = (X @ W2).to(torch.float32)
    logits2.add_(B2)
    logits2 = logits2.contiguous()

    # Allocate output
    out = torch.empty((M,), device=X.device, dtype=torch.float32)

    # Kernel launch params
    # Reasonable defaults for L4 / large N
    BLOCK_M = 32
    # Choose BLOCK_N based on N heuristics
    if N >= 4096:
        BLOCK_N = 128
        num_warps = 4
    elif N >= 2048:
        BLOCK_N = 128
        num_warps = 4
    else:
        BLOCK_N = 64
        num_warps = 4

    grid = ( (M + BLOCK_M - 1) // BLOCK_M, )

    _jsd_from_logits_kernel[grid](
        logits1, logits2,
        M, N,
        logits1.stride(0), logits1.stride(1),
        logits2.stride(0), logits2.stride(1),
        out,
        BLOCK_M=BLOCK_M,
        BLOCK_N=BLOCK_N,
        EPS=1e-20,
        num_warps=num_warps,
        num_stages=2,
    )
    return out
'''
        return {"code": code}