import torch
import triton
import triton.language as tl

@triton.jit
def fused_linear_ce_kernel(
    X_ptr, W_ptr, B_ptr, targets_ptr, output_ptr,
    M, K, N,
    stride_xm, stride_xk,
    stride_wk, stride_wn,
    stride_bn,
    stride_targets_m,
    stride_output_m,
    BLOCK_SIZE_M: tl.constexpr,
    BLOCK_SIZE_N: tl.constexpr,
    BLOCK_SIZE_K: tl.constexpr,
    USE_ACCUMULATOR: tl.constexpr,
):
    pid_m = tl.program_id(0)
    pid_n = tl.program_id(1)
    
    offs_m = pid_m * BLOCK_SIZE_M + tl.arange(0, BLOCK_SIZE_M)
    offs_n = pid_n * BLOCK_SIZE_N + tl.arange(0, BLOCK_SIZE_N)
    offs_k = tl.arange(0, BLOCK_SIZE_K)
    
    X_ptrs = X_ptr + offs_m[:, None] * stride_xm + offs_k[None, :] * stride_xk
    W_ptrs = W_ptr + offs_k[:, None] * stride_wk + offs_n[None, :] * stride_wn
    
    acc = tl.zeros((BLOCK_SIZE_M, BLOCK_SIZE_N), dtype=tl.float32)
    
    for k in range(0, tl.cdiv(K, BLOCK_SIZE_K)):
        k_remaining = K - k * BLOCK_SIZE_K
        k_size = tl.minimum(BLOCK_SIZE_K, k_remaining)
        
        mask_x = (offs_m[:, None] < M) & (offs_k[None, :] < k_size)
        mask_w = (offs_k[:, None] < k_size) & (offs_n[None, :] < N)
        
        x = tl.load(X_ptrs, mask=mask_x, other=0.0).to(tl.float32)
        w = tl.load(W_ptrs, mask=mask_w, other=0.0).to(tl.float32)
        
        acc += tl.dot(x, w, allow_tf32=False)
        
        X_ptrs += BLOCK_SIZE_K * stride_xk
        W_ptrs += BLOCK_SIZE_K * stride_wk
    
    if USE_ACCUMULATOR:
        b_ptrs = B_ptr + offs_n * stride_bn
        b = tl.load(b_ptrs, mask=offs_n < N, other=0.0)
        acc += b[None, :]
    
    mask = (offs_m[:, None] < M) & (offs_n[None, :] < N)
    acc = tl.where(mask, acc, float('-inf'))
    
    max_val = tl.max(acc, axis=1)
    
    exp_vals = tl.exp(acc - max_val[:, None])
    sumexp = tl.sum(exp_vals, axis=1)
    
    targets_ptrs = targets_ptr + offs_m * stride_targets_m
    target_idx = tl.load(targets_ptrs, mask=offs_m < M, other=0)
    
    target_mask = (offs_n[None, :] == target_idx[:, None])
    target_logits = tl.sum(acc * target_mask, axis=1)
    
    log_sumexp = tl.log(sumexp)
    losses = -(target_logits - max_val - log_sumexp)
    
    output_ptrs = output_ptr + offs_m * stride_output_m
    tl.store(output_ptrs, losses, mask=offs_m < M)

