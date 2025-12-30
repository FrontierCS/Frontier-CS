import math
import torch
import triton
import triton.language as tl


def _ceil_div(a, b):
    return (a + b - 1) // b


@triton.jit
def _kernel_chunk_summarize(
    X_ptr, A_ptr, B_ptr, M_ptr, C_ptr,
    stride_x0, stride_x1,
    stride_a0, stride_a1,
    stride_b0, stride_b1,
    stride_m0, stride_m1,
    stride_c0, stride_c1,
    D,
    CHUNK: tl.constexpr,
    BLOCK_D: tl.constexpr,
):
    pid_chunk = tl.program_id(0)
    pid_d = tl.program_id(1)

    offs_d = pid_d * BLOCK_D + tl.arange(0, BLOCK_D)
    mask_d = offs_d < D

    # Initialize accumulators in fp32
    y = tl.zeros([BLOCK_D], dtype=tl.float32)
    prodA = tl.ones([BLOCK_D], dtype=tl.float32)

    start_t = pid_chunk * CHUNK
    for s in tl.static_range(0, CHUNK):
        t = start_t + s
        a = tl.load(A_ptr + t * stride_a0 + offs_d * stride_a1, mask=mask_d, other=0).to(tl.float32)
        x = tl.load(X_ptr + t * stride_x0 + offs_d * stride_x1, mask=mask_d, other=0).to(tl.float32)
        b = tl.load(B_ptr + t * stride_b0 + offs_d * stride_b1, mask=mask_d, other=0).to(tl.float32)
        u = x * b
        y = a * y + u
        prodA = prodA * a

    tl.store(M_ptr + pid_chunk * stride_m0 + offs_d * stride_m1, prodA, mask=mask_d)
    tl.store(C_ptr + pid_chunk * stride_c0 + offs_d * stride_c1, y, mask=mask_d)


@triton.jit
def _kernel_chunk_prefix(
    M_ptr, C_ptr, INIT_ptr,
    stride_m0, stride_m1,
    stride_c0, stride_c1,
    stride_i0, stride_i1,
    D,
    NC: tl.constexpr,
    BLOCK_D: tl.constexpr,
):
    pid_d = tl.program_id(0)
    offs_d = pid_d * BLOCK_D + tl.arange(0, BLOCK_D)
    mask_d = offs_d < D

    state = tl.zeros([BLOCK_D], dtype=tl.float32)
    for k in tl.static_range(0, NC):
        # store initial state for chunk k
        tl.store(INIT_ptr + k * stride_i0 + offs_d * stride_i1, state, mask=mask_d)
        Mk = tl.load(M_ptr + k * stride_m0 + offs_d * stride_m1, mask=mask_d, other=1.0).to(tl.float32)
        Ck = tl.load(C_ptr + k * stride_c0 + offs_d * stride_c1, mask=mask_d, other=0.0).to(tl.float32)
        state = Mk * state + Ck


@triton.jit
def _kernel_chunk_compute(
    X_ptr, A_ptr, B_ptr, INIT_ptr, Y_ptr,
    stride_x0, stride_x1,
    stride_a0, stride_a1,
    stride_b0, stride_b1,
    stride_i0, stride_i1,
    stride_y0, stride_y1,
    D,
    CHUNK: tl.constexpr,
    BLOCK_D: tl.constexpr,
):
    pid_chunk = tl.program_id(0)
    pid_d = tl.program_id(1)

    offs_d = pid_d * BLOCK_D + tl.arange(0, BLOCK_D)
    mask_d = offs_d < D

    init = tl.load(INIT_ptr + pid_chunk * stride_i0 + offs_d * stride_i1, mask=mask_d, other=0.0).to(tl.float32)
    y = init

    start_t = pid_chunk * CHUNK
    for s in tl.static_range(0, CHUNK):
        t = start_t + s
        a = tl.load(A_ptr + t * stride_a0 + offs_d * stride_a1, mask=mask_d, other=0).to(tl.float32)
        x = tl.load(X_ptr + t * stride_x0 + offs_d * stride_x1, mask=mask_d, other=0).to(tl.float32)
        b = tl.load(B_ptr + t * stride_b0 + offs_d * stride_b1, mask=mask_d, other=0).to(tl.float32)
        u = x * b
        y = a * y + u
        tl.store(Y_ptr + t * stride_y0 + offs_d * stride_y1, y.to(tl.float16), mask=mask_d)


