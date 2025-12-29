class Solution:
    def solve(self, spec_path: str = None) -> dict:
        code = """
import torch
import triton
import triton.language as tl
import math

@triton.jit
def row_max_kernel(
    x_ptr, stride_xm, stride_xk,
    w_ptr, stride_wk, stride_wn,
    b_ptr, stride_bn,
    row_max_ptr, stride_rm,
    M: tl.int32, K: tl.int32, N: tl.int32,
    BLOCK_M: tl.constexpr,
    BLOCK_N: tl.constexpr,
    BLOCK_K: tl.constexpr
):
    pid_m = tl.program_id(0)
    block_start_m = pid_m * BLOCK_M
    m_offsets = block_start_m + tl.arange(0, BLOCK_M)
    mask_m = m_offsets < M
    acc = tl.full((BLOCK_M,), float("-inf"), dtype=tl.float32)
    for start_n in range(0, N, BLOCK_N):
        n_offsets = start_n + tl.arange(0, BLOCK_N)
        mask_n = n_offsets < N
        local_logits = tl.zeros((BLOCK_M, BLOCK_N), dtype=tl.float32)
        for start_k in range(0, K, BLOCK_K):
            k_offsets = start_k + tl.arange(0, BLOCK_K)
            mask_k = k_offsets < K
            x_offsets = m_offsets[:, None] * stride_xm + k_offsets[None, :] * stride_xk
            x_mask = mask_m[:, None] & mask_k[None, :]
            x = tl.load(x_ptr + x_offsets, mask=x_mask, other=0.0, dtype=tl.float16).to(tl.float32)
            w_offsets = k_offsets[:, None] * stride_wk + n_offsets[None, :] * stride_wn
            w_mask = mask_k[:, None] & mask_n[None, :]
            w = tl.load(w_ptr + w_offsets, mask=w_mask, other=0.0, dtype=tl.float16).to(tl.float32)
            partial = tl.sum(x[:, :, None] * w[None, :, :], axis=1)
            local_logits += partial
        b_offsets = n_offsets * stride_bn
        b_mask = mask_n
        b_tile = tl.load(b_ptr + b_offsets, mask=b_mask, other=0.0)
        local_logits += b_tile[None, :]
        local_logits = tl.where(mask_n[None, :], local_logits, float("-inf"))
        tile_max = tl.max(local_logits, axis=1)
        acc = tl.maximum(acc, tile_max)
    row_max_offsets = m_offsets * stride_rm
    row_max_mask = mask_m
    tl.store(row_max_ptr + row_max_offsets, acc, mask=row_max_mask)

@triton.jit
def sum_exp_kernel(
    x_ptr, stride_xm, stride_xk,
    w_ptr, stride_wk, stride_wn,
    b_ptr, stride_bn,
    row_max_ptr, stride_rm,
    sum_exp_ptr, stride_se,
    M: tl.int32, K: tl.int32, N: tl.int32,
    BLOCK_M: tl.constexpr,
    BLOCK_N: tl.constexpr,
    BLOCK_K: tl.constexpr
):
    pid_m = tl.program_id(0)
    block_start_m = pid_m * BLOCK_M
    m_offsets = block_start_m + tl.arange(0, BLOCK_M)
    mask_m = m_offsets < M
    acc = tl.zeros((BLOCK_M,), dtype=tl.float32)
    rmax_offsets = m_offsets * stride_rm
    rmax_mask = mask_m
    rmax = tl.load(row_max_ptr + rmax_offsets, mask=rmax_mask, other=0.0)
    for start_n in range(0, N, BLOCK_N):
        n_offsets = start_n + tl.arange(0, BLOCK_N)
        mask_n = n_offsets < N
        local_logits = tl.zeros((BLOCK_M, BLOCK_N), dtype=tl.float32)
        for start_k in range(0, K, BLOCK_K):
            k_offsets = start_k + tl.arange(0, BLOCK_K)
            mask_k = k_offsets < K
            x_offsets = m_offsets[:, None] * stride_xm + k_offsets[None, :] * stride_xk
            x_mask = mask_m[:, None] & mask_k[None, :]
            x = tl.load(x_ptr + x_offsets, mask=x_mask, other=0.0, dtype=tl.float16).to(tl.float32)
            w_offsets = k_offsets[:, None] * stride_wk + n_offsets[None, :] * stride_wn
            w_mask = mask_k[:, None] & mask_n[None, :]
            w = tl.load(w_ptr + w_offsets, mask=w_mask, other=0.0, dtype=tl.float16).to(tl.float32)
            partial = tl.sum(x[:, :, None] * w[None, :, :], axis=1)
            local_logits += partial
        b_offsets = n_offsets * stride_bn
        b_mask = mask_n
        b_tile = tl.load(b_ptr + b_offsets, mask=b_mask, other=0.0)
        local_logits += b_tile[None, :]
        local_logits = tl.where(mask_n[None, :], local_logits, float("-inf"))
        sub = local_logits - rmax[:, None]
        expv = tl.exp(sub)
        partial_sum = tl.sum(expv, axis=1)
        acc += partial_sum
    sum_exp_offsets = m_offsets * stride_se
    sum_exp_mask = mask_m
    tl.store(sum_exp_ptr + sum_exp_offsets, acc, mask=sum_exp_mask)

@triton.jit
def target_logit_kernel(
    x_ptr, stride_xm, stride_xk,
    w_ptr, stride_wk, stride_wn,
    b_ptr, stride_bn,
    targets_ptr, stride_tg,
    y_ptr, stride_yl,
    M: tl.int32, K: tl.int32, N: tl.int32,
    BLOCK_K: tl.constexpr
):
    pid = tl.program_id(0)
    if pid >= M:
        return
    m = pid
    tgt_offset = m * stride_tg
    tgt = tl.load(targets_ptr + tgt_offset, dtype=tl.int64)
    if tgt >= N:
        return
    acc = tl.float32(0.0)
    for start_k in range(0, K, BLOCK_K):
        k_offsets = start_k + tl.arange(0, BLOCK_K)
        mask_k = k_offsets < K
        x_offsets = tl.full((BLOCK_K,), m * stride_xm + k_offsets * stride_xk, dtype=tl.int64)
        x = tl.load(x_ptr + x_offsets, mask=mask_k, other=0.0, dtype=tl.float16).to(tl.float32)
        w_offsets = k_offsets * stride_wk + tgt * stride_wn
        w = tl.load(w_ptr + w_offsets, mask=mask_k, other=0.0, dtype=tl.float16).to(tl.float32)
        acc += tl.sum(x * w)
    b_offset = tgt * stride_bn
    b_val = tl.load(b_ptr + b_offset)
    acc += b_val
    tl.store(y_ptr + m * stride_yl, acc)

def fused_linear_ce(X: torch.Tensor, W: torch.Tensor, B: torch.Tensor, targets: torch.Tensor) -> torch.Tensor:
    M, K = X.shape
    _, N = W.shape
    device = X.device
    dtype_f32 = torch.float32
    row_max = torch.empty(M, dtype=dtype_f32, device=device)
    sum_exp = torch.empty(M, dtype=dtype_f32, device=device)
    target_logits = torch.empty(M, dtype=dtype_f32, device=device)
    loss = torch.empty(M, dtype=dtype_f32, device=device)
    stride_xm = X.stride(0)
    stride_xk = X.stride(1)
    stride_wk = W.stride(0)
    stride_wn = W.stride(1)
    stride_bn = B.stride(0)
    stride_tg = targets.stride(0)
    stride_rm = row_max.stride(0)
    stride_se = sum_exp.stride(0)
    stride_tl = target_logits.stride(0)
    BLOCK_M = 128
    BLOCK_N = 128
    BLOCK_K = 64
    grid_m = lambda meta: (triton.cdiv(M, BLOCK_M), )
    row_max_kernel[grid_m](
        X, stride_xm, stride_xk,
        W, stride_wk, stride_wn,
        B, stride_bn,
        row_max, stride_rm,
        M, K, N,
        BLOCK_M=BLOCK_M,
        BLOCK_N=BLOCK_N,
        BLOCK_K=BLOCK_K
    )
    sum_exp_kernel[grid_m](
        X, stride_xm, stride_xk,
        W, stride_wk, stride_wn,
        B, stride_bn,
        row_max, stride_rm,
        sum_exp, stride_se,
        M, K, N,
        BLOCK_M=BLOCK_M,
        BLOCK_N=BLOCK_N,
        BLOCK_K=BLOCK_K
    )
    grid_t = lambda meta: (M, )
    target_logit_kernel[grid_t](
        X, stride_xm, stride_xk,
        W, stride_wk, stride_wn,
        B, stride_bn,
        targets, stride_tg,
        target_logits, stride_tl,
        M, K, N,
        BLOCK_K=BLOCK_K
    )
    log_sum_exp = torch.log(sum_exp) + row_max
    loss = log_sum_exp - target_logits
    return loss
"""
        return {"code": code}