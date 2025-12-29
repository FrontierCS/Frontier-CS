import torch
import triton
import triton.language as tl

@triton.jit
def fused_linear_kernel(
    X_PTR, W1_PTR, B1_PTR, W2_PTR, B2_PTR, LOGITS1_PTR, LOGITS2_PTR,
    M, K, N,
    STRIDE_XM, STRIDE_XK,
    STRIDE_W1K, STRIDE_W1N,
    STRIDE_B1N,
    STRIDE_W2K, STRIDE_W2N,
    STRIDE_B2N,
    STRIDE_L1M, STRIDE_L1N,
    STRIDE_L2M, STRIDE_L2N,
    BLOCK_M: tl.constexpr,
    BLOCK_N: tl.constexpr,
    BLOCK_K: tl.constexpr
):
    pid = tl.program_id(0)
    num_pid_in_row = tl.cdiv(N, BLOCK_N)
    row_pid = pid // num_pid_in_row
    col_pid = pid % num_pid_in_row

    offs_m = row_pid * BLOCK_M + tl.arange(0, BLOCK_M)
    offs_n = col_pid * BLOCK_N + tl.arange(0, BLOCK_N)
    offs_m_mask = offs_m < M
    offs_n_mask = offs_n < N

    acc1 = tl.zeros((BLOCK_M, BLOCK_N), dtype=tl.float32)
    acc2 = tl.zeros((BLOCK_M, BLOCK_N), dtype=tl.float32)

    lo = 0
    while lo < K:
        offs_k = lo + tl.arange(0, BLOCK_K)
        x_ptrs = X_PTR + offs_m[:, None] * STRIDE_XM + offs_k[None, :] * STRIDE_XK
        x_mask = offs_m_mask[:, None] & (offs_k[None, :] < K)
        x = tl.load(x_ptrs, mask=x_mask, other=0.0, eviction_policy="evict_last").to(tl.float32)

        w1_ptrs = W1_PTR + offs_k[:, None] * STRIDE_W1K + offs_n[None, :] * STRIDE_W1N
        w1_mask = (offs_k[:, None] < K) & offs_n_mask[None, :]
        w1 = tl.load(w1_ptrs, mask=w1_mask, other=0.0, eviction_policy="evict_last").to(tl.float32)
        acc1 += tl.dot(x, w1)

        w2_ptrs = W2_PTR + offs_k[:, None] * STRIDE_W2K + offs_n[None, :] * STRIDE_W2N
        w2_mask = (offs_k[:, None] < K) & offs_n_mask[None, :]
        w2 = tl.load(w2_ptrs, mask=w2_mask, other=0.0, eviction_policy="evict_last").to(tl.float32)
        acc2 += tl.dot(x, w2)

        lo += BLOCK_K

    b1_ptrs = B1_PTR + offs_n * STRIDE_B1N
    b1_mask = offs_n_mask
    b1 = tl.load(b1_ptrs, mask=b1_mask, other=0.0)
    acc1 += b1[None, :]

    b2_ptrs = B2_PTR + offs_n * STRIDE_B2N
    b2_mask = offs_n_mask
    b2 = tl.load(b2_ptrs, mask=b2_mask, other=0.0)
    acc2 += b2[None, :]

    l1_ptrs = LOGITS1_PTR + offs_m[:, None] * STRIDE_L1M + offs_n[None, :] * STRIDE_L1N
    l1_mask = offs_m_mask[:, None] & offs_n_mask[None, :]
    tl.store(l1_ptrs, acc1, mask=l1_mask)

    l2_ptrs = LOGITS2_PTR + offs_m[:, None] * STRIDE_L2M + offs_n[None, :] * STRIDE_L2N
    l2_mask = offs_m_mask[:, None] & offs_n_mask[None, :]
    tl.store(l2_ptrs, acc2, mask=l2_mask)


