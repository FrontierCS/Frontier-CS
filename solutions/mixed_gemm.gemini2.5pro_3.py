import torch
import triton
import triton.language as tl

class Solution:
    def solve(self, spec_path: str = None) -> dict:
        """
        Returns a dict with a Python code string for the Triton kernel.
        """
        python_code_string = """
import torch
import triton
import triton.language as tl

@triton.autotune(
    configs=[
        triton.Config({'BLOCK_SIZE_M': 128, 'BLOCK_SIZE_N': 256, 'BLOCK_SIZE_K': 32, 'GROUP_SIZE_M': 8, 'num_stages': 3, 'num_warps': 8}),
        triton.Config({'BLOCK_SIZE_M': 256, 'BLOCK_SIZE_N': 128, 'BLOCK_SIZE_K': 32, 'GROUP_SIZE_M': 8, 'num_stages': 3, 'num_warps': 8}),
        triton.Config({'BLOCK_SIZE_M': 256, 'BLOCK_SIZE_N': 64, 'BLOCK_SIZE_K': 32, 'GROUP_SIZE_M': 8, 'num_stages': 4, 'num_warps': 4}),
        triton.Config({'BLOCK_SIZE_M': 64, 'BLOCK_SIZE_N': 256, 'BLOCK_SIZE_K': 32, 'GROUP_SIZE_M': 8, 'num_stages': 4, 'num_warps': 4}),
        triton.Config({'BLOCK_SIZE_M': 128, 'BLOCK_SIZE_N': 128, 'BLOCK_SIZE_K': 32, 'GROUP_SIZE_M': 8, 'num_stages': 4, 'num_warps': 4}),
        triton.Config({'BLOCK_SIZE_M': 128, 'BLOCK_SIZE_N': 64, 'BLOCK_SIZE_K': 32, 'GROUP_SIZE_M': 8, 'num_stages': 4, 'num_warps': 4}),
        triton.Config({'BLOCK_SIZE_M': 64, 'BLOCK_SIZE_N': 128, 'BLOCK_SIZE_K': 32, 'GROUP_SIZE_M': 8, 'num_stages': 4, 'num_warps': 4}),
        triton.Config({'BLOCK_SIZE_M': 128, 'BLOCK_SIZE_N': 32, 'BLOCK_SIZE_K': 32, 'GROUP_SIZE_M': 8, 'num_stages': 4, 'num_warps': 4}),
        triton.Config({'BLOCK_SIZE_M': 64, 'BLOCK_SIZE_N': 32, 'BLOCK_SIZE_K': 32, 'GROUP_SIZE_M': 8, 'num_stages': 5, 'num_warps': 2}),
        # configs with larger K block
        triton.Config({'BLOCK_SIZE_M': 128, 'BLOCK_SIZE_N': 128, 'BLOCK_SIZE_K': 64, 'GROUP_SIZE_M': 8, 'num_stages': 3, 'num_warps': 8}),
        triton.Config({'BLOCK_SIZE_M': 64, 'BLOCK_SIZE_N': 128, 'BLOCK_SIZE_K': 64, 'GROUP_SIZE_M': 8, 'num_stages': 3, 'num_warps': 4}),
        triton.Config({'BLOCK_SIZE_M': 128, 'BLOCK_SIZE_N': 64, 'BLOCK_SIZE_K': 64, 'GROUP_SIZE_M': 8, 'num_stages': 3, 'num_warps': 4}),
    ],
    key=['M', 'N', 'K'],
)
@triton.jit
def _linear_gelu_kernel(
    X, W, B, Y,
    M, N, K,
    stride_xm, stride_xk,
    stride_wk, stride_wn,
    stride_ym, stride_yn,
    BLOCK_SIZE_M: tl.constexpr,
    BLOCK_SIZE_N: tl.constexpr,
    BLOCK_SIZE_K: tl.constexpr,
    GROUP_SIZE_M: tl.constexpr,
):
    pid = tl.program_id(axis=0)
    num_pid_n = tl.cdiv(N, BLOCK_SIZE_N)
    num_pid_m = tl.cdiv(M, BLOCK_SIZE_M)
    
    # Grouping PIDs for L2 cache locality on W
    num_pid_in_group = GROUP_SIZE_M * num_pid_n
    group_id = pid // num_pid_in_group
    first_pid_m = group_id * GROUP_SIZE_M
    group_size = min(num_pid_m - first_pid_m, GROUP_SIZE_M)
    pid_m = first_pid_m + (pid % group_size)
    pid_n = (pid % num_pid_in_group) // group_size

    # Pointers and offsets for the current block
    offs_m = pid_m * BLOCK_SIZE_M + tl.arange(0, BLOCK_SIZE_M)
    offs_n = pid_n * BLOCK_SIZE_N + tl.arange(0, BLOCK_SIZE_N)
    offs_k = tl.arange(0, BLOCK_SIZE_K)

    x_ptrs = X + (offs_m[:, None] * stride_xm + offs_k[None, :] * stride_xk)
    w_ptrs = W + (offs_k[:, None] * stride_wk + offs_n[None, :] * stride_wn)

    # Accumulator in float32 for precision
    accumulator = tl.zeros((BLOCK_SIZE_M, BLOCK_SIZE_N), dtype=tl.float32)

    # Main loop over the K dimension
    for k in range(0, tl.cdiv(K, BLOCK_SIZE_K)):
        # Boundary checks for loading
        mask_x = (offs_m[:, None] < M) & ((k * BLOCK_SIZE_K + offs_k[None, :]) < K)
        mask_w = ((k * BLOCK_SIZE_K + offs_k[:, None]) < K) & (offs_n[None, :] < N)
        
        a = tl.load(x_ptrs + k * BLOCK_SIZE_K * stride_xk, mask=mask_x, other=0.0)
        b = tl.load(w_ptrs + k * BLOCK_SIZE_K * stride_wk, mask=mask_w, other=0.0)

        # Matrix multiplication
        accumulator = tl.dot(a, b, accumulator)

    # Load and add bias
    b_ptrs = B + offs_n
    mask_b = offs_n < N
    bias = tl.load(b_ptrs, mask=mask_b, other=0.0)
    accumulator = accumulator + bias[None, :]

    # Apply GELU activation: gelu(x) = x * 0.5 * (1.0 + erf(x / sqrt(2)))
    inv_sqrt2 = 0.7071067811865476
    x = accumulator
    erf_val = tl.extra.cuda.libdevice.erf(x * inv_sqrt2)
    gelu_out = x * 0.5 * (1.0 + erf_val)

    # Store the final result
    y_ptrs = Y + (offs_m[:, None] * stride_ym + offs_n[None, :] * stride_yn)
    mask_y = (offs_m[:, None] < M) & (offs_n[None, :] < N)
    tl.store(y_ptrs, gelu_out.to(Y.dtype.element_ty), mask=mask_y)

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
    assert X.is_cuda and W.is_cuda and B.is_cuda
    assert X.dtype == torch.float16 and W.dtype == torch.float16 and B.dtype == torch.float32
    assert X.shape[1] == W.shape[0] and W.shape[1] == B.shape[0]

    M, K = X.shape
    _, N = W.shape

    Y = torch.empty((M, N), device=X.device, dtype=torch.float16)
    
    # Grid is 1D to enable grouping for better L2 cache performance
    grid = lambda META: (triton.cdiv(M, META['BLOCK_SIZE_M']) * triton.cdiv(N, META['BLOCK_SIZE_N']),)

    _linear_gelu_kernel[grid](
        X, W, B, Y,
        M, N, K,
        X.stride(0), X.stride(1),
        W.stride(0), W.stride(1),
        Y.stride(0), Y.stride(1),
    )
    return Y

"""
        return {"code": python_code_string}
