import torch
import triton
import triton.language as tl


@triton.jit
def _fused_linear_jsd_kernel(
    # Pointers to matrices
    x_ptr,
    w1_ptr,
    b1_ptr,
    w2_ptr,
    b2_ptr,
    output_ptr,
    # Matrix dimensions
    M,
    N,
    K,
    # Strides
    stride_xm,
    stride_xk,
    stride_w1k,
    stride_w1n,
    stride_w2k,
    stride_w2n,
    # Meta-parameters
    BLOCK_SIZE_M: tl.constexpr,
    BLOCK_SIZE_N: tl.constexpr,
    BLOCK_SIZE_K: tl.constexpr,
):
    # Program ID
    pid_m = tl.program_id(axis=0)
    pid_n = tl.program_id(axis=1)
    
    # Offsets
    offs_m = pid_m * BLOCK_SIZE_M + tl.arange(0, BLOCK_SIZE_M)
    offs_n = pid_n * BLOCK_SIZE_N + tl.arange(0, BLOCK_SIZE_N)
    offs_k = tl.arange(0, BLOCK_SIZE_K)
    
    # Create masks for boundary checks
    mask_m = offs_m < M
    mask_n = offs_n < N
    
    # Initialize accumulators
    acc1 = tl.zeros((BLOCK_SIZE_M, BLOCK_SIZE_N), dtype=tl.float32)
    acc2 = tl.zeros((BLOCK_SIZE_M, BLOCK_SIZE_N), dtype=tl.float32)
    
    # Load biases
    b1 = tl.load(b1_ptr + offs_n, mask=mask_n, other=0.0).to(tl.float32)
    b2 = tl.load(b2_ptr + offs_n, mask=mask_n, other=0.0).to(tl.float32)
    
    # Broadcast biases to all rows in block
    b1_broadcast = tl.broadcast_to(b1, (BLOCK_SIZE_M, BLOCK_SIZE_N))
    b2_broadcast = tl.broadcast_to(b2, (BLOCK_SIZE_M, BLOCK_SIZE_N))
    
    # Add biases to accumulators
    acc1 += b1_broadcast
    acc2 += b2_broadcast
    
    # Compute matrix multiplication with tiling
    for k in range(0, tl.cdiv(K, BLOCK_SIZE_K)):
        # Compute offsets for K dimension
        k_offs = k * BLOCK_SIZE_K
        k_range = k_offs + offs_k
        k_mask = k_range < K
        
        # Load tiles from X, W1, and W2
        x_ptr_base = x_ptr + (offs_m[:, None] * stride_xm + k_range[None, :] * stride_xk)
        w1_ptr_base = w1_ptr + (k_range[:, None] * stride_w1k + offs_n[None, :] * stride_w1n)
        w2_ptr_base = w2_ptr + (k_range[:, None] * stride_w2k + offs_n[None, :] * stride_w2n)
        
        x = tl.load(x_ptr_base, mask=mask_m[:, None] & k_mask[None, :], other=0.0).to(tl.float32)
        w1 = tl.load(w1_ptr_base, mask=k_mask[:, None] & mask_n[None, :], other=0.0).to(tl.float32)
        w2 = tl.load(w2_ptr_base, mask=k_mask[:, None] & mask_n[None, :], other=0.0).to(tl.float32)
        
        # Compute matrix multiplication
        acc1 += tl.dot(x, w1, allow_tf32=False)
        acc2 += tl.dot(x, w2, allow_tf32=False)
    
    # Store logits to shared memory for first pass
    logits1 = acc1
    logits2 = acc2
    
    # First pass: compute log-sum-exp for logits1 and logits2
    # Compute max for numerical stability
    max1 = tl.max(logits1, axis=1, keep_dims=True)
    max2 = tl.max(logits2, axis=1, keep_dims=True)
    
    # Compute exp of shifted logits
    exp1 = tl.exp(logits1 - max1)
    exp2 = tl.exp(logits2 - max2)
    
    # Sum along N dimension
    sum_exp1 = tl.sum(exp1, axis=1, keep_dims=True)
    sum_exp2 = tl.sum(exp2, axis=1, keep_dims=True)
    
    # Compute log probabilities
    log_p = logits1 - max1 - tl.log(sum_exp1)
    log_q = logits2 - max2 - tl.log(sum_exp2)
    
    # Compute probabilities
    p = tl.exp(log_p)
    q = tl.exp(log_q)
    
    # Compute M = 0.5 * (p + q)
    m = 0.5 * (p + q)
    
    # Compute log M using log-sum-exp for numerical stability
    log_m = tl.log(0.5) + tl.log(tl.exp(log_p) + tl.exp(log_q))
    
    # Compute KL divergences
    kl_p = p * (log_p - log_m)
    kl_q = q * (log_q - log_m)
    
    # Sum KL divergences along N dimension
    kl_p_sum = tl.sum(kl_p, axis=1)
    kl_q_sum = tl.sum(kl_q, axis=1)
    
    # Compute JSD
    jsd = 0.5 * (kl_p_sum + kl_q_sum)
    
    # Store result
    out_ptr = output_ptr + offs_m
    tl.store(out_ptr, jsd, mask=mask_m)


