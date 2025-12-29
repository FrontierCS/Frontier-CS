import os
import tempfile
import textwrap
import hashlib

_KERNEL_CODE = r"""
import math
import torch
import triton
import triton.language as tl


@triton.jit
def _ragged_attn_fwd(
    Q_ptr, K_ptr, V_ptr, O_ptr, ROW_LENS_ptr,
    stride_qm: tl.constexpr, stride_qd: tl.constexpr,
    stride_kn: tl.constexpr, stride_kd: tl.constexpr,
    stride_vn: tl.constexpr, stride_vd: tl.constexpr,
    stride_om: tl.constexpr, stride_od: tl.constexpr,
    scale,
    N: tl.constexpr,
    D: tl.constexpr,
    DV: tl.constexpr,
    BN: tl.constexpr,
):
    pid_m = tl.program_id(0)

    row_len = tl.load(ROW_LENS_ptr + pid_m).to(tl.int32)
    row_len = tl.maximum(row_len, 0)
    row_len = tl.minimum(row_len, N)

    d = tl.arange(0, D)
    dv = tl.arange(0, DV)

    q = tl.load(Q_ptr + pid_m * stride_qm + d * stride_qd, mask=d < D, other=0.0).to(tl.float16)

    m = tl.full((), -1.0e9, tl.float32)
    l = tl.zeros((), tl.float32)
    acc = tl.zeros((DV,), tl.float32)

    for start in tl.static_range(0, N, BN):
        k_offs = start + tl.arange(0, BN)
        k_mask_n = k_offs < N
        valid = k_offs < row_len

        k = tl.load(
            K_ptr + k_offs[None, :] * stride_kn + d[:, None] * stride_kd,
            mask=(k_mask_n[None, :] & (d[:, None] < D)),
            other=0.0,
        ).to(tl.float16)

        scores = tl.dot(q[None, :], k)[0, :].to(tl.float32) * scale
        scores = tl.where(valid, scores, -float("inf"))

        m_ij = tl.max(scores, axis=0)
        m_new = tl.maximum(m, m_ij)
        alpha = tl.exp(m - m_new)
        p = tl.exp(scores - m_new)

        l_new = l * alpha + tl.sum(p, axis=0)

        v = tl.load(
            V_ptr + k_offs[:, None] * stride_vn + dv[None, :] * stride_vd,
            mask=(k_mask_n[:, None] & valid[:, None] & (dv[None, :] < DV)),
            other=0.0,
        ).to(tl.float16)

        pv = tl.dot(p.to(tl.float16)[None, :], v)[0, :].to(tl.float32)
        acc = acc * alpha + pv

        m = m_new
        l = l_new

    l = tl.where(l > 0.0, l, 1.0)
    out = acc / l
    tl.store(O_ptr + pid_m * stride_om + dv * stride_od, out.to(tl.float16), mask=dv < DV)


def ragged_attn(Q: torch.Tensor, K: torch.Tensor, V: torch.Tensor, row_lens: torch.Tensor) -> torch.Tensor:
    if not (Q.is_cuda and K.is_cuda and V.is_cuda and row_lens.is_cuda):
        raise ValueError("All inputs must be CUDA tensors.")
    if Q.dtype != torch.float16 or K.dtype != torch.float16 or V.dtype != torch.float16:
        raise ValueError("Q, K, V must be float16.")
    if Q.ndim != 2 or K.ndim != 2 or V.ndim != 2 or row_lens.ndim != 1:
        raise ValueError("Expected Q,K,V to be 2D and row_lens to be 1D.")
    M, D = Q.shape
    N, Dk = K.shape
    Nv, DV = V.shape
    if Dk != D:
        raise ValueError("Q and K must have same feature dimension.")
    if Nv != N:
        raise ValueError("K and V must have same number of rows.")
    if row_lens.shape[0] != M:
        raise ValueError("row_lens must have shape (M,).")

    if row_lens.dtype != torch.int32:
        row_lens_i32 = row_lens.to(torch.int32)
    else:
        row_lens_i32 = row_lens
    if not row_lens_i32.is_contiguous():
        row_lens_i32 = row_lens_i32.contiguous()

    if not Q.is_contiguous():
        Q = Q.contiguous()
    if not K.is_contiguous():
        K = K.contiguous()
    if not V.is_contiguous():
        V = V.contiguous()

    O = torch.empty((M, DV), device=Q.device, dtype=torch.float16)

    BN = 128
    scale = 1.0 / math.sqrt(D)

    grid = (M,)
    _ragged_attn_fwd[grid](
        Q, K, V, O, row_lens_i32,
        Q.stride(0), Q.stride(1),
        K.stride(0), K.stride(1),
        V.stride(0), V.stride(1),
        O.stride(0), O.stride(1),
        scale,
        N=N, D=D, DV=DV, BN=BN,
        num_warps=4,
        num_stages=2,
    )
    return O
"""


class Solution:
    def solve(self, spec_path: str = None) -> dict:
        code = textwrap.dedent(_KERNEL_CODE).lstrip()
        h = hashlib.sha256(code.encode("utf-8")).hexdigest()[:16]
        path = os.path.join(tempfile.gettempdir(), f"ragged_attn_triton_{h}.py")
        if (not os.path.exists(path)) or (open(path, "r", encoding="utf-8").read() != code):
            with open(path, "w", encoding="utf-8") as f:
                f.write(code)
        return {"program_path": path}