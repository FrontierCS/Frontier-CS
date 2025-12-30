import torch
import triton
import triton.language as tl


class Solution:
    def solve(self, spec_path: str = None) -> dict:
        code = r'''
import torch
import triton
import triton.language as tl

@triton.jit
def _scan_chunk_kernel(
    X_ptr, A_ptr, B_ptr, Y_ptr, S_ptr,
    stride_x_l, stride_x_d,
    stride_a_l, stride_a_d,
    stride_b_l, stride_b_d,
    stride_y_l, stride_y_d,
    D,
    CHUNK: tl.constexpr,
    BD: tl.constexpr,
):
    pid_d = tl.program_id(axis=0)
    offs_d = pid_d * BD + tl.arange(0, BD)
    mask_d = offs_d < D

    # Load initial state for this D-tile
    s = tl.load(S_ptr + offs_d, mask=mask_d, other=0).to(tl.float32)

    x_base = X_ptr + offs_d * stride_x_d
    a_base = A_ptr + offs_d * stride_a_d
    b_base = B_ptr + offs_d * stride_b_d
    y_base = Y_ptr + offs_d * stride_y_d

    # Sequential scan within the chunk
    for t in range(0, CHUNK):
        a_t = tl.load(a_base + t * stride_a_l, mask=mask_d, other=0).to(tl.float32)
        b_t = tl.load(b_base + t * stride_b_l, mask=mask_d, other=0).to(tl.float32)
        x_t = tl.load(x_base + t * stride_x_l, mask=mask_d, other=0).to(tl.float32)
        s = a_t * s + b_t * x_t
        tl.store(y_base + t * stride_y_l, s.to(tl.float16), mask=mask_d)

    # Write final state for this D-tile back
    tl.store(S_ptr + offs_d, s.to(tl.float16), mask=mask_d)


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
    assert X.is_cuda and A.is_cuda and B.is_cuda, "All inputs must be CUDA tensors"
    assert X.dtype == torch.float16 and A.dtype == torch.float16 and B.dtype == torch.float16, "Inputs must be float16"
    assert X.ndim == 2 and A.ndim == 2 and B.ndim == 2, "Inputs must be 2D tensors"
    L, D = X.shape
    assert A.shape == (L, D) and B.shape == (L, D), "A and B must match X shape"
    assert chunk > 0 and (L % chunk == 0), "L must be divisible by chunk size"

    Y = torch.empty_like(X)

    # Persistent state across chunks per feature dimension
    state = torch.zeros(D, dtype=X.dtype, device=X.device)

    num_tiles_d = (D + BD - 1) // BD
    num_warps = 4 if BD <= 128 else 8

    for start in range(0, L, chunk):
        X_i = X[start:start + chunk]
        A_i = A[start:start + chunk]
        B_i = B[start:start + chunk]
        Y_i = Y[start:start + chunk]

        grid = (num_tiles_d,)
        _scan_chunk_kernel[grid](
            X_i, A_i, B_i, Y_i, state,
            X_i.stride(0), X_i.stride(1),
            A_i.stride(0), A_i.stride(1),
            B_i.stride(0), B_i.stride(1),
            Y_i.stride(0), Y_i.stride(1),
            D,
            CHUNK=chunk,
            BD=BD,
            num_warps=num_warps,
            num_stages=2,
        )
    return Y
'''
        return {"code": code}