@triton.jit
def _fused_linear_jsd_kernel_optimized(
    # Pointers to matrices
    x_ptr,
    w1_ptr,
    b1_ptr,
    w2_ptr,
    b2_ptr,
    output_ptr,
    # Matrix dimensions
    M,
    N,
    K,
    # Strides
    stride_xm,
    stride_xk,
    stride_w1k,
    stride_w1n,
    stride_w2k,
    stride_w2n,
    # Meta-parameters
    BLOCK_SIZE_M: tl.constexpr,
    BLOCK_SIZE_N: tl.constexpr,
    BLOCK_SIZE_K: tl.constexpr,
    GROUP_SIZE_M: tl.constexpr,
):
    # Program ID
    pid = tl.program_id(axis=0)
    
    # Number of program IDs along M dimension
    num_pid_m = tl.cdiv(M, BLOCK_SIZE_M)
    num_pid_n = tl.cdiv(N, BLOCK_SIZE_N)
    
    # Decompose program ID
    pid_m = pid // num_pid_n
    pid_n = pid % num_pid_n
    
    # Reorder program IDs for better L2 cache hit rate
    num_blocks_m = tl.cdiv(M, BLOCK_SIZE_M)
    num_blocks_n = tl.cdiv(N, BLOCK_SIZE_N)
    
    group_id = pid_m // GROUP_SIZE_M
    group_size = min(num_blocks_m - group_id * GROUP_SIZE_M, GROUP_SIZE_M)
    pid_m = group_id * GROUP_SIZE_M + (pid_n % group_size)
    pid_n = pid_n // group_size
    
    # Return if out of bounds
    if pid_m >= num_blocks_m:
        return
    
    # Offsets
    offs_m = pid_m * BLOCK_SIZE_M + tl.arange(0, BLOCK_SIZE_M)
    offs_n = pid_n * BLOCK_SIZE_N + tl.arange(0, BLOCK_SIZE_N)
    offs_k = tl.arange(0, BLOCK_SIZE_K)
    
    # Create masks
    mask_m = offs_m < M
    mask_n = offs_n < N
    
    # Initialize accumulators
    acc1 = tl.zeros((BLOCK_SIZE_M, BLOCK_SIZE_N), dtype=tl.float32)
    acc2 = tl.zeros((BLOCK_SIZE_M, BLOCK_SIZE_N), dtype=tl.float32)
    
    # Load biases
    b1 = tl.load(b1_ptr + offs_n, mask=mask_n, other=0.0).to(tl.float32)
    b2 = tl.load(b2_ptr + offs_n, mask=mask_n, other=0.0).to(tl.float32)
    
    # Broadcast biases
    b1_broadcast = tl.broadcast_to(b1, (BLOCK_SIZE_M, BLOCK_SIZE_N))
    b2_broadcast = tl.broadcast_to(b2, (BLOCK_SIZE_M, BLOCK_SIZE_N))
    
    acc1 += b1_broadcast
    acc2 += b2_broadcast
    
    # Compute matrix multiplication
    k_iters = tl.cdiv(K, BLOCK_SIZE_K)
    
    for k in range(0, k_iters):
        # Compute offsets for K dimension
        k_offs = k * BLOCK_SIZE_K
        k_range = k_offs + offs_k
        k_mask = k_range < K
        
        # Load tiles
        x_ptr_base = x_ptr + (offs_m[:, None] * stride_xm + k_range[None, :] * stride_xk)
        w1_ptr_base = w1_ptr + (k_range[:, None] * stride_w1k + offs_n[None, :] * stride_w1n)
        w2_ptr_base = w2_ptr + (k_range[:, None] * stride_w2k + offs_n[None, :] * stride_w2n)
        
        x = tl.load(x_ptr_base, mask=mask_m[:, None] & k_mask[None, :], other=0.0).to(tl.float32)
        w1 = tl.load(w1_ptr_base, mask=k_mask[:, None] & mask_n[None, :], other=0.0).to(tl.float32)
        w2 = tl.load(w2_ptr_base, mask=k_mask[:, None] & mask_n[None, :], other=0.0).to(tl.float32)
        
        # Accumulate
        acc1 += tl.dot(x, w1, allow_tf32=True)
        acc2 += tl.dot(x, w2, allow_tf32=True)
    
    # Convert to logits
    logits1 = acc1
    logits2 = acc2
    
    # Compute max for numerical stability
    max1 = tl.max(logits1, axis=1, keep_dims=True)
    max2 = tl.max(logits2, axis=1, keep_dims=True)
    
    # Compute exp of shifted logits
    exp1 = tl.exp(logits1 - max1)
    exp2 = tl.exp(logits2 - max2)
    
    # Sum along N dimension
    sum_exp1 = tl.sum(exp1, axis=1, keep_dims=True)
    sum_exp2 = tl.sum(exp2, axis=1, keep_dims=True)
    
    # Compute log probabilities
    log_p = logits1 - max1 - tl.log(sum_exp1)
    log_q = logits2 - max2 - tl.log(sum_exp2)
    
    # Compute M and log M
    log_m = tl.log(0.5) + tl.log(tl.exp(log_p) + tl.exp(log_q))
    
    # Compute KL divergences
    kl_p = tl.exp(log_p) * (log_p - log_m)
    kl_q = tl.exp(log_q) * (log_q - log_m)
    
    # Sum KL divergences
    kl_p_sum = tl.sum(kl_p, axis=1)
    kl_q_sum = tl.sum(kl_q, axis=1)
    
    # Compute JSD
    jsd = 0.5 * (kl_p_sum + kl_q_sum)
    
    # Store result - need to reduce across N dimension
    # Use atomic add to accumulate across different pid_n
    out_ptr = output_ptr + offs_m
    tl.atomic_add(out_ptr, jsd, mask=mask_m)


