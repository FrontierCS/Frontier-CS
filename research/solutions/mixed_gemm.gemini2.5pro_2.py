import torch
import triton
import triton.language as tl

# The `Solution` class is the required entry point.
# It provides the optimized Triton kernel code as a string.
class Solution:
    def solve(self, spec_path: str = None) -> dict:
        """
        Returns a dict with the Triton kernel code for the mixed GEMM problem.
        """
        kernel_code = """
import torch
import triton
import triton.language as tl

@triton.autotune(
    configs=[
        # A range of configurations to find the best performance on the target hardware (NVIDIA L4)
        # Larger block sizes for M and N are generally good for large matrices.
        triton.Config({'BLOCK_SIZE_M': 128, 'BLOCK_SIZE_N': 256, 'BLOCK_SIZE_K': 64, 'GROUP_SIZE_M': 8, 'num_stages': 4, 'num_warps': 8}),
        triton.Config({'BLOCK_SIZE_M': 256, 'BLOCK_SIZE_N': 128, 'BLOCK_SIZE_K': 64, 'GROUP_SIZE_M': 8, 'num_stages': 4, 'num_warps': 8}),
        triton.Config({'BLOCK_SIZE_M': 256, 'BLOCK_SIZE_N': 64,  'BLOCK_SIZE_K': 64, 'GROUP_SIZE_M': 8, 'num_stages': 4, 'num_warps': 4}),
        triton.Config({'BLOCK_SIZE_M': 64,  'BLOCK_SIZE_N': 256, 'BLOCK_SIZE_K': 64, 'GROUP_SIZE_M': 8, 'num_stages': 4, 'num_warps': 4}),
        triton.Config({'BLOCK_SIZE_M': 128, 'BLOCK_SIZE_N': 128, 'BLOCK_SIZE_K': 64, 'GROUP_SIZE_M': 8, 'num_stages': 4, 'num_warps': 4}),
        triton.Config({'BLOCK_SIZE_M': 128, 'BLOCK_SIZE_N': 64,  'BLOCK_SIZE_K': 64, 'GROUP_SIZE_M': 8, 'num_stages': 5, 'num_warps': 4}),
        triton.Config({'BLOCK_SIZE_M': 64,  'BLOCK_SIZE_N': 128, 'BLOCK_SIZE_K': 64, 'GROUP_SIZE_M': 8, 'num_stages': 5, 'num_warps': 4}),
        triton.Config({'BLOCK_SIZE_M': 128, 'BLOCK_SIZE_N': 32,  'BLOCK_SIZE_K': 64, 'GROUP_SIZE_M': 8, 'num_stages': 5, 'num_warps': 4}),
        # Configurations with different K block sizes
        triton.Config({'BLOCK_SIZE_M': 128, 'BLOCK_SIZE_N': 128, 'BLOCK_SIZE_K': 32, 'GROUP_SIZE_M': 8, 'num_stages': 4, 'num_warps': 4}),
        triton.Config({'BLOCK_SIZE_M': 64,  'BLOCK_SIZE_N': 64,  'BLOCK_SIZE_K': 128, 'GROUP_SIZE_M': 8, 'num_stages': 3, 'num_warps': 8}),
        # Configuration for potentially higher occupancy
        triton.Config({'BLOCK_SIZE_M': 64,  'BLOCK_SIZE_N': 128, 'BLOCK_SIZE_K': 32, 'GROUP_SIZE_M': 8, 'num_stages': 3, 'num_warps': 4}),
        # Large block size configuration
        triton.Config({'BLOCK_SIZE_M': 256, 'BLOCK_SIZE_N': 256, 'BLOCK_SIZE_K': 64, 'GROUP_SIZE_M': 8, 'num_stages': 3, 'num_warps': 8}),
    ],
    key=['M', 'N', 'K'],
)
@triton.jit
def _linear_gelu_kernel(
    X, W, B, Out,
    M, N, K,
    stride_xm, stride_xk,
    stride_wk, stride_wn,
    stride_outm, stride_outn,
    BLOCK_SIZE_M: tl.constexpr,
    BLOCK_SIZE_N: tl.constexpr,
    BLOCK_SIZE_K: tl.constexpr,
    GROUP_SIZE_M: tl.constexpr,
):
    """
    Triton kernel for Fused Linear + Bias + GELU.
    """
    # -----------------------------------------------------------
    # Map program ids `pid` to the block of C it computes.
    # This is done in a grouped ordering to promote L2 cache reuse.
    pid = tl.program_id(axis=0)
    num_pid_m = tl.cdiv(M, BLOCK_SIZE_M)
    num_pid_n = tl.cdiv(N, BLOCK_SIZE_N)
    num_pid_in_group = GROUP_SIZE_M * num_pid_n
    group_id = pid // num_pid_in_group
    first_pid_m = group_id * GROUP_SIZE_M
    group_size = min(num_pid_m - first_pid_m, GROUP_SIZE_M)
    pid_m = first_pid_m + (pid % group_size)
    pid_n = (pid % num_pid_in_group) // group_size

    # ----------------------------------------------------------
    # Create pointers for the first blocks of X and W.
    # We will advance this pointer as we move in the K direction
    # and accumulate matmuls.
    offs_am = (pid_m * BLOCK_SIZE_M + tl.arange(0, BLOCK_SIZE_M))
    offs_bn = (pid_n * BLOCK_SIZE_N + tl.arange(0, BLOCK_SIZE_N))
    
    # Initialize accumulator with zeros, using float32 for precision.
    accumulator = tl.zeros((BLOCK_SIZE_M, BLOCK_SIZE_N), dtype=tl.float32)

    # Main loop over the K dimension
    for k_base in range(0, K, BLOCK_SIZE_K):
        offs_k = k_base + tl.arange(0, BLOCK_SIZE_K)
        
        # Pointers to the current blocks in X and W
        x_ptrs = X + (offs_am[:, None] * stride_xm + offs_k[None, :] * stride_xk)
        w_ptrs = W + (offs_k[:, None] * stride_wk + offs_bn[None, :] * stride_wn)

        # Load blocks of X and W, applying masks for boundary conditions.
        x_mask = (offs_am[:, None] < M) & (offs_k[None, :] < K)
        w_mask = (offs_k[:, None] < K) & (offs_bn[None, :] < N)
        
        a = tl.load(x_ptrs, mask=x_mask, other=0.0)
        b = tl.load(w_ptrs, mask=w_mask, other=0.0)

        # Perform the matrix multiplication and accumulate the result.
        # tl.dot will use Tensor Cores for fp16 inputs.
        accumulator += tl.dot(a, b)

    # -----------------------------------------------------------
    # Fused operations: Bias addition and GELU activation
    
    # 1. Add bias vector B
    b_ptrs = B + offs_bn
    bias_mask = offs_bn < N
    # Load bias, convert to float32 to match accumulator type
    bias = tl.load(b_ptrs, mask=bias_mask, other=0.0).to(tl.float32)
    accumulator += bias[None, :]

    # 2. Apply GELU activation function
    # GELU(x) = 0.5 * x * (1 + erf(x / sqrt(2)))
    GELU_SCALAR_CONST = 0.7071067811865475  # 1/sqrt(2)
    erf_arg = accumulator * GELU_SCALAR_CONST
    # Use the CUDA libdevice erf function as specified
    erf_val = tl.extra.cuda.libdevice.erf(erf_arg)
    result = accumulator * 0.5 * (1.0 + erf_val)

    # Cast the final result to the output dtype (float16)
    result = result.to(Out.dtype.element_ty)
    
    # -----------------------------------------------------------
    # Write the result block to the output tensor.
    offs_outm = pid_m * BLOCK_SIZE_M + tl.arange(0, BLOCK_SIZE_M)
    offs_outn = pid_n * BLOCK_SIZE_N + tl.arange(0, BLOCK_SIZE_N)
    
    out_ptrs = Out + (offs_outm[:, None] * stride_outm + offs_outn[None, :] * stride_outn)
    output_mask = (offs_outm[:, None] < M) & (offs_outn[None, :] < N)
    tl.store(out_ptrs, result, mask=output_mask)


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
    # Basic input validation
    assert X.is_cuda and W.is_cuda and B.is_cuda, "Input tensors must be on a CUDA device."
    assert X.dtype == torch.float16, "Input tensor X must be of type float16."
    assert W.dtype == torch.float16, "Weight tensor W must be of type float16."
    assert B.dtype == torch.float32, "Bias tensor B must be of type float32."
    assert X.shape[1] == W.shape[0], "Incompatible dimensions for matrix multiplication."
    assert B.shape[0] == W.shape[1], "Bias shape must match weight's output dimension."

    M, K = X.shape
    _, N = W.shape

    # Allocate the output tensor
    Out = torch.empty((M, N), device=X.device, dtype=torch.float16)

    # Grid for launching the kernel
    # The grid is 1D, and the kernel maps the program ID to 2D block coordinates
    grid = lambda META: (
        triton.cdiv(M, META['BLOCK_SIZE_M']) * triton.cdiv(N, META['BLOCK_SIZE_N']),
    )

    # Launch the Triton kernel
    _linear_gelu_kernel[grid](
        X, W, B, Out,
        M, N, K,
        X.stride(0), X.stride(1),
        W.stride(0), W.stride(1),
        Out.stride(0), Out.stride(1),
    )

    return Out
"""
        return {"code": kernel_code}