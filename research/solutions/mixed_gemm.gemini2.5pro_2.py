import torch
import triton
import triton.language as tl

class Solution:
    def solve(self, spec_path: str = None) -> dict:
        """
        Returns a dict with either:
        - {"code": "python_code_string"}
        - {"program_path": "path/to/kernel.py"}
        """
        kernel_code = r"""
import torch
import triton
import triton.language as tl
from triton.language.extra.cuda.libdevice import erf


@triton.jit
def _linear_gelu_kernel(
    X, W, B, Z,
    stride_xm, stride_xk,
    stride_wk, stride_wn,
    stride_zm, stride_zn,
    M, N, K,
    BLOCK_SIZE_M: tl.constexpr,
    BLOCK_SIZE_N: tl.constexpr,
    BLOCK_SIZE_K: tl.constexpr,
):
    """
    Triton kernel for mixed-precision GEMM with bias and GELU activation.
    Computes Z = GELU(X @ W + B).
    - X is (M, K) float16
    - W is (K, N) float16
    - B is (N,)   float32
    - Z is (M, N) float16
    Accumulation and intermediate computations are done in float32.
    """
    # -----------------------------------------------------------
    # Map program ids `pid` to the block of Z it should compute.
    # This is done in a row-major ordering.
    pid_m = tl.program_id(axis=0)
    pid_n = tl.program_id(axis=1)

    # ----------------------------------------------------------
    # Create pointers for the first blocks of X and W.
    # We will advance these pointers as we move in the K direction
    # and accumulate.
    offs_m = pid_m * BLOCK_SIZE_M + tl.arange(0, BLOCK_SIZE_M)
    offs_n = pid_n * BLOCK_SIZE_N + tl.arange(0, BLOCK_SIZE_N)
    offs_k = tl.arange(0, BLOCK_SIZE_K)
    
    x_ptrs = X + (offs_m[:, None] * stride_xm + offs_k[None, :] * stride_xk)
    w_ptrs = W + (offs_k[:, None] * stride_wk + offs_n[None, :] * stride_wn)

    # -----------------------------------------------------------
    # Iterate to compute a block of the Z matrix.
    # We accumulate into a `[BLOCK_SIZE_M, BLOCK_SIZE_N]` block
    # of fp32 values for higher precision.
    accumulator = tl.zeros((BLOCK_SIZE_M, BLOCK_SIZE_N), dtype=tl.float32)
    for k in range(0, tl.cdiv(K, BLOCK_SIZE_K)):
        # Load the next block of X and W, guarding against out-of-bounds accesses.
        # These are fp16 values, which will be upcast to fp32 by tl.dot.
        mask_x = (offs_m[:, None] < M) & (offs_k[None, :] < K)
        mask_w = (offs_k[:, None] < K) & (offs_n[None, :] < N)
        x = tl.load(x_ptrs, mask=mask_x, other=0.0)
        w = tl.load(w_ptrs, mask=mask_w, other=0.0)
        
        # We accumulate along the K dimension.
        accumulator += tl.dot(x, w)
        
        # Advance the pointers to the next K block.
        x_ptrs += BLOCK_SIZE_K * stride_xk
        w_ptrs += BLOCK_SIZE_K * stride_wk

    # -----------------------------------------------------------
    # Add bias and apply GELU activation.
    
    # Load bias, which is a 1D vector of size N.
    b_ptrs = B + offs_n
    mask_b = offs_n < N
    bias = tl.load(b_ptrs, mask=mask_b, other=0.0)
    
    # Add bias to the accumulator. Bias is float32.
    # Triton handles the broadcasting of the bias vector.
    accumulator += bias

    # GELU activation: gelu(x) = x * 0.5 * (1.0 + erf(x / sqrt(2)))
    # 1/sqrt(2) = 0.7071067811865476
    gelu_in = accumulator.to(tl.float32)
    m_sqrt2 = 0.7071067811865476
    erf_in = gelu_in * m_sqrt2
    erf_val = erf(erf_in)
    gelu_out = gelu_in * 0.5 * (1.0 + erf_val)

    # Convert to output type (float16).
    output = gelu_out.to(tl.float16)

    # ----------------------------------------------------------
    # Write back the block of the output matrix.
    z_ptrs = Z + offs_m[:, None] * stride_zm + offs_n[None, :] * stride_zn
    mask_z = (offs_m[:, None] < M) & (offs_n[None, :] < N)
    tl.store(z_ptrs, output, mask=mask_z)

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
    # Check constraints.
    assert X.shape[1] == W.shape[0], "Incompatible dimensions"
    assert X.device.type == 'cuda' and W.device.type == 'cuda' and B.device.type == 'cuda'
    
    M, K = X.shape
    _, N = W.shape
    
    # Allocate output tensor.
    Z = torch.empty((M, N), device=X.device, dtype=torch.float16)

    # A single, well-tuned configuration for the given problem sizes.
    # These parameters are chosen to maximize occupancy and data reuse
    # on modern GPUs like the L4 for large matrix multiplications.
    BLOCK_SIZE_M = 128
    BLOCK_SIZE_N = 256
    BLOCK_SIZE_K = 64
    num_warps = 8
    num_stages = 3

    # Grid for launching the kernel.
    grid = (triton.cdiv(M, BLOCK_SIZE_M), triton.cdiv(N, BLOCK_SIZE_N))
    
    _linear_gelu_kernel[grid](
        X, W, B, Z,
        X.stride(0), X.stride(1),
        W.stride(0), W.stride(1),
        Z.stride(0), Z.stride(1),
        M, N, K,
        BLOCK_SIZE_M=BLOCK_SIZE_M,
        BLOCK_SIZE_N=BLOCK_SIZE_N,
        BLOCK_SIZE_K=BLOCK_SIZE_K,
        num_warps=num_warps,
        num_stages=num_stages
    )
    
    return Z
"""
        return {"code": kernel_code}
