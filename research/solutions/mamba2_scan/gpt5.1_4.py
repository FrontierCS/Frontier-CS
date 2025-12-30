import torch
import triton
import triton.language as tl


KERNEL_CODE = """
import torch
import triton
import triton.language as tl


@triton.jit
def _mamba2_scan_kernel(
    X_ptr, A_ptr, B_ptr, Y_ptr,
    L, D,
    stride_x_l, stride_x_d,
    stride_a_l, stride_a_d,
    stride_b_l, stride_b_d,
    stride_y_l, stride_y_d,
    BD: tl.constexpr,
):
    pid = tl.program_id(0)
    d_offsets = pid * BD + tl.arange(0, BD)
    mask_d = d_offsets < D

    y_prev = tl.zeros([BD], dtype=tl.float32)

    for l in range(0, L):
        x_ptrs = X_ptr + l * stride_x_l + d_offsets * stride_x_d
        a_ptrs = A_ptr + l * stride_a_l + d_offsets * stride_a_d
        b_ptrs = B_ptr + l * stride_b_l + d_offsets * stride_b_d
        y_ptrs = Y_ptr + l * stride_y_l + d_offsets * stride_y_d

        x = tl.load(x_ptrs, mask=mask_d, other=0.0).to(tl.float32)
        a = tl.load(a_ptrs, mask=mask_d, other=0.0).to(tl.float32)
        b = tl.load(b_ptrs, mask=mask_d, other=0.0).to(tl.float32)

        y = a * y_prev + b * x
        tl.store(y_ptrs, y.to(tl.float16), mask=mask_d)
        y_prev = y


def chunk_scan(X: torch.Tensor, A: torch.Tensor, B: torch.Tensor, chunk: int = 128, BD: int = 128) -> torch.Tensor:
    \"""
    Mamba2 chunked scan computation.

    Args:
        X: Input tensor of shape (L, D) - input sequence (float16)
        A: Input tensor of shape (L, D) - decay factors (float16)
        B: Input tensor of shape (L, D) - input weights (float16)
        chunk: Chunk size for parallel processing (unused, kept for API compatibility)
        BD: Block dimension for feature dimension tiling (default 128)

    Returns:
        Output tensor of shape (L, D) - scan output (float16)
    \"""
    if X.dtype != torch.float16 or A.dtype != torch.float16 or B.dtype != torch.float16:
        raise TypeError("X, A, B must be float16 tensors")
    if not X.is_cuda or not A.is_cuda or not B.is_cuda:
        raise TypeError("X, A, B must be CUDA tensors")
    if X.shape != A.shape or X.shape != B.shape:
        raise ValueError("X, A, B must have the same shape")

    L, D = X.shape
    Y = torch.empty_like(X)

    grid = (triton.cdiv(D, BD),)

    _mamba2_scan_kernel[grid](
        X, A, B, Y,
        L, D,
        X.stride(0), X.stride(1),
        A.stride(0), A.stride(1),
        B.stride(0), B.stride(1),
        Y.stride(0), Y.stride(1),
        BD=BD,
        num_warps=4,
        num_stages=2,
    )
    return Y
"""

# Execute the kernel code in this module's global namespace
exec(KERNEL_CODE, globals())


class Solution:
    def solve(self, spec_path: str = None) -> dict:
        return {"code": KERNEL_CODE}