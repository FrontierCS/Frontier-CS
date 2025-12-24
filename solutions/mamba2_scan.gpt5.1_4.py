import os
import torch
import triton
import triton.language as tl


@triton.jit
def _scan_chunk_kernel(
    X_ptr,
    A_ptr,
    B_ptr,
    Y_ptr,
    State_ptr,
    L,
    D,
    CHUNK_IDX,
    stride_x_l,
    stride_x_d,
    stride_a_l,
    stride_a_d,
    stride_b_l,
    stride_b_d,
    stride_y_l,
    stride_y_d,
    stride_state_c,
    stride_state_d,
    CHUNK_SIZE: tl.constexpr,
    BD: tl.constexpr,
):
    pid = tl.program_id(0)
    offs_d = pid * BD + tl.arange(0, BD)
    mask_d = offs_d < D

    start_t = CHUNK_IDX * CHUNK_SIZE

    x_ptrs = X_ptr + start_t * stride_x_l + offs_d * stride_x_d
    a_ptrs = A_ptr + start_t * stride_a_l + offs_d * stride_a_d
    b_ptrs = B_ptr + start_t * stride_b_l + offs_d * stride_b_d
    y_ptrs = Y_ptr + start_t * stride_y_l + offs_d * stride_y_d

    state_in_ptrs = State_ptr + CHUNK_IDX * stride_state_c + offs_d * stride_state_d
    y_prev = tl.load(state_in_ptrs, mask=mask_d, other=0.0).to(tl.float32)

    for t in range(CHUNK_SIZE):
        idx_l = start_t + t
        active = mask_d & (idx_l < L)

        a_val = tl.load(a_ptrs, mask=active, other=0.0).to(tl.float32)
        b_val = tl.load(b_ptrs, mask=active, other=0.0).to(tl.float32)
        x_val = tl.load(x_ptrs, mask=active, other=0.0).to(tl.float32)

        y_val = a_val * y_prev + b_val * x_val

        tl.store(y_ptrs, y_val.to(tl.float16), mask=active)

        a_ptrs += stride_a_l
        b_ptrs += stride_b_l
        x_ptrs += stride_x_l
        y_ptrs += stride_y_l

        y_prev = tl.where(active, y_val, y_prev)

    state_out_ptrs = State_ptr + (CHUNK_IDX + 1) * stride_state_c + offs_d * stride_state_d
    tl.store(state_out_ptrs, y_prev.to(tl.float16), mask=mask_d)


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
    assert X.is_cuda and A.is_cuda and B.is_cuda, "Inputs must be CUDA tensors"
    assert X.shape == A.shape == B.shape, "X, A, B must have the same shape"
    assert X.dtype == A.dtype == B.dtype, "X, A, B must have the same dtype"

    L, D = X.shape
    assert L % chunk == 0, "Sequence length L must be divisible by chunk size"

    Y = torch.empty_like(X)

    num_chunks = L // chunk
    state = torch.zeros((num_chunks + 1, D), dtype=X.dtype, device=X.device)

    stride_x_l, stride_x_d = X.stride()
    stride_a_l, stride_a_d = A.stride()
    stride_b_l, stride_b_d = B.stride()
    stride_y_l, stride_y_d = Y.stride()
    stride_state_c, stride_state_d = state.stride()

    grid = (triton.cdiv(D, BD),)

    for chunk_idx in range(num_chunks):
        _scan_chunk_kernel[grid](
            X,
            A,
            B,
            Y,
            state,
            L,
            D,
            chunk_idx,
            stride_x_l,
            stride_x_d,
            stride_a_l,
            stride_a_d,
            stride_b_l,
            stride_b_d,
            stride_y_l,
            stride_y_d,
            stride_state_c,
            stride_state_d,
            CHUNK_SIZE=chunk,
            BD=BD,
            num_warps=4,
            num_stages=2,
        )

    return Y


class Solution:
    def solve(self, spec_path: str = None) -> dict:
        return {"program_path": os.path.abspath(__file__)}
