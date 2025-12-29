import torch
import triton
import triton.language as tl
import os
import json

@triton.jit
def fused_linear_jsd_kernel(
    X_ptr, W1_ptr, B1_ptr, W2_ptr, B2_ptr, output_ptr,
    M, K, N,
    stride_Xm, stride_Xk,
    stride_W1k, stride_W1n,
    stride_W2k, stride_W2n,
    stride_output_m,
    BLOCK_M: tl.constexpr,
    BLOCK_N: tl.constexpr,
    BLOCK_K: tl.constexpr,
    TWO_PASS: tl.constexpr,
    USE_FP16_ACCUM: tl.constexpr,
):
    pid_m = tl.program_id(0)
    pid_n = tl.program_id(1)
    
    offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
    offs_n = pid_n * BLOCK_N + tl.arange(0, BLOCK_N)
    offs_k = tl.arange(0, BLOCK_K)
    
    X_ptrs = X_ptr + offs_m[:, None] * stride_Xm + offs_k[None, :] * stride_Xk
    W1_ptrs = W1_ptr + offs_k[:, None] * stride_W1k + offs_n[None, :] * stride_W1n
    W2_ptrs = W2_ptr + offs_k[:, None] * stride_W2k + offs_n[None, :] * stride_W2n
    
    mask_m = offs_m < M
    mask_n = offs_n < N
    
    acc1 = tl.zeros((BLOCK_M, BLOCK_N), dtype=tl.float32)
    acc2 = tl.zeros((BLOCK_M, BLOCK_N), dtype=tl.float32)
    
    for k in range(0, K, BLOCK_K):
        k_remaining = K - k
        mask_k = offs_k < k_remaining
        
        X = tl.load(X_ptrs, mask=mask_m[:, None] & mask_k[None, :], other=0.0)
        W1 = tl.load(W1_ptrs, mask=mask_k[:, None] & mask_n[None, :], other=0.0)
        W2 = tl.load(W2_ptrs, mask=mask_k[:, None] & mask_n[None, :], other=0.0)
        
        if USE_FP16_ACCUM:
            X_f32 = X.to(tl.float32)
            W1_f32 = W1.to(tl.float32)
            W2_f32 = W2.to(tl.float32)
            acc1 += tl.dot(X_f32, W1_f32)
            acc2 += tl.dot(X_f32, W2_f32)
        else:
            acc1 += tl.dot(X, W1)
            acc2 += tl.dot(X, W2)
        
        X_ptrs += BLOCK_K * stride_Xk
        W1_ptrs += BLOCK_K * stride_W1k
        W2_ptrs += BLOCK_K * stride_W2k
    
    if TWO_PASS == 1:
        # First pass: compute log-sum-exp for both distributions
        B1 = tl.load(B1_ptr + offs_n, mask=mask_n, other=0.0)
        B2 = tl.load(B2_ptr + offs_n, mask=mask_n, other=0.0)
        
        logits1 = acc1 + B1[None, :]
        logits2 = acc2 + B2[None, :]
        
        # Compute max for numerical stability
        max1 = tl.max(logits1, axis=1)
        max2 = tl.max(logits2, axis=1)
        
        # Compute sum of exponentials
        exp1 = tl.exp(logits1 - max1[:, None])
        exp2 = tl.exp(logits2 - max2[:, None])
        
        sum_exp1 = tl.sum(exp1, axis=1)
        sum_exp2 = tl.sum(exp2, axis=1)
        
        log_sum_exp1 = tl.log(sum_exp1) + max1
        log_sum_exp2 = tl.log(sum_exp2) + max2
        
        # Store intermediate results in shared memory
        smem_max1 = tl.zeros((BLOCK_M,), dtype=tl.float32)
        smem_max2 = tl.zeros((BLOCK_M,), dtype=tl.float32)
        smem_log_sum_exp1 = tl.zeros((BLOCK_M,), dtype=tl.float32)
        smem_log_sum_exp2 = tl.zeros((BLOCK_M,), dtype=tl.float32)
        
        tl.store(smem_max1 + offs_m * 0, max1, mask=mask_m)
        tl.store(smem_max2 + offs_m * 0, max2, mask=mask_m)
        tl.store(smem_log_sum_exp1 + offs_m * 0, log_sum_exp1, mask=mask_m)
        tl.store(smem_log_sum_exp2 + offs_m * 0, log_sum_exp2, mask=mask_m)
        
        tl.debug_barrier()
        
        # Load shared values for this row
        max1_val = tl.load(smem_max1 + offs_m * 0, mask=mask_m, other=0.0)
        max2_val = tl.load(smem_max2 + offs_m * 0, mask=mask_m, other=0.0)
        log_sum_exp1_val = tl.load(smem_log_sum_exp1 + offs_m * 0, mask=mask_m, other=0.0)
        log_sum_exp2_val = tl.load(smem_log_sum_exp2 + offs_m * 0, mask=mask_m, other=0.0)
        
        # Second pass: compute JSD
        logits1 = acc1 + B1[None, :]
        logits2 = acc2 + B2[None, :]
        
        # Compute probabilities
        p = tl.exp(logits1 - log_sum_exp1_val[:, None])
        q = tl.exp(logits2 - log_sum_exp2_val[:, None])
        m = 0.5 * (p + q)
        
        # Compute KL divergences with numerical stability
        log_p = logits1 - log_sum_exp1_val[:, None]
        log_q = logits2 - log_sum_exp2_val[:, None]
        log_m = tl.log(m + 1e-12)
        
        kl_p_m = p * (log_p - log_m)
        kl_q_m = q * (log_q - log_m)
        
        # Mask invalid computations
        kl_p_m = tl.where(p > 1e-12, kl_p_m, 0.0)
        kl_q_m = tl.where(q > 1e-12, kl_q_m, 0.0)
        
        jsd = 0.5 * (kl_p_m + kl_q_m)
        
        # Sum across N dimension
        jsd_sum = tl.sum(jsd, axis=1)
        
        # Accumulate across blocks
        output_ptrs = output_ptr + offs_m * stride_output_m
        if pid_n == 0:
            tl.store(output_ptrs, jsd_sum, mask=mask_m)
        else:
            old = tl.load(output_ptrs, mask=mask_m, other=0.0)
            tl.store(output_ptrs, old + jsd_sum, mask=mask_m)
    else:
        # Single-pass JSD computation (less accurate but faster)
        B1 = tl.load(B1_ptr + offs_n, mask=mask_n, other=0.0)
        B2 = tl.load(B2_ptr + offs_n, mask=mask_n, other=0.0)
        
        logits1 = acc1 + B1[None, :]
        logits2 = acc2 + B2[None, :]
        
        # Compute probabilities with numerical stability
        max1 = tl.max(logits1, axis=1)
        max2 = tl.max(logits2, axis=1)
        
        p = tl.exp(logits1 - max1[:, None])
        q = tl.exp(logits2 - max2[:, None])
        
        p_sum = tl.sum(p, axis=1)
        q_sum = tl.sum(q, axis=1)
        
        p = p / p_sum[:, None]
        q = q / q_sum[:, None]
        m = 0.5 * (p + q)
        
        # Compute JSD
        log_p = tl.log(p + 1e-12)
        log_q = tl.log(q + 1e-12)
        log_m = tl.log(m + 1e-12)
        
        kl_p_m = p * (log_p - log_m)
        kl_q_m = q * (log_q - log_m)
        
        jsd = 0.5 * (kl_p_m + kl_q_m)
        jsd_sum = tl.sum(jsd, axis=1)
        
        output_ptrs = output_ptr + offs_m * stride_output_m
        if pid_n == 0:
            tl.store(output_ptrs, jsd_sum, mask=mask_m)
        else:
            old = tl.load(output_ptrs, mask=mask_m, other=0.0)
            tl.store(output_ptrs, old + jsd_sum, mask=mask_m)

