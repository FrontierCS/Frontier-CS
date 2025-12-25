import textwrap


KERNEL_CODE = textwrap.dedent(
    r"""
import torch
import triton
import triton.language as tl


@triton.jit
def _chunk_summary_kernel(
    X_ptr, A_ptr, B_ptr,
    Ach_ptr, Uch_ptr,
    stride_xl: tl.constexpr, stride_xd: tl.constexpr,
    stride_al: tl.constexpr, stride_ad: tl.constexpr,
    stride_bl: tl.constexpr, stride_bd: tl.constexpr,
    stride_chl: tl.constexpr, stride_chd: tl.constexpr,
    L: tl.constexpr, D: tl.constexpr,
    CHUNK: tl.constexpr, BD: tl.constexpr,
):
    pid_c = tl.program_id(0)
    pid_d = tl.program_id(1)

    d_offs = pid_d * BD + tl.arange(0, BD)
    d_mask = d_offs < D

    t0 = pid_c * CHUNK

    y = tl.zeros([BD], dtype=tl.float32)
    prod = tl.full([BD], 1.0, dtype=tl.float32)

    # Assume L divisible by CHUNK, so valid for all pid_c in grid
    # tl.static_range requires CHUNK to be tl.constexpr
    for i in tl.static_range(0, CHUNK):
        t = t0 + i
        x = tl.load(X_ptr + t * stride_xl + d_offs * stride_xd, mask=d_mask, other=0.0).to(tl.float32)
        a = tl.load(A_ptr + t * stride_al + d_offs * stride_ad, mask=d_mask, other=0.0).to(tl.float32)
        b = tl.load(B_ptr + t * stride_bl + d_offs * stride_bd, mask=d_mask, other=0.0).to(tl.float32)
        u = b * x
        y = a * y + u
        prod = prod * a

    tl.store(Ach_ptr + pid_c * stride_chl + d_offs * stride_chd, prod, mask=d_mask)
    tl.store(Uch_ptr + pid_c * stride_chl + d_offs * stride_chd, y, mask=d_mask)


@triton.jit
def _chunk_prefix_kernel(
    Ach_ptr, Uch_ptr,
    Y0_ptr,
    stride_chl: tl.constexpr, stride_chd: tl.constexpr,
    stride_y0l: tl.constexpr, stride_y0d: tl.constexpr,
    NCH: tl.constexpr, D: tl.constexpr,
    MAX_NCH: tl.constexpr, BD: tl.constexpr,
):
    pid_d = tl.program_id(0)
    d_offs = pid_d * BD + tl.arange(0, BD)
    d_mask = d_offs < D

    y = tl.zeros([BD], dtype=tl.float32)

    # For chunk k, y is y_start[k] (state before applying chunk k)
    for k in tl.static_range(0, MAX_NCH):
        in_range = k < NCH
        # store y_start
        tl.store(Y0_ptr + k * stride_y0l + d_offs * stride_y0d, y, mask=d_mask & in_range)

        a = tl.load(Ach_ptr + k * stride_chl + d_offs * stride_chd, mask=d_mask & in_range, other=1.0).to(tl.float32)
        u = tl.load(Uch_ptr + k * stride_chl + d_offs * stride_chd, mask=d_mask & in_range, other=0.0).to(tl.float32)
        y = a * y + u


@triton.jit
def _chunk_apply_kernel(
    X_ptr, A_ptr, B_ptr,
    Y0_ptr,
    Y_ptr,
    stride_xl: tl.constexpr, stride_xd: tl.constexpr,
    stride_al: tl.constexpr, stride_ad: tl.constexpr,
    stride_bl: tl.constexpr, stride_bd: tl.constexpr,
    stride_y0l: tl.constexpr, stride_y0d: tl.constexpr,
    stride_yl: tl.constexpr, stride_yd: tl.constexpr,
    L: tl.constexpr, D: tl.constexpr,
    CHUNK: tl.constexpr, BD: tl.constexpr,
):
    pid_c = tl.program_id(0)
    pid_d = tl.program_id(1)

    d_offs = pid_d * BD + tl.arange(0, BD)
    d_mask = d_offs < D

    t0 = pid_c * CHUNK

    y = tl.load(Y0_ptr + pid_c * stride_y0l + d_offs * stride_y0d, mask=d_mask, other=0.0).to(tl.float32)

    for i in tl.static_range(0, CHUNK):
        t = t0 + i
        x = tl.load(X_ptr + t * stride_xl + d_offs * stride_xd, mask=d_mask, other=0.0).to(tl.float32)
        a = tl.load(A_ptr + t * stride_al + d_offs * stride_ad, mask=d_mask, other=0.0).to(tl.float32)
        b = tl.load(B_ptr + t * stride_bl + d_offs * stride_bd, mask=d_mask, other=0.0).to(tl.float32)
        y = a * y + b * x
        tl.store(Y_ptr + t * stride_yl + d_offs * stride_yd, y.to(tl.float16), mask=d_mask)


def chunk_scan(X: torch.Tensor, A: torch.Tensor, B: torch.Tensor, chunk: int = 128, BD: int = 128) -> torch.Tensor:
    assert X.is_cuda and A.is_cuda and B.is_cuda
    assert X.dtype == torch.float16 and A.dtype == torch.float16 and B.dtype == torch.float16
    assert X.ndim == 2 and A.ndim == 2 and B.ndim == 2
    L, D = X.shape
    assert A.shape == (L, D) and B.shape == (L, D)
    assert L % chunk == 0

    if not X.is_contiguous():
        X = X.contiguous()
    if not A.is_contiguous():
        A = A.contiguous()
    if not B.is_contiguous():
        B = B.contiguous()

    nch = L // chunk
    max_nch = 64
    if nch > max_nch:
        max_nch = 1
        while max_nch < nch:
            max_nch *= 2
        if max_nch < 64:
            max_nch = 64

    Ach = torch.empty((nch, D), device=X.device, dtype=torch.float32)
    Uch = torch.empty((nch, D), device=X.device, dtype=torch.float32)
    Y0 = torch.empty((nch, D), device=X.device, dtype=torch.float32)
    Y = torch.empty((L, D), device=X.device, dtype=torch.float16)

    stride_xl, stride_xd = X.stride()
    stride_al, stride_ad = A.stride()
    stride_bl, stride_bd = B.stride()

    stride_chl, stride_chd = Ach.stride()
    stride_y0l, stride_y0d = Y0.stride()
    stride_yl, stride_yd = Y.stride()

    grid1 = (nch, triton.cdiv(D, BD))
    _chunk_summary_kernel[grid1](
        X, A, B,
        Ach, Uch,
        stride_xl=stride_xl, stride_xd=stride_xd,
        stride_al=stride_al, stride_ad=stride_ad,
        stride_bl=stride_bl, stride_bd=stride_bd,
        stride_chl=stride_chl, stride_chd=stride_chd,
        L=L, D=D,
        CHUNK=chunk, BD=BD,
        num_warps=4,
        num_stages=2,
    )

    grid2 = (triton.cdiv(D, BD),)
    _chunk_prefix_kernel[grid2](
        Ach, Uch,
        Y0,
        stride_chl=stride_chl, stride_chd=stride_chd,
        stride_y0l=stride_y0l, stride_y0d=stride_y0d,
        NCH=nch, D=D,
        MAX_NCH=max_nch, BD=BD,
        num_warps=4,
        num_stages=1,
    )

    grid3 = (nch, triton.cdiv(D, BD))
    _chunk_apply_kernel[grid3](
        X, A, B,
        Y0,
        Y,
        stride_xl=stride_xl, stride_xd=stride_xd,
        stride_al=stride_al, stride_ad=stride_ad,
        stride_bl=stride_bl, stride_bd=stride_bd,
        stride_y0l=stride_y0l, stride_y0d=stride_y0d,
        stride_yl=stride_yl, stride_yd=stride_yd,
        L=L, D=D,
        CHUNK=chunk, BD=BD,
        num_warps=4,
        num_stages=2,
    )

    return Y
"""
).lstrip()


class Solution:
    def solve(self, spec_path: str = None) -> dict:
        return {"code": KERNEL_CODE}