def fused_linear_jsd(X: torch.Tensor, W1: torch.Tensor, B1: torch.Tensor, 
                    W2: torch.Tensor, B2: torch.Tensor) -> torch.Tensor:
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
    # Check input shapes
    M, K = X.shape
    N = W1.shape[1]
    
    assert X.shape == (M, K), f"X shape mismatch: {X.shape} != {(M, K)}"
    assert W1.shape == (K, N), f"W1 shape mismatch: {W1.shape} != {(K, N)}"
    assert W2.shape == (K, N), f"W2 shape mismatch: {W2.shape} != {(K, N)}"
    assert B1.shape == (N,), f"B1 shape mismatch: {B1.shape} != {(N,)}"
    assert B2.shape == (N,), f"B2 shape mismatch: {B2.shape} != {(N,)}"
    
    # Check dtypes
    assert X.dtype == torch.float16, f"X dtype {X.dtype} != float16"
    assert W1.dtype == torch.float16, f"W1 dtype {W1.dtype} != float16"
    assert W2.dtype == torch.float16, f"W2 dtype {W2.dtype} != float16"
    assert B1.dtype == torch.float32, f"B1 dtype {B1.dtype} != float32"
    assert B2.dtype == torch.float32, f"B2 dtype {B2.dtype} != float32"
    
    # Allocate output
    output = torch.zeros((M,), dtype=torch.float32, device=X.device)
    
    # Choose kernel configuration based on problem size
    if M <= 256:
        # For small batch sizes, use simpler kernel
        BLOCK_SIZE_M = min(64, triton.next_power_of_2(M))
        BLOCK_SIZE_N = min(128, triton.next_power_of_2(N))
        BLOCK_SIZE_K = min(64, triton.next_power_of_2(K))
        
        grid = (
            triton.cdiv(M, BLOCK_SIZE_M),
            triton.cdiv(N, BLOCK_SIZE_N),
        )
        
        _fused_linear_jsd_kernel[grid](
            X, W1, B1, W2, B2, output,
            M, N, K,
            X.stride(0), X.stride(1),
            W1.stride(0), W1.stride(1),
            W2.stride(0), W2.stride(1),
            BLOCK_SIZE_M=BLOCK_SIZE_M,
            BLOCK_SIZE_N=BLOCK_SIZE_N,
            BLOCK_SIZE_K=BLOCK_SIZE_K,
        )
    else:
        # For larger batch sizes, use optimized kernel with better cache utilization
        BLOCK_SIZE_M = 64
        BLOCK_SIZE_N = 128
        BLOCK_SIZE_K = 64
        GROUP_SIZE_M = 8
        
        grid = (triton.cdiv(M, BLOCK_SIZE_M) * triton.cdiv(N, BLOCK_SIZE_N),)
        
        # Initialize output with zeros
        output.zero_()
        
        _fused_linear_jsd_kernel_optimized[grid](
            X, W1, B1, W2, B2, output,
            M, N, K,
            X.stride(0), X.stride(1),
            W1.stride(0), W1.stride(1),
            W2.stride(0), W2.stride(1),
            BLOCK_SIZE_M=BLOCK_SIZE_M,
            BLOCK_SIZE_N=BLOCK_SIZE_N,
            BLOCK_SIZE_K=BLOCK_SIZE_K,
            GROUP_SIZE_M=GROUP_SIZE_M,
        )
    
    return output


