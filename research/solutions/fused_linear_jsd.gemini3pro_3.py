import torch
import triton
import triton.language as tl

class Solution:
    def solve(self, spec_path: str = None) -> dict:
        return {"code": r"""
import torch
import triton
import triton.language as tl

@triton.jit
def _linear_lse_kernel(
    X_ptr, W1_ptr, B1_ptr, W2_ptr, B2_ptr,
    L1_ptr, L2_ptr,
    LSE1_ptr, LSE2_ptr,
    M, K, N,
    stride_xm, stride_xk,
    stride_w1k, stride_w1n,
    stride_w2k, stride_w2n,
    stride_l1m, stride_l1n,
    stride_l2m, stride_l2n,
    BLOCK_M: tl.constexpr, BLOCK_N: tl.constexpr, BLOCK_K: tl.constexpr
):
    pid_m = tl.program_id(0)
    offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
    
    # Initialize online softmax stats: max and sum_exp
    m1 = tl.zeros([BLOCK_M], dtype=tl.float32) - float('inf')
    s1 = tl.zeros([BLOCK_M], dtype=tl.float32)
    m2 = tl.zeros([BLOCK_M], dtype=tl.float32) - float('inf')
    s2 = tl.zeros([BLOCK_M], dtype=tl.float32)

    # Iterate over N in blocks to compute logits and update stats
    for start_n in range(0, N, BLOCK_N):
        offs_n = start_n + tl.arange(0, BLOCK_N)
        mask_n = offs_n < N
        
        # Accumulators for logits
        acc1 = tl.zeros([BLOCK_M, BLOCK_N], dtype=tl.float32)
        acc2 = tl.zeros([BLOCK_M, BLOCK_N], dtype=tl.float32)
        
        # Compute fused matrix multiplication for this N block
        for start_k in range(0, K, BLOCK_K):
            offs_k = start_k + tl.arange(0, BLOCK_K)
            mask_k = offs_k < K
            mask_mk = (offs_m[:, None] < M) & mask_k[None, :]
            
            # Load X tile
            x = tl.load(X_ptr + offs_m[:, None] * stride_xm + offs_k[None, :] * stride_xk, 
                        mask=mask_mk, other=0.0)
            
            # Load W1 tile
            mask_kn = mask_k[:, None] & mask_n[None, :]
            w1 = tl.load(W1_ptr + offs_k[:, None] * stride_w1k + offs_n[None, :] * stride_w1n,
                         mask=mask_kn, other=0.0)
            acc1 += tl.dot(x, w1)
            
            # Load W2 tile
            w2 = tl.load(W2_ptr + offs_k[:, None] * stride_w2k + offs_n[None, :] * stride_w2n,
                         mask=mask_kn, other=0.0)
            acc2 += tl.dot(x, w2)

        # Add Bias
        b1 = tl.load(B1_ptr + offs_n, mask=mask_n, other=0.0)
        acc1 += b1[None, :]
        
        b2 = tl.load(B2_ptr + offs_n, mask=mask_n, other=0.0)
        acc2 += b2[None, :]

        # Store Logits (fp16) to global memory for the second pass
        mask_mn = (offs_m[:, None] < M) & mask_n[None, :]
        tl.store(L1_ptr + offs_m[:, None] * stride_l1m + offs_n[None, :] * stride_l1n, 
                 acc1.to(tl.float16), mask=mask_mn)
        tl.store(L2_ptr + offs_m[:, None] * stride_l2m + offs_n[None, :] * stride_l2n, 
                 acc2.to(tl.float16), mask=mask_mn)

        # Online Softmax Update for Set 1
        # Mask invalid elements with -inf for max calc
        acc1_masked = tl.where(mask_n[None, :], acc1, -float('inf'))
        max1_curr = tl.max(acc1_masked, 1)
        new_m1 = tl.maximum(m1, max1_curr)
        
        # Calculate sum of exp, handling the shift
        # exp(x - new_max)
        term1 = tl.exp(acc1_masked - new_m1[:, None])
        sum1_curr = tl.sum(tl.where(mask_n[None, :], term1, 0.0), 1)
        
        s1 = s1 * tl.exp(m1 - new_m1) + sum1_curr
        m1 = new_m1

        # Online Softmax Update for Set 2
        acc2_masked = tl.where(mask_n[None, :], acc2, -float('inf'))
        max2_curr = tl.max(acc2_masked, 1)
        new_m2 = tl.maximum(m2, max2_curr)
        
        term2 = tl.exp(acc2_masked - new_m2[:, None])
        sum2_curr = tl.sum(tl.where(mask_n[None, :], term2, 0.0), 1)
        
        s2 = s2 * tl.exp(m2 - new_m2) + sum2_curr
        m2 = new_m2

    # Store Log-Sum-Exp results
    lse1 = m1 + tl.log(s1)
    lse2 = m2 + tl.log(s2)
    
    tl.store(LSE1_ptr + offs_m, lse1, mask=offs_m < M)
    tl.store(LSE2_ptr + offs_m, lse2, mask=offs_m < M)

@triton.jit
def _jsd_kernel(
    L1_ptr, L2_ptr, LSE1_ptr, LSE2_ptr, Out_ptr,
    M, N,
    stride_l1m, stride_l1n,
    stride_l2m, stride_l2n,
    BLOCK_N: tl.constexpr
):
    pid_m = tl.program_id(0)
    if pid_m >= M: return
    
    lse1 = tl.load(LSE1_ptr + pid_m)
    lse2 = tl.load(LSE2_ptr + pid_m)
    
    jsd_acc = 0.0
    
    for start_n in range(0, N, BLOCK_N):
        offs_n = start_n + tl.arange(0, BLOCK_N)
        mask_n = offs_n < N
        
        l1 = tl.load(L1_ptr + pid_m * stride_l1m + offs_n * stride_l1n, mask=mask_n, other=-float('inf')).to(tl.float32)
        l2 = tl.load(L2_ptr + pid_m * stride_l2m + offs_n * stride_l2n, mask=mask_n, other=-float('inf')).to(tl.float32)
        
        # logP, logQ
        log_p = l1 - lse1
        log_q = l2 - lse2
        
        # P, Q
        p = tl.exp(log_p)
        q = tl.exp(log_q)
        
        # M = 0.5 * (P + Q)
        # logM = log(0.5) + log(P + Q)
        # log(P + Q) = log(exp(logP) + exp(logQ)) = max(logP, logQ) + log(1 + exp(-abs(logP - logQ)))
        # Robust LSE for M
        max_log = tl.maximum(log_p, log_q)
        diff = -tl.abs(log_p - log_q)
        # Handle -inf in diff (if one prob is 0)
        # exp(-inf) is 0.
        log_sum = max_log + tl.log(1.0 + tl.exp(diff))
        log_m = -0.69314718056 + log_sum  # ln(0.5) approx
        
        # KL terms: p * (log_p - log_m)
        t1 = p * (log_p - log_m)
        t2 = q * (log_q - log_m)
        
        # Mask valid
        t1 = tl.where(mask_n, t1, 0.0)
        t2 = tl.where(mask_n, t2, 0.0)
        
        jsd_acc += tl.sum(0.5 * (t1 + t2))
        
    tl.store(Out_ptr + pid_m, jsd_acc)

def fused_linear_jsd(X: torch.Tensor, W1: torch.Tensor, B1: torch.Tensor, W2: torch.Tensor, B2: torch.Tensor) -> torch.Tensor:
    M, K = X.shape
    _, N = W1.shape
    
    # Allocations
    # Intermediate Logits: (M, N) float16
    logits1 = torch.empty((M, N), device=X.device, dtype=torch.float16)
    logits2 = torch.empty((M, N), device=X.device, dtype=torch.float16)
    
    # LSE: (M,) float32
    lse1 = torch.empty((M,), device=X.device, dtype=torch.float32)
    lse2 = torch.empty((M,), device=X.device, dtype=torch.float32)
    
    # Output: (M,) float32
    output = torch.empty((M,), device=X.device, dtype=torch.float32)
    
    # Pass 1: Fused Linear + LSE
    BLOCK_M = 32 
    BLOCK_N = 128
    BLOCK_K = 32
    
    grid1 = (triton.cdiv(M, BLOCK_M),)
    
    _linear_lse_kernel[grid1](
        X, W1, B1, W2, B2,
        logits1, logits2,
        lse1, lse2,
        M, K, N,
        X.stride(0), X.stride(1),
        W1.stride(0), W1.stride(1),
        W2.stride(0), W2.stride(1),
        logits1.stride(0), logits1.stride(1),
        logits2.stride(0), logits2.stride(1),
        BLOCK_M=BLOCK_M, BLOCK_N=BLOCK_N, BLOCK_K=BLOCK_K
    )
    
    # Pass 2: JSD
    # Process one row per program instance
    BLOCK_SIZE_JSD = 1024
    grid2 = (M,)
    
    _jsd_kernel[grid2](
        logits1, logits2, lse1, lse2, output,
        M, N,
        logits1.stride(0), logits1.stride(1),
        logits2.stride(0), logits2.stride(1),
        BLOCK_N=BLOCK_SIZE_JSD
    )
    
    return output
"""}