def fused_linear_jsd(X: torch.Tensor, W1: torch.Tensor, B1: torch.Tensor, W2: torch.Tensor, B2: torch.Tensor) -> torch.Tensor:
    M, K = X.shape
    N = W1.shape[1]
    assert W1.shape == (K, N)
    assert W2.shape == (K, N)
    assert B1.shape[0] == N
    assert B2.shape[0] == N

    logits1 = torch.empty((M, N), dtype=torch.float32, device=X.device)
    logits2 = torch.empty((M, N), dtype=torch.float32, device=X.device)

    BLOCK_M = 128
    BLOCK_N = 128
    BLOCK_K = 128

    def grid(meta):
        return (triton.cdiv(M, meta['BLOCK_M']) * triton.cdiv(N, meta['BLOCK_N']), )

    fused_linear_kernel[grid](
        X, W1, B1, W2, B2, logits1, logits2,
        M, K, N,
        X.stride(0), X.stride(1),
        W1.stride(0), W1.stride(1),
        B1.stride(0),
        W2.stride(0), W2.stride(1),
        B2.stride(0),
        logits1.stride(0), logits1.stride(1),
        logits2.stride(0), logits2.stride(1),
        BLOCK_M=BLOCK_M,
        BLOCK_N=BLOCK_N,
        BLOCK_K=BLOCK_K,
        num_stages=4,
        num_warps=8
    )

    lse1 = torch.logsumexp(logits1, dim=1)
    lse2 = torch.logsumexp(logits2, dim=1)

    log_p = logits1 - lse1.unsqueeze(1)
    log_q = logits2 - lse2.unsqueeze(1)
    p = torch.exp(log_p)
    q = torch.exp(log_q)
    m = 0.5 * (p + q)
    m = torch.clamp(m, min=1e-8)
    log_m = torch.log(m)

    kl_pm = torch.sum(p * (log_p - log_m), dim=1)
    kl_qm = torch.sum(q * (log_q - log_m), dim=1)
    jsd = 0.5 * (kl_pm + kl_qm)

    return jsd


