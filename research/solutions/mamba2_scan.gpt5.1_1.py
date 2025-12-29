import os
import torch
import triton
import triton.language as tl


@triton.jit
def _scan_chunk_kernel(
    X_ptr, A_ptr, B_ptr, Y_ptr,
    stride_x_l, stride_x_d,
    stride_a_l, stride_a_d,
    stride_b_l, stride_b_d,
    stride_y_l, stride_y_d,
    D,
    chunk_start,
    init_row,
    CHUNK_SIZE: tl.constexpr,
    BLOCK_D: tl.constexpr,
):
    pid = tl.program_id(axis=0)
    offs_d = pid * BLOCK_D + tl.arange(0, BLOCK_D)
    mask_d = offs_d < D

    # Load initial state from previous timestep if available, else zeros
    y = tl.zeros([BLOCK_D], dtype=tl.float32)
    if init_row >= 0:
        init_ptrs = Y_ptr + init_row * stride_y_l + offs_d * stride_y_d
        y = tl.load(init_ptrs, mask=mask_d, other=0.0).to(tl.float32)

    # Base pointers for this chunk
    x_ptrs = X_ptr + chunk_start * stride_x_l + offs_d * stride_x_d
    a_ptrs = A_ptr + chunk_start * stride_a_l + offs_d * stride_a_d
    b_ptrs = B_ptr + chunk_start * stride_b_l + offs_d * stride_b_d
    y_ptrs = Y_ptr + chunk_start * stride_y_l + offs_d * stride_y_d

    # Sequential scan inside the chunk
    for _ in range(CHUNK_SIZE):
        x = tl.load(x_ptrs, mask=mask_d, other=0.0).to(tl.float32)
        a = tl.load(a_ptrs, mask=mask_d, other=0.0).to(tl.float32)
        b = tl.load(b_ptrs, mask=mask_d, other=0.0).to(tl.float32)

        y = a * y + b * x

        tl.store(y_ptrs, y.to(tl.float16), mask=mask_d)

        x_ptrs += stride_x_l
        a_ptrs += stride_a_l
        b_ptrs += stride_b_l
        y_ptrs += stride_y_l


def chunk_scan(X: torch.Tensor, A: torch.Tensor, B: torch.Tensor, chunk: int = 128, BD: int = 128) -> torch.Tensor:
    """
    Mamba2 chunked scan computation.

    y_t = a_t * y_{t-1} + b_t * x_t
    """
    assert X.device.type == "cuda", "X must be on CUDA device"
    assert A.device == X.device and B.device == X.device, "A and B must be on same device as X"
    assert X.dtype == torch.float16 and A.dtype == torch.float16 and B.dtype == torch.float16, "All inputs must be float16"
    assert X.shape == A.shape == B.shape, "X, A, B must have same shape"

    L, D = X.shape
    assert L % chunk == 0, "Sequence length L must be divisible by chunk size"

    # Ensure contiguous inputs for simple stride math
    if not X.is_contiguous():
        X = X.contiguous()
    if not A.is_contiguous():
        A = A.contiguous()
    if not B.is_contiguous():
        B = B.contiguous()

    Y = torch.empty_like(X)

    stride_x_l, stride_x_d = X.stride()
    stride_a_l, stride_a_d = A.stride()
    stride_b_l, stride_b_d = B.stride()
    stride_y_l, stride_y_d = Y.stride()

    BD = min(BD, D)
    if BD <= 32:
        num_warps = 2
    elif BD <= 64:
        num_warps = 4
    else:
        num_warps = 8

    grid = lambda meta: (triton.cdiv(D, meta["BLOCK_D"]),)

    n_chunks = L // chunk
    for chunk_idx in range(n_chunks):
        chunk_start = chunk_idx * chunk
        init_row = chunk_start - 1 if chunk_idx > 0 else -1

        _scan_chunk_kernel[grid](
            X, A, B, Y,
            stride_x_l, stride_x_d,
            stride_a_l, stride_a_d,
            stride_b_l, stride_b_d,
            stride_y_l, stride_y_d,
            D,
            chunk_start,
            init_row,
            CHUNK_SIZE=chunk,
            BLOCK_D=BD,
            num_warps=num_warps,
            num_stages=2,
        )

    return Y


class Solution:
    def solve(self, spec_path: str = None) -> dict:
        # Use this file as the program path so that `chunk_scan` is available.
        return {"program_path": os.path.abspath(__file__)}