class Solution:
    def solve(self, spec_path: str = None) -> dict:
        return {"code": """
import torch
import triton
import triton.language as tl


@triton.jit
def _fused_linear_jsd_kernel(
    # Pointers to matrices
    x_ptr,
    w1_ptr,
    b1_ptr,
    w2_ptr,
    b2_ptr,
    output_ptr,
    # Matrix dimensions
    M,
    N,
    K,
    # Strides
    stride_xm,
    stride_xk,
    stride_w1k,
    stride_w1n,
    stride_w2k,
    stride_w2n,
    # Meta-parameters
    BLOCK_SIZE_M: tl.constexpr,
    BLOCK_SIZE_N: tl.constexpr,
    BLOCK_SIZE_K: tl.constexpr,
):
    # Program ID
    pid_m = tl.program_id(axis=0)
    pid_n = tl.program_id(axis=1)
    
    # Offsets
    offs_m = pid_m * BLOCK_SIZE_M + tl.arange(0, BLOCK_SIZE_M)
    offs_n = pid_n * BLOCK_SIZE_N + tl.arange(0, BLOCK_SIZE_N)
    offs_k = tl.arange(0, BLOCK_SIZE_K)
    
    # Create masks for boundary checks
    mask_m = offs_m < M
    mask_n = offs_n < N
    
    # Initialize accumulators
    acc1 = tl.zeros((BLOCK_SIZE_M, BLOCK_SIZE_N), dtype=tl.float32)
    acc2 = tl.zeros((BLOCK_SIZE_M, BLOCK_SIZE_N), dtype=tl.float32)
    
    # Load biases
    b1 = tl.load(b1_ptr + offs_n, mask=mask_n, other=0.0).to(tl.float32)
    b2 = tl.load(b2_ptr + offs_n, mask=mask_n, other=0.0).to(tl.float32)
    
    # Broadcast biases to all rows in block
    b1_broadcast = tl.broadcast_to(b1, (BLOCK_SIZE_M, BLOCK_SIZE_N))
    b2_broadcast = tl.broadcast_to(b2, (BLOCK_SIZE_M, BLOCK_SIZE_N))
    
    # Add biases to accumulators
    acc1 += b1_broadcast
    acc2 += b2_broadcast
    
    # Compute matrix multiplication with tiling
    for k in range(0, tl.cdiv(K, BLOCK_SIZE_K)):
        # Compute offsets for K dimension
        k_offs = k * BLOCK_SIZE_K
        k_range = k_offs + offs_k
        k_mask = k_range < K
        
        # Load tiles from X, W1, and W2
        x_ptr_base = x_ptr + (offs_m[:, None] * stride_xm + k_range[None, :] * stride_xk)
        w1_ptr_base = w1_ptr + (k_range[:, None] * stride_w1k + offs_n[None, :] * stride_w1n)
        w2_ptr_base = w2_ptr + (k_range[:, None] * stride_w2k + offs_n[None, :] * stride_w2n)
        
        x = tl.load(x_ptr_base, mask=mask_m[:, None] & k_mask[None, :], other=0.0).to(tl.float32)
        w1 = tl.load(w1_ptr_base, mask=k_mask[:, None] & mask_n[None, :], other=0.0).to(tl.float32)
        w2 = tl.load(w2_ptr_base, mask=k_mask[:, None] & mask_n[None, :], other=0.0).to(tl.float32)
        
        # Compute matrix multiplication
        acc1 += tl.dot(x, w1, allow_tf32=False)
        acc2 += tl.dot(x, w2, allow_tf32=False)
    
    # Store logits to shared memory for first pass
    logits1 = acc1
    logits2 = acc2
    
    # First pass: compute log-sum-exp for logits1 and logits2
    # Compute max for numerical stability
    max1 = tl.max(logits1, axis=1, keep_dims=True)
    max2 = tl.max(logits2, axis=1, keep_dims=True)
    
    # Compute exp of shifted logits
    exp1 = tl.exp(logits1 - max1)
    exp2 = tl.exp(logits2 - max2)
    
    # Sum along N dimension
    sum_exp1 = tl.sum(exp1, axis=1, keep_dims=True)
    sum_exp2 = tl.sum(exp2, axis=1, keep_dims=True)
    
    # Compute log probabilities
    log_p = logits1 - max1 - tl.log(sum_exp1)
    log_q = logits2 - max2 - tl.log(sum_exp2)
    
    # Compute probabilities
    p = tl.exp(log_p)
    q = tl.exp(log_q)
    
    # Compute M = 0.5 * (p + q)
    m = 0.5 * (p + q)
    
    # Compute log M using log-sum-exp for numerical stability
    log_m = tl.log(0.5) + tl.log(tl.exp(log_p) + tl.exp(log_q))
    
    # Compute KL divergences
    kl_p = p * (log_p - log_m)
    kl_q = q * (log_q - log_m)
    
    # Sum KL divergences along N dimension
    kl_p_sum = tl.sum(kl_p, axis=1)
    kl_q_sum = tl.sum(kl_q, axis=1)
    
    # Compute JSD
    jsd = 0.5 * (kl_p_sum + kl_q_sum)
    
    # Store result
    out_ptr = output_ptr + offs_m
    tl.store(out_ptr, jsd, mask=mask_m)


@triton.jit
def _fused_linear_jsd_kernel_optimized(
    # Pointers to matrices
    x_ptr,
    w1_ptr,
    b1_ptr,
    w2_ptr,
    b2_ptr,
    output_ptr,
    # Matrix dimensions
    M,
    N,
    K,
    # Strides
    stride_xm,
    stride_xk,
    stride_w1k,
    stride_w1n,
    stride_w2k,
    stride_w2n,
    # Meta-parameters
    BLOCK_SIZE_M: tl.constexpr,
    BLOCK_SIZE_N: tl.constexpr,
    BLOCK_SIZE_K: tl.constexpr,
    GROUP_SIZE_M: tl.constexpr,
):
    # Program ID
    pid = tl.program_id(axis=0)
    
    # Number of program IDs along M dimension
    num_pid_m = tl.cdiv(M, BLOCK_SIZE_M)
    num_pid_n = tl.cdiv(N, BLOCK_SIZE_N)
    
    # Decompose program ID
    pid_m = pid // num_pid_n
    pid_n = pid % num_pid_n
    
    # Reorder program IDs for better L2 cache hit rate
    num_blocks_m = tl.cdiv(M, BLOCK_SIZE_M)
    num_blocks_n = tl.cdiv(N, BLOCK_SIZE_N)
    
    group_id = pid_m // GROUP_SIZE_M
    group_size = min(num_blocks_m - group_id * GROUP_SIZE_M, GROUP_SIZE_M)
    pid_m = group_id * GROUP_SIZE_M + (pid_n % group_size)
    pid_n = pid_n // group_size
    
    # Return if out of bounds
    if pid_m >= num_blocks_m:
        return
    
    # Offsets
    offs_m = pid_m * BLOCK_SIZE_M + tl.arange(0, BLOCK_SIZE_M)
    offs_n = pid_n * BLOCK_SIZE_N + tl.arange(0, BLOCK_SIZE_N)
    offs_k = tl.arange(0, BLOCK_SIZE_K)
    
    # Create masks
    mask_m = offs_m < M
    mask_n = offs_n < N
    
    # Initialize accumulators
    acc1 = tl.zeros((BLOCK_SIZE_M, BLOCK_SIZE_N), dtype=tl.float32)
    acc2 = tl.zeros((BLOCK_SIZE_M, BLOCK_SIZE_N), dtype=tl.float32)
    
    # Load biases
    b1 = tl.load(b1_ptr + offs_n, mask=mask_n, other=0.0).to(tl.float32)
    b2 = tl.load(b2_ptr + offs_n, mask=mask_n, other=0.0).to(tl.float32)
    
    # Broadcast biases
    b1_broadcast = tl.broadcast_to(b1, (BLOCK_SIZE_M, BLOCK_SIZE_N))
    b2_broadcast = tl.broadcast_to(b2, (BLOCK_SIZE_M, BLOCK_SIZE_N))
    
    acc1 += b1_broadcast
    acc2 += b2_broadcast
    
    # Compute matrix multiplication
    k_iters = tl.cdiv(K, BLOCK_SIZE_K)
    
    for k in range(0, k_iters):
        # Compute offsets for K dimension
        k_offs = k * BLOCK_SIZE_K
        k_range = k_offs + offs_k
        k_mask = k_range < K
        
        # Load tiles
        x_ptr_base = x_ptr + (offs_m[:, None] * stride_xm + k_range[None, :] * stride_xk)
        w1_ptr_base = w1_ptr + (k_range[:, None] * stride_w1k + offs_n[None, :] * stride_w1n)
        w2_ptr_base = w2_ptr + (k_range[:, None] * stride_w2k + offs_n[None, :] * stride_w2n)
        
        x = tl.load(x_ptr_base, mask=mask_m[:, None] & k_mask[None, :], other=0.0).to(tl.float32)
        w1 = tl.load(w1_ptr_base, mask=k_mask[:, None] & mask_n[None, :], other=0.0).to(tl.float32)
        w2 = tl.load(w2_ptr_base, mask=k_mask[:, None] & mask_n[None, :], other=0.0).to(tl.float32)
        
        # Accumulate
        acc1 += tl.dot(x, w1, allow_tf32=True)
        acc2 += tl.dot(x, w2, allow_tf32=True)
    
    # Convert to logits
    logits1 = acc1
    logits2 = acc2
    
    # Compute max for numerical stability
    max1 = tl.max(logits1, axis=1, keep_dims=True)
    max2 = tl.max(logits2, axis=1, keep_dims=True)
    
    # Compute exp of shifted logits
    exp1 = tl.exp(logits1 - max1)
    exp2 = tl.exp(logits2 - max2)
    
    # Sum along N dimension
    sum_exp1 = tl.sum(exp1, axis=1, keep_dims=True)
    sum_exp2 = tl.sum(exp2, axis=1, keep_dims=True)
    
    # Compute log probabilities
    log_p = logits1 - max1 - tl.log(sum_exp1)
    log_q = logits2 - max2 - tl.log(sum_exp2)
    
    # Compute M and log M
    log_m = tl.log(0.5) + tl.log(tl.exp(log_p) + tl.exp(log_q))
    
    # Compute KL divergences
    kl_p = tl.exp(log_p) * (log_p - log_m)
    kl_q = tl.exp(log_q) * (log_q - log_m)
    
    # Sum KL divergences
    kl_p_sum = tl.sum(kl_p, axis=1)
    kl_q_sum = tl.sum(kl_q, axis=1)
    
    # Compute JSD
    jsd = 0.5 * (kl_p_sum + kl_q_sum)
    
    # Store result - need to reduce across N dimension
    # Use atomic add to accumulate across different pid_n
    out_ptr = output_ptr + offs_m
    tl.atomic_add(out_ptr, jsd, mask=mask_m)


def fused_linear_jsd(X: torch.Tensor, W1: torch.Tensor, B1: torch.Tensor, 
                    W2: torch.Tensor, B2: torch.Tensor) -> torch.Tensor:
    # Check input shapes
    M, K = X.shape
    N = W1.shape[1]
    
    assert X.shape == (M, K), f"X shape mismatch: {X.shape} != {(M, K)}"
    assert W1.shape == (K, N), f"W1 shape mismatch: {W1.shape} != {(K, N)}"
    assert W2.shape == (K, N), f"W2 shape mismatch: {W2.shape} != {(K, N)}"
    assert B1.shape == (N,), f"B1 shape mismatch: {B1.shape} != {(N,)}"
    assert B2.shape == (N,), f"B2 shape mismatch: {B2.shape} != {(N,)}"
    
    # Check dtypes
    assert X.dtype == torch.float16, f"X dtype {X.dtype} != float16"
    assert W1.dtype == torch.float16, f"W1 dtype {W1.dtype} != float16"
    assert W2.dtype == torch.float16, f"W2 dtype {W2.dtype} != float16"
    assert B1.dtype == torch.float32, f"B1 dtype {B1.dtype} != float32"
    assert B2.dtype == torch.float32, f"B2 dtype {B2.dtype} != float32"
    
    # Allocate output
    output = torch.zeros((M,), dtype=torch.float32, device=X.device)
    
    # Choose kernel configuration based on problem size
    if M <= 256:
        # For small batch sizes, use simpler kernel
        BLOCK_SIZE_M = min(64, triton.next_power_of_2(M))
        BLOCK_SIZE_N = min(128, triton.next_power_of_2(N))
        BLOCK_SIZE_K = min(64, triton.next_power_of_2(K))
        
        grid = (
            triton.cdiv(M, BLOCK_SIZE_M),
            triton.cdiv(N, BLOCK_SIZE_N),
        )
        
        _fused_linear_jsd_kernel[grid](
            X, W1, B1, W2, B2, output,
            M, N, K,
            X.stride(0), X.stride(1),
            W1.stride(0), W1.stride(1),
            W2.stride(0), W2.stride(1),
            BLOCK_SIZE_M=BLOCK_SIZE_M,
            BLOCK_SIZE_N=BLOCK_SIZE_N,
            BLOCK_SIZE_K=BLOCK_SIZE_K,
        )
    else:
        # For larger batch sizes, use optimized kernel with better cache utilization
        BLOCK_SIZE_M = 64
        BLOCK_SIZE_N = 128
        BLOCK_SIZE_K = 64
        GROUP_SIZE_M = 8
        
        grid = (triton.cdiv(M, BLOCK_SIZE_M) * triton.cdiv(N, BLOCK_SIZE_N),)
        
        # Initialize output with zeros
        output.zero_()
        
        _fused_linear_jsd_kernel_optimized[grid](
            X, W1, B1, W2, B2, output,
            M, N, K,
            X.stride(0), X.stride(1),
            W1.stride(0), W1.stride(1),
            W2.stride(0), W2.stride(1),
            BLOCK_SIZE_M=BLOCK_SIZE_M,
            BLOCK_SIZE_N=BLOCK_SIZE_N,
            BLOCK_SIZE_K=BLOCK_SIZE_K,
            GROUP_SIZE_M=GROUP_SIZE_M,
        )
    
    return output
"""}