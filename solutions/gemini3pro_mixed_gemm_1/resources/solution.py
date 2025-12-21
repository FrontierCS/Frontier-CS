import torch
import triton
import triton.language as tl

class Solution:
    def solve(self, spec_path: str = None) -> dict:
        code = r"""
import torch
import triton
import triton.language as tl

@triton.jit
def gelu_op(x):
    # GELU activation: x * 0.5 * (1.0 + erf(x * 0.7071067811865476))
    # Using libdevice erf for efficiency and precision as suggested
    return x * 0.5 * (1.0 + tl.extra.cuda.libdevice.erf(x * 0.7071067811865476))

@triton.autotune(
    configs=[
        triton.Config({'BLOCK_SIZE_M': 128, 'BLOCK_SIZE_N': 128, 'BLOCK_SIZE_K': 32, 'GROUP_SIZE_M': 8}, num_stages=3, num_warps=8),
        triton.Config({'BLOCK_SIZE_M': 128, 'BLOCK_SIZE_N': 64, 'BLOCK_SIZE_K': 32, 'GROUP_SIZE_M': 8}, num_stages=4, num_warps=4),
        triton.Config({'BLOCK_SIZE_M': 64, 'BLOCK_SIZE_N': 128, 'BLOCK_SIZE_K': 32, 'GROUP_SIZE_M': 8}, num_stages=4, num_warps=4),
        triton.Config({'BLOCK_SIZE_M': 64, 'BLOCK_SIZE_N': 64, 'BLOCK_SIZE_K': 32, 'GROUP_SIZE_M': 8}, num_stages=4, num_warps=4),
        triton.Config({'BLOCK_SIZE_M': 128, 'BLOCK_SIZE_N': 256, 'BLOCK_SIZE_K': 64, 'GROUP_SIZE_M': 8}, num_stages=3, num_warps=8),
        triton.Config({'BLOCK_SIZE_M': 256, 'BLOCK_SIZE_N': 128, 'BLOCK_SIZE_K': 64, 'GROUP_SIZE_M': 8}, num_stages=3, num_warps=8),
    ],
    key=['M', 'N', 'K'],
)
@triton.jit
def mixed_gemm_gelu_kernel(
    X_ptr, W_ptr, B_ptr, Out_ptr,
    M, N, K,
    stride_xm, stride_xk,
    stride_wk, stride_wn,
    stride_om, stride_on,
    BLOCK_SIZE_M: tl.constexpr, BLOCK_SIZE_N: tl.constexpr, BLOCK_SIZE_K: tl.constexpr,
    GROUP_SIZE_M: tl.constexpr,
):
    # PID mapping and Swizzling
    pid = tl.program_id(axis=0)
    num_pid_m = tl.cdiv(M, BLOCK_SIZE_M)
    num_pid_n = tl.cdiv(N, BLOCK_SIZE_N)
    num_pid_in_group = GROUP_SIZE_M * num_pid_n
    group_id = pid // num_pid_in_group
    first_pid_m = group_id * GROUP_SIZE_M
    group_size_m = min(num_pid_m - first_pid_m, GROUP_SIZE_M)
    pid_m = first_pid_m + (pid % group_size_m)
    pid_n = (pid % num_pid_in_group) // group_size_m

    # Block offsets
    offs_am = (pid_m * BLOCK_SIZE_M + tl.arange(0, BLOCK_SIZE_M)) % M
    offs_bn = (pid_n * BLOCK_SIZE_N + tl.arange(0, BLOCK_SIZE_N)) % N
    offs_k = tl.arange(0, BLOCK_SIZE_K)

    # Input pointers
    # X: (M, K)
    a_ptrs = X_ptr + (offs_am[:, None] * stride_xm + offs_k[None, :] * stride_xk)
    # W: (K, N)
    b_ptrs = W_ptr + (offs_k[:, None] * stride_wk + offs_bn[None, :] * stride_wn)

    # Accumulator (float32)
    accumulator = tl.zeros((BLOCK_SIZE_M, BLOCK_SIZE_N), dtype=tl.float32)

    # Main Loop
    for k in range(0, tl.cdiv(K, BLOCK_SIZE_K)):
        # Handling K edge cases (though K is typically aligned in this problem)
        k_remaining = K - k * BLOCK_SIZE_K
        
        # Load A and B
        a = tl.load(a_ptrs, mask=offs_k[None, :] < k_remaining, other=0.0)
        b = tl.load(b_ptrs, mask=offs_k[:, None] < k_remaining, other=0.0)
        
        # Matrix Multiplication
        accumulator = tl.dot(a, b, accumulator)
        
        # Advance pointers
        a_ptrs += BLOCK_SIZE_K * stride_xk
        b_ptrs += BLOCK_SIZE_K * stride_wk

    # Load Bias (N,)
    bias_ptrs = B_ptr + offs_bn
    bias = tl.load(bias_ptrs, mask=offs_bn < N, other=0.0)
    
    # Fused Computation
    # Add Bias
    accumulator = accumulator + bias[None, :]
    # Apply GELU
    accumulator = gelu_op(accumulator)
    
    # Store Output (converted to float16)
    out_ptrs = Out_ptr + (offs_am[:, None] * stride_om + offs_bn[None, :] * stride_on)
    c_mask = (offs_am[:, None] < M) & (offs_bn[None, :] < N)
    tl.store(out_ptrs, accumulator.to(tl.float16), mask=c_mask)

def linear_gelu(X: torch.Tensor, W: torch.Tensor, B: torch.Tensor) -> torch.Tensor:
    # Validation
    assert X.is_cuda and W.is_cuda and B.is_cuda
    M, K = X.shape
    Kw, N = W.shape
    assert K == Kw, "Matrix dimensions mismatch"
    
    # Output Tensor
    output = torch.empty((M, N), device=X.device, dtype=torch.float16)
    
    # Kernel Launch
    grid = lambda META: (triton.cdiv(M, META['BLOCK_SIZE_M']) * triton.cdiv(N, META['BLOCK_SIZE_N']), )
    
    mixed_gemm_gelu_kernel[grid](
        X, W, B, output,
        M, N, K,
        X.stride(0), X.stride(1),
        W.stride(0), W.stride(1),
        output.stride(0), output.stride(1),
    )
    
    return output
"""
        return {"code": code}