def chunk_scan(X: torch.Tensor, A: torch.Tensor, B: torch.Tensor, chunk: int = 128, BD: int = 128) -> torch.Tensor:
    """
    Mamba2 chunked scan computation.
    y_t = a_t * y_{t-1} + b_t * x_t
    """
    assert X.is_cuda and A.is_cuda and B.is_cuda, "Inputs must be on CUDA device"
    assert X.dtype == torch.float16 and A.dtype == torch.float16 and B.dtype == torch.float16, "Inputs must be float16"
    assert X.shape == A.shape == B.shape, "Shapes of X, A, B must match"
    L, D = X.shape
    assert L % chunk == 0, "L must be divisible by chunk"
    n_chunks = L // chunk

    # Allocate temporaries
    device = X.device
    M = torch.empty((n_chunks, D), dtype=torch.float32, device=device)
    C = torch.empty((n_chunks, D), dtype=torch.float32, device=device)
    INIT = torch.empty((n_chunks, D), dtype=torch.float32, device=device)
    Y = torch.empty((L, D), dtype=torch.float16, device=device)

    grid_chunks = (n_chunks, _ceil_div(D, BD))
    grid_d = (_ceil_div(D, BD),)

    # Heuristic for num_warps
    num_warps = 8 if BD >= 128 else 4

    # Summarize each chunk: compute M and C
    _kernel_chunk_summarize[grid_chunks](
        X, A, B, M, C,
        X.stride(0), X.stride(1),
        A.stride(0), A.stride(1),
        B.stride(0), B.stride(1),
        M.stride(0), M.stride(1),
        C.stride(0), C.stride(1),
        D,
        CHUNK=chunk,
        BLOCK_D=BD,
        num_warps=num_warps,
        num_stages=2,
    )

    # Prefix to get initial state per chunk
    _kernel_chunk_prefix[grid_d](
        M, C, INIT,
        M.stride(0), M.stride(1),
        C.stride(0), C.stride(1),
        INIT.stride(0), INIT.stride(1),
        D,
        NC=n_chunks,
        BLOCK_D=BD,
        num_warps=4 if BD <= 64 else 8,
        num_stages=1,
    )

    # Final compute: produce Y
    _kernel_chunk_compute[grid_chunks](
        X, A, B, INIT, Y,
        X.stride(0), X.stride(1),
        A.stride(0), A.stride(1),
        B.stride(0), B.stride(1),
        INIT.stride(0), INIT.stride(1),
        Y.stride(0), Y.stride(1),
        D,
        CHUNK=chunk,
        BLOCK_D=BD,
        num_warps=num_warps,
        num_stages=2,
    )

    return Y


