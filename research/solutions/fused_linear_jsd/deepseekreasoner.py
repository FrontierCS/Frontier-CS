import torch
import triton
import triton.language as tl

@triton.jit
def _fused_linear_jsd_kernel(
    X_ptr,
    W1_ptr,
    B1_ptr,
    W2_ptr,
    B2_ptr,
    output_ptr,
    M,
    K,
    N,
    stride_Xm,
    stride_Xk,
    stride_W1k,
    stride_W1n,
    stride_W2k,
    stride_W2n,
    BLOCK_SIZE_M: tl.constexpr,
    BLOCK_SIZE_K: tl.constexpr,
    BLOCK_SIZE_N: tl.constexpr,
    USE_LOG_SUM_EXP: tl.constexpr,
):
    # First pass: compute logits and log-sum-exp for each sample
    pid_m = tl.program_id(0)
    pid_n = tl.program_id(1)
    
    offs_m = pid_m * BLOCK_SIZE_M + tl.arange(0, BLOCK_SIZE_M)
    offs_k = tl.arange(0, BLOCK_SIZE_K)
    offs_n = pid_n * BLOCK_SIZE_N + tl.arange(0, BLOCK_SIZE_N)
    
    # Mask for boundaries
    m_mask = offs_m < M
    n_mask = offs_n < N
    
    # Initialize accumulators for logits
    acc1 = tl.zeros((BLOCK_SIZE_M, BLOCK_SIZE_N), dtype=tl.float32)
    acc2 = tl.zeros((BLOCK_SIZE_M, BLOCK_SIZE_N), dtype=tl.float32)
    
    # Load bias vectors
    b1 = tl.load(B1_ptr + offs_n, mask=n_mask, other=0.0).to(tl.float32)
    b2 = tl.load(B2_ptr + offs_n, mask=n_mask, other=0.0).to(tl.float32)
    
    # Broadcast bias to M dimension
    b1 = tl.broadcast_to(b1[None, :], (BLOCK_SIZE_M, BLOCK_SIZE_N))
    b2 = tl.broadcast_to(b2[None, :], (BLOCK_SIZE_M, BLOCK_SIZE_N))
    
    # Matrix multiplication with tiling
    for k_block in range(0, K, BLOCK_SIZE_K):
        k_mask = (k_block + offs_k) < K
        
        # Load X tile
        X_ptrs = X_ptr + (offs_m[:, None] * stride_Xm + 
                         (k_block + offs_k[None, :]) * stride_Xk)
        x = tl.load(X_ptrs, mask=m_mask[:, None] & k_mask[None, :], other=0.0).to(tl.float32)
        
        # Load W1 tile
        W1_ptrs = W1_ptr + ((k_block + offs_k[:, None]) * stride_W1k + 
                           offs_n[None, :] * stride_W1n)
        w1 = tl.load(W1_ptrs, mask=k_mask[:, None] & n_mask[None, :], other=0.0).to(tl.float32)
        
        # Load W2 tile
        W2_ptrs = W2_ptr + ((k_block + offs_k[:, None]) * stride_W2k + 
                           offs_n[None, :] * stride_W2n)
        w2 = tl.load(W2_ptrs, mask=k_mask[:, None] & n_mask[None, :], other=0.0).to(tl.float32)
        
        # Accumulate matrix products
        acc1 += tl.dot(x, w1, allow_tf32=False)
        acc2 += tl.dot(x, w2, allow_tf32=False)
    
    # Add biases
    acc1 += b1
    acc2 += b2
    
    # Compute logits (convert to float32 for stability)
    logits1 = acc1
    logits2 = acc2
    
    if USE_LOG_SUM_EXP:
        # Compute log-sum-exp for numerical stability
        max1 = tl.max(logits1, axis=1)
        max2 = tl.max(logits2, axis=1)
        
        exp1 = tl.exp(logits1 - max1[:, None])
        exp2 = tl.exp(logits2 - max2[:, None])
        
        sum1 = tl.sum(exp1, axis=1)
        sum2 = tl.sum(exp2, axis=1)
        
        log_sum_exp1 = tl.log(sum1) + max1
        log_sum_exp2 = tl.log(sum2) + max2
        
        # Compute probabilities (in log space for stability)
        log_p = logits1 - log_sum_exp1[:, None]
        log_q = logits2 - log_sum_exp2[:, None]
        
        # Compute M = 0.5 * (P + Q)
        # Use log-sum-exp trick for 0.5*(exp(log_p) + exp(log_q))
        max_pq = tl.maximum(log_p, log_q)
        exp_p = tl.exp(log_p - max_pq)
        exp_q = tl.exp(log_q - max_pq)
        log_m = tl.log(0.5 * (exp_p + exp_q)) + max_pq
        
        # Compute KL divergences
        # KL(P||M) = sum(P * (log(P) - log(M)))
        # Handle zeros safely
        kl_p = tl.where(
            log_p > -1e20,  # Not -inf
            tl.exp(log_p) * (log_p - log_m),
            0.0
        )
        
        kl_q = tl.where(
            log_q > -1e20,  # Not -inf
            tl.exp(log_q) * (log_q - log_m),
            0.0
        )
        
        # Sum KL divergences and compute JSD
        jsd = 0.5 * (tl.sum(kl_p, axis=1) + tl.sum(kl_q, axis=1))
    else:
        # Direct computation (less stable)
        # Softmax
        max1 = tl.max(logits1, axis=1)
        max2 = tl.max(logits2, axis=1)
        
        exp1 = tl.exp(logits1 - max1[:, None])
        exp2 = tl.exp(logits2 - max2[:, None])
        
        p = exp1 / tl.sum(exp1, axis=1)[:, None]
        q = exp2 / tl.sum(exp2, axis=1)[:, None]
        
        # M = 0.5*(p + q)
        m = 0.5 * (p + q)
        
        # Compute KL divergences with epsilon for numerical stability
        epsilon = 1e-8
        kl_p = p * (tl.log(p + epsilon) - tl.log(m + epsilon))
        kl_q = q * (tl.log(q + epsilon) - tl.log(m + epsilon))
        
        jsd = 0.5 * (tl.sum(kl_p, axis=1) + tl.sum(kl_q, axis=1))
    
    # Store result
    output_ptrs = output_ptr + offs_m
    tl.store(output_ptrs, jsd, mask=m_mask)