def fused_linear_jsd(
    X: torch.Tensor, 
    W1: torch.Tensor, 
    B1: torch.Tensor, 
    W2: torch.Tensor, 
    B2: torch.Tensor
) -> torch.Tensor:
    M, K = X.shape
    N = W1.shape[1]
    
    assert X.dtype == torch.float16
    assert W1.dtype == torch.float16
    assert W2.dtype == torch.float16
    assert B1.dtype == torch.float32
    assert B2.dtype == torch.float32
    assert X.is_cuda
    
    output = torch.zeros(M, dtype=torch.float32, device=X.device)
    
    # Choose block sizes based on problem dimensions
    if M >= 256 and N >= 4096:
        BLOCK_M, BLOCK_N, BLOCK_K = 128, 128, 64
    elif M >= 128:
        BLOCK_M, BLOCK_N, BLOCK_K = 64, 128, 64
    else:
        BLOCK_M, BLOCK_N, BLOCK_K = 32, 128, 64
    
    grid = (triton.cdiv(M, BLOCK_M), triton.cdiv(N, BLOCK_N))
    
    # Use two-pass for better numerical stability
    TWO_PASS = 1
    USE_FP16_ACCUM = 0  # Use float32 accumulation for better precision
    
    fused_linear_jsd_kernel[grid](
        X, W1, B1, W2, B2, output,
        M, K, N,
        X.stride(0), X.stride(1),
        W1.stride(0), W1.stride(1),
        W2.stride(0), W2.stride(1),
        output.stride(0),
        BLOCK_M=BLOCK_M,
        BLOCK_N=BLOCK_N,
        BLOCK_K=BLOCK_K,
        TWO_PASS=TWO_PASS,
        USE_FP16_ACCUM=USE_FP16_ACCUM,
        num_warps=8 if BLOCK_N >= 128 else 4,
        num_stages=3,
    )
    
    return output

