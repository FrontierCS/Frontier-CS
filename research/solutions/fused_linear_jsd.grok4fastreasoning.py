import torch
import triton
import triton.language as tl
import inspect

class Solution:
    def solve(self, spec_path: str = None) -> dict:
        code = """
import torch
import triton
import triton.language as tl

@triton.jit
def linear_kernel(
    X_PTR, W1_PTR, B1_PTR, W2_PTR, B2_PTR, LOGITS1_PTR, LOGITS2_PTR,
    M: tl.int32, K: tl.int32, N: tl.int32,
    STRIDE_XM: tl.int32, STRIDE_XK: tl.int32,
    STRIDE_W1K: tl.int32, STRIDE_W1N: tl.int32,
    STRIDE_W2K: tl.int32, STRIDE_W2N: tl.int32,
    STRIDE_B1: tl.int32, STRIDE_B2: tl.int32,
    STRIDE_L1M: tl.int32, STRIDE_L1N: tl.int32,
    STRIDE_L2M: tl.int32, STRIDE_L2N: tl.int32,
    BLOCK_M: tl.constexpr, BLOCK_N: tl.constexpr, BLOCK_K: tl.constexpr
):
    pid_m = tl.program_id(0)
    pid_n = tl.program_id(1)
    offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
    offs_n = pid_n * BLOCK_N + tl.arange(0, BLOCK_N)
    offs_k = tl.arange(0, BLOCK_K)
    x_ptrs = X_PTR + (offs_m[:, None] * STRIDE_XM + offs_k[None, :] * STRIDE_XK) * 2
    w1_ptrs = W1_PTR + (offs_k[:, None] * STRIDE_W1K + offs_n[None, :] * STRIDE_W1N) * 2
    w2_ptrs = W2_PTR + (offs_k[:, None] * STRIDE_W2K + offs_n[None, :] * STRIDE_W2N) * 2
    lo1_ptrs = LOGITS1_PTR + (offs_m[:, None] * STRIDE_L1M + offs_n[None, :] * STRIDE_L1N) * 4
    lo2_ptrs = LOGITS2_PTR + (offs_m[:, None] * STRIDE_L2M + offs_n[None, :] * STRIDE_L2N) * 4
    b1_ptrs = B1_PTR + offs_n * STRIDE_B1 * 4
    b2_ptrs = B2_PTR + offs_n * STRIDE_B2 * 4
    acc1 = tl.zeros((BLOCK_M, BLOCK_N), dtype=tl.float32)
    acc2 = tl.zeros((BLOCK_M, BLOCK_N), dtype=tl.float32)
    for k in range(0, K, BLOCK_K):
        x_ptr = x_ptrs + k * STRIDE_XK * 2
        w1_ptr = w1_ptrs + k * STRIDE_W1K * 2
        w2_ptr = w2_ptrs + k * STRIDE_W2K * 2
        x_mask = (offs_m[:, None] < M) & ((offs_k[None, :] + k) < K)
        w_mask = ((offs_k[:, None] + k) < K) & (offs_n[None, :] < N)
        x = tl.load(x_ptr, mask=x_mask, other=tl.float16(0.0))
        w1 = tl.load(w1_ptr, mask=w_mask, other=tl.float16(0.0))
        w2 = tl.load(w2_ptr, mask=w_mask, other=tl.float16(0.0))
        acc1 += tl.dot(x, w1)
        acc2 += tl.dot(x, w2)
    b1_mask = offs_n < N
    b1 = tl.load(b1_ptrs, mask=b1_mask, other=0.0)
    b2 = tl.load(b2_ptrs, mask=b1_mask, other=0.0)
    acc1 += b1[None, :]
    acc2 += b2[None, :]
    store_mask = (offs_m[:, None] < M) & (offs_n[None, :] < N)
    tl.store(lo1_ptrs, acc1, mask=store_mask)
    tl.store(lo2_ptrs, acc2, mask=store_mask)

@triton.jit
def jsd_kernel(
    LOGITS1_PTR, LOGITS2_PTR, OUTPUT_PTR,
    M: tl.int32, N: tl.int32,
    STRIDE_L1M: tl.int32, STRIDE_L1N: tl.int32,
    STRIDE_L2M: tl.int32, STRIDE_L2N: tl.int32,
    STRIDE_OUT: tl.int32,
    BLOCK_N: tl.constexpr
):
    pid = tl.program_id(0)
    if pid >= M:
        return
    m = pid
    offs_n = tl.arange(0, BLOCK_N)
    l1_base = LOGITS1_PTR + m * STRIDE_L1M * 4
    l2_base = LOGITS2_PTR + m * STRIDE_L2M * 4
    out_ptr = OUTPUT_PTR + m * STRIDE_OUT * 4
    INF = 1e10
    max1 = -INF
    max2 = -INF
    for start_n in range(0, N, BLOCK_N):
        l1_offsets = (start_n + offs_n) * STRIDE_L1N * 4
        l2_offsets = (start_n + offs_n) * STRIDE_L2N * 4
        l1_ptr = l1_base + l1_offsets
        l2_ptr = l2_base + l2_offsets
        n_mask = (start_n + offs_n < N)
        l1_tile = tl.load(l1_ptr, mask=n_mask, other=-INF)
        l2_tile = tl.load(l2_ptr, mask=n_mask, other=-INF)
        tile_max1 = tl.max(l1_tile)
        tile_max2 = tl.max(l2_tile)
        max1 = tl.maximum(max1, tile_max1)
        max2 = tl.maximum(max2, tile_max2)
    sum_exp1 = 0.0
    sum_exp2 = 0.0
    for start_n in range(0, N, BLOCK_N):
        l1_offsets = (start_n + offs_n) * STRIDE_L1N * 4
        l2_offsets = (start_n + offs_n) * STRIDE_L2N * 4
        l1_ptr = l1_base + l1_offsets
        l2_ptr = l2_base + l2_offsets
        n_mask = (start_n + offs_n < N)
        l1_tile = tl.load(l1_ptr, mask=n_mask, other=-INF)
        l2_tile = tl.load(l2_ptr, mask=n_mask, other=-INF)
        exp1 = tl.exp(l1_tile - max1)
        exp2 = tl.exp(l2_tile - max2)
        sum_exp1 += tl.sum(exp1)
        sum_exp2 += tl.sum(exp2)
    lse1 = max1 + tl.log(sum_exp1)
    lse2 = max2 + tl.log(sum_exp2)
    sum_p_l1 = 0.0
    sum_q_l2 = 0.0
    sum_p_logm = 0.0
    sum_q_logm = 0.0
    for start_n in range(0, N, BLOCK_N):
        l1_offsets = (start_n + offs_n) * STRIDE_L1N * 4
        l2_offsets = (start_n + offs_n) * STRIDE_L2N * 4
        l1_ptr = l1_base + l1_offsets
        l2_ptr = l2_base + l2_offsets
        n_mask = (start_n + offs_n < N)
        l1_tile = tl.load(l1_ptr, mask=n_mask, other=-INF)
        l2_tile = tl.load(l2_ptr, mask=n_mask, other=-INF)
        logp = l1_tile - lse1
        logq = l2_tile - lse2
        p = tl.exp(logp)
        q = tl.exp(logq)
        m = 0.5 * (p + q)
        logm = tl.where(m > 0.0, tl.log(m), 0.0)
        l1_safe = tl.where(n_mask, l1_tile, 0.0)
        l2_safe = tl.where(n_mask, l2_tile, 0.0)
        p_safe = tl.where(n_mask, p, 0.0)
        q_safe = tl.where(n_mask, q, 0.0)
        sum_p_l1 += tl.sum(p * l1_safe)
        sum_q_l2 += tl.sum(q * l2_safe)
        sum_p_logm += tl.sum(p_safe * logm)
        sum_q_logm += tl.sum(q_safe * logm)
    sum_p_logp = sum_p_l1 - lse1
    sum_q_logq = sum_q_l2 - lse2
    kl_pm = sum_p_logp - sum_p_logm
    kl_qm = sum_q_logq - sum_q_logm
    jsd_val = 0.5 * (kl_pm + kl_qm)
    tl.store(out_ptr, jsd_val)

def fused_linear_jsd(X: torch.Tensor, W1: torch.Tensor, B1: torch.Tensor, W2: torch.Tensor, B2: torch.Tensor) -> torch.Tensor:
    M, K = X.shape
    N = W1.shape[1]
    device = X.device
    logits1 = torch.empty((M, N), dtype=torch.float32, device=device)
    logits2 = torch.empty((M, N), dtype=torch.float32, device=device)
    output = torch.empty((M,), dtype=torch.float32, device=device)
    BLOCK_M = 128
    BLOCK_N = 128
    BLOCK_K = 64
    def linear_grid(meta):
        return (triton.cdiv(M, meta['BLOCK_M']), triton.cdiv(N, meta['BLOCK_N']))
    linear_kernel[linear_grid](
        X, W1, B1, W2, B2, logits1, logits2,
        M, K, N,
        X.stride(0), X.stride(1),
        W1.stride(0), W1.stride(1),
        W2.stride(0), W2.stride(1),
        B1.stride(0), B2.stride(0),
        logits1.stride(0), logits1.stride(1),
        logits2.stride(0), logits2.stride(1),
        BLOCK_M=BLOCK_M, BLOCK_N=BLOCK_N, BLOCK_K=BLOCK_K
    )
    JSD_BLOCK = 256
    jsd_kernel[(M,)](
        logits1, logits2, output,
        M, N,
        logits1.stride(0), logits1.stride(1),
        logits2.stride(0), logits2.stride(1),
        output.stride(0),
        BLOCK_N=JSD_BLOCK
    )
    return output
"""
        return {"code": code}
