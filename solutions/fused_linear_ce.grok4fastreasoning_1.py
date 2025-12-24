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
def row_max_kernel(
    X_ptr, W_ptr, B_ptr, row_max_ptr,
    M: tl.int32, K: tl.int32, N: tl.int32,
    stride_xm: tl.int32, stride_xk: tl.int32,
    stride_wk: tl.int32, stride_wn: tl.int32,
    stride_b: tl.int32,
    stride_rm: tl.int32
):
    pid_m = tl.program_id(0)
    if pid_m >= M:
        return
    pid_n = tl.program_id(1)
    n_start = pid_n * 256
    offs_n = n_start + tl.arange(0, 256)
    mask_n = offs_n < N
    acc = tl.zeros([256], dtype=tl.float32)
    for k_start in range(0, K, 64):
        offs_k = tl.arange(0, 64)
        mask_k = k_start + offs_k < K
        x_ptrs = X_ptr + pid_m * stride_xm + (k_start + offs_k) * stride_xk
        x_tile = tl.load(x_ptrs, mask=mask_k, other=0.0, dtype=tl.float16).to(tl.float32)
        for kk in range(64):
            k = k_start + kk
            if k >= K:
                break
            w_ptrs = W_ptr + k * stride_wk + n_start * stride_wn + tl.arange(0, 256) * stride_wn
            w_k = tl.load(w_ptrs, mask=mask_n, other=0.0, dtype=tl.float16).to(tl.float32)
            acc += x_tile[kk] * w_k
    b_ptrs = B_ptr + offs_n * stride_b
    b_vec = tl.load(b_ptrs, mask=mask_n, other=0.0, dtype=tl.float32)
    acc += b_vec
    rm_ptr = row_max_ptr + pid_m * stride_rm
    tl.atomic_max(rm_ptr, acc, mask=mask_n)

@triton.jit
def ce_kernel(
    X_ptr, W_ptr, B_ptr, targets_ptr, row_max_ptr, sum_exp_ptr, target_shifted_ptr,
    M: tl.int32, K: tl.int32, N: tl.int32,
    stride_xm: tl.int32, stride_xk: tl.int32,
    stride_wk: tl.int32, stride_wn: tl.int32,
    stride_b: tl.int32, stride_t: tl.int64,
    stride_rm: tl.int32, stride_se: tl.int32, stride_tl: tl.int32
):
    pid_m = tl.program_id(0)
    if pid_m >= M:
        return
    pid_n = tl.program_id(1)
    n_start = pid_n * 256
    offs_n = n_start + tl.arange(0, 256)
    mask_n = offs_n < N
    acc = tl.zeros([256], dtype=tl.float32)
    for k_start in range(0, K, 64):
        offs_k = tl.arange(0, 64)
        mask_k = k_start + offs_k < K
        x_ptrs = X_ptr + pid_m * stride_xm + (k_start + offs_k) * stride_xk
        x_tile = tl.load(x_ptrs, mask=mask_k, other=0.0, dtype=tl.float16).to(tl.float32)
        for kk in range(64):
            k = k_start + kk
            if k >= K:
                break
            w_ptrs = W_ptr + k * stride_wk + n_start * stride_wn + tl.arange(0, 256) * stride_wn
            w_k = tl.load(w_ptrs, mask=mask_n, other=0.0, dtype=tl.float16).to(tl.float32)
            acc += x_tile[kk] * w_k
    b_ptrs = B_ptr + offs_n * stride_b
    b_vec = tl.load(b_ptrs, mask=mask_n, other=0.0, dtype=tl.float32)
    acc += b_vec
    row_max_m = tl.load(row_max_ptr + pid_m * stride_rm, dtype=tl.float32)
    acc -= row_max_m
    exp_vec = tl.exp(acc)
    partial_sum = tl.sum(exp_vec)
    tl.atomic_add(sum_exp_ptr + pid_m * stride_se, partial_sum)
    target_n = tl.load(targets_ptr + pid_m * stride_t, dtype=tl.int64)
    in_range = (target_n >= n_start) & (target_n < n_start + 256)
    if in_range:
        local_idx = (target_n - tl.int64(n_start)).to(tl.int32)
        is_target = (tl.arange(0, 256) == local_idx)
        tgt_val = tl.where(is_target, acc, 0.0)
        tl.store(target_shifted_ptr + pid_m * stride_tl, tgt_val, mask=is_target)

def fused_linear_ce(X: torch.Tensor, W: torch.Tensor, B: torch.Tensor, targets: torch.Tensor) -> torch.Tensor:
    M, K = X.shape
    assert W.shape[0] == K
    N = W.shape[1]
    assert B.shape[0] == N
    assert targets.shape[0] == M
    device = X.device
    num_n_blocks = 32
    grid = (M, num_n_blocks)
    row_max = torch.full((M,), float('-inf'), dtype=torch.float32, device=device)
    sum_exp = torch.zeros((M,), dtype=torch.float32, device=device)
    target_shifted = torch.zeros((M,), dtype=torch.float32, device=device)
    row_max_kernel[grid](
        X, W, B, row_max,
        M, K, N,
        X.stride(0), X.stride(1),
        W.stride(0), W.stride(1),
        B.stride(0),
        row_max.stride(0)
    )
    ce_kernel[grid](
        X, W, B, targets, row_max, sum_exp, target_shifted,
        M, K, N,
        X.stride(0), X.stride(1),
        W.stride(0), W.stride(1),
        B.stride(0),
        targets.stride(0),
        row_max.stride(0),
        sum_exp.stride(0),
        target_shifted.stride(0)
    )
    losses = -target_shifted + torch.log(sum_exp)
    return losses
"""
        return {"code": code}
