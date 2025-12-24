import torch
import triton
import triton.language as tl

@triton.jit
def linear_jsd_kernel(
    # Pointers to matrices
    x_ptr, w1_ptr, b1_ptr, w2_ptr, b2_ptr, output_ptr,
    # Matrix dimensions
    M, K, N,
    # Strides
    stride_xm, stride_xk,
    stride_w1k, stride_w1n,
    stride_w2k, stride_w2n,
    stride_output_m,
    # Meta-parameters
    BLOCK_SIZE_M: tl.constexpr,
    BLOCK_SIZE_N: tl.constexpr,
    BLOCK_SIZE_K: tl.constexpr,
    GROUP_SIZE_M: tl.constexpr,
    TWO_PASS: tl.constexpr,
):
    # Program ID
    pid = tl.program_id(0)
    num_pid_n = tl.cdiv(N, BLOCK_SIZE_N)
    num_pid_m = tl.cdiv(M, BLOCK_SIZE_M)
    num_pid_in_group = GROUP_SIZE_M * num_pid_n
    group_id = pid // num_pid_in_group
    first_pid_m = group_id * GROUP_SIZE_M
    group_size_m = min(num_pid_m - first_pid_m, GROUP_SIZE_M)
    pid_m = first_pid_m + (pid % group_size_m)
    pid_n = (pid % num_pid_in_group) // group_size_m
    
    # Offsets for the block
    offs_m = pid_m * BLOCK_SIZE_M + tl.arange(0, BLOCK_SIZE_M)
    offs_n = pid_n * BLOCK_SIZE_N + tl.arange(0, BLOCK_SIZE_N)
    offs_k = tl.arange(0, BLOCK_SIZE_K)
    
    # Load input tile
    x_ptrs = x_ptr + (offs_m[:, None] * stride_xm + offs_k[None, :] * stride_xk)
    x_mask = (offs_m[:, None] < M) & (offs_k[None, :] < K)
    x = tl.load(x_ptrs, mask=x_mask, other=0.0)
    
    # Load weights
    w1_ptrs = w1_ptr + (offs_k[:, None] * stride_w1k + offs_n[None, :] * stride_w1n)
    w2_ptrs = w2_ptr + (offs_k[:, None] * stride_w2k + offs_n[None, :] * stride_w2n)
    w_mask = (offs_k[:, None] < K) & (offs_n[None, :] < N)
    w1 = tl.load(w1_ptrs, mask=w_mask, other=0.0)
    w2 = tl.load(w2_ptrs, mask=w_mask, other=0.0)
    
    # Convert to float32 for accumulation
    x = x.to(tl.float32)
    w1 = w1.to(tl.float32)
    w2 = w2.to(tl.float32)
    
    # Compute matrix multiplication
    acc1 = tl.zeros((BLOCK_SIZE_M, BLOCK_SIZE_N), dtype=tl.float32)
    acc2 = tl.zeros((BLOCK_SIZE_M, BLOCK_SIZE_N), dtype=tl.float32)
    
    # Accumulate dot products
    for k in range(0, tl.cdiv(K, BLOCK_SIZE_K)):
        if k * BLOCK_SIZE_K < K:
            # Load next tile
            x_tile = tl.load(x_ptr + (offs_m[:, None] * stride_xm + 
                           (k * BLOCK_SIZE_K + offs_k[None, :]) * stride_xk),
                           mask=(offs_m[:, None] < M) & 
                           ((k * BLOCK_SIZE_K + offs_k[None, :]) < K),
                           other=0.0).to(tl.float32)
            
            w1_tile = tl.load(w1_ptr + ((k * BLOCK_SIZE_K + offs_k[:, None]) * stride_w1k + 
                            offs_n[None, :] * stride_w1n),
                            mask=((k * BLOCK_SIZE_K + offs_k[:, None]) < K) & 
                            (offs_n[None, :] < N),
                            other=0.0).to(tl.float32)
            
            w2_tile = tl.load(w2_ptr + ((k * BLOCK_SIZE_K + offs_k[:, None]) * stride_w2k + 
                            offs_n[None, :] * stride_w2n),
                            mask=((k * BLOCK_SIZE_K + offs_k[:, None]) < K) & 
                            (offs_n[None, :] < N),
                            other=0.0).to(tl.float32)
            
            acc1 += tl.dot(x_tile, w1_tile)
            acc2 += tl.dot(x_tile, w2_tile)
    
    # Add biases
    if BLOCK_SIZE_N == N:
        b1 = tl.load(b1_ptr + offs_n, mask=offs_n < N)
        b2 = tl.load(b2_ptr + offs_n, mask=offs_n < N)
        acc1 += b1[None, :]
        acc2 += b2[None, :]
    else:
        for nb in range(0, N, BLOCK_SIZE_N):
            offs_nb = nb + tl.arange(0, BLOCK_SIZE_N)
            b1 = tl.load(b1_ptr + offs_nb, mask=offs_nb < N)
            b2 = tl.load(b2_ptr + offs_nb, mask=offs_nb < N)
            acc1 += b1[None, :]
            acc2 += b2[None, :]
    
    # Store intermediate results for two-pass algorithm
    if TWO_PASS:
        # First pass: compute max for numerical stability
        max1 = tl.max(acc1, axis=1)
        max2 = tl.max(acc2, axis=1)
        
        # Compute exp of shifted values
        exp1 = tl.exp(acc1 - max1[:, None])
        exp2 = tl.exp(acc2 - max2[:, None])
        
        # Sum of exponentials
        sum_exp1 = tl.sum(exp1, axis=1)
        sum_exp2 = tl.sum(exp2, axis=1)
        
        # Store intermediate results in shared memory
        exp1_ptr = tl.make_block_ptr(exp1, shape=(BLOCK_SIZE_M, BLOCK_SIZE_N), 
                                     strides=(BLOCK_SIZE_N, 1), offsets=(0, 0), 
                                     block_shape=(BLOCK_SIZE_M, BLOCK_SIZE_N), order=(1, 0))
        exp2_ptr = tl.make_block_ptr(exp2, shape=(BLOCK_SIZE_M, BLOCK_SIZE_N), 
                                     strides=(BLOCK_SIZE_N, 1), offsets=(0, 0), 
                                     block_shape=(BLOCK_SIZE_M, BLOCK_SIZE_N), order=(1, 0))
        
        # Second pass: compute JSD
        # Normalize to get probabilities
        p = exp1 / sum_exp1[:, None]
        q = exp2 / sum_exp2[:, None]
        
        # Mixture distribution
        m = (p + q) * 0.5
        
        # Compute KL divergences with numerical stability
        # log(p/m) = log(p) - log(m)
        # Handle cases where p or q is 0
        safe_p = tl.where(p > 0, p, 1e-12)
        safe_q = tl.where(q > 0, q, 1e-12)
        safe_m = tl.where(m > 0, m, 1e-12)
        
        log_p = tl.log(safe_p)
        log_q = tl.log(safe_q)
        log_m = tl.log(safe_m)
        
        kl_pm = p * (log_p - log_m)
        kl_qm = q * (log_q - log_m)
        
        # Sum KL divergences
        jsd = 0.5 * (tl.sum(kl_pm, axis=1) + tl.sum(kl_qm, axis=1))
        
        # Store final JSD
        output_ptrs = output_ptr + offs_m * stride_output_m
        output_mask = offs_m < M
        tl.store(output_ptrs, jsd, mask=output_mask)
    else:
        # Single-pass implementation (less numerically stable)
        # Compute softmax
        max1 = tl.max(acc1, axis=1)
        max2 = tl.max(acc2, axis=1)
        
        exp1 = tl.exp(acc1 - max1[:, None])
        exp2 = tl.exp(acc2 - max2[:, None])
        
        sum_exp1 = tl.sum(exp1, axis=1)
        sum_exp2 = tl.sum(exp2, axis=1)
        
        p = exp1 / sum_exp1[:, None]
        q = exp2 / sum_exp2[:, None]
        
        m = (p + q) * 0.5
        
        # Compute JSD directly
        safe_p = tl.where(p > 0, p, 1e-12)
        safe_q = tl.where(q > 0, q, 1e-12)
        safe_m = tl.where(m > 0, m, 1e-12)
        
        jsd = 0.5 * (tl.sum(p * tl.log(safe_p / safe_m), axis=1) + 
                     tl.sum(q * tl.log(safe_q / safe_m), axis=1))
        
        # Store result
        output_ptrs = output_ptr + offs_m * stride_output_m
        output_mask = offs_m < M
        tl.store(output_ptrs, jsd, mask=output_mask)

