import torch
import triton
import triton.language as tl

class Solution:
    def solve(self, spec_path: str = None) -> dict:
        code = """
def fused_linear_jsd(X: torch.Tensor, W1: torch.Tensor, B1: torch.Tensor, W2: torch.Tensor, B2: torch.Tensor) -> torch.Tensor:
    M, K = X.shape
    _, N = W1.shape
    logits1 = torch.empty((M, N), dtype=torch.float32, device=X.device)
    logits2 = torch.empty((M, N), dtype=torch.float32, device=X.device)
    @triton.jit
    def kernel(X_ptr, W1_ptr, W2_ptr, C1_ptr, C2_ptr, M: tl.int32, N: tl.int32, K: tl.int32,
               stride_xm, stride_xk, stride_w1k, stride_w1n, stride_w2k, stride_w2n,
               stride_c1m, stride_c1n, stride_c2m, stride_c2n,
               BLOCK_M : tl.constexpr, BLOCK_N : tl.constexpr, BLOCK_K : tl.constexpr):
        pid_m = tl.program_id(0)
        pid_n = tl.program_id(1)
        offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
        offs_n = pid_n * BLOCK_N + tl.arange(0, BLOCK_N)
        acc1 = tl.zeros((BLOCK_M, BLOCK_N), dtype=tl.float32)
        acc2 = tl.zeros((BLOCK_M, BLOCK_N), dtype=tl.float32)
        for k in range(0, K, BLOCK_K):
            offs_k = k + tl.arange(0, BLOCK_K)
            x_mask = (offs_m[:,None] < M) & (offs_k[None,:] < K)
            x = tl.load(X_ptr + offs_m[:,None] * stride_xm + offs_k[None,:] * stride_xk,
                        mask=x_mask, other=0.0, dtype=tl.float16)
            w1_mask = (offs_k[:,None] < K) & (offs_n[None,:] < N)
            w1 = tl.load(W1_ptr + offs_k[:,None] * stride_w1k + offs_n[None,:] * stride_w1n,
                         mask=w1_mask, other=0.0, dtype=tl.float16)
            w2 = tl.load(W2_ptr + offs_k[:,None] * stride_w2k + offs_n[None,:] * stride_w2n,
                         mask=w1_mask, other=0.0, dtype=tl.float16)
            acc1 += tl.dot(x.to(tl.float32), w1.to(tl.float32))
            acc2 += tl.dot(x.to(tl.float32), w2.to(tl.float32))
        c_mask = (offs_m[:,None] < M) & (offs_n[None,:] < N)
        tl.store(C1_ptr + offs_m[:,None] * stride_c1m + offs_n[None,:] * stride_c1n, acc1, mask=c_mask)
        tl.store(C2_ptr + offs_m[:,None] * stride_c2m + offs_n[None,:] * stride_c2n, acc2, mask=c_mask)
    BLOCK_M = 64
    BLOCK_N = 128
    BLOCK_K = 128
    grid = (triton.cdiv(M, BLOCK_M), triton.cdiv(N, BLOCK_N))
    kernel[grid](X, W1, W2, logits1, logits2, M, N, K,
                 X.stride(0), X.stride(1),
                 W1.stride(0), W1.stride(1),
                 W2.stride(0), W2.stride(1),
                 logits1.stride(0), logits1.stride(1),
                 logits2.stride(0), logits2.stride(1),
                 BLOCK_M=BLOCK_M, BLOCK_N=BLOCK_N, BLOCK_K=BLOCK_K)
    logits1 += B1.unsqueeze(0)
    logits2 += B2.unsqueeze(0)
    P = torch.softmax(logits1, dim=-1)
    Q = torch.softmax(logits2, dim=-1)
    M_avg = 0.5 * (P + Q)
    eps = 1e-8
    P_safe = torch.clamp(P, min=eps)
    Q_safe = torch.clamp(Q, min=eps)
    M_safe = torch.clamp(M_avg, min=eps)
    kl_p = (P_safe * (torch.log(P_safe) - torch.log(M_safe))).sum(dim=1)
    kl_q = (Q_safe * (torch.log(Q_safe) - torch.log(M_safe))).sum(dim=1)
    jsd = 0.5 * (kl_p + kl_q)
    return jsd
"""
        return {"code": code}