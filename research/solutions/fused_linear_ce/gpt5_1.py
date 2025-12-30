from textwrap import dedent

class Solution:
    def solve(self, spec_path: str = None) -> dict:
        code = dedent('''
import torch
import triton
import triton.language as tl

@triton.jit
def fused_linear_ce_kernel(
    X_ptr, W_ptr, B_ptr, T_ptr, Out_ptr,
    M, N, K,
    stride_xm, stride_xk,
    stride_wk, stride_wn,
    stride_b,
    stride_tm,
    stride_om,
    BLOCK_M: tl.constexpr, BLOCK_N: tl.constexpr, BLOCK_K: tl.constexpr,
):
    pid_m = tl.program_id(axis=0)
    rm = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
    mask_m = rm < M

    t = tl.load(T_ptr + rm * stride_tm, mask=mask_m, other=0).to(tl.int32)

    neg_inf = float('-inf')
    row_max = tl.full((BLOCK_M,), neg_inf, dtype=tl.float32)

    n0 = 0
    while n0 < N:
        cn = n0 + tl.arange(0, BLOCK_N)
        col_mask = cn < N
        acc = tl.zeros((BLOCK_M, BLOCK_N), dtype=tl.float32)
        k0 = 0
        while k0 < K:
            offs_k = k0 + tl.arange(0, BLOCK_K)
            k_mask = offs_k < K
            x_ptrs = X_ptr + rm[:, None] * stride_xm + offs_k[None, :] * stride_xk
            w_ptrs = W_ptr + offs_k[:, None] * stride_wk + cn[None, :] * stride_wn
            x = tl.load(x_ptrs, mask=mask_m[:, None] & k_mask[None, :], other=0.0)
            w = tl.load(w_ptrs, mask=k_mask[:, None] & col_mask[None, :], other=0.0)
            acc += tl.dot(x, w)
            k0 += BLOCK_K
        b = tl.load(B_ptr + cn * stride_b, mask=col_mask, other=0.0)
        logits = acc + b[None, :]
        logits_masked = tl.where(col_mask[None, :], logits, neg_inf)
        tile_max = tl.max(logits_masked, axis=1)
        row_max = tl.maximum(row_max, tile_max)
        n0 += BLOCK_N

    sumexp = tl.zeros((BLOCK_M,), dtype=tl.float32)
    target_logits = tl.full((BLOCK_M,), neg_inf, dtype=tl.float32)
    n0 = 0
    while n0 < N:
        cn = n0 + tl.arange(0, BLOCK_N)
        col_mask = cn < N
        acc = tl.zeros((BLOCK_M, BLOCK_N), dtype=tl.float32)
        k0 = 0
        while k0 < K:
            offs_k = k0 + tl.arange(0, BLOCK_K)
            k_mask = offs_k < K
            x_ptrs = X_ptr + rm[:, None] * stride_xm + offs_k[None, :] * stride_xk
            w_ptrs = W_ptr + offs_k[:, None] * stride_wk + cn[None, :] * stride_wn
            x = tl.load(x_ptrs, mask=mask_m[:, None] & k_mask[None, :], other=0.0)
            w = tl.load(w_ptrs, mask=k_mask[:, None] & col_mask[None, :], other=0.0)
            acc += tl.dot(x, w)
            k0 += BLOCK_K
        b = tl.load(B_ptr + cn * stride_b, mask=col_mask, other=0.0)
        logits = acc + b[None, :]
        logits_shifted = logits - row_max[:, None]
        exps = tl.exp(logits_shifted)
        exps = tl.where(col_mask[None, :], exps, 0.0)
        sumexp += tl.sum(exps, axis=1)
        eq = (cn[None, :] == t[:, None])
        eq = eq & col_mask[None, :]
        masked_logits = tl.where(eq, logits, neg_inf)
        val = tl.max(masked_logits, axis=1)
        target_logits = tl.maximum(target_logits, val)
        n0 += BLOCK_N

    losses = tl.log(sumexp) + row_max - target_logits
    tl.store(Out_ptr + rm * stride_om, losses, mask=mask_m)

def fused_linear_ce(X: torch.Tensor, W: torch.Tensor, B: torch.Tensor, targets: torch.Tensor) -> torch.Tensor:
    if X.ndim != 2 or W.ndim != 2:
        raise ValueError("X and W must be 2D")
    M, K = X.shape
    K2, N = W.shape
    if K != K2:
        raise ValueError("Incompatible shapes")
    if B.ndim != 1 or B.shape[0] != N:
        raise ValueError("B must be 1D and match W.shape[1]")
    if targets.ndim != 1 or targets.shape[0] != M:
        raise ValueError("targets must be 1D and match X.shape[0]")
    device = X.device
    if X.dtype not in (torch.float16, torch.bfloat16):
        X = X.to(torch.float16)
    if W.dtype not in (torch.float16, torch.bfloat16):
        W = W.to(torch.float16)
    if B.dtype != torch.float32:
        B = B.to(torch.float32)
    Xc = X.contiguous()
    Wc = W.contiguous()
    Bc = B.contiguous()
    Tc = targets.contiguous()
    out = torch.empty((M,), device=device, dtype=torch.float32)

    BLOCK_M = 16
    if N >= 8192:
        BLOCK_N = 128
    elif N >= 4096:
        BLOCK_N = 128
    else:
        BLOCK_N = 64
    BLOCK_K = 64
    num_warps = 8 if BLOCK_N >= 128 else 4
    num_stages = 4
    try:
        grid = (triton.cdiv(M, BLOCK_M),)
        fused_linear_ce_kernel[grid](
            Xc, Wc, Bc, Tc, out,
            M, N, K,
            Xc.stride(0), Xc.stride(1),
            Wc.stride(0), Wc.stride(1),
            Bc.stride(0),
            Tc.stride(0),
            out.stride(0),
            BLOCK_M=BLOCK_M, BLOCK_N=BLOCK_N, BLOCK_K=BLOCK_K,
            num_warps=num_warps, num_stages=num_stages,
        )
        return out
    except Exception:
        logits = (Xc @ Wc).to(torch.float32)
        logits = logits + Bc
        max_logits = logits.max(dim=1, keepdim=True).values
        lse = (logits - max_logits).exp().sum(dim=1).log() + max_logits.squeeze(1)
        tgt_logits = logits.gather(1, Tc.view(-1, 1)).squeeze(1)
        return lse - tgt_logits
''')
        return {"code": code}