class Solution:
    def solve(self, spec_path: str = None) -> dict:
        code = """import torch
import triton
import triton.language as tl

@triton.jit
def fused_linear_kernel(
    X_PTR, W1_PTR, B1_PTR, W2_PTR, B2_PTR, LOGITS1_PTR, LOGITS2_PTR,
    M, K, N,
    STRIDE_XM, STRIDE_XK,
    STRIDE_W1K, STRIDE_W1N,
    STRIDE_B1N,
    STRIDE_W2K, STRIDE_W2N,
    STRIDE_B2N,
    STRIDE_L1M, STRIDE_L1N,
    STRIDE_L2M, STRIDE_L2N,
    BLOCK_M: tl.constexpr,
    BLOCK_N: tl.constexpr,
    BLOCK_K: tl.constexpr
):
    pid = tl.program_id(0)
    num_pid_in_row = tl.cdiv(N, BLOCK_N)
    row_pid = pid // num_pid_in_row
    col_pid = pid % num_pid_in_row

    offs_m = row_pid * BLOCK_M + tl.arange(0, BLOCK_M)
    offs_n = col_pid * BLOCK_N + tl.arange(0, BLOCK_N)
    offs_m_mask = offs_m < M
    offs_n_mask = offs_n < N

    acc1 = tl.zeros((BLOCK_M, BLOCK_N), dtype=tl.float32)
    acc2 = tl.zeros((BLOCK_M, BLOCK_N), dtype=tl.float32)

    lo = 0
    while lo < K:
        offs_k = lo + tl.arange(0, BLOCK_K)
        x_ptrs = X_PTR + offs_m[:, None] * STRIDE_XM + offs_k[None, :] * STRIDE_XK
        x_mask = offs_m_mask[:, None] & (offs_k[None, :] < K)
        x = tl.load(x_ptrs, mask=x_mask, other=0.0, eviction_policy="evict_last").to(tl.float32)

        w1_ptrs = W1_PTR + offs_k[:, None] * STRIDE_W1K + offs_n[None, :] * STRIDE_W1N
        w1_mask = (offs_k[:, None] < K) & offs_n_mask[None, :]
        w1 = tl.load(w1_ptrs, mask=w1_mask, other=0.0, eviction_policy="evict_last").to(tl.float32)
        acc1 += tl.dot(x, w1)

        w2_ptrs = W2_PTR + offs_k[:, None] * STRIDE_W2K + offs_n[None, :] * STRIDE_W2N
        w2_mask = (offs_k[:, None] < K) & offs_n_mask[None, :]
        w2 = tl.load(w2_ptrs, mask=w2_mask, other=0.0, eviction_policy="evict_last").to(tl.float32)
        acc2 += tl.dot(x, w2)

        lo += BLOCK_K

    b1_ptrs = B1_PTR + offs_n * STRIDE_B1N
    b1_mask = offs_n_mask
    b1 = tl.load(b1_ptrs, mask=b1_mask, other=0.0)
    acc1 += b1[None, :]

    b2_ptrs = B2_PTR + offs_n * STRIDE_B2N
    b2_mask = offs_n_mask
    b2 = tl.load(b2_ptrs, mask=b2_mask, other=0.0)
    acc2 += b2[None, :]

    l1_ptrs = LOGITS1_PTR + offs_m[:, None] * STRIDE_L1M + offs_n[None, :] * STRIDE_L1N
    l1_mask = offs_m_mask[:, None] & offs_n_mask[None, :]
    tl.store(l1_ptrs, acc1, mask=l1_mask)

    l2_ptrs = LOGITS2_PTR + offs_m[:, None] * STRIDE_L2M + offs_n[None, :] * STRIDE_L2N
    l2_mask = offs_m_mask[:, None] & offs_n_mask[None, :]
    tl.store(l2_ptrs, acc2, mask=l2_mask)


def fused_linear_jsd(X: torch.Tensor, W1: torch.Tensor, B1: torch.Tensor, W2: torch.Tensor, B2: torch.Tensor) -> torch.Tensor:
    M, K = X.shape
    N = W1.shape[1]
    assert W1.shape == (K, N)
    assert W2.shape == (K, N)
    assert B1.shape[0] == N
    assert B2.shape[0] == N

    logits1 = torch.empty((M, N), dtype=torch.float32, device=X.device)
    logits2 = torch.empty((M, N), dtype=torch.float32, device=X.device)

    BLOCK_M = 128
    BLOCK_N = 128
    BLOCK_K = 128

    def grid(meta):
        return (triton.cdiv(M, meta['BLOCK_M']) * triton.cdiv(N, meta['BLOCK_N']), )

    fused_linear_kernel[grid](
        X, W1, B1, W2, B2, logits1, logits2,
        M, K, N,
        X.stride(0), X.stride(1),
        W1.stride(0), W1.stride(1),
        B1.stride(0),
        W2.stride(0), W2.stride(1),
        B2.stride(0),
        logits1.stride(0), logits1.stride(1),
        logits2.stride(0), logits2.stride(1),
        BLOCK_M=BLOCK_M,
        BLOCK_N=BLOCK_N,
        BLOCK_K=BLOCK_K,
        num_stages=4,
        num_warps=8
    )

    lse1 = torch.logsumexp(logits1, dim=1)
    lse2 = torch.logsumexp(logits2, dim=1)

    log_p = logits1 - lse1.unsqueeze(1)
    log_q = logits2 - lse2.unsqueeze(1)
    p = torch.exp(log_p)
    q = torch.exp(log_q)
    m = 0.5 * (p + q)
    m = torch.clamp(m, min=1e-8)
    log_m = torch.log(m)

    kl_pm = torch.sum(p * (log_p - log_m), dim=1)
    kl_qm = torch.sum(q * (log_q - log_m), dim=1)
    jsd = 0.5 * (kl_pm + kl_qm)

    return jsd
"""
        return {"code": code}