def fused_linear_jsd(
    X: torch.Tensor,
    W1: torch.Tensor,
    B1: torch.Tensor,
    W2: torch.Tensor,
    B2: torch.Tensor,
) -> torch.Tensor:
    """
    Fused linear layers with Jensen-Shannon Divergence computation.
    
    Args:
        X: Input tensor of shape (M, K) - input features (float16)
        W1: Weight tensor of shape (K, N) - first weight matrix (float16)
        B1: Bias tensor of shape (N,) - first bias vector (float32)
        W2: Weight tensor of shape (K, N) - second weight matrix (float16)
        B2: Bias tensor of shape (N,) - second bias vector (float32)
    
    Returns:
        Output tensor of shape (M,) - Jensen-Shannon Divergence per sample (float32)
    """
    # Validate inputs
    assert X.dtype == torch.float16
    assert W1.dtype == torch.float16
    assert W2.dtype == torch.float16
    assert B1.dtype == torch.float32
    assert B2.dtype == torch.float32
    
    M, K = X.shape
    N = W1.shape[1]
    
    assert W1.shape == (K, N), f"W1 shape mismatch: {W1.shape} != {(K, N)}"
    assert W2.shape == (K, N), f"W2 shape mismatch: {W2.shape} != {(K, N)}"
    assert B1.shape == (N,), f"B1 shape mismatch: {B1.shape} != {(N,)}"
    assert B2.shape == (N,), f"B2 shape mismatch: {B2.shape} != {(N,)}"
    
    # Allocate output
    output = torch.empty(M, device=X.device, dtype=torch.float32)
    
    # Choose kernel configuration based on problem size
    if M >= 256 and N >= 4096:
        BLOCK_SIZE_M = 64
        BLOCK_SIZE_K = 64
        BLOCK_SIZE_N = 128
    elif M >= 128:
        BLOCK_SIZE_M = 32
        BLOCK_SIZE_K = 64
        BLOCK_SIZE_N = 128
    else:
        BLOCK_SIZE_M = 16
        BLOCK_SIZE_K = 32
        BLOCK_SIZE_N = 64
    
    # Calculate grid size
    grid_m = triton.cdiv(M, BLOCK_SIZE_M)
    grid_n = triton.cdiv(N, BLOCK_SIZE_N)
    
    # Launch kernel
    _fused_linear_jsd_kernel[ (grid_m, grid_n) ](
        X,
        W1,
        B1,
        W2,
        B2,
        output,
        M,
        K,
        N,
        X.stride(0),
        X.stride(1),
        W1.stride(0),
        W1.stride(1),
        W2.stride(0),
        W2.stride(1),
        BLOCK_SIZE_M=BLOCK_SIZE_M,
        BLOCK_SIZE_K=BLOCK_SIZE_K,
        BLOCK_SIZE_N=BLOCK_SIZE_N,
        USE_LOG_SUM_EXP=True,  # Use log-sum-exp for numerical stability
    )
    
    return output

