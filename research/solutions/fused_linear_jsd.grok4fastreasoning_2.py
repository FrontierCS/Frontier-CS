class Solution:
    def solve(self, spec_path: str = None) -> dict:
        code = """
import torch
import triton
import triton.language as tl

@triton.jit
def first_pass_kernel(
    X_PTR, W1_PTR, B1_PTR, W2_PTR, B2_PTR,
    PARTIAL1_PTR, PARTIAL2_PTR,
    M: tl.int32, K: tl.int32, N: tl.int32, NUM_BLOCKS_N: tl.int32,
    STRIDE_XM: tl.int32, STRIDE_XK: tl.int32,
    STRIDE_W1K: tl.int32, STRIDE_W1N: tl.int32, STRIDE_B1N: tl.int32,
    STRIDE_W2K: tl.int32, STRIDE_W2N: tl.int32, STRIDE_B2N: tl.int32,
    BLOCK_M: tl.constexpr, BLOCK_N: tl.constexpr, BLOCK_K: tl.constexpr
):
    pid_m = tl.program_id(0)
    pid_n = tl.program_id(1)
    block_start_m = pid_m * BLOCK_M
    block_start_n = pid_n * BLOCK_N
    offs_m = tl.arange(0, BLOCK_M)
    offs_n = tl.arange(0, BLOCK_N)
    offs_k = tl.arange(0, BLOCK_K)
    acc1 = tl.zeros((BLOCK_M, BLOCK_N), dtype=tl.float32)
    acc2 = tl.zeros((BLOCK_M, BLOCK_N), dtype=tl.float32)
    for start_k in range(0, K, BLOCK_K):
        k_offs = start_k + offs_k
        k_mask = k_offs < K
        x_ptrs = X_PTR + ((block_start_m + offs_m)[:, None] * STRIDE_XM + k_offs[None, :] * STRIDE_XK)
        x_mask = ((offs_m[:, None] < (M - block_start_m)) & k_mask[None, :])
        x = tl.load(x_ptrs, mask=x_mask, other=0.0)
        w1_ptrs = W1_PTR + (k_offs[:, None] * STRIDE_W1K + (block_start_n + offs_n)[None, :] * STRIDE_W1N)
        w1_mask = (k_mask[:, None] & ((block_start_n + offs_n)[None, :] < (N - block_start_n)))
        w1 = tl.load(w1_ptrs, mask=w1_mask, other=0.0)
        acc1 += tl.dot(x, w1)
        w2_ptrs = W2_PTR + (k_offs[:, None] * STRIDE_W2K + (block_start_n + offs_n)[None, :] * STRIDE_W2N)
        w2 = tl.load(w2_ptrs, mask=w1_mask, other=0.0)
        acc2 += tl.dot(x, w2)
    b1_ptrs = B1_PTR + (block_start_n + offs_n) * STRIDE_B1N
    b1_mask = (block_start_n + offs_n) < N
    b1 = tl.load(b1_ptrs, mask=b1_mask, other=0.0)
    acc1 += b1[None, :]
    b2_ptrs = B2_PTR + (block_start_n + offs_n) * STRIDE_B2N
    b2 = tl.load(b2_ptrs, mask=b1_mask, other=0.0)
    acc2 += b2[None, :]
    n_mask_full = (block_start_n + offs_n) < N
    invalid_val = tl.full([BLOCK_N], -100000.0, dtype=tl.float32)
    acc1 = tl.where(n_mask_full[None, :], acc1, invalid_val)
    acc2 = tl.where(n_mask_full[None, :], acc2, invalid_val)
    for ii in range(BLOCK_M):
        if block_start_m + ii >= M:
            continue
        row1 = acc1[ii]
        maxv1 = tl.max(row1)
        s1 = tl.sum(tl.exp(row1 - maxv1))
        lse1_val = maxv1 + tl.log(s1)
        offset = (block_start_m + ii) * NUM_BLOCKS_N + pid_n
        tl.store(PARTIAL1_PTR + offset, lse1_val)
        row2 = acc2[ii]
        maxv2 = tl.max(row2)
        s2 = tl.sum(tl.exp(row2 - maxv2))
        lse2_val = maxv2 + tl.log(s2)
        tl.store(PARTIAL2_PTR + offset, lse2_val)

@triton.jit
def second_pass_kernel(
    X_PTR, W1_PTR, B1_PTR, W2_PTR, B2_PTR,
    LSE1_PTR, LSE2_PTR,
    PARTIAL_P_LOGP_PTR, PARTIAL_Q_LOGQ_PTR, PARTIAL_P_LOGPQ_PTR, PARTIAL_Q_LOGPQ_PTR,
    M: tl.int32, K: tl.int32, N: tl.int32, NUM_BLOCKS_N: tl.int32,
    STRIDE_XM: tl.int32, STRIDE_XK: tl.int32,
    STRIDE_W1K: tl.int32, STRIDE_W1N: tl.int32, STRIDE_B1N: tl.int32,
    STRIDE_W2K: tl.int32, STRIDE_W2N: tl.int32, STRIDE_B2N: tl.int32,
    STRIDE_LSE1: tl.int32, STRIDE_LSE2: tl.int32,
    BLOCK_M: tl.constexpr, BLOCK_N: tl.constexpr, BLOCK_K: tl.constexpr
):
    pid_m = tl.program_id(0)
    pid_n = tl.program_id(1)
    block_start_m = pid_m * BLOCK_M
    block_start_n = pid_n * BLOCK_N
    offs_m = tl.arange(0, BLOCK_M)
    offs_n = tl.arange(0, BLOCK_N)
    offs_k = tl.arange(0, BLOCK_K)
    acc1 = tl.zeros((BLOCK_M, BLOCK_N), dtype=tl.float32)
    acc2 = tl.zeros((BLOCK_M, BLOCK_N), dtype=tl.float32)
    for start_k in range(0, K, BLOCK_K):
        k_offs = start_k + offs_k
        k_mask = k_offs < K
        x_ptrs = X_PTR + ((block_start_m + offs_m)[:, None] * STRIDE_XM + k_offs[None, :] * STRIDE_XK)
        x_mask = ((offs_m[:, None] < (M - block_start_m)) & k_mask[None, :])
        x = tl.load(x_ptrs, mask=x_mask, other=0.0)
        w1_ptrs = W1_PTR + (k_offs[:, None] * STRIDE_W1K + (block_start_n + offs_n)[None, :] * STRIDE_W1N)
        w1_mask = (k_mask[:, None] & ((block_start_n + offs_n)[None, :] < (N - block_start_n)))
        w1 = tl.load(w1_ptrs, mask=w1_mask, other=0.0)
        acc1 += tl.dot(x, w1)
        w2_ptrs = W2_PTR + (k_offs[:, None] * STRIDE_W2K + (block_start_n + offs_n)[None, :] * STRIDE_W2N)
        w2 = tl.load(w2_ptrs, mask=w1_mask, other=0.0)
        acc2 += tl.dot(x, w2)
    b1_ptrs = B1_PTR + (block_start_n + offs_n) * STRIDE_B1N
    b1_mask = (block_start_n + offs_n) < N
    b1 = tl.load(b1_ptrs, mask=b1_mask, other=0.0)
    acc1 += b1[None, :]
    b2_ptrs = B2_PTR + (block_start_n + offs_n) * STRIDE_B2N
    b2 = tl.load(b2_ptrs, mask=b1_mask, other=0.0)
    acc2 += b2[None, :]
    n_mask_full = (block_start_n + offs_n) < N
    invalid_val = tl.full([BLOCK_N], -100000.0, dtype=tl.float32)
    acc1 = tl.where(n_mask_full[None, :], acc1, invalid_val)
    acc2 = tl.where(n_mask_full[None, :], acc2, invalid_val)
    lse1_ptrs = LSE1_PTR + (block_start_m + offs_m) * STRIDE_LSE1
    lse1_mask = offs_m < (M - block_start_m)
    lse1_block = tl.load(lse1_ptrs, mask=lse1_mask, other=0.0)
    lse2_ptrs = LSE2_PTR + (block_start_m + offs_m) * STRIDE_LSE2
    lse2_block = tl.load(lse2_ptrs, mask=lse1_mask, other=0.0)
    for ii in range(BLOCK_M):
        if block_start_m + ii >= M:
            continue
        logp = acc1[ii] - lse1_block[ii]
        p = tl.exp(logp)
        logq = acc2[ii] - lse2_block[ii]
        q = tl.exp(logq)
        contrib_p_logp = tl.sum(p * logp)
        contrib_q_logq = tl.sum(q * logq)
        pq = p + q
        logpq = tl.log(pq + 1e-8)
        contrib_p_logpq = tl.sum(p * logpq)
        contrib_q_logpq = tl.sum(q * logpq)
        offset = (block_start_m + ii) * NUM_BLOCKS_N + pid_n
        tl.store(PARTIAL_P_LOGP_PTR + offset, contrib_p_logp)
        tl.store(PARTIAL_Q_LOGQ_PTR + offset, contrib_q_logq)
        tl.store(PARTIAL_P_LOGPQ_PTR + offset, contrib_p_logpq)
        tl.store(PARTIAL_Q_LOGPQ_PTR + offset, contrib_q_logpq)

def fused_linear_jsd(X: torch.Tensor, W1: torch.Tensor, B1: torch.Tensor, W2: torch.Tensor, B2: torch.Tensor) -> torch.Tensor:
    M, K = X.shape
    N = W1.shape[1]
    device = X.device
    dtype_f32 = torch.float32
    BLOCK_M: int = 64
    BLOCK_N: int = 128
    BLOCK_K: int = 128
    num_blocks_n = (N + BLOCK_N - 1) // BLOCK_N
    partial1_flat = torch.empty(M * num_blocks_n, dtype=dtype_f32, device=device)
    partial2_flat = torch.empty(M * num_blocks_n, dtype=dtype_f32, device=device)
    grid = lambda meta: (triton.cdiv(M, meta['BLOCK_M']), num_blocks_n)
    first_pass_kernel[grid](X, W1, B1, W2, B2, partial1_flat, partial2_flat, torch.int32(M), torch.int32(K), torch.int32(N), torch.int32(num_blocks_n),
                            torch.int32(X.stride(0)), torch.int32(X.stride(1)),
                            torch.int32(W1.stride(0)), torch.int32(W1.stride(1)), torch.int32(B1.stride(0)),
                            torch.int32(W2.stride(0)), torch.int32(W2.stride(1)), torch.int32(B2.stride(0)),
                            BLOCK_M=BLOCK_M, BLOCK_N=BLOCK_N, BLOCK_K=BLOCK_K)
    partial1 = partial1_flat.view(M, num_blocks_n)
    partial2 = partial2_flat.view(M, num_blocks_n)
    max1 = partial1.max(dim=1).values
    sum_exp1 = torch.exp(partial1 - max1.unsqueeze(1)).sum(dim=1)
    lse1 = max1 + torch.log(sum_exp1)
    max2 = partial2.max(dim=1).values
    sum_exp2 = torch.exp(partial2 - max2.unsqueeze(1)).sum(dim=1)
    lse2 = max2 + torch.log(sum_exp2)
    partial_p_logp_flat = torch.empty(M * num_blocks_n, dtype=dtype_f32, device=device)
    partial_q_logq_flat = torch.empty(M * num_blocks_n, dtype=dtype_f32, device=device)
    partial_p_logpq_flat = torch.empty(M * num_blocks_n, dtype=dtype_f32, device=device)
    partial_q_logpq_flat = torch.empty(M * num_blocks_n, dtype=dtype_f32, device=device)
    second_pass_kernel[grid](X, W1, B1, W2, B2, lse1, lse2, partial_p_logp_flat, partial_q_logq_flat, partial_p_logpq_flat, partial_q_logpq_flat,
                             torch.int32(M), torch.int32(K), torch.int32(N), torch.int32(num_blocks_n),
                             torch.int32(X.stride(0)), torch.int32(X.stride(1)),
                             torch.int32(W1.stride(0)), torch.int32(W1.stride(1)), torch.int32(B1.stride(0)),
                             torch.int32(W2.stride(0)), torch.int32(W2.stride(1)), torch.int32(B2.stride(0)),
                             torch.int32(lse1.stride(0)), torch.int32(lse2.stride(0)),
                             BLOCK_M=BLOCK_M, BLOCK_N=BLOCK_N, BLOCK_K=BLOCK_K)
    total_p_logp = partial_p_logp_flat.view(M, num_blocks_n).sum(dim=1)
    total_q_logq = partial_q_logq_flat.view(M, num_blocks_n).sum(dim=1)
    total_p_logpq = partial_p_logpq_flat.view(M, num_blocks_n).sum(dim=1)
    total_q_logpq = partial_q_logpq_flat.view(M, num_blocks_n).sum(dim=1)
    log_half = torch.log(torch.tensor(0.5, dtype=dtype_f32, device=device))
    sum_p_logm = log_half + total_p_logpq
    sum_q_logm = log_half + total_q_logpq
    kl1 = total_p_logp - sum_p_logm
    kl2 = total_q_logq - sum_q_logm
    return 0.5 * (kl1 + kl2)
"""
        return {"code": code}