import torch
import triton
import triton.language as tl


@triton.jit
def chunk_summary_kernel(
    X_ptr, A_ptr, B_ptr,
    A_chunk_ptr, B_chunk_ptr,
    L, D,
    stride_x_l, stride_x_d,
    stride_a_l, stride_a_d,
    stride_b_l, stride_b_d,
    stride_ach_l, stride_ach_d,
    stride_bch_l, stride_bch_d,
    CHUNK: tl.constexpr,
    BD: tl.constexpr,
):
    chunk_id = tl.program_id(0)
    pid_d = tl.program_id(1)

    d_offsets = pid_d * BD + tl.arange(0, BD)
    mask_d = d_offsets < D

    P = tl.full((BD,), 1.0, tl.float32)
    y = tl.zeros((BD,), dtype=tl.float32)

    for i in tl.static_range(0, CHUNK):
        l_idx = chunk_id * CHUNK + i

        base_x = l_idx * stride_x_l
        base_a = l_idx * stride_a_l
        base_b = l_idx * stride_b_l

        x_ptrs = X_ptr + base_x + d_offsets * stride_x_d
        a_ptrs = A_ptr + base_a + d_offsets * stride_a_d
        b_ptrs = B_ptr + base_b + d_offsets * stride_b_d

        x = tl.load(x_ptrs, mask=mask_d, other=0.0).to(tl.float32)
        a = tl.load(a_ptrs, mask=mask_d, other=1.0).to(tl.float32)
        b = tl.load(b_ptrs, mask=mask_d, other=0.0).to(tl.float32)

        y = a * y + b * x
        P = P * a

    ach_ptrs = A_chunk_ptr + chunk_id * stride_ach_l + d_offsets * stride_ach_d
    bch_ptrs = B_chunk_ptr + chunk_id * stride_bch_l + d_offsets * stride_bch_d

    tl.store(ach_ptrs, P, mask=mask_d)
    tl.store(bch_ptrs, y, mask=mask_d)


@triton.jit
def chunk_prefix_kernel(
    A_chunk_ptr, B_chunk_ptr, S_chunk_ptr,
    D,
    stride_ach_l, stride_ach_d,
    stride_bch_l, stride_bch_d,
    stride_s_l, stride_s_d,
    NUM_CHUNKS: tl.constexpr,
    BD: tl.constexpr,
):
    pid_d = tl.program_id(0)
    d_offsets = pid_d * BD + tl.arange(0, BD)
    mask_d = d_offsets < D

    s = tl.zeros((BD,), dtype=tl.float32)

    for j in tl.static_range(0, NUM_CHUNKS):
        s_ptrs = S_chunk_ptr + j * stride_s_l + d_offsets * stride_s_d
        tl.store(s_ptrs, s, mask=mask_d)

        ach_ptrs = A_chunk_ptr + j * stride_ach_l + d_offsets * stride_ach_d
        bch_ptrs = B_chunk_ptr + j * stride_bch_l + d_offsets * stride_bch_d

        A = tl.load(ach_ptrs, mask=mask_d, other=1.0)
        B = tl.load(bch_ptrs, mask=mask_d, other=0.0)

        s = A * s + B


