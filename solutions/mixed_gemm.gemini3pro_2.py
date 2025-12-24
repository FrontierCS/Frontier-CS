import torch
import triton
import triton.language as tl

class Solution:
    def solve(self, spec_path: str = None) -> dict:
        code = r"""
import torch
import triton
import triton.language as tl

@triton.autotune(
    configs=[
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 128, 'BLOCK_K': 32, 'GROUP_SIZE_M': 8}, num_stages=3, num_warps=8),
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 64, 'BLOCK_K': 32, 'GROUP_SIZE_M': 8}, num_stages=4, num_warps=4),
        triton.Config({'BLOCK_M': 64, 'BLOCK_N': 128, 'BLOCK_K': 32, 'GROUP_SIZE_M': 8}, num_stages=4, num_warps=4),
        triton.Config({'BLOCK_M': 64, 'BLOCK_N': 64, 'BLOCK_K': 32, 'GROUP_SIZE_M': 8}, num_stages=4, num_warps=4),
    ],
    key=['M', 'N', 'K'],
)
@triton.jit
def fused_linear_gelu_kernel(
    x_ptr, w_ptr, b_ptr, out_ptr,
    M, N, K,
    stride_xm, stride_xk,
    stride_wk, stride_wn,
    stride_om, stride_on,
    BLOCK_M: tl.constexpr, BLOCK_N: tl.constexpr, BLOCK_K: tl.constexpr,
    GROUP_SIZE_M: tl.constexpr,
):
    # Program ID
    pid = tl.program_id(axis=0)
    num_pid_m = tl.cdiv(M, BLOCK_M)
    num_pid_n = tl.cdiv(N, BLOCK_N)
    num_pid_in_group = GROUP_SIZE_M * num_pid_n
    group_id = pid // num_pid_in_group
    first_pid_m = group_id * GROUP_SIZE_M
    group_size_m = min(num_pid_m - first_pid_m, GROUP_SIZE_M)
    pid_m = first_pid_m + (pid % group_size_m)
    pid_n = (pid % num_pid_in_group) // group_size_m

    # Block offsets
    offs_am = (pid_m * BLOCK_M + tl.arange(0, BLOCK_M)) % M
    offs_bn = (pid_n * BLOCK_N + tl.arange(0, BLOCK_N)) % N
    offs_k = tl.arange(0, BLOCK_K)

    # Pointers
    # X is (M, K), W is (K, N)
    x_ptrs = x_ptr + (offs_am[:, None] * stride_xm + offs_k[None, :] * stride_xk)
    w_ptrs = w_ptr + (offs_k[:, None] * stride_wk + offs_bn[None, :] * stride_wn)

    # Accumulator (float32 for stability)
    accumulator = tl.zeros((BLOCK_M, BLOCK_N), dtype=tl.float32)

    # Matrix Multiplication loop
    for k in range(0, tl.cdiv(K, BLOCK_K)):
        # Load with masking for K dimension
        x = tl.load(x_ptrs, mask=offs_k[None, :] < K - k * BLOCK_K, other=0.0)
        w = tl.load(w_ptrs, mask=offs_k[:, None] < K - k * BLOCK_K, other=0.0)
        
        # Accumulate
        accumulator = tl.dot(x, w, accumulator)
        
        # Advance pointers
        x_ptrs += BLOCK_K * stride_xk
        w_ptrs += BLOCK_K * stride_wk

    # Bias Addition (float32)
    # Bias is shape (N,)
    bias_ptrs = b_ptr + offs_bn
    bias = tl.load(bias_ptrs, mask=offs_bn < N, other=0.0)
    accumulator = accumulator + bias[None, :]

    # GELU Activation
    # gelu(x) = x * 0.5 * (1.0 + erf(x * 0.70710678))
    v_sqrt1_2 = 0.70710678
    v_0_5 = 0.5
    v_one = 1.0
    
    erf_arg = accumulator * v_sqrt1_2
    erf_val = tl.math.erf(erf_arg)
    gelu_val = accumulator * v_0_5 * (v_one + erf_val)

    # Store result (float16)
    out_ptrs = out_ptr + (offs_am[:, None] * stride_om + offs_bn[None, :] * stride_on)
    tl.store(out_ptrs, gelu_val.to(tl.float16), mask=(offs_am[:, None] < M) & (offs_bn[None, :] < N))

def linear_gelu(X: torch.Tensor, W: torch.Tensor, B: torch.Tensor) -> torch.Tensor:
    # Validation
    assert X.is_cuda and W.is_cuda and B.is_cuda
    M, K = X.shape
    Kw, N = W.shape
    assert K == Kw, "Dimension mismatch between X and W"
    assert B.shape[0] == N, "Dimension mismatch between W and B"
    
    # Output buffer
    out = torch.empty((M, N), device=X.device, dtype=torch.float16)
    
    # Kernel launch
    grid = lambda META: (triton.cdiv(M, META['BLOCK_M']) * triton.cdiv(N, META['BLOCK_N']), )
    
    fused_linear_gelu_kernel[grid](
        X, W, B, out,
        M, N, K,
        X.stride(0), X.stride(1),
        W.stride(0), W.stride(1),
        out.stride(0), out.stride(1)
    )
    
    return out
"""
        return {"code": code}
