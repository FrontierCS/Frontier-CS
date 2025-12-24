import torch
import triton
import triton.language as tl


@triton.jit
def _linear_gelu_kernel(
    # Pointers to matrices
    X_ptr, W_ptr, B_ptr, Out_ptr,
    # Matrix dimensions
    M, N, K,
    # Strides
    stride_xm, stride_xk,
    stride_wk, stride_wn,
    stride_bn,
    stride_outm, stride_outn,
    # Meta-parameters
    BLOCK_SIZE_M: tl.constexpr,
    BLOCK_SIZE_N: tl.constexpr,
    BLOCK_SIZE_K: tl.constexpr,
    GROUP_SIZE_M: tl.constexpr,
):
    # Program ID
    pid = tl.program_id(axis=0)
    num_pid_m = tl.cdiv(M, BLOCK_SIZE_M)
    num_pid_n = tl.cdiv(N, BLOCK_SIZE_N)
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

    # Pointers for X and W
    X_ptrs = X_ptr + (offs_m[:, None] * stride_xm + offs_k[None, :] * stride_xk)
    W_ptrs = W_ptr + (offs_k[:, None] * stride_wk + offs_n[None, :] * stride_wn)

    # Accumulator
    acc = tl.zeros((BLOCK_SIZE_M, BLOCK_SIZE_N), dtype=tl.float32)

    # Loop over K
    for k in range(0, K, BLOCK_SIZE_K):
        # Load X and W
        x = tl.load(X_ptrs, mask=(offs_m[:, None] < M) & (offs_k[None, :] < K - k), other=0.0)
        w = tl.load(W_ptrs, mask=(offs_k[:, None] < K - k) & (offs_n[None, :] < N), other=0.0)
        
        # Convert to float32 and accumulate
        x_f32 = x.to(tl.float32)
        w_f32 = w.to(tl.float32)
        acc += tl.dot(x_f32, w_f32)
        
        # Update pointers
        X_ptrs += BLOCK_SIZE_K * stride_xk
        W_ptrs += BLOCK_SIZE_K * stride_wk

    # Add bias
    if B_ptr is not None:
        b_ptrs = B_ptr + offs_n
        bias = tl.load(b_ptrs, mask=offs_n < N, other=0.0)
        acc += bias[None, :]

    # GELU activation
    # GELU(x) = 0.5 * x * (1 + tanh(sqrt(2/π) * (x + 0.044715 * x^3)))
    # Use approximation for better performance
    x = acc
    # Fast GELU approximation from DAWNBench
    gelu = x * 0.5 * (1.0 + tl.tanh(0.7978845608028654 * (x + 0.044715 * x * x * x)))

    # Convert to fp16 and store
    offs_outm = pid_m * BLOCK_SIZE_M + tl.arange(0, BLOCK_SIZE_M)
    offs_outn = pid_n * BLOCK_SIZE_N + tl.arange(0, BLOCK_SIZE_N)
    out_ptrs = Out_ptr + (offs_outm[:, None] * stride_outm + offs_outn[None, :] * stride_outn)
    tl.store(out_ptrs, gelu.to(tl.float16),
             mask=(offs_outm[:, None] < M) & (offs_outn[None, :] < N))


def linear_gelu(X: torch.Tensor, W: torch.Tensor, B: torch.Tensor) -> torch.Tensor:
    """
    Linear layer with GELU activation computation.
    
    Args:
        X: Input tensor of shape (M, K) - input features (float16)
        W: Weight tensor of shape (K, N) - weight matrix (float16)
        B: Bias tensor of shape (N,) - bias vector (float32)
    
    Returns:
        Output tensor of shape (M, N) - output with GELU activation (float16)
    """
    # Check dimensions
    M, K = X.shape
    K_check, N = W.shape
    assert K == K_check, f"Dimension mismatch: X.shape={X.shape}, W.shape={W.shape}"
    assert B.shape == (N,), f"Bias shape mismatch: B.shape={B.shape}, expected ({N},)"
    
    # Allocate output
    out = torch.empty((M, N), dtype=torch.float16, device=X.device)
    
    # Grid size
    grid = lambda META: (triton.cdiv(M, META['BLOCK_SIZE_M']) * 
                        triton.cdiv(N, META['BLOCK_SIZE_N']),)
    
    # Tuning parameters
    BLOCK_SIZE_M = 64
    BLOCK_SIZE_N = 64
    BLOCK_SIZE_K = 32
    GROUP_SIZE_M = 8
    
    # Launch kernel
    _linear_gelu_kernel[grid](
        X, W, B, out,
        M, N, K,
        X.stride(0), X.stride(1),
        W.stride(0), W.stride(1),
        B.stride(0),
        out.stride(0), out.stride(1),
        BLOCK_SIZE_M=BLOCK_SIZE_M,
        BLOCK_SIZE_N=BLOCK_SIZE_N,
        BLOCK_SIZE_K=BLOCK_SIZE_K,
        GROUP_SIZE_M=GROUP_SIZE_M,
    )
    
    return out


