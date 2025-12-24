import torch
import triton
import triton.language as tl


@triton.jit
def _kernel_scan_zero(
    X_ptr, A_ptr, B_ptr, Y_ptr,
    Aprod_ptr, Bend_ptr,
    L, D,
    stride_x_row, stride_x_col,
    stride_a_row, stride_a_col,
    stride_b_row, stride_b_col,
    stride_y_row, stride_y_col,
    stride_ap_row, stride_ap_col,
    stride_be_row, stride_be_col,
    CHUNK: tl.constexpr,
    BD: tl.constexpr,
):
    chunk_id = tl.program_id(0)
    dblock = tl.program_id(1)

    d_offsets = dblock * BD + tl.arange(0, BD)
    mask_d = d_offsets < D

    base_row = chunk_id * CHUNK

    y = tl.zeros([BD], dtype=tl.float32)
    prod = tl.ones([BD], dtype=tl.float32)

    for i in tl.static_range(0, CHUNK):
        row = base_row + i

        a_ptrs = A_ptr + row * stride_a_row + d_offsets * stride_a_col
        b_ptrs = B_ptr + row * stride_b_row + d_offsets * stride_b_col
        x_ptrs = X_ptr + row * stride_x_row + d_offsets * stride_x_col
        y_ptrs = Y_ptr + row * stride_y_row + d_offsets * stride_y_col

        a = tl.load(a_ptrs, mask=mask_d, other=1.0).to(tl.float32)
        b = tl.load(b_ptrs, mask=mask_d, other=0.0).to(tl.float32)
        x = tl.load(x_ptrs, mask=mask_d, other=0.0).to(tl.float32)

        u = b * x
        y = a * y + u
        prod = prod * a

        tl.store(y_ptrs, y.to(tl.float16), mask=mask_d)

    ap_ptrs = Aprod_ptr + chunk_id * stride_ap_row + d_offsets * stride_ap_col
    be_ptrs = Bend_ptr + chunk_id * stride_be_row + d_offsets * stride_be_col

    tl.store(ap_ptrs, prod, mask=mask_d)
    tl.store(be_ptrs, y, mask=mask_d)


@triton.jit
def _kernel_compute_yin(
    Aprod_ptr, Bend_ptr, Yin_ptr,
    D,
    stride_ap_row, stride_ap_col,
    stride_be_row, stride_be_col,
    stride_yi_row, stride_yi_col,
    NCHUNK: tl.constexpr,
    BD: tl.constexpr,
):
    dblock = tl.program_id(0)
    d_offsets = dblock * BD + tl.arange(0, BD)
    mask_d = d_offsets < D

    yin = tl.zeros([BD], dtype=tl.float32)

    for c in tl.static_range(0, NCHUNK):
        yi_ptrs = Yin_ptr + c * stride_yi_row + d_offsets * stride_yi_col
        tl.store(yi_ptrs, yin, mask=mask_d)

        ap_ptrs = Aprod_ptr + c * stride_ap_row + d_offsets * stride_ap_col
        be_ptrs = Bend_ptr + c * stride_be_row + d_offsets * stride_be_col

        aprod = tl.load(ap_ptrs, mask=mask_d, other=1.0).to(tl.float32)
        bend = tl.load(be_ptrs, mask=mask_d, other=0.0).to(tl.float32)

        yend = aprod * yin + bend
        yin = yend