@triton.jit
def chunk_scan_kernel(
    X_ptr, A_ptr, B_ptr,
    S_chunk_ptr, Y_ptr,
    L, D,
    stride_x_l, stride_x_d,
    stride_a_l, stride_a_d,
    stride_b_l, stride_b_d,
    stride_s_l, stride_s_d,
    stride_y_l, stride_y_d,
    CHUNK: tl.constexpr,
    BD: tl.constexpr,
):
    chunk_id = tl.program_id(0)
    pid_d = tl.program_id(1)

    d_offsets = pid_d * BD + tl.arange(0, BD)
    mask_d = d_offsets < D

    s_ptrs = S_chunk_ptr + chunk_id * stride_s_l + d_offsets * stride_s_d
    s = tl.load(s_ptrs, mask=mask_d, other=0.0).to(tl.float32)

    for i in tl.static_range(0, CHUNK):
        l_idx = chunk_id * CHUNK + i

        base_x = l_idx * stride_x_l
        base_a = l_idx * stride_a_l
        base_b = l_idx * stride_b_l
        base_y = l_idx * stride_y_l

        x_ptrs = X_ptr + base_x + d_offsets * stride_x_d
        a_ptrs = A_ptr + base_a + d_offsets * stride_a_d
        b_ptrs = B_ptr + base_b + d_offsets * stride_b_d

        x = tl.load(x_ptrs, mask=mask_d, other=0.0).to(tl.float32)
        a = tl.load(a_ptrs, mask=mask_d, other=1.0).to(tl.float32)
        b = tl.load(b_ptrs, mask=mask_d, other=0.0).to(tl.float32)

        s = a * s + b * x

        y_ptrs = Y_ptr + base_y + d_offsets * stride_y_d
        tl.store(y_ptrs, s.to(tl.float16), mask=mask_d)


def chunk_scan(X: torch.Tensor, A: torch.Tensor, B: torch.Tensor, chunk: int = 128, BD: int = 128) -> torch.Tensor:
    L, D = X.shape
    assert X.shape == A.shape == B.shape
    assert X.is_cuda and A.is_cuda and B.is_cuda
    assert X.dtype == torch.float16 and A.dtype == torch.float16 and B.dtype == torch.float16
    assert L % chunk == 0, "L must be divisible by chunk"
    num_chunks = L // chunk

    device = X.device

    A_chunk = torch.empty((num_chunks, D), device=device, dtype=torch.float32)
    B_chunk = torch.empty((num_chunks, D), device=device, dtype=torch.float32)
    S_chunk = torch.empty((num_chunks, D), device=device, dtype=torch.float32)

    grid_summary = (num_chunks, triton.cdiv(D, BD))
    chunk_summary_kernel[grid_summary](
        X, A, B,
        A_chunk, B_chunk,
        L, D,
        X.stride(0), X.stride(1),
        A.stride(0), A.stride(1),
        B.stride(0), B.stride(1),
        A_chunk.stride(0), A_chunk.stride(1),
        B_chunk.stride(0), B_chunk.stride(1),
        CHUNK=chunk,
        BD=BD,
        num_warps=4,
        num_stages=2,
    )

    grid_prefix = (triton.cdiv(D, BD),)
    chunk_prefix_kernel[grid_prefix](
        A_chunk, B_chunk, S_chunk,
        D,
        A_chunk.stride(0), A_chunk.stride(1),
        B_chunk.stride(0), B_chunk.stride(1),
        S_chunk.stride(0), S_chunk.stride(1),
        NUM_CHUNKS=num_chunks,
        BD=BD,
        num_warps=4,
        num_stages=2,
    )

    Y = torch.empty_like(X)

    grid_scan = (num_chunks, triton.cdiv(D, BD))
    chunk_scan_kernel[grid_scan](
        X, A, B,
        S_chunk, Y,
        L, D,
        X.stride(0), X.stride(1),
        A.stride(0), A.stride(1),
        B.stride(0), B.stride(1),
        S_chunk.stride(0), S_chunk.stride(1),
        Y.stride(0), Y.stride(1),
        CHUNK=chunk,
        BD=BD,
        num_warps=4,
        num_stages=2,
    )

    return Y


class Solution:
    def solve(self, spec_path: str = None) -> dict:
        import inspect

        parts = [
            "import torch",
            "import triton",
            "import triton.language as tl",
            "",
            inspect.getsource(chunk_summary_kernel),
            "",
            inspect.getsource(chunk_prefix_kernel),
            "",
            inspect.getsource(chunk_scan_kernel),
            "",
            inspect.getsource(chunk_scan),
        ]
        code = "\n".join(parts)
        return {"code": code}