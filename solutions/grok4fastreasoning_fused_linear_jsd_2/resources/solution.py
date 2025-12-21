import torch
import triton
import triton.language as tl

class Solution:
    def solve(self, spec_path: str = None) -> dict:
        code = """
import torch
import triton
import triton.language as tl

@triton.jit
def _fused_linear_jsd_kernel(
    X_ptr, W1_ptr, B1_ptr, W2_ptr, B2_ptr, L1_ptr, L2_ptr,
    M, K, N,
    stride_xm, stride_xk,
    stride_w1k, stride_w1n,
    stride_b1n,
    stride_w2k, stride_w2n,
    stride_b2n,
    stride_l1m, stride_l1n,
    stride_l2m, stride_l2n,
    BLOCK_M: tl.constexpr,
    BLOCK_N: tl.constexpr,
    BLOCK_K: tl.constexpr
):
    pid_m = tl.program_id(0)
    pid_n = tl.program_id(1)

    offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
    offs_n = pid_n * BLOCK_N + tl.arange(0, BLOCK_N)
    offs_k = tl.arange(0, BLOCK_K)

    x_ptrs = X_ptr + (offs_m[:, None] * stride_xm + offs_k[None, :] * stride_xk)
    x_mask = (offs_m[:, None] < M) & (offs_k[None, :] < K)
    x = tl.load(x_ptrs, mask=x_mask, other=tl.float16(0)).to(tl.float32)

    acc1 = tl.zeros((BLOCK_M, BLOCK_N), dtype=tl.float32)
    acc2 = tl.zeros((BLOCK_M, BLOCK_N), dtype=tl.float32)

    for start_k in range(0, K, BLOCK_K):
        offs_k_cur = start_k + offs_k

        w1_ptrs = W1_ptr + (offs_k_cur[None, :] * stride_w1k + offs_n[:, None] * stride_w1n)
        w1_mask = (offs_k_cur[None, :] < K) & (offs_n[:, None] < N)
        w1 = tl.load(w1_ptrs, mask=w1_mask, other=tl.float16(0)).to(tl.float32)

        w2_ptrs = W2_ptr + (offs_k_cur[None, :] * stride_w2k + offs_n[:, None] * stride_w2n)
        w2_mask = (offs_k_cur[None, :] < K) & (offs_n[:, None] < N)
        w2 = tl.load(w2_ptrs, mask=w2_mask, other=tl.float16(0)).to(tl.float32)

        acc1 += tl.dot(x, w1)
        acc2 += tl.dot(x, w2)

    b1_ptrs = B1_ptr + offs_n * stride_b1n
    b1_mask = offs_n < N
    b1 = tl.load(b1_ptrs, mask=b1_mask, other=0.0)
    acc1 += b1[None, :]

    b2_ptrs = B2_ptr + offs_n * stride_b2n
    b2_mask = offs_n < N
    b2 = tl.load(b2_ptrs, mask=b2_mask, other=0.0)
    acc2 += b2[None, :]

    l1_ptrs = L1_ptr + (offs_m[:, None] * stride_l1m + offs_n[None, :] * stride_l1n)
    l1_mask = (offs_m[:, None] < M) & (offs_n[None, :] < N)
    tl.store(l1_ptrs, acc1, mask=l1_mask)

    l2_ptrs = L2_ptr + (offs_m[:, None] * stride_l2m + offs_n[None, :] * stride_l2n)
    l2_mask = (offs_m[:, None] < M) & (offs_n[None, :] < N)
    tl.store(l2_ptrs, acc2, mask=l2_mask)


def fused_linear_jsd(X: torch.Tensor, W1: torch.Tensor, B1: torch.Tensor, W2: torch.Tensor, B2: torch.Tensor) -> torch.Tensor:
    M, K = X.shape
    N = W1.shape[1]
    assert W1.shape == (K, N)
    assert W2.shape == (K, N)
    assert B1.shape == (N,)
    assert B2.shape == (N,)
    device = X.device

    logits1 = torch.empty((M, N), dtype=torch.float32, device=device)
    logits2 = torch.empty((M, N), dtype=torch.float32, device=device)

    BLOCK_M = 128
    BLOCK_N = 128
    BLOCK_K = 64

    grid = (triton.cdiv(M, BLOCK_M), triton.cdiv(N, BLOCK_N))

    _fused_linear_jsd_kernel[grid](
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
        num_stages=4
    )

    P = torch.softmax(logits1, dim=-1)
    Q = torch.softmax(logits2, dim=-1)
    M_probs = 0.5 * (P + Q)

    zero = torch.tensor(0.0, device=device)
    log_ratio_p = torch.where(P > 0, P.log() - M_probs.log(), zero)
    log_ratio_q = torch.where(Q > 0, Q.log() - M_probs.log(), zero)

    kl_p = torch.sum(P * log_ratio_p, dim=-1)
    kl_q = torch.sum(Q * log_ratio_q, dim=-1)

    jsd = 0.5 * (kl_p + kl_q)
    return jsd
"""
        return {"code": code}
