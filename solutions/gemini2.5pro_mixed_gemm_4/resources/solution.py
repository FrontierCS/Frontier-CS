import torch
import triton
import triton.language as tl
import inspect

@triton.autotune(
    configs=[
        triton.Config({'BLOCK_SIZE_M': 128, 'BLOCK_SIZE_N': 256, 'BLOCK_SIZE_K': 64, 'GROUP_SIZE_M': 8, 'num_warps': 8, 'num_stages': 3}),
        triton.Config({'BLOCK_SIZE_M': 256, 'BLOCK_SIZE_N': 128, 'BLOCK_SIZE_K': 64, 'GROUP_SIZE_M': 8, 'num_warps': 8, 'num_stages': 3}),
        triton.Config({'BLOCK_SIZE_M': 128, 'BLOCK_SIZE_N': 128, 'BLOCK_SIZE_K': 64, 'GROUP_SIZE_M': 8, 'num_warps': 4, 'num_stages': 3}),
        triton.Config({'BLOCK_SIZE_M': 256, 'BLOCK_SIZE_N': 64, 'BLOCK_SIZE_K': 64, 'GROUP_SIZE_M': 8, 'num_warps': 4, 'num_stages': 4}),
        triton.Config({'BLOCK_SIZE_M': 64, 'BLOCK_SIZE_N': 256, 'BLOCK_SIZE_K': 64, 'GROUP_SIZE_M': 8, 'num_warps': 4, 'num_stages': 4}),
        triton.Config({'BLOCK_SIZE_M': 128, 'BLOCK_SIZE_N': 64, 'BLOCK_SIZE_K': 64, 'GROUP_SIZE_M': 8, 'num_warps': 4, 'num_stages': 4}),
        triton.Config({'BLOCK_SIZE_M': 64, 'BLOCK_SIZE_N': 128, 'BLOCK_SIZE_K': 64, 'GROUP_SIZE_M': 8, 'num_warps': 4, 'num_stages': 4}),
        triton.Config({'BLOCK_SIZE_M': 128, 'BLOCK_SIZE_N': 256, 'BLOCK_SIZE_K': 32, 'GROUP_SIZE_M': 8, 'num_warps': 8, 'num_stages': 4}),
        triton.Config({'BLOCK_SIZE_M': 256, 'BLOCK_SIZE_N': 128, 'BLOCK_SIZE_K': 32, 'GROUP_SIZE_M': 8, 'num_warps': 8, 'num_stages': 4}),
        triton.Config({'BLOCK_SIZE_M': 128, 'BLOCK_SIZE_N': 128, 'BLOCK_SIZE_K': 32, 'GROUP_SIZE_M': 8, 'num_warps': 4, 'num_stages': 2}),
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
    """
    Triton kernel for fused Linear + Bias + GELU.
    """
    pid = tl.program_id(axis=0)
    num_pid_n = tl.cdiv(N, BLOCK_SIZE_N)
    num_pids_in_group = GROUP_SIZE_M * num_pid_n
    group_id = pid // num_pids_in_group
    first_pid_m = group_id * GROUP_SIZE_M
    group_size = min(tl.cdiv(M, BLOCK_SIZE_M) - first_pid_m, GROUP_SIZE_M)
    pid_m = first_pid_m + (pid % group_size)
    pid_n = (pid % num_pids_in_group) // group_size

    offs_am = (pid_m * BLOCK_SIZE_M + tl.arange(0, BLOCK_SIZE_M))
    offs_bn = (pid_n * BLOCK_SIZE_N + tl.arange(0, BLOCK_SIZE_N))
    offs_k = tl.arange(0, BLOCK_SIZE_K)
    x_ptrs = X + (offs_am[:, None] * stride_xm + offs_k[None, :] * stride_xk)
    w_ptrs = W + (offs_k[:, None] * stride_wk + offs_bn[None, :] * stride_wn)

    accumulator = tl.zeros((BLOCK_SIZE_M, BLOCK_SIZE_N), dtype=tl.float32)
    
    for k in range(0, K, BLOCK_SIZE_K):
        a = tl.load(x_ptrs, mask=offs_am[:, None] < M, other=0.0)
        b = tl.load(w_ptrs, mask=offs_bn[None, :] < N, other=0.0)
        accumulator += tl.dot(a, b, allow_tf32=True)
        x_ptrs += BLOCK_SIZE_K * stride_xk
        w_ptrs += BLOCK_SIZE_K * stride_wk
    
    bias_ptrs = B + offs_bn
    bias = tl.load(bias_ptrs, mask=offs_bn < N, other=0.0)
    accumulator += bias[None, :]

    inv_sqrt2 = 0.7071067811865476
    result = accumulator * 0.5 * (1.0 + tl.extra.cuda.libdevice.erf(accumulator * inv_sqrt2))
    
    offs_ym = pid_m * BLOCK_SIZE_M + tl.arange(0, BLOCK_SIZE_M)
    offs_yn = pid_n * BLOCK_SIZE_N + tl.arange(0, BLOCK_SIZE_N)
    y_ptrs = Y + offs_ym[:, None] * stride_ym + offs_yn[None, :] * stride_yn
    y_mask = (offs_ym[:, None] < M) & (offs_yn[None, :] < N)
    tl.store(y_ptrs, result.to(tl.float16), mask=y_mask)

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
    M, K = X.shape
    _, N = W.shape
    
    Y = torch.empty((M, N), device=X.device, dtype=torch.float16)
    
    grid = lambda META: (triton.cdiv(M, META['BLOCK_SIZE_M']) * triton.cdiv(N, META['BLOCK_SIZE_N']),)

    _linear_gelu_kernel[grid](
        X, W, B, Y,
        M, N, K,
        X.stride(0), X.stride(1),
        W.stride(0), W.stride(1),
        Y.stride(0), Y.stride(1),
    )
    return Y

class Solution:
    def solve(self, spec_path: str = None) -> dict:
        """
        Returns a dict with either:
        - {"code": "python_code_string"}
        - {"program_path": "path/to/kernel.py"}
        """
        # Get the source code of the kernel and its launcher
        kernel_source = inspect.getsource(_linear_gelu_kernel)
        launcher_source = inspect.getsource(linear_gelu)

        # The full code string to be returned
        code_string = f"""
import torch
import triton
import triton.language as tl

{kernel_source}

{launcher_source}
"""
        return {"code": code_string}