class Solution:
    def solve(self, spec_path: str = None) -> dict:
        code = r'''
import math
import torch
import triton
import triton.language as tl


def _ceil_div(a, b):
    return (a + b - 1) // b


@triton.jit
def _kernel_chunk_summarize(
    X_ptr, A_ptr, B_ptr, M_ptr, C_ptr,
    stride_x0, stride_x1,
    stride_a0, stride_a1,
    stride_b0, stride_b1,
    stride_m0, stride_m1,
    stride_c0, stride_c1,
    D,
    CHUNK: tl.constexpr,
    BLOCK_D: tl.constexpr,
):
    pid_chunk = tl.program_id(0)
    pid_d = tl.program_id(1)

    offs_d = pid_d * BLOCK_D + tl.arange(0, BLOCK_D)
    mask_d = offs_d < D

    # Initialize accumulators in fp32
    y = tl.zeros([BLOCK_D], dtype=tl.float32)
    prodA = tl.ones([BLOCK_D], dtype=tl.float32)

    start_t = pid_chunk * CHUNK
    for s in tl.static_range(0, CHUNK):
        t = start_t + s
        a = tl.load(A_ptr + t * stride_a0 + offs_d * stride_a1, mask=mask_d, other=0).to(tl.float32)
        x = tl.load(X_ptr + t * stride_x0 + offs_d * stride_x1, mask=mask_d, other=0).to(tl.float32)
        b = tl.load(B_ptr + t * stride_b0 + offs_d * stride_b1, mask=mask_d, other=0).to(tl.float32)
        u = x * b
        y = a * y + u
        prodA = prodA * a

    tl.store(M_ptr + pid_chunk * stride_m0 + offs_d * stride_m1, prodA, mask=mask_d)
    tl.store(C_ptr + pid_chunk * stride_c0 + offs_d * stride_c1, y, mask=mask_d)


@triton.jit
def _kernel_chunk_prefix(
    M_ptr, C_ptr, INIT_ptr,
    stride_m0, stride_m1,
    stride_c0, stride_c1,
    stride_i0, stride_i1,
    D,
    NC: tl.constexpr,
    BLOCK_D: tl.constexpr,
):
    pid_d = tl.program_id(0)
    offs_d = pid_d * BLOCK_D + tl.arange(0, BLOCK_D)
    mask_d = offs_d < D

    state = tl.zeros([BLOCK_D], dtype=tl.float32)
    for k in tl.static_range(0, NC):
        # store initial state for chunk k
        tl.store(INIT_ptr + k * stride_i0 + offs_d * stride_i1, state, mask=mask_d)
        Mk = tl.load(M_ptr + k * stride_m0 + offs_d * stride_m1, mask=mask_d, other=1.0).to(tl.float32)
        Ck = tl.load(C_ptr + k * stride_c0 + offs_d * stride_c1, mask=mask_d, other=0.0).to(tl.float32)
        state = Mk * state + Ck


@triton.jit
def _kernel_chunk_compute(
    X_ptr, A_ptr, B_ptr, INIT_ptr, Y_ptr,
    stride_x0, stride_x1,
    stride_a0, stride_a1,
    stride_b0, stride_b1,
    stride_i0, stride_i1,
    stride_y0, stride_y1,
    D,
    CHUNK: tl.constexpr,
    BLOCK_D: tl.constexpr,
):
    pid_chunk = tl.program_id(0)
    pid_d = tl.program_id(1)

    offs_d = pid_d * BLOCK_D + tl.arange(0, BLOCK_D)
    mask_d = offs_d < D

    init = tl.load(INIT_ptr + pid_chunk * stride_i0 + offs_d * stride_i1, mask=mask_d, other=0.0).to(tl.float32)
    y = init

    start_t = pid_chunk * CHUNK
    for s in tl.static_range(0, CHUNK):
        t = start_t + s
        a = tl.load(A_ptr + t * stride_a0 + offs_d * stride_a1, mask=mask_d, other=0).to(tl.float32)
        x = tl.load(X_ptr + t * stride_x0 + offs_d * stride_x1, mask=mask_d, other=0).to(tl.float32)
        b = tl.load(B_ptr + t * stride_b0 + offs_d * stride_b1, mask=mask_d, other=0).to(tl.float32)
        u = x * b
        y = a * y + u
        tl.store(Y_ptr + t * stride_y0 + offs_d * stride_y1, y.to(tl.float16), mask=mask_d)


def chunk_scan(X: torch.Tensor, A: torch.Tensor, B: torch.Tensor, chunk: int = 128, BD: int = 128) -> torch.Tensor:
    """
    Mamba2 chunked scan computation.
    y_t = a_t * y_{t-1} + b_t * x_t
    """
    assert X.is_cuda and A.is_cuda and B.is_cuda, "Inputs must be on CUDA device"
    assert X.dtype == torch.float16 and A.dtype == torch.float16 and B.dtype == torch.float16, "Inputs must be float16"
    assert X.shape == A.shape == B.shape, "Shapes of X, A, B must match"
    L, D = X.shape
    assert L % chunk == 0, "L must be divisible by chunk"
    n_chunks = L // chunk

    # Allocate temporaries
    device = X.device
    M = torch.empty((n_chunks, D), dtype=torch.float32, device=device)
    C = torch.empty((n_chunks, D), dtype=torch.float32, device=device)
    INIT = torch.empty((n_chunks, D), dtype=torch.float32, device=device)
    Y = torch.empty((L, D), dtype=torch.float16, device=device)

    grid_chunks = (n_chunks, _ceil_div(D, BD))
    grid_d = (_ceil_div(D, BD),)

    # Heuristic for num_warps
    num_warps = 8 if BD >= 128 else 4

    # Summarize each chunk: compute M and C
    _kernel_chunk_summarize[grid_chunks](
        X, A, B, M, C,
        X.stride(0), X.stride(1),
        A.stride(0), A.stride(1),
        B.stride(0), B.stride(1),
        M.stride(0), M.stride(1),
        C.stride(0), C.stride(1),
        D,
        CHUNK=chunk,
        BLOCK_D=BD,
        num_warps=num_warps,
        num_stages=2,
    )

    # Prefix to get initial state per chunk
    _kernel_chunk_prefix[grid_d](
        M, C, INIT,
        M.stride(0), M.stride(1),
        C.stride(0), C.stride(1),
        INIT.stride(0), INIT.stride(1),
        D,
        NC=n_chunks,
        BLOCK_D=BD,
        num_warps=4 if BD <= 64 else 8,
        num_stages=1,
    )

    # Final compute: produce Y
    _kernel_chunk_compute[grid_chunks](
        X, A, B, INIT, Y,
        X.stride(0), X.stride(1),
        A.stride(0), A.stride(1),
        B.stride(0), B.stride(1),
        INIT.stride(0), INIT.stride(1),
        Y.stride(0), Y.stride(1),
        D,
        CHUNK=chunk,
        BLOCK_D=BD,
        num_warps=num_warps,
        num_stages=2,
    )

    return Y
'''
        return {"code": code}