@triton.jit
def _kernel_apply_state(
    A_ptr, Yin_ptr, Y_ptr,
    D,
    stride_a_row, stride_a_col,
    stride_yi_row, stride_yi_col,
    stride_y_row, stride_y_col,
    CHUNK: tl.constexpr,
    BD: tl.constexpr,
):
    chunk_id = tl.program_id(0)
    dblock = tl.program_id(1)

    d_offsets = dblock * BD + tl.arange(0, BD)
    mask_d = d_offsets < D

    base_row = chunk_id * CHUNK

    yin_ptrs = Yin_ptr + chunk_id * stride_yi_row + d_offsets * stride_yi_col
    yin = tl.load(yin_ptrs, mask=mask_d, other=0.0).to(tl.float32)

    p = tl.ones([BD], dtype=tl.float32)

    for i in tl.static_range(0, CHUNK):
        row = base_row + i

        a_ptrs = A_ptr + row * stride_a_row + d_offsets * stride_a_col
        y_ptrs = Y_ptr + row * stride_y_row + d_offsets * stride_y_col

        a = tl.load(a_ptrs, mask=mask_d, other=1.0).to(tl.float32)
        p = p * a

        corr = p * yin
        y_cur = tl.load(y_ptrs, mask=mask_d, other=0.0).to(tl.float32)
        y_new = y_cur + corr
        tl.store(y_ptrs, y_new.to(tl.float16), mask=mask_d)


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
    assert X.shape == A.shape == B.shape, "X, A, B must have the same shape"
    L, D = X.shape
    assert L % chunk == 0, "L must be divisible by chunk"
    device = X.device

    if not X.is_cuda or not A.is_cuda or not B.is_cuda:
        # Fallback CPU/GPU PyTorch implementation
        y = torch.zeros(D, dtype=torch.float32, device=device)
        Y = torch.empty_like(X, dtype=torch.float16)
        for t in range(L):
            y = A[t].to(torch.float32) * y + (B[t].to(torch.float32) * X[t].to(torch.float32))
            Y[t] = y.to(torch.float16)
        return Y

    n_chunks = L // chunk
    n_dblocks = triton.cdiv(D, BD)

    Y = torch.empty_like(X, dtype=torch.float16)

    # Chunk-level accumulated product of A and end-state with zero init
    Aprod = torch.empty((n_chunks, D), dtype=torch.float32, device=device)
    Bend = torch.empty((n_chunks, D), dtype=torch.float32, device=device)
    Yin = torch.empty((n_chunks, D), dtype=torch.float32, device=device)

    grid_zero = (n_chunks, n_dblocks)
    _kernel_scan_zero[grid_zero](
        X, A, B, Y,
        Aprod, Bend,
        L, D,
        X.stride(0), X.stride(1),
        A.stride(0), A.stride(1),
        B.stride(0), B.stride(1),
        Y.stride(0), Y.stride(1),
        Aprod.stride(0), Aprod.stride(1),
        Bend.stride(0), Bend.stride(1),
        CHUNK=chunk, BD=BD, num_warps=4, num_stages=2
    )

    grid_yin = (n_dblocks,)
    _kernel_compute_yin[grid_yin](
        Aprod, Bend, Yin,
        D,
        Aprod.stride(0), Aprod.stride(1),
        Bend.stride(0), Bend.stride(1),
        Yin.stride(0), Yin.stride(1),
        NCHUNK=n_chunks, BD=BD, num_warps=4, num_stages=1
    )

    _kernel_apply_state[grid_zero](
        A, Yin, Y,
        D,
        A.stride(0), A.stride(1),
        Yin.stride(0), Yin.stride(1),
        Y.stride(0), Y.stride(1),
        CHUNK=chunk, BD=BD, num_warps=4, num_stages=2
    )

    return Y


