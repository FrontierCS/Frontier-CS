import torch
import triton
import triton.language as tl
import math

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
    row_max = torch.full((M,), float('-inf'), dtype=torch.float32, device=device)
    sum_exp = torch.zeros((M,), dtype=torch.float32, device=device)
    output = torch.empty((M,), dtype=torch.float32, device=device)

    @triton.jit
    def linear_bias_kernel(
        X_ptr, W_ptr, B_ptr, logits_ptr,
        M, K, N,
        stride_xm, stride_xk,
        stride_wk, stride_wn,
        stride_bn,
        stride_lm, stride_ln,
        BLOCK_M: tl.constexpr,
        BLOCK_N: tl.constexpr,
        BLOCK_K: tl.constexpr,
    ):
        pid_m = tl.program_id(0)
        pid_n = tl.program_id(1)
        offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
        offs_n = pid_n * BLOCK_N + tl.arange(0, BLOCK_N)
        mask_m = offs_m < M
        mask_n = offs_n < N
        acc = tl.zeros((BLOCK_M, BLOCK_N), dtype=tl.float32)
        offs_k = tl.arange(0, BLOCK_K)
        for start_k in range(0, K, BLOCK_K):
            k_mask = (start_k + offs_k) < K
            x_offsets = offs_m[:, None] * stride_xm + (start_k + offs_k)[None, :] * stride_xk
            x_ptrs = X_ptr + x_offsets
            x = tl.load(x_ptrs, mask=mask_m[:, None] & k_mask[None, :], other=0.0).to(tl.float32)
            w_offsets = (start_k + offs_k)[:, None] * stride_wk + offs_n[None, :] * stride_wn
            w_ptrs = W_ptr + w_offsets
            w = tl.load(w_ptrs, mask=k_mask[:, None] & mask_n[None, :], other=0.0).to(tl.float32)
            acc += tl.dot(x, w)
        b_offsets = offs_n * stride_bn
        b_ptrs = B_ptr + b_offsets
        b = tl.load(b_ptrs, mask=mask_n, other=0.0)
        acc += b[None, :]
        l_offsets = offs_m[:, None] * stride_lm + offs_n[None, :] * stride_ln
        l_ptrs = logits_ptr + l_offsets
        l_mask = mask_m[:, None] & mask_n[None, :]
        tl.store(l_ptrs, acc, mask=l_mask)

    BLOCK_M = 64
    BLOCK_N = 128
    BLOCK_K = 128
    grid_m = triton.cdiv(M, BLOCK_M)
    grid_n = triton.cdiv(N, BLOCK_N)
    linear_bias_kernel[grid=(grid_m, grid_n)](
        X.data_ptr(), W.data_ptr(), B.data_ptr(), logits.data_ptr(),
        M, K, N,
        X.stride(0), X.stride(1),
        W.stride(0), W.stride(1),
        B.stride(0),
        logits.stride(0), logits.stride(1),
        BLOCK_M=BLOCK_M, BLOCK_N=BLOCK_N, BLOCK_K=BLOCK_K,
    )

    @triton.jit
    def row_max_kernel(
        logits_ptr, row_max_ptr,
        M, N,
        stride_lm, stride_ln, stride_rm,
        BLOCK_N: tl.constexpr,
    ):
        pid_m = tl.program_id(0)
        pid_n = tl.program_id(1)
        if pid_m >= M:
            return
        offs_n = pid_n * BLOCK_N + tl.arange(0, BLOCK_N)
        mask_n = offs_n < N
        logits_offsets = pid_m * stride_lm + offs_n * stride_ln
        logits_ptrs = logits_ptr + logits_offsets
        logits_block = tl.load(logits_ptrs, mask=mask_n, other=-1e9)
        block_max = tl.max(logits_block.to(tl.float32), axis=0)
        addr = row_max_ptr + pid_m * stride_rm
        for _ in range(10):
            old = tl.load(addr)
            if block_max <= old:
                break
            if tl.atomic_cas(addr, old, block_max) == old:
                break

    BLOCK_RED_N = 1024
    grid_n_red = triton.cdiv(N, BLOCK_RED_N)
    row_max_kernel[grid=(M, grid_n_red)](
        logits.data_ptr(), row_max.data_ptr(),
        M, N,
        logits.stride(0), logits.stride(1), row_max.stride(0),
        BLOCK_RED_N,
    )

    @triton.jit
    def sum_exp_kernel(
        logits_ptr, row_max_ptr, sum_exp_ptr,
        M, N,
        stride_lm, stride_ln, stride_rm, stride_se,
        BLOCK_N: tl.constexpr,
    ):
        pid_m = tl.program_id(0)
        pid_n = tl.program_id(1)
        if pid_m >= M:
            return
        offs_n = pid_n * BLOCK_N + tl.arange(0, BLOCK_N)
        mask_n = offs_n < N
        logits_offsets = pid_m * stride_lm + offs_n * stride_ln
        logits_ptrs = logits_ptr + logits_offsets
        logits_block = tl.load(logits_ptrs, mask=mask_n, other=0.0)
        row_max_m = tl.load(row_max_ptr + pid_m * stride_rm)
        centered = logits_block.to(tl.float32) - row_max_m
        exp_block = tl.exp(centered)
        block_sum = tl.sum(exp_block, axis=0)
        tl.atomic_add(sum_exp_ptr + pid_m * stride_se, block_sum)

    sum_exp_kernel[grid=(M, grid_n_red)](
        logits.data_ptr(), row_max.data_ptr(), sum_exp.data_ptr(),
        M, N,
        logits.stride(0), logits.stride(1), row_max.stride(0), sum_exp.stride(0),
        BLOCK_RED_N,
    )

    @triton.jit
    def loss_kernel(
        logits_ptr, targets_ptr, row_max_ptr, sum_exp_ptr, output_ptr,
        M, N,
        stride_lm, stride_ln, stride_tm,
        stride_rm, stride_se, stride_om,
    ):
        pid = tl.program_id(0)
        if pid >= M:
            return
        target_idx = tl.load(targets_ptr + pid * stride_tm).to(tl.int64)
        logit_ptr = logits_ptr + pid * stride_lm + target_idx * stride_ln
        logit_target = tl.load(logit_ptr).to(tl.float32)
        rm = tl.load(row_max_ptr + pid * stride_rm)
        se = tl.load(sum_exp_ptr + pid * stride_se)
        if se == 0.0:
            loss = torch.tensor(0.0, dtype=torch.float32)
        else:
            lse = rm + tl.log(se)
            loss = -(logit_target - lse)
        tl.store(output_ptr + pid * stride_om, loss)

    loss_kernel[grid=(M,)](
        logits.data_ptr(), targets.data_ptr(), row_max.data_ptr(), sum_exp.data_ptr(), output.data_ptr(),
        M, N,
        logits.stride(0), logits.stride(1), targets.stride(0),
        row_max.stride(0), sum_exp.stride(0), output.stride(0),
    )
    return output
"""
        return {"code": code}