@triton.jit
def fused_linear_ce_kernel_small(
    X_ptr, W_ptr, B_ptr, targets_ptr, output_ptr,
    M, K, N,
    stride_xm, stride_xk,
    stride_wk, stride_wn,
    stride_bn,
    stride_targets_m,
    stride_output_m,
    BLOCK_SIZE_M: tl.constexpr,
    BLOCK_SIZE_N: tl.constexpr,
    BLOCK_SIZE_K: tl.constexpr,
):
    pid = tl.program_id(0)
    
    offs_m = pid * BLOCK_SIZE_M + tl.arange(0, BLOCK_SIZE_M)
    offs_n = tl.arange(0, BLOCK_SIZE_N)
    offs_k = tl.arange(0, BLOCK_SIZE_K)
    
    X_ptrs = X_ptr + offs_m[:, None] * stride_xm + offs_k[None, :] * stride_xk
    
    acc = tl.zeros((BLOCK_SIZE_M, N), dtype=tl.float32)
    
    num_blocks_n = tl.cdiv(N, BLOCK_SIZE_N)
    
    for block_n in range(num_blocks_n):
        start_n = block_n * BLOCK_SIZE_N
        offs_n_block = start_n + tl.arange(0, BLOCK_SIZE_N)
        
        current_acc = tl.zeros((BLOCK_SIZE_M, BLOCK_SIZE_N), dtype=tl.float32)
        
        for k in range(0, tl.cdiv(K, BLOCK_SIZE_K)):
            k_remaining = K - k * BLOCK_SIZE_K
            k_size = tl.minimum(BLOCK_SIZE_K, k_remaining)
            
            mask_x = (offs_m[:, None] < M) & (offs_k[None, :] < k_size)
            mask_w = (offs_k[:, None] < k_size) & (offs_n_block[None, :] < N)
            
            x = tl.load(X_ptrs, mask=mask_x, other=0.0).to(tl.float32)
            
            W_ptrs = W_ptr + offs_k[:, None] * stride_wk + offs_n_block[None, :] * stride_wn
            w = tl.load(W_ptrs, mask=mask_w, other=0.0).to(tl.float32)
            
            current_acc += tl.dot(x, w, allow_tf32=False)
            
            X_ptrs += BLOCK_SIZE_K * stride_xk
        
        X_ptrs -= K * stride_xk
        
        if block_n == 0:
            b_ptrs = B_ptr + offs_n_block * stride_bn
            b = tl.load(b_ptrs, mask=offs_n_block < N, other=0.0)
            current_acc += b[None, :]
        
        store_mask = (offs_m[:, None] < M) & (offs_n_block[None, :] < N)
        
        col_indices = start_n + tl.arange(0, BLOCK_SIZE_N)
        row_expanded = offs_m[:, None]
        store_offsets = row_expanded * N + col_indices[None, :]
        
        acc_ptrs = acc + store_offsets
        tl.store(acc_ptrs, current_acc, mask=store_mask)
    
    max_val = tl.max(acc, axis=1)
    
    exp_vals = tl.exp(acc - max_val[:, None])
    sumexp = tl.sum(exp_vals, axis=1)
    
    targets_ptrs = targets_ptr + offs_m * stride_targets_m
    target_idx = tl.load(targets_ptrs, mask=offs_m < M, other=0)
    
    target_mask = tl.arange(0, N)[None, :] == target_idx[:, None]
    target_logits = tl.sum(acc * target_mask, axis=1)
    
    log_sumexp = tl.log(sumexp)
    losses = -(target_logits - max_val - log_sumexp)
    
    output_ptrs = output_ptr + offs_m * stride_output_m
    tl.store(output_ptrs, losses, mask=offs_m < M)

def fused_linear_ce(X: torch.Tensor, W: torch.Tensor, B: torch.Tensor, targets: torch.Tensor) -> torch.Tensor:
    M, K = X.shape
    N = W.shape[1]
    
    output = torch.empty(M, device=X.device, dtype=torch.float32)
    
    if M <= 256:
        BLOCK_SIZE_M = min(64, triton.next_power_of_2(M))
        BLOCK_SIZE_N = 128
        BLOCK_SIZE_K = 32
        
        grid = (triton.cdiv(M, BLOCK_SIZE_M),)
        
        fused_linear_ce_kernel_small[grid](
            X, W, B, targets, output,
            M, K, N,
            X.stride(0), X.stride(1),
            W.stride(0), W.stride(1),
            B.stride(0),
            targets.stride(0),
            output.stride(0),
            BLOCK_SIZE_M=BLOCK_SIZE_M,
            BLOCK_SIZE_N=BLOCK_SIZE_N,
            BLOCK_SIZE_K=BLOCK_SIZE_K,
        )
    else:
        if N <= 4096:
            BLOCK_SIZE_M = 64
            BLOCK_SIZE_N = 128
        else:
            BLOCK_SIZE_M = 32
            BLOCK_SIZE_N = 64
        
        BLOCK_SIZE_K = 32
        
        grid = (triton.cdiv(M, BLOCK_SIZE_M), triton.cdiv(N, BLOCK_SIZE_N))
        
        fused_linear_ce_kernel[grid](
            X, W, B, targets, output,
            M, K, N,
            X.stride(0), X.stride(1),
            W.stride(0), W.stride(1),
            B.stride(0),
            targets.stride(0),
            output.stride(0),
            BLOCK_SIZE_M=BLOCK_SIZE_M,
            BLOCK_SIZE_N=BLOCK_SIZE_N,
            BLOCK_SIZE_K=BLOCK_SIZE_K,
            USE_ACCUMULATOR=True,
        )
    
    return output

class Solution:
    def solve(self, spec_path: str = None) -> dict:
        return {"code": self._get_code()}
    
    def _get_code(self) -> str:
        import inspect
        return inspect.getsource(fused_linear_ce) + "\n\n" + inspect.getsource(Solution)