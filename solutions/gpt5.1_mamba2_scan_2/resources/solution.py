import os
import torch
import triton
import triton.language as tl


@triton.jit
def mamba2_scan_kernel(
    X_ptr, A_ptr, B_ptr, Y_ptr,
    stride_x_l, stride_x_d,
    stride_a_l, stride_a_d,
    stride_b_l, stride_b_d,
    stride_y_l, stride_y_d,
    L: tl.constexpr, D: tl.constexpr,
    BLOCK_D: tl.constexpr,
):
    pid = tl.program_id(axis=0)
    offs_d = pid * BLOCK_D + tl.arange(0, BLOCK_D)
    mask_d = offs_d < D

    y_prev = tl.zeros([BLOCK_D], dtype=tl.float32)

    for l in range(0, L):
        x_ptrs = X_ptr + l * stride_x_l + offs_d * stride_x_d
        a_ptrs = A_ptr + l * stride_a_l + offs_d * stride_a_d
        b_ptrs = B_ptr + l * stride_b_l + offs_d * stride_b_d
        y_ptrs = Y_ptr + l * stride_y_l + offs_d * stride_y_d

        x = tl.load(x_ptrs, mask=mask_d, other=0.0)
        a = tl.load(a_ptrs, mask=mask_d, other=0.0)
        b = tl.load(b_ptrs, mask=mask_d, other=0.0)

        x_f = x.to(tl.float32)
        a_f = a.to(tl.float32)
        b_f = b.to(tl.float32)

        y_prev = a_f * y_prev + b_f * x_f
        tl.store(y_ptrs, y_prev.to(tl.float16), mask=mask_d)


def chunk_scan(X: torch.Tensor, A: torch.Tensor, B: torch.Tensor, chunk: int = 128, BD: int = 128) -> torch.Tensor:
    """
    Mamba2 chunked scan computation.
    
    Args:
        X: Input tensor of shape (L, D) - input sequence (float16)
        A: Input tensor of shape (L, D) - decay factors (float16)
        B: Input tensor of shape (L, D) - input weights (float16)
        chunk: Chunk size for parallel processing (default 128)
        BD: Block dimension for feature dimension tiling (default 128)
    
    Returns:
        Output tensor of shape (L, D) - scan output (float16)
    """
    assert X.device.type == "cuda", "X must be on CUDA"
    assert A.device.type == "cuda" and B.device.type == "cuda", "A and B must be on CUDA"
    assert X.dtype == torch.float16 and A.dtype == torch.float16 and B.dtype == torch.float16, "Inputs must be float16"
    assert X.shape == A.shape == B.shape, "X, A, B must have the same shape"
    L, D = X.shape
    assert L % chunk == 0, "L must be divisible by chunk"

    Y = torch.empty_like(X)

    BLOCK_D = min(BD, D)
    grid = (triton.cdiv(D, BLOCK_D),)

    mamba2_scan_kernel[grid](
        X, A, B, Y,
        X.stride(0), X.stride(1),
        A.stride(0), A.stride(1),
        B.stride(0), B.stride(1),
        Y.stride(0), Y.stride(1),
        L=L, D=D, BLOCK_D=BLOCK_D,
        num_warps=4,
        num_stages=2,
    )

    return Y


class Solution:
    def solve(self, spec_path: str = None) -> dict:
        return {"program_path": os.path.abspath(__file__)}
