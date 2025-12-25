import torch
import triton
import triton.language as tl

class Solution:
    def solve(self, spec_path: str = None) -> dict:
        code = """
import torch
import triton
import triton.language as tl

def fused_linear_ce(X: torch.Tensor, W: torch.Tensor, B: torch.Tensor, targets: torch.Tensor) -> torch.Tensor:
    M, K = X.shape
    _, N = W.shape
    device = X.device
    logits = torch.empty((M, N), dtype=torch.float32, device=device)
    
    # Matmul + bias kernel
    BLOCK_M = 128
    BLOCK_N = 128
    BLOCK_K = 64
    grid_mm = (triton.cdiv(M, BLOCK_M), triton.cdiv(N, BLOCK_N))
    stride_xm = X.stride(0)
    stride_xk = X.stride(1)
    stride_wk = W.stride(0)
    stride_wn = W.stride(1)
    stride_b = B.stride(0)
    stride_om = logits.stride(0)
    stride_on = logits.stride(1)
    
    @triton.jit
    def matmul_kernel(
        x_ptr, w_ptr, b_ptr, o_ptr,
        M: tl.constexpr, N: tl.constexpr, K: tl.constexpr,
        stride_xm: tl.constexpr, stride_xk: tl.constexpr,
        stride_wk: tl.constexpr, stride_wn: tl.constexpr,
        stride_b: tl.constexpr, stride_om: tl.constexpr, stride_on: tl.constexpr,
        BLOCK_M: tl.constexpr, BLOCK_N: tl.constexpr, BLOCK_K: tl.constexpr
    ):
        pid_m = tl.program_id(0)
        pid_n = tl.program_id(1)
        offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
        offs_n = pid_n * BLOCK_N + tl.arange(0, BLOCK_N)
        mask_m = offs_m < M
        mask_n = offs_n < N
        acc = tl.zeros((BLOCK_M, BLOCK_N), dtype=tl.float32)
        for k_start in range(0, K, BLOCK_K):
            offs_k = k_start + tl.arange(0, BLOCK_K)
            mask_k = offs_k < K
            x_ptrs = x_ptr + (offs_m[:, None] * stride_xm + offs_k[None, :] * stride_xk)
            w_ptrs = w_ptr + (offs_k[:, None] * stride_wk + offs_n[None, :] * stride_wn)
            x_mask = mask_m[:, None] & mask_k[None, :]
            w_mask = mask_k[:, None] & mask_n[None, :]
            x = tl.load(x_ptrs, mask=x_mask, other=0.0)
            w = tl.load(w_ptrs, mask=w_mask, other=0.0)
            acc += tl.dot(x, w)
        b = tl.load(b_ptr + offs_n * stride_b, mask=mask_n, other=0.0)
        acc += b[None, :]
        o_ptrs = o_ptr + (offs_m[:, None] * stride_om + offs_n[None, :] * stride_on)
        mask_o = mask_m[:, None] & mask_n[None, :]
        tl.store(o_ptrs, acc, mask=mask_o)
    
    matmul_kernel[grid_mm](
        X, W, B, logits, M, N, K,
        stride_xm, stride_xk, stride_wk, stride_wn, stride_b, stride_om, stride_on,
        BLOCK_M, BLOCK_N, BLOCK_K
    )
    
    # CE pass 1: max and target logit
    max_logits = torch.empty(M, dtype=torch.float32, device=device)
    target_logits = torch.empty(M, dtype=torch.float32, device=device)
    BLOCK_N_CE = 1024
    grid_ce = (M,)
    stride_lm = logits.stride(0)
    stride_ln = logits.stride(1)
    stride_t = targets.stride(0)
    stride_max = max_logits.stride(0)
    stride_tlog = target_logits.stride(0)
    
    @triton.jit
    def ce_pass1_kernel(
        l_ptr, t_ptr, max_ptr, tlog_ptr,
        M: tl.constexpr, N: tl.constexpr,
        stride_lm: tl.constexpr, stride_ln: tl.constexpr,
        stride_t: tl.constexpr, stride_max: tl.constexpr, stride_tlog: tl.constexpr,
        BLOCK_N: tl.constexpr
    ):
        pid = tl.program_id(0)
        if pid >= M:
            return
        row_max = tl.float32(-1e9)
        target_log = tl.float32(0.0)
        t = tl.load(t_ptr + pid * stride_t)
        num_blocks = (N + BLOCK_N - 1) // BLOCK_N
        for j in range(num_blocks):
            n_start = j * BLOCK_N
            offs_n = tl.arange(0, BLOCK_N)
            mask_n = (n_start + offs_n) < N
            l_off = pid * stride_lm + (n_start + offs_n) * stride_ln
            sub = tl.load(l_ptr + l_off, mask=mask_n, other=tl.float32(-1e9))
            sub_max = tl.max(sub, axis=0)
            row_max = tl.maximum(row_max, sub_max)
            if n_start <= t < n_start + BLOCK_N:
                idx = tl.int32(t - n_start)
                target_log = sub[idx]
        tl.store(max_ptr + pid * stride_max, row_max)
        tl.store(tlog_ptr + pid * stride_tlog, target_log)
    
    ce_pass1_kernel[grid_ce](
        logits, targets, max_logits, target_logits, M, N,
        stride_lm, stride_ln, stride_t, stride_max, stride_tlog,
        BLOCK_N=BLOCK_N_CE
    )
    
    # CE pass 2: sumexp and loss
    output = torch.empty(M, dtype=torch.float32, device=device)
    stride_out = output.stride(0)
    stride_max2 = max_logits.stride(0)
    stride_tlog2 = target_logits.stride(0)
    
    @triton.jit
    def ce_pass2_kernel(
        l_ptr, max_ptr, tlog_ptr, out_ptr,
        M: tl.constexpr, N: tl.constexpr,
        stride_lm: tl.constexpr, stride_ln: tl.constexpr,
        stride_max: tl.constexpr, stride_tlog: tl.constexpr, stride_out: tl.constexpr,
        BLOCK_N: tl.constexpr
    ):
        pid = tl.program_id(0)
        if pid >= M:
            return
        row_max = tl.load(max_ptr + pid * stride_max)
        target_log = tl.load(tlog_ptr + pid * stride_tlog)
        sum_exp = tl.float32(0.0)
        num_blocks = (N + BLOCK_N - 1) // BLOCK_N
        for j in range(num_blocks):
            n_start = j * BLOCK_N
            offs_n = tl.arange(0, BLOCK_N)
            mask_n = (n_start + offs_n) < N
            l_off = pid * stride_lm + (n_start + offs_n) * stride_ln
            sub = tl.load(l_ptr + l_off, mask=mask_n, other=tl.float32(0.0))
            sub = sub - row_max
            exp_sub = tl.exp(sub)
            partial = tl.sum(exp_sub, axis=0)
            sum_exp += partial
        logsum = tl.log(sum_exp) + row_max
        loss = - (target_log - logsum)
        tl.store(out_ptr + pid * stride_out, loss)
    
    ce_pass2_kernel[grid_ce](
        logits, max_logits, target_logits, output, M, N,
        stride_lm, stride_ln, stride_max2, stride_tlog2, stride_out,
        BLOCK_N=BLOCK_N_CE
    )
    
    return output
"""
        return {"code": code}