class Solution:
    def solve(self, spec_path: str = None) -> dict:
        code = r'''
import torch
import triton
import triton.language as tl


@triton.jit
def _kernel_scan_zero(
    X_ptr, A_ptr, B_ptr, Y_ptr,
    Aprod_ptr, Bend_ptr,
    L, D,
    stride_x_row, stride_x_col,
    stride_a_row, stride_a_col,
    stride_b_row, stride_b_col,
    stride_y_row, stride_y_col,
    stride_ap_row, stride_ap_col,
    stride_be_row, stride_be_col,
    CHUNK: tl.constexpr,
    BD: tl.constexpr,
):
    chunk_id = tl.program_id(0)
    dblock = tl.program_id(1)

    d_offsets = dblock * BD + tl.arange(0, BD)
    mask_d = d_offsets < D

    base_row = chunk_id * CHUNK

    y = tl.zeros([BD], dtype=tl.float32)
    prod = tl.ones([BD], dtype=tl.float32)

    for i in tl.static_range(0, CHUNK):
        row = base_row + i

        a_ptrs = A_ptr + row * stride_a_row + d_offsets * stride_a_col
        b_ptrs = B_ptr + row * stride_b_row + d_offsets * stride_b_col
        x_ptrs = X_ptr + row * stride_x_row + d_offsets * stride_x_col
        y_ptrs = Y_ptr + row * stride_y_row + d_offsets * stride_y_col

        a = tl.load(a_ptrs, mask=mask_d, other=1.0).to(tl.float32)
        b = tl.load(b_ptrs, mask=mask_d, other=0.0).to(tl.float32)
        x = tl.load(x_ptrs, mask=mask_d, other=0.0).to(tl.float32)

        u = b * x
        y = a * y + u
        prod = prod * a

        tl.store(y_ptrs, y.to(tl.float16), mask=mask_d)

    ap_ptrs = Aprod_ptr + chunk_id * stride_ap_row + d_offsets * stride_ap_col
    be_ptrs = Bend_ptr + chunk_id * stride_be_row + d_offsets * stride_be_col

    tl.store(ap_ptrs, prod, mask=mask_d)
    tl.store(be_ptrs, y, mask=mask_d)


@triton.jit
def _kernel_compute_yin(
    Aprod_ptr, Bend_ptr, Yin_ptr,
    D,
    stride_ap_row, stride_ap_col,
    stride_be_row, stride_be_col,
    stride_yi_row, stride_yi_col,
    NCHUNK: tl.constexpr,
    BD: tl.constexpr,
):
    dblock = tl.program_id(0)
    d_offsets = dblock * BD + tl.arange(0, BD)
    mask_d = d_offsets < D

    yin = tl.zeros([BD], dtype=tl.float32)

    for c in tl.static_range(0, NCHUNK):
        yi_ptrs = Yin_ptr + c * stride_yi_row + d_offsets * stride_yi_col
        tl.store(yi_ptrs, yin, mask=mask_d)

        ap_ptrs = Aprod_ptr + c * stride_ap_row + d_offsets * stride_ap_col
        be_ptrs = Bend_ptr + c * stride_be_row + d_offsets * stride_be_col

        aprod = tl.load(ap_ptrs, mask=mask_d, other=1.0).to(tl.float32)
        bend = tl.load(be_ptrs, mask=mask_d, other=0.0).to(tl.float32)

        yend = aprod * yin + bend
        yin = yend


@triton.jit
def _kernel_apply_state(
    A_ptr, Yin_ptr, Y_ptr,
    D,
    stride_a_row, stride_a_col,
    stride_yi_row, stride_yi_col,
    stride_y_row, stride_y_col,
    CHUNK: tl.constexpr,
    BD: tl.constexpr,
):
    chunk_id = tl.program_id(0)
    dblock = tl.program_id(1)

    d_offsets = dblock * BD + tl.arange(0, BD)
    mask_d = d_offsets < D

    base_row = chunk_id * CHUNK

    yin_ptrs = Yin_ptr + chunk_id * stride_yi_row + d_offsets * stride_yi_col
    yin = tl.load(yin_ptrs, mask=mask_d, other=0.0).to(tl.float32)

    p = tl.ones([BD], dtype=tl.float32)

    for i in tl.static_range(0, CHUNK):
        row = base_row + i

        a_ptrs = A_ptr + row * stride_a_row + d_offsets * stride_a_col
        y_ptrs = Y_ptr + row * stride_y_row + d_offsets * stride_y_col

        a = tl.load(a_ptrs, mask=mask_d, other=1.0).to(tl.float32)
        p = p * a

        corr = p * yin
        y_cur = tl.load(y_ptrs, mask=mask_d, other=0.0).to(tl.float32)
        y_new = y_cur + corr
        tl.store(y_ptrs, y_new.to(tl.float16), mask=mask_d)


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
    assert X.shape == A.shape == B.shape, "X, A, B must have the same shape"
    L, D = X.shape
    assert L % chunk == 0, "L must be divisible by chunk"
    device = X.device

    if not X.is_cuda or not A.is_cuda or not B.is_cuda:
        y = torch.zeros(D, dtype=torch.float32, device=device)
        Y = torch.empty_like(X, dtype=torch.float16)
        for t in range(L):
            y = A[t].to(torch.float32) * y + (B[t].to(torch.float32) * X[t].to(torch.float32))
            Y[t] = y.to(torch.float16)
        return Y

    n_chunks = L // chunk
    n_dblocks = triton.cdiv(D, BD)

    Y = torch.empty_like(X, dtype=torch.float16)

    Aprod = torch.empty((n_chunks, D), dtype=torch.float32, device=device)
    Bend = torch.empty((n_chunks, D), dtype=torch.float32, device=device)
    Yin = torch.empty((n_chunks, D), dtype=torch.float32, device=device)

    grid_zero = (n_chunks, n_dblocks)
    _kernel_scan_zero[grid_zero](
        X, A, B, Y,
        Aprod, Bend,
        L, D,
        X.stride(0), X.stride(1),
        A.stride(0), A.stride(1),
        B.stride(0), B.stride(1),
        Y.stride(0), Y.stride(1),
        Aprod.stride(0), Aprod.stride(1),
        Bend.stride(0), Bend.stride(1),
        CHUNK=chunk, BD=BD, num_warps=4, num_stages=2
    )

    grid_yin = (n_dblocks,)
    _kernel_compute_yin[grid_yin](
        Aprod, Bend, Yin,
        D,
        Aprod.stride(0), Aprod.stride(1),
        Bend.stride(0), Bend.stride(1),
        Yin.stride(0), Yin.stride(1),
        NCHUNK=n_chunks, BD=BD, num_warps=4, num_stages=1
    )

    _kernel_apply_state[grid_zero](
        A, Yin, Y,
        D,
        A.stride(0), A.stride(1),
        Yin.stride(0), Yin.stride(1),
        Y.stride(0), Y.stride(1),
        CHUNK=chunk, BD=BD, num_warps=4, num_stages=2
    )

    return Y
'''
        return {"code": code}
