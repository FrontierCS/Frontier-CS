import torch
import triton
import triton.language as tl


@triton.jit
def _chunk_scan_kernel(X_ptr, A_ptr, B_ptr, Y_ptr, init_state_ptr,
                       L, D,
                       chunk_start, chunk_size,
                       stride_x_l, stride_x_d,
                       stride_a_l, stride_a_d,
                       stride_b_l, stride_b_d,
                       stride_y_l, stride_y_d,
                       BLOCK_D: tl.constexpr):
    pid_d = tl.program_id(0)
    d_offsets = pid_d * BLOCK_D + tl.arange(0, BLOCK_D)
    mask_d = d_offsets < D

    y_prev = tl.load(init_state_ptr + d_offsets, mask=mask_d, other=0.0).to(tl.float32)

    t = 0
    while t < chunk_size:
        l_index = chunk_start + t
        offs_x = l_index * stride_x_l + d_offsets * stride_x_d
        offs_a = l_index * stride_a_l + d_offsets * stride_a_d
        offs_b = l_index * stride_b_l + d_offsets * stride_b_d

        x = tl.load(X_ptr + offs_x, mask=mask_d, other=0.0).to(tl.float32)
        a = tl.load(A_ptr + offs_a, mask=mask_d, other=0.0).to(tl.float32)
        b = tl.load(B_ptr + offs_b, mask=mask_d, other=0.0).to(tl.float32)

        y = a * y_prev + b * x

        offs_y = l_index * stride_y_l + d_offsets * stride_y_d
        tl.store(Y_ptr + offs_y, y.to(tl.float16), mask=mask_d)

        y_prev = y
        t += 1


def chunk_scan(X: torch.Tensor, A: torch.Tensor, B: torch.Tensor, chunk: int = 128, BD: int = 128) -> torch.Tensor:
    """
    Mamba2 chunked scan computation.
    """
    assert X.is_cuda and A.is_cuda and B.is_cuda
    assert X.dtype == torch.float16 and A.dtype == torch.float16 and B.dtype == torch.float16
    assert X.shape == A.shape == B.shape

    L, D = X.shape
    assert L % chunk == 0

    Y = torch.empty_like(X)

    BLOCK_D = BD
    grid = lambda meta: (triton.cdiv(D, meta["BLOCK_D"]),)

    init_state = torch.zeros(D, device=X.device, dtype=torch.float16)

    stride_x_l, stride_x_d = X.stride()
    stride_a_l, stride_a_d = A.stride()
    stride_b_l, stride_b_d = B.stride()
    stride_y_l, stride_y_d = Y.stride()

    for chunk_start in range(0, L, chunk):
        _chunk_scan_kernel[grid](
            X, A, B, Y, init_state,
            L, D,
            chunk_start, chunk,
            stride_x_l, stride_x_d,
            stride_a_l, stride_a_d,
            stride_b_l, stride_b_d,
            stride_y_l, stride_y_d,
            BLOCK_D=BLOCK_D,
            num_warps=4,
        )
        init_state = Y[chunk_start + chunk - 1]

    return Y


class Solution:
    def solve(self, spec_path: str = None) -> dict:
        code = '''import torch
import triton
import triton.language as tl


@triton.jit
def _chunk_scan_kernel(X_ptr, A_ptr, B_ptr, Y_ptr, init_state_ptr,
                       L, D,
                       chunk_start, chunk_size,
                       stride_x_l, stride_x_d,
                       stride_a_l, stride_a_d,
                       stride_b_l, stride_b_d,
                       stride_y_l, stride_y_d,
                       BLOCK_D: tl.constexpr):
    pid_d = tl.program_id(0)
    d_offsets = pid_d * BLOCK_D + tl.arange(0, BLOCK_D)
    mask_d = d_offsets < D

    y_prev = tl.load(init_state_ptr + d_offsets, mask=mask_d, other=0.0).to(tl.float32)

    t = 0
    while t < chunk_size:
        l_index = chunk_start + t
        offs_x = l_index * stride_x_l + d_offsets * stride_x_d
        offs_a = l_index * stride_a_l + d_offsets * stride_a_d
        offs_b = l_index * stride_b_l + d_offsets * stride_b_d

        x = tl.load(X_ptr + offs_x, mask=mask_d, other=0.0).to(tl.float32)
        a = tl.load(A_ptr + offs_a, mask=mask_d, other=0.0).to(tl.float32)
        b = tl.load(B_ptr + offs_b, mask=mask_d, other=0.0).to(tl.float32)

        y = a * y_prev + b * x

        offs_y = l_index * stride_y_l + d_offsets * stride_y_d
        tl.store(Y_ptr + offs_y, y.to(tl.float16), mask=mask_d)

        y_prev = y
        t += 1


def chunk_scan(X: torch.Tensor, A: torch.Tensor, B: torch.Tensor, chunk: int = 128, BD: int = 128) -> torch.Tensor:
    """
    Mamba2 chunked scan computation.
    """
    assert X.is_cuda and A.is_cuda and B.is_cuda
    assert X.dtype == torch.float16 and A.dtype == torch.float16 and B.dtype == torch.float16
    assert X.shape == A.shape == B.shape

    L, D = X.shape
    assert L % chunk == 0

    Y = torch.empty_like(X)

    BLOCK_D = BD
    grid = lambda meta: (triton.cdiv(D, meta["BLOCK_D"]),)

    init_state = torch.zeros(D, device=X.device, dtype=torch.float16)

    stride_x_l, stride_x_d = X.stride()
    stride_a_l, stride_a_d = A.stride()
    stride_b_l, stride_b_d = B.stride()
    stride_y_l, stride_y_d = Y.stride()

    for chunk_start in range(0, L, chunk):
        _chunk_scan_kernel[grid](
            X, A, B, Y, init_state,
            L, D,
            chunk_start, chunk,
            stride_x_l, stride_x_d,
            stride_a_l, stride_a_d,
            stride_b_l, stride_b_d,
            stride_y_l, stride_y_d,
            BLOCK_D=BLOCK_D,
            num_warps=4,
        )
        init_state = Y[chunk_start + chunk - 1]

    return Y
'''
        return {"code": code}