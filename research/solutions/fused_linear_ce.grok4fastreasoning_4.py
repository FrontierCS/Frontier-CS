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
def fused_linear_kernel(
    X_PTR, WT_PTR, B_PTR, LOGITS_PTR,
    M: tl.int32, K: tl.int32, N: tl.int32,
    STRIDE_XM: tl.int32, STRIDE_XK: tl.int32,
    STRIDE_WTM: tl.int32, STRIDE_WTK: tl.int32,
    STRIDE_BN: tl.int32,
    STRIDE_LM: tl.int32, STRIDE_LN: tl.int32,
    BLOCK_M: tl.constexpr,
    BLOCK_N: tl.constexpr,
    BLOCK_K: tl.constexpr,
):
    pid_m = tl.program_id(0)
    pid_n = tl.program_id(1)
    block_start_m = pid_m * BLOCK_M
    offs_m = block_start_m + tl.arange(0, BLOCK_M)
    m_mask = offs_m < M
    block_start_n = pid_n * BLOCK_N
    offs_n = block_start_n + tl.arange(0, BLOCK_N)
    n_mask = offs_n < N
    acc = tl.zeros((BLOCK_M, BLOCK_N), dtype=tl.float32)
    for start_k in range(0, K, BLOCK_K):
        offs_k = start_k + tl.arange(0, BLOCK_K)
        k_mask = offs_k < K
        x_ptrs = X_PTR + (offs_m[:, None] * STRIDE_XM + offs_k[None, :] * STRIDE_XK)
        x_mask = m_mask[:, None] & k_mask[None, :]
        x = tl.load(x_ptrs, mask=x_mask, other=0.0).to(tl.float32)
        w_ptrs = WT_PTR + (offs_n[:, None] * STRIDE_WTM + offs_k[None, :] * STRIDE_WTK)
        w_mask = n_mask[:, None] & k_mask[None, :]
        w = tl.load(w_ptrs, mask=w_mask, other=0.0).to(tl.float32)
        acc += tl.dot(x, tl.trans(w))
    b_ptrs = B_PTR + offs_n * STRIDE_BN
    b_mask = n_mask
    b = tl.load(b_ptrs, mask=b_mask, other=0.0)
    logits_block = acc + b[None, :]
    l_ptrs = LOGITS_PTR + (offs_m[:, None] * STRIDE_LM + offs_n[None, :] * STRIDE_LN)
    l_mask = m_mask[:, None] & n_mask[None, :]
    tl.store(l_ptrs, logits_block, mask=l_mask)

def fused_linear_ce(X: torch.Tensor, W: torch.Tensor, B: torch.Tensor, targets: torch.Tensor) -> torch.Tensor:
    M, K = X.shape
    N = W.shape[1]
    Wt = W.t().contiguous()
    device = X.device
    logits = torch.empty((M, N), dtype=torch.float32, device=device)
    def grid(meta):
        return (
            triton.cdiv(M, meta['BLOCK_M']),
            triton.cdiv(N, meta['BLOCK_N']),
        )
    fused_linear_kernel[grid](
        X, Wt, B, logits,
        M, K, N,
        X.stride(0), X.stride(1),
        Wt.stride(0), Wt.stride(1),
        B.stride(0),
        logits.stride(0), logits.stride(1),
        BLOCK_M=128,
        BLOCK_N=256,
        BLOCK_K=64,
    )
    row_max = torch.max(logits, dim=1).values
    target_logits = torch.gather(logits, 1, targets.unsqueeze(1)).squeeze(1)
    centered = logits - row_max.unsqueeze(1)
    sum_exp = torch.sum(torch.exp(centered), dim=1)
    log_sum_exp = row_max + torch.log(sum_exp)
    loss = -(target_logits - log_sum_exp)
    return loss
"""
        return {"code": code}