def fused_linear_jsd(X: torch.Tensor, W1: torch.Tensor, B1: torch.Tensor, 
                     W2: torch.Tensor, B2: torch.Tensor) -> torch.Tensor:
    """
    Fused linear layers with Jensen-Shannon Divergence computation.
    """
    # Check input dimensions
    M, K = X.shape
    assert W1.shape == (K, B1.shape[0]), f"W1 shape mismatch: {W1.shape} vs {(K, B1.shape[0])}"
    assert W2.shape == (K, B2.shape[0]), f"W2 shape mismatch: {W2.shape} vs {(K, B2.shape[0])}"
    assert B1.shape == B2.shape, f"Bias shape mismatch: {B1.shape} vs {B2.shape}"
    
    N = B1.shape[0]
    
    # Allocate output
    output = torch.empty(M, dtype=torch.float32, device=X.device)
    
    # Determine optimal block sizes
    def get_config(M, N, K):
        if M <= 128:
            BLOCK_SIZE_M = 32
            BLOCK_SIZE_N = 128
            BLOCK_SIZE_K = 32
            GROUP_SIZE_M = 8
        elif M <= 256:
            BLOCK_SIZE_M = 64
            BLOCK_SIZE_N = 128
            BLOCK_SIZE_K = 32
            GROUP_SIZE_M = 8
        else:
            BLOCK_SIZE_M = 128
            BLOCK_SIZE_N = 128
            BLOCK_SIZE_K = 32
            GROUP_SIZE_M = 8
        return BLOCK_SIZE_M, BLOCK_SIZE_N, BLOCK_SIZE_K, GROUP_SIZE_M
    
    BLOCK_SIZE_M, BLOCK_SIZE_N, BLOCK_SIZE_K, GROUP_SIZE_M = get_config(M, N, K)
    
    # Adjust block sizes based on available resources
    while BLOCK_SIZE_M * BLOCK_SIZE_N * 2 > 65536:  # Shared memory limit
        if BLOCK_SIZE_N > 64:
            BLOCK_SIZE_N //= 2
        elif BLOCK_SIZE_M > 32:
            BLOCK_SIZE_M //= 2
        else:
            BLOCK_SIZE_K //= 2
    
    # Compute grid size
    grid = lambda META: (triton.cdiv(M, META['BLOCK_SIZE_M']) * 
                        triton.cdiv(N, META['BLOCK_SIZE_N']),)
    
    # Launch kernel
    linear_jsd_kernel[grid](
        X, W1, B1, W2, B2, output,
        M, K, N,
        X.stride(0), X.stride(1),
        W1.stride(0), W1.stride(1),
        W2.stride(0), W2.stride(1),
        output.stride(0),
        BLOCK_SIZE_M=BLOCK_SIZE_M,
        BLOCK_SIZE_N=BLOCK_SIZE_N,
        BLOCK_SIZE_K=BLOCK_SIZE_K,
        GROUP_SIZE_M=GROUP_SIZE_M,
        TWO_PASS=True,
    )
    
    return output