class Solution:
    def solve(self, spec_path: str = None) -> dict:
        if spec_path and os.path.exists(spec_path):
            with open(spec_path, 'r') as f:
                spec = json.load(f)
            
            # Generate specialized kernel based on spec
            kernel_code = self._generate_specialized_kernel(spec)
            return {"code": kernel_code}
        else:
            # Return the default implementation
            code = self._get_default_code()
            return {"code": code}
    
    def _generate_specialized_kernel(self, spec):
        """Generate specialized kernel based on problem specification"""
        # Extract parameters from spec
        M_list = spec.get('M_list', [128, 256])
        K = spec.get('K', 2048)
        N = spec.get('N', 4096)
        
        # Generate specialized kernel with optimal parameters
        specialized_code = f'''import torch
import triton
import triton.language as tl

@triton.jit
def fused_linear_jsd_kernel_specialized(
    X_ptr, W1_ptr, B1_ptr, W2_ptr, B2_ptr, output_ptr,
    M, K, N,
    stride_Xm, stride_Xk,
    stride_W1k, stride_W1n,
    stride_W2k, stride_W2n,
    stride_output_m,
    BLOCK_M: tl.constexpr,
    BLOCK_N: tl.constexpr,
    BLOCK_K: tl.constexpr,
):
    pid_m = tl.program_id(0)
    pid_n = tl.program_id(1)
    
    offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
    offs_n = pid_n * BLOCK_N + tl.arange(0, BLOCK_N)
    offs_k = tl.arange(0, BLOCK_K)
    
    X_ptrs = X_ptr + offs_m[:, None] * stride_Xm + offs_k[None, :] * stride_Xk
    W1_ptrs = W1_ptr + offs_k[:, None] * stride_W1k + offs_n[None, :] * stride_W1n
    W2_ptrs = W2_ptr + offs_k[:, None] * stride_W2k + offs_n[None, :] * stride_W2n
    
    mask_m = offs_m < M
    mask_n = offs_n < N
    
    acc1 = tl.zeros((BLOCK_M, BLOCK_N), dtype=tl.float32)
    acc2 = tl.zeros((BLOCK_M, BLOCK_N), dtype=tl.float32)
    
    for k in range(0, K, BLOCK_K):
        k_remaining = K - k
        mask_k = offs_k < k_remaining
        
        X = tl.load(X_ptrs, mask=mask_m[:, None] & mask_k[None, :], other=0.0)
        W1 = tl.load(W1_ptrs, mask=mask_k[:, None] & mask_n[None, :], other=0.0)
        W2 = tl.load(W2_ptrs, mask=mask_k[:, None] & mask_n[None, :], other=0.0)
        
        X_f32 = X.to(tl.float32)
        W1_f32 = W1.to(tl.float32)
        W2_f32 = W2.to(tl.float32)
        acc1 += tl.dot(X_f32, W1_f32)
        acc2 += tl.dot(X_f32, W2_f32)
        
        X_ptrs += BLOCK_K * stride_Xk
        W1_ptrs += BLOCK_K * stride_W1k
        W2_ptrs += BLOCK_K * stride_W2k
    
    # First pass: compute log-sum-exp
    B1 = tl.load(B1_ptr + offs_n, mask=mask_n, other=0.0)
    B2 = tl.load(B2_ptr + offs_n, mask=mask_n, other=0.0)
    
    logits1 = acc1 + B1[None, :]
    logits2 = acc2 + B2[None, :]
    
    max1 = tl.max(logits1, axis=1)
    max2 = tl.max(logits2, axis=1)
    
    exp1 = tl.exp(logits1 - max1[:, None])
    exp2 = tl.exp(logits2 - max2[:, None])
    
    sum_exp1 = tl.sum(exp1, axis=1)
    sum_exp2 = tl.sum(exp2, axis=1)
    
    log_sum_exp1 = tl.log(sum_exp1) + max1
    log_sum_exp2 = tl.log(sum_exp2) + max2
    
    # Store in shared memory for second pass
    smem_max1 = tl.zeros((BLOCK_M,), dtype=tl.float32)
    smem_max2 = tl.zeros((BLOCK_M,), dtype=tl.float32)
    smem_log_sum_exp1 = tl.zeros((BLOCK_M,), dtype=tl.float32)
    smem_log_sum_exp2 = tl.zeros((BLOCK_M,), dtype=tl.float32)
    
    tl.store(smem_max1 + offs_m * 0, max1, mask=mask_m)
    tl.store(smem_max2 + offs_m * 0, max2, mask=mask_m)
    tl.store(smem_log_sum_exp1 + offs_m * 0, log_sum_exp1, mask=mask_m)
    tl.store(smem_log_sum_exp2 + offs_m * 0, log_sum_exp2, mask=mask_m)
    
    tl.debug_barrier()
    
    # Load shared values
    max1_val = tl.load(smem_max1 + offs_m * 0, mask=mask_m, other=0.0)
    max2_val = tl.load(smem_max2 + offs_m * 0, mask=mask_m, other=0.0)
    log_sum_exp1_val = tl.load(smem_log_sum_exp1 + offs_m * 0, mask=mask_m, other=0.0)
    log_sum_exp2_val = tl.load(smem_log_sum_exp2 + offs_m * 0, mask=mask_m, other=0.0)
    
    # Second pass: compute JSD
    logits1 = acc1 + B1[None, :]
    logits2 = acc2 + B2[None, :]
    
    p = tl.exp(logits1 - log_sum_exp1_val[:, None])
    q = tl.exp(logits2 - log_sum_exp2_val[:, None])
    m = 0.5 * (p + q)
    
    log_p = logits1 - log_sum_exp1_val[:, None]
    log_q = logits2 - log_sum_exp2_val[:, None]
    log_m = tl.log(m + 1e-12)
    
    kl_p_m = p * (log_p - log_m)
    kl_q_m = q * (log_q - log_m)
    
    kl_p_m = tl.where(p > 1e-12, kl_p_m, 0.0)
    kl_q_m = tl.where(q > 1e-12, kl_q_m, 0.0)
    
    jsd = 0.5 * (kl_p_m + kl_q_m)
    jsd_sum = tl.sum(jsd, axis=1)
    
    output_ptrs = output_ptr + offs_m * stride_output_m
    if pid_n == 0:
        tl.store(output_ptrs, jsd_sum, mask=mask_m)
    else:
        old = tl.load(output_ptrs, mask=mask_m, other=0.0)
        tl.store(output_ptrs, old + jsd_sum, mask=mask_m)

def fused_linear_jsd(
    X: torch.Tensor, 
    W1: torch.Tensor, 
    B1: torch.Tensor, 
    W2: torch.Tensor, 
    B2: torch.Tensor
) -> torch.Tensor:
    M, K = X.shape
    N = W1.shape[1]
    
    assert X.dtype == torch.float16
    assert W1.dtype == torch.float16
    assert W2.dtype == torch.float16
    assert B1.dtype == torch.float32
    assert B2.dtype == torch.float32
    assert X.is_cuda
    
    output = torch.zeros(M, dtype=torch.float32, device=X.device)
    
    # Optimal block sizes for the given specifications
    BLOCK_M = 64
    BLOCK_N = 128
    BLOCK_K = 64
    
    grid = (triton.cdiv(M, BLOCK_M), triton.cdiv(N, BLOCK_N))
    
    fused_linear_jsd_kernel_specialized[grid](
        X, W1, B1, W2, B2, output,
        M, K, N,
        X.stride(0), X.stride(1),
        W1.stride(0), W1.stride(1),
        W2.stride(0), W2.stride(1),
        output.stride(0),
        BLOCK_M=BLOCK_M,
        BLOCK_N=BLOCK_N,
        BLOCK_K=BLOCK_K,
        num_warps=4,
        num_stages=3,
    )
    
    return output
'''
        return specialized_code
    
    def _get_default_code(self):
        """Return the default implementation code"""
        # Import the entire code from this file
        import inspect
        return inspect.getsource(inspect.getmodule(inspect.currentframe()))