class Solution:
    def solve(self, spec_path: str = None) -> dict:
        code = '''import torch
import triton
import triton.language as tl

@triton.jit
def _fused_linear_jsd_kernel(
    X_ptr,
    W1_ptr,
    B1_ptr,
    W2_ptr,
    B2_ptr,
    output_ptr,
    M,
    K,
    N,
    stride_Xm,
    stride_Xk,
    stride_W1k,
    stride_W1n,
    stride_W2k,
    stride_W2n,
    BLOCK_SIZE_M: tl.constexpr,
    BLOCK_SIZE_K: tl.constexpr,
    BLOCK_SIZE_N: tl.constexpr,
    USE_LOG_SUM_EXP: tl.constexpr,
):
    # First pass: compute logits and log-sum-exp for each sample
    pid_m = tl.program_id(0)
    pid_n = tl.program_id(1)
    
    offs_m = pid_m * BLOCK_SIZE_M + tl.arange(0, BLOCK_SIZE_M)
    offs_k = tl.arange(0, BLOCK_SIZE_K)
    offs_n = pid_n * BLOCK_SIZE_N + tl.arange(0, BLOCK_SIZE_N)
    
    # Mask for boundaries
    m_mask = offs_m < M
    n_mask = offs_n < N
    
    # Initialize accumulators for logits
    acc1 = tl.zeros((BLOCK_SIZE_M, BLOCK_SIZE_N), dtype=tl.float32)
    acc2 = tl.zeros((BLOCK_SIZE_M, BLOCK_SIZE_N), dtype=tl.float32)
    
    # Load bias vectors
    b1 = tl.load(B1_ptr + offs_n, mask=n_mask, other=0.0).to(tl.float32)
    b2 = tl.load(B2_ptr + offs_n, mask=n_mask, other=0.0).to(tl.float32)
    
    # Broadcast bias to M dimension
    b1 = tl.broadcast_to(b1[None, :], (BLOCK_SIZE_M, BLOCK_SIZE_N))
    b2 = tl.broadcast_to(b2[None, :], (BLOCK_SIZE_M, BLOCK_SIZE_N))
    
    # Matrix multiplication with tiling
    for k_block in range(0, K, BLOCK_SIZE_K):
        k_mask = (k_block + offs_k) < K
        
        # Load X tile
        X_ptrs = X_ptr + (offs_m[:, None] * stride_Xm + 
                         (k_block + offs_k[None, :]) * stride_Xk)
        x = tl.load(X_ptrs, mask=m_mask[:, None] & k_mask[None, :], other=0.0).to(tl.float32)
        
        # Load W1 tile
        W1_ptrs = W1_ptr + ((k_block + offs_k[:, None]) * stride_W1k + 
                           offs_n[None, :] * stride_W1n)
        w1 = tl.load(W1_ptrs, mask=k_mask[:, None] & n_mask[None, :], other=0.0).to(tl.float32)
        
        # Load W2 tile
        W2_ptrs = W2_ptr + ((k_block + offs_k[:, None]) * stride_W2k + 
                           offs_n[None, :] * stride_W2n)
        w2 = tl.load(W2_ptrs, mask=k_mask[:, None] & n_mask[None, :], other=0.0).to(tl.float32)
        
        # Accumulate matrix products
        acc1 += tl.dot(x, w1, allow_tf32=False)
        acc2 += tl.dot(x, w2, allow_tf32=False)
    
    # Add biases
    acc1 += b1
    acc2 += b2
    
    # Compute logits (convert to float32 for stability)
    logits1 = acc1
    logits2 = acc2
    
    if USE_LOG_SUM_EXP:
        # Compute log-sum-exp for numerical stability
        max1 = tl.max(logits1, axis=1)
        max2 = tl.max(logits2, axis=1)
        
        exp1 = tl.exp(logits1 - max1[:, None])
        exp2 = tl.exp(logits2 - max2[:, None])
        
        sum1 = tl.sum(exp1, axis=1)
        sum2 = tl.sum(exp2, axis=1)
        
        log_sum_exp1 = tl.log(sum1) + max1
        log_sum_exp2 = tl.log(sum2) + max2
        
        # Compute probabilities (in log space for stability)
        log_p = logits1 - log_sum_exp1[:, None]
        log_q = logits2 - log_sum_exp2[:, None]
        
        # Compute M = 0.5 * (P + Q)
        # Use log-sum-exp trick for 0.5*(exp(log_p) + exp(log_q))
        max_pq = tl.maximum(log_p, log_q)
        exp_p = tl.exp(log_p - max_pq)
        exp_q = tl.exp(log_q - max_pq)
        log_m = tl.log(0.5 * (exp_p + exp_q)) + max_pq
        
        # Compute KL divergences
        # KL(P||M) = sum(P * (log(P) - log(M)))
        # Handle zeros safely
        kl_p = tl.where(
            log_p > -1e20,  # Not -inf
            tl.exp(log_p) * (log_p - log_m),
            0.0
        )
        
        kl_q = tl.where(
            log_q > -1e20,  # Not -inf
            tl.exp(log_q) * (log_q - log_m),
            0.0
        )
        
        # Sum KL divergences and compute JSD
        jsd = 0.5 * (tl.sum(kl_p, axis=1) + tl.sum(kl_q, axis=1))
    else:
        # Direct computation (less stable)
        # Softmax
        max1 = tl.max(logits1, axis=1)
        max2 = tl.max(logits2, axis=1)
        
        exp1 = tl.exp(logits1 - max1[:, None])
        exp2 = tl.exp(logits2 - max2[:, None])
        
        p = exp1 / tl.sum(exp1, axis=1)[:, None]
        q = exp2 / tl.sum(exp2, axis=1)[:, None]
        
        # M = 0.5*(p + q)
        m = 0.5 * (p + q)
        
        # Compute KL divergences with epsilon for numerical stability
        epsilon = 1e-8
        kl_p = p * (tl.log(p + epsilon) - tl.log(m + epsilon))
        kl_q = q * (tl.log(q + epsilon) - tl.log(m + epsilon))
        
        jsd = 0.5 * (tl.sum(kl_p, axis=1) + tl.sum(kl_q, axis=1))
    
    # Store result
    output_ptrs = output_ptr + offs_m
    tl.store(output_ptrs, jsd, mask=m_mask)

def fused_linear_jsd(
    X: torch.Tensor,
    W1: torch.Tensor,
    B1: torch.Tensor,
    W2: torch.Tensor,
    B2: torch.Tensor,
) -> torch.Tensor:
    """
    Fused linear layers with Jensen-Shannon Divergence computation.
    
    Args:
        X: Input tensor of shape (M, K) - input features (float16)
        W1: Weight tensor of shape (K, N) - first weight matrix (float16)
        B1: Bias tensor of shape (N,) - first bias vector (float32)
        W2: Weight tensor of shape (K, N) - second weight matrix (float16)
        B2: Bias tensor of shape (N,) - second bias vector (float32)
    
    Returns:
        Output tensor of shape (M,) - Jensen-Shannon Divergence per sample (float32)
    """
    # Validate inputs
    assert X.dtype == torch.float16
    assert W1.dtype == torch.float16
    assert W2.dtype == torch.float16
    assert B1.dtype == torch.float32
    assert B2.dtype == torch.float32
    
    M, K = X.shape
    N = W1.shape[1]
    
    assert W1.shape == (K, N), f"W1 shape mismatch: {W1.shape} != {(K, N)}"
    assert W2.shape == (K, N), f"W2 shape mismatch: {W2.shape} != {(K, N)}"
    assert B1.shape == (N,), f"B1 shape mismatch: {B1.shape} != {(N,)}"
    assert B2.shape == (N,), f"B2 shape mismatch: {B2.shape} != {(N,)}"
    
    # Allocate output
    output = torch.empty(M, device=X.device, dtype=torch.float32)
    
    # Choose kernel configuration based on problem size
    if M >= 256 and N >= 4096:
        BLOCK_SIZE_M = 64
        BLOCK_SIZE_K = 64
        BLOCK_SIZE_N = 128
    elif M >= 128:
        BLOCK_SIZE_M = 32
        BLOCK_SIZE_K = 64
        BLOCK_SIZE_N = 128
    else:
        BLOCK_SIZE_M = 16
        BLOCK_SIZE_K = 32
        BLOCK_SIZE_N = 64
    
    # Calculate grid size
    grid_m = triton.cdiv(M, BLOCK_SIZE_M)
    grid_n = triton.cdiv(N, BLOCK_SIZE_N)
    
    # Launch kernel
    _fused_linear_jsd_kernel[ (grid_m, grid_n) ](
        X,
        W1,
        B1,
        W2,
        B2,
        output,
        M,
        K,
        N,
        X.stride(0),
        X.stride(1),
        W1.stride(0),
        W1.stride(1),
        W2.stride(0),
        W2.stride(1),
        BLOCK_SIZE_M=BLOCK_SIZE_M,
        BLOCK_SIZE_K=BLOCK_SIZE_K,
        BLOCK_SIZE_N=BLOCK_SIZE_N,
        USE_LOG_SUM_EXP=True,  # Use log-sum-exp for numerical stability
    )
    
    return output
'''
        return {"code": code}