class Solution:
    def solve(self, spec_path: str = None) -> dict:
        return {"code": """import torch
import triton
import triton.language as tl


@triton.jit
def _linear_gelu_kernel(
    # Pointers to matrices
    X_ptr, W_ptr, B_ptr, Out_ptr,
    # Matrix dimensions
    M, N, K,
    # Strides
    stride_xm, stride_xk,
    stride_wk, stride_wn,
    stride_bn,
    stride_outm, stride_outn,
    # Meta-parameters
    BLOCK_SIZE_M: tl.constexpr,
    BLOCK_SIZE_N: tl.constexpr,
    BLOCK_SIZE_K: tl.constexpr,
    GROUP_SIZE_M: tl.constexpr,
):
    # Program ID
    pid = tl.program_id(axis=0)
    num_pid_m = tl.cdiv(M, BLOCK_SIZE_M)
    num_pid_n = tl.cdiv(N, BLOCK_SIZE_N)
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

    # Pointers for X and W
    X_ptrs = X_ptr + (offs_m[:, None] * stride_xm + offs_k[None, :] * stride_xk)
    W_ptrs = W_ptr + (offs_k[:, None] * stride_wk + offs_n[None, :] * stride_wn)

    # Accumulator
    acc = tl.zeros((BLOCK_SIZE_M, BLOCK_SIZE_N), dtype=tl.float32)

    # Loop over K
    for k in range(0, K, BLOCK_SIZE_K):
        # Load X and W
        x = tl.load(X_ptrs, mask=(offs_m[:, None] < M) & (offs_k[None, :] < K - k), other=0.0)
        w = tl.load(W_ptrs, mask=(offs_k[:, None] < K - k) & (offs_n[None, :] < N), other=0.0)
        
        # Convert to float32 and accumulate
        x_f32 = x.to(tl.float32)
        w_f32 = w.to(tl.float32)
        acc += tl.dot(x_f32, w_f32)
        
        # Update pointers
        X_ptrs += BLOCK_SIZE_K * stride_xk
        W_ptrs += BLOCK_SIZE_K * stride_wk

    # Add bias
    if B_ptr is not None:
        b_ptrs = B_ptr + offs_n
        bias = tl.load(b_ptrs, mask=offs_n < N, other=0.0)
        acc += bias[None, :]

    # GELU activation
    # GELU(x) = 0.5 * x * (1 + tanh(sqrt(2/π) * (x + 0.044715 * x^3)))
    # Use approximation for better performance
    x = acc
    # Fast GELU approximation from DAWNBench
    gelu = x * 0.5 * (1.0 + tl.tanh(0.7978845608028654 * (x + 0.044715 * x * x * x)))

    # Convert to fp16 and store
    offs_outm = pid_m * BLOCK_SIZE_M + tl.arange(0, BLOCK_SIZE_M)
    offs_outn = pid_n * BLOCK_SIZE_N + tl.arange(0, BLOCK_SIZE_N)
    out_ptrs = Out_ptr + (offs_outm[:, None] * stride_outm + offs_outn[None, :] * stride_outn)
    tl.store(out_ptrs, gelu.to(tl.float16),
             mask=(offs_outm[:, None] < M) & (offs_outn[None, :] < N))


def linear_gelu(X: torch.Tensor, W: torch.Tensor, B: torch.Tensor) -> torch.Tensor:
    \"\"\"
    Linear layer with GELU activation computation.
    
    Args:
        X: Input tensor of shape (M, K) - input features (float16)
        W: Weight tensor of shape (K, N) - weight matrix (float16)
        B: Bias tensor of shape (N,) - bias vector (float32)
    
    Returns:
        Output tensor of shape (M, N) - output with GELU activation (float16)
    \"\"\"
    # Check dimensions
    M, K = X.shape
    K_check, N = W.shape
    assert K == K_check, f"Dimension mismatch: X.shape={X.shape}, W.shape={W.shape}"
    assert B.shape == (N,), f"Bias shape mismatch: B.shape={B.shape}, expected ({N},)"
    
    # Allocate output
    out = torch.empty((M, N), dtype=torch.float16, device=X.device)
    
    # Grid size
    grid = lambda META: (triton.cdiv(M, META['BLOCK_SIZE_M']) * 
                        triton.cdiv(N, META['BLOCK_SIZE_N']),)
    
    # Tuning parameters
    BLOCK_SIZE_M = 64
    BLOCK_SIZE_N = 64
    BLOCK_SIZE_K = 32
    GROUP_SIZE_M = 8
    
    # Launch kernel
    _linear_gelu_kernel[grid](
        X, W, B, out,
        M, N, K,
        X.stride(0), X.stride(1),
        W.stride(0), W.stride(1),
        B.stride(0),
        out.stride(0), out.stride(1),
        BLOCK_SIZE_M=BLOCK_SIZE_M,
        BLOCK_SIZE_N=BLOCK_SIZE_N,
        BLOCK_SIZE_K=BLOCK_SIZE_K,
        GROUP_SIZE_M=GROUP_SIZE_M,
    )
    
    return out
"""}
