class Solution:
    def solve(self, spec_path: str = None) -> dict:
        code = """
import torch
import triton
import triton.language as tl

@triton.jit
def fused_linear_kernel(
    X, W1, W2, LOGITS1, LOGITS2,
    M, N, K,
    BLOCK_M: tl.constexpr,
    BLOCK_N: tl.constexpr,
    BLOCK_K: tl.constexpr
):
    pid_m = tl.program_id(0)
    pid_n = tl.program_id(1)
    block_m = tl.arange(0, BLOCK_M)
    block_n = tl.arange(0, BLOCK_N)
    offs_m = pid_m * BLOCK_M + block_m
    offs_n = pid_n * BLOCK_N + block_n
    mask_m = offs_m < M
    mask_n = offs_n < N
    acc1 = tl.zeros((BLOCK_M, BLOCK_N), dtype=tl.float32)
    acc2 = tl.zeros((BLOCK_M, BLOCK_N), dtype=tl.float32)
    for start_k in range(0, K, BLOCK_K):
        offs_k = start_k + tl.arange(0, BLOCK_K)
        mask_k = offs_k < K
        x_offs = (offs_m[:, None] * K + offs_k[None, :]) * 2
        x = tl.load(X + x_offs, mask=mask_m[:, None] & mask_k[None, :], other=0.0).to(tl.float32)
        w1_offs = (offs_k[:, None] * N + offs_n[None, :]) * 2
        w1 = tl.load(W1 + w1_offs, mask=mask_k[:, None] & mask_n[None, :], other=0.0).to(tl.float32)
        w2_offs = (offs_k[:, None] * N + offs_n[None, :]) * 2
        w2 = tl.load(W2 + w2_offs, mask=mask_k[:, None] & mask_n[None, :], other=0.0).to(tl.float32)
        acc1 += tl.dot(x, w1)
        acc2 += tl.dot(x, w2)
    l1_offs = (offs_m[:, None] * N + offs_n[None, :]) * 4
    tl.store(LOGITS1 + l1_offs, acc1, mask=mask_m[:, None] & mask_n[None, :])
    l2_offs = (offs_m[:, None] * N + offs_n[None, :]) * 4
    tl.store(LOGITS2 + l2_offs, acc2, mask=mask_m[:, None] & mask_n[None, :])

def fused_linear_jsd(X: torch.Tensor, W1: torch.Tensor, B1: torch.Tensor, W2: torch.Tensor, B2: torch.Tensor) -> torch.Tensor:
    M, K = X.shape
    _, N = W1.shape
    device = X.device
    logits1 = torch.empty((M, N), dtype=torch.float32, device=device)
    logits2 = torch.empty((M, N), dtype=torch.float32, device=device)
    BLOCK_M = 128
    BLOCK_N = 128
    BLOCK_K = 64
    grid = (triton.cdiv(M, BLOCK_M), triton.cdiv(N, BLOCK_N))
    fused_linear_kernel[grid](
        X, W1, W2, logits1, logits2, M, N, K,
        BLOCK_M=BLOCK_M,
        BLOCK_N=BLOCK_N,
        BLOCK_K=BLOCK_K,
        num_stages=4,
        num_warps=8,
    )
    logits1 = logits1 + B1.unsqueeze(0)
    logits2 = logits2 + B2.unsqueeze(0)
    lse1 = torch.logsumexp(logits1, dim=-1)
    lse2 = torch.logsumexp(logits2, dim=-1)
    p = torch.exp(logits1 - lse1.unsqueeze(-1))
    q = torch.exp(logits2 - lse2.unsqueeze(-1))
    m = 0.5 * (p + q)
    log_p = torch.log(p)
    log_q = torch.log(q)
    log_m = torch.log(m)
    kl1 = (p * (log_p - log_m)).sum(dim=-1)
    kl2 = (q * (log_q - log_m)).sum(dim=-1)
    jsd = 0.5 * (kl1 + kl2)
    return jsd
"""
        return {"code": code}