class Solution:
    def solve(self, spec_path: str = None) -> dict:
        return {"code": """
import torch
import triton
import triton.language as tl

@triton.jit
def linear_jsd_kernel(
    # Pointers to matrices
    x_ptr, w1_ptr, b1_ptr, w2_ptr, b2_ptr, output_ptr,
    # Matrix dimensions
    M, K, N,
    # Strides
    stride_xm, stride_xk,
    stride_w1k, stride_w1n,
    stride_w2k, stride_w2n,
    stride_output_m,
    # Meta-parameters
    BLOCK_SIZE_M: tl.constexpr,
    BLOCK_SIZE_N: tl.constexpr,
    BLOCK_SIZE_K: tl.constexpr,
    GROUP_SIZE_M: tl.constexpr,
    TWO_PASS: tl.constexpr,
):
    # Program ID
    pid = tl.program_id(0)
    num_pid_n = tl.cdiv(N, BLOCK_SIZE_N)
    num_pid_m = tl.cdiv(M, BLOCK_SIZE_M)
    num_pid_in_group = GROUP_SIZE_M * num_pid_n
    group_id = pid // num_pid_in_group
    first_pid_m = group_id * GROUP_SIZE_M
    group_size_m = min(num_pid_m - first_pid_m, GROUP_SIZE_M)
    pid_m = first_pid_m + (pid % group_size_m)
    pid_n = (pid % num_pid_in_group) // group_size_m
    
    # Offsets for the block
    offs_m = pid_m * BLOCK_SIZE_M + tl.arange(0, BLOCK_SIZE_M)
    offs_n = pid_n * BLOCK_SIZE_N + tl.arange(0, BLOCK_SIZE_N)
    offs_k = tl.arange(0, BLOCK_SIZE_K)
    
    # Load input tile
    x_ptrs = x_ptr + (offs_m[:, None] * stride_xm + offs_k[None, :] * stride_xk)
    x_mask = (offs_m[:, None] < M) & (offs_k[None, :] < K)
    x = tl.load(x_ptrs, mask=x_mask, other=0.0)
    
    # Load weights
    w1_ptrs = w1_ptr + (offs_k[:, None] * stride_w1k + offs_n[None, :] * stride_w1n)
    w2_ptrs = w2_ptr + (offs_k[:, None] * stride_w2k + offs_n[None, :] * stride_w2n)
    w_mask = (offs_k[:, None] < K) & (offs_n[None, :] < N)
    w1 = tl.load(w1_ptrs, mask=w_mask, other=0.0)
    w2 = tl.load(w2_ptrs, mask=w_mask, other=0.0)
    
    # Convert to float32 for accumulation
    x = x.to(tl.float32)
    w1 = w1.to(tl.float32)
    w2 = w2.to(tl.float32)
    
    # Compute matrix multiplication
    acc1 = tl.zeros((BLOCK_SIZE_M, BLOCK_SIZE_N), dtype=tl.float32)
    acc2 = tl.zeros((BLOCK_SIZE_M, BLOCK_SIZE_N), dtype=tl.float32)
    
    # Accumulate dot products
    for k in range(0, tl.cdiv(K, BLOCK_SIZE_K)):
        if k * BLOCK_SIZE_K < K:
            # Load next tile
            x_tile = tl.load(x_ptr + (offs_m[:, None] * stride_xm + 
                           (k * BLOCK_SIZE_K + offs_k[None, :]) * stride_xk),
                           mask=(offs_m[:, None] < M) & 
                           ((k * BLOCK_SIZE_K + offs_k[None, :]) < K),
                           other=0.0).to(tl.float32)
            
            w1_tile = tl.load(w1_ptr + ((k * BLOCK_SIZE_K + offs_k[:, None]) * stride_w1k + 
                            offs_n[None, :] * stride_w1n),
                            mask=((k * BLOCK_SIZE_K + offs_k[:, None]) < K) & 
                            (offs_n[None, :] < N),
                            other=0.0).to(tl.float32)
            
            w2_tile = tl.load(w2_ptr + ((k * BLOCK_SIZE_K + offs_k[:, None]) * stride_w2k + 
                            offs_n[None, :] * stride_w2n),
                            mask=((k * BLOCK_SIZE_K + offs_k[:, None]) < K) & 
                            (offs_n[None, :] < N),
                            other=0.0).to(tl.float32)
            
            acc1 += tl.dot(x_tile, w1_tile)
            acc2 += tl.dot(x_tile, w2_tile)
    
    # Add biases
    if BLOCK_SIZE_N == N:
        b1 = tl.load(b1_ptr + offs_n, mask=offs_n < N)
        b2 = tl.load(b2_ptr + offs_n, mask=offs_n < N)
        acc1 += b1[None, :]
        acc2 += b2[None, :]
    else:
        for nb in range(0, N, BLOCK_SIZE_N):
            offs_nb = nb + tl.arange(0, BLOCK_SIZE_N)
            b1 = tl.load(b1_ptr + offs_nb, mask=offs_nb < N)
            b2 = tl.load(b2_ptr + offs_nb, mask=offs_nb < N)
            acc1 += b1[None, :]
            acc2 += b2[None, :]
    
    # Two-pass algorithm for numerical stability
    # First pass: compute max and sum for softmax
    max1 = tl.max(acc1, axis=1)
    max2 = tl.max(acc2, axis=1)
    
    exp1 = tl.exp(acc1 - max1[:, None])
    exp2 = tl.exp(acc2 - max2[:, None])
    
    sum_exp1 = tl.sum(exp1, axis=1)
    sum_exp2 = tl.sum(exp2, axis=1)
    
    # Second pass: compute JSD
    # Normalize to get probabilities
    p = exp1 / sum_exp1[:, None]
    q = exp2 / sum_exp2[:, None]
    
    # Mixture distribution
    m = (p + q) * 0.5
    
    # Compute KL divergences with numerical stability
    # Handle cases where p, q, or m is 0
    safe_p = tl.where(p > 0, p, 1e-12)
    safe_q = tl.where(q > 0, q, 1e-12)
    safe_m = tl.where(m > 0, m, 1e-12)
    
    log_p = tl.log(safe_p)
    log_q = tl.log(safe_q)
    log_m = tl.log(safe_m)
    
    kl_pm = p * (log_p - log_m)
    kl_qm = q * (log_q - log_m)
    
    # Sum KL divergences
    jsd = 0.5 * (tl.sum(kl_pm, axis=1) + tl.sum(kl_qm, axis=1))
    
    # Store final JSD
    output_ptrs = output_ptr + offs_m * stride_output_m
    output_mask = offs_m < M
    tl.store(output_ptrs, jsd, mask=output_mask)

def fused_linear_jsd(X: torch.Tensor, W1: torch.Tensor, B1: torch.Tensor, 
                     W2: torch.Tensor, B2: torch.Tensor) -> torch.Tensor:
    # Check input dimensions
    M, K = X.shape
    N = B1.shape[0]
    
    # Allocate output
    output = torch.empty(M, dtype=torch.float32, device=X.device)
    
    # Determine optimal block sizes based on problem size
    def get_config(M, N, K):
        if M <= 128:
            BLOCK_SIZE_M = 32
            BLOCK_SIZE_N = 128
            BLOCK_SIZE_K = 32
            GROUP_SIZE_M = 8
        elif M <= 256:
            BLOCK_SIZE_M = 64
            BLOCK_SIZE_N = 128
            BLOCK_SIZE_K = 32
            GROUP_SIZE_M = 8
        else:
            BLOCK_SIZE_M = 128
            BLOCK_SIZE_N = 128
            BLOCK_SIZE_K = 32
            GROUP_SIZE_M = 8
        return BLOCK_SIZE_M, BLOCK_SIZE_N, BLOCK_SIZE_K, GROUP_SIZE_M
    
    BLOCK_SIZE_M, BLOCK_SIZE_N, BLOCK_SIZE_K, GROUP_SIZE_M = get_config(M, N, K)
    
    # Adjust block sizes to fit in shared memory
    while BLOCK_SIZE_M * BLOCK_SIZE_N * 2 > 65536:
        if BLOCK_SIZE_N > 64:
            BLOCK_SIZE_N //= 2
        elif BLOCK_SIZE_M > 32:
            BLOCK_SIZE_M //= 2
        else:
            BLOCK_SIZE_K //= 2
    
    # Compute grid size
    grid = lambda META: (triton.cdiv(M, META['BLOCK_SIZE_M']) * 
                        triton.cdiv(N, META['BLOCK_SIZE_N']),)
    
    # Launch kernel
    linear_jsd_kernel[grid](
        X, W1, B1, W2, B2, output,
        M, K, N,
        X.stride(0), X.stride(1),
        W1.stride(0), W1.stride(1),
        W2.stride(0), W2.stride(1),
        output.stride(0),
        BLOCK_SIZE_M=BLOCK_SIZE_M,
        BLOCK_SIZE_N=BLOCK_SIZE_N,
        BLOCK_SIZE_K=BLOCK_SIZE_K,
        GROUP_SIZE_M=GROUP_SIZE_M,
        TWO_PASS=True,
    )
    
    return output
"""}
