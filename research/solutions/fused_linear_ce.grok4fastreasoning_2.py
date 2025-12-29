class Solution:
    def solve(self, spec_path: str = None) -> dict:
        code = """
import torch
import triton
import triton.language as tl

def fused_linear_ce(X: torch.Tensor, W: torch.Tensor, B: torch.Tensor, targets: torch.Tensor) -> torch.Tensor:
    M, K = X.shape
    N = W.shape[1]
    device = X.device
    logits = torch.empty((M, N), dtype=torch.float32, device=device)
    BLOCK_M = 128
    BLOCK_N = 128
    BLOCK_K = 64

    @triton.jit
    def kernel(
        X_PTR, W_PTR, B_PTR, LOGITS_PTR,
        M: tl.int32, N: tl.int32, K: tl.int32,
        BLOCK_M: tl.constexpr,
        BLOCK_N: tl.constexpr,
        BLOCK_K: tl.constexpr
    ):
        pid_m = tl.program_id(0)
        pid_n = tl.program_id(1)
        rm = tl.arange(0, BLOCK_M)
        rn = tl.arange(0, BLOCK_N)
        offs_m = pid_m * BLOCK_M + rm
        offs_n = pid_n * BLOCK_N + rn
        acc = tl.zeros((BLOCK_M, BLOCK_N), dtype=tl.float32)
        rk = tl.arange(0, BLOCK_K)
        for sk in range(0, K, BLOCK_K):
            offs_k = sk + rk
            x_ptrs = X_PTR + (offs_m[:, None] * K + offs_k[None, :])
            x_mask = (offs_m[:, None] < M) & (offs_k[None, :] < K)
            x = tl.load(x_ptrs, mask=x_mask, other=0.0)
            w_ptrs = W_PTR + (offs_k[:, None] * N + offs_n[None, :])
            w_mask = (offs_k[:, None] < K) & (offs_n[None, :] < N)
            w = tl.load(w_ptrs, mask=w_mask, other=0.0)
            acc += tl.dot(x, w)
        b_ptrs = B_PTR + offs_n
        b_mask = offs_n < N
        b = tl.load(b_ptrs, mask=b_mask, other=0.0)
        b = b.to(tl.float32)[None, :]
        acc += b
        logits_ptrs = LOGITS_PTR + (offs_m[:, None] * N + offs_n[None, :])
        logits_mask = (offs_m[:, None] < M) & (offs_n[None, :] < N)
        tl.store(logits_ptrs, acc, mask=logits_mask)

    grid = (triton.cdiv(M, BLOCK_M), triton.cdiv(N, BLOCK_N))
    kernel[grid](
        X, W, B, logits,
        M, N, K,
        BLOCK_M=BLOCK_M,
        BLOCK_N=BLOCK_N,
        BLOCK_K=BLOCK_K
    )
    row_max = torch.max(logits, dim=1).values
    arange = torch.arange(M, device=device)
    target_logits = logits[arange, targets]
    shifted = logits - row_max.unsqueeze(1)
    sum_exps = torch.sum(torch.exp(shifted), dim=1)
    losses = -(target_logits - row_max - torch.log(sum_exps))
    return losses
"""
        return {"code": code}