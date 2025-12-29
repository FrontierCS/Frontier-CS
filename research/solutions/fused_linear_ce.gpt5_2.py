import os

class Solution:
    def solve(self, spec_path: str = None) -> dict:
        code = r"""
import torch
import triton
import triton.language as tl


@triton.jit
def fused_linear_ce_kernel(
    X_ptr, W_ptr, B_ptr, T_ptr, Out_ptr,
    M, N, K,
    stride_xm, stride_xk,
    stride_wk, stride_wn,
    BLOCK_M: tl.constexpr, BLOCK_N: tl.constexpr, BLOCK_K: tl.constexpr
):
    pid_m = tl.program_id(0)
    offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
    mask_m = offs_m < M

    offs_n = tl.arange(0, BLOCK_N)

    m_i = tl.full([BLOCK_M], -float('inf'), dtype=tl.float32)
    s_i = tl.zeros([BLOCK_M], dtype=tl.float32)
    tval = tl.zeros([BLOCK_M], dtype=tl.float32)

    t_idx = tl.load(T_ptr + offs_m, mask=mask_m, other=0)
    t = t_idx.to(tl.int32)

    n_start = 0
    while n_start < N:
        n_offs = n_start + offs_n
        mask_n = n_offs < N

        acc = tl.zeros([BLOCK_M, BLOCK_N], dtype=tl.float32)

        k_start = 0
        while k_start < K:
            k_offs = k_start + tl.arange(0, BLOCK_K)
            mask_k = k_offs < K

            a_ptrs = X_ptr + offs_m[:, None] * stride_xm + k_offs[None, :] * stride_xk
            a = tl.load(a_ptrs, mask=mask_m[:, None] & mask_k[None, :], other=0.0)

            b_ptrs = W_ptr + k_offs[:, None] * stride_wk + n_offs[None, :] * stride_wn
            b = tl.load(b_ptrs, mask=mask_k[:, None] & mask_n[None, :], other=0.0)

            acc += tl.dot(a, b)
            k_start += BLOCK_K

        bias = tl.load(B_ptr + n_offs, mask=mask_n, other=0.0).to(tl.float32)
        acc += bias[None, :]

        acc = tl.where(mask_n[None, :], acc, -float('inf'))

        tmax = tl.max(acc, axis=1)
        m_new = tl.maximum(m_i, tmax)
        acc_shifted = acc - m_new[:, None]
        tile_exp_sum = tl.sum(tl.exp(acc_shifted), axis=1)
        s_i = s_i * tl.exp(m_i - m_new) + tile_exp_sum
        m_i = m_new

        n_idx = n_offs
        match = (n_idx[None, :].to(tl.int32) == t[:, None])
        match = match & mask_n[None, :] & mask_m[:, None]
        pick = tl.where(match, acc, 0.0)
        t_tile_val = tl.sum(pick, axis=1)
        has_match = tl.sum(match.to(tl.int32), axis=1) > 0
        tval = tl.where(has_match, t_tile_val, tval)

        n_start += BLOCK_N

    logsumexp = m_i + tl.log(s_i)
    loss = logsumexp - tval
    tl.store(Out_ptr + offs_m, loss, mask=mask_m)


def fused_linear_ce(X: torch.Tensor, W: torch.Tensor, B: torch.Tensor, targets: torch.Tensor) -> torch.Tensor:
    if not (X.is_cuda and W.is_cuda and B.is_cuda and targets.is_cuda):
        raise RuntimeError("All inputs must be on CUDA device")
    if X.dtype != torch.float16 or W.dtype != torch.float16:
        raise TypeError("X and W must be float16")
    if B.dtype != torch.float32:
        raise TypeError("B must be float32")
    if targets.dtype != torch.long:
        raise TypeError("targets must be int64 (torch.long)")
    if X.ndim != 2 or W.ndim != 2 or B.ndim != 1 or targets.ndim != 1:
        raise ValueError("Invalid input dimensions")
    M, K = X.shape
    K_w, N = W.shape
    if K_w != K:
        raise ValueError("Incompatible shapes: X.shape[1] != W.shape[0]")
    if B.numel() != N:
        raise ValueError("Bias shape mismatch")
    if targets.numel() != M:
        raise ValueError("Targets length must equal batch size")

    out = torch.empty(M, dtype=torch.float32, device=X.device)

    BLOCK_M = 64
    BLOCK_N = 128
    BLOCK_K = 64
    NUM_WARPS = 8
    NUM_STAGES = 3

    grid = (triton.cdiv(M, BLOCK_M),)

    fused_linear_ce_kernel[grid](
        X, W, B, targets, out,
        M, N, K,
        X.stride(0), X.stride(1),
        W.stride(0), W.stride(1),
        BLOCK_M=BLOCK_M, BLOCK_N=BLOCK_N, BLOCK_K=BLOCK_K,
        num_warps=NUM_WARPS, num_stages=NUM_STAGES
    )
    return out
"""
        return {"code": code}