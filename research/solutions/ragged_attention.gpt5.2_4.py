import os
import math
import torch
import triton
import triton.language as tl


@triton.jit
def _ragged_attn_kernel(
    Q_ptr,
    K_ptr,
    V_ptr,
    O_ptr,
    RL_ptr,
    stride_qm: tl.constexpr,
    stride_qd: tl.constexpr,
    stride_kn: tl.constexpr,
    stride_kd: tl.constexpr,
    stride_vn: tl.constexpr,
    stride_vd: tl.constexpr,
    stride_om: tl.constexpr,
    stride_od: tl.constexpr,
    M: tl.constexpr,
    N: tl.constexpr,
    D: tl.constexpr,
    DV: tl.constexpr,
    SCALE: tl.constexpr,
    BLOCK_M: tl.constexpr,
    BLOCK_N: tl.constexpr,
):
    pid_m = tl.program_id(0)

    offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
    mask_m = offs_m < M

    row_len = tl.load(RL_ptr + offs_m, mask=mask_m, other=0).to(tl.int32)

    offs_d = tl.arange(0, D)
    q = tl.load(Q_ptr + offs_m[:, None] * stride_qm + offs_d[None, :] * stride_qd, mask=mask_m[:, None], other=0.0).to(tl.float16)

    m_i = tl.full([BLOCK_M], -float("inf"), tl.float32)
    l_i = tl.zeros([BLOCK_M], tl.float32)
    acc = tl.zeros([BLOCK_M, DV], tl.float32)

    offs_dv = tl.arange(0, DV)

    tl.multiple_of(D, 8)
    tl.multiple_of(DV, 8)
    tl.multiple_of(BLOCK_N, 16)

    for start_n in tl.static_range(0, N, BLOCK_N):
        offs_n = start_n + tl.arange(0, BLOCK_N)
        mask_n = offs_n < N

        k = tl.load(K_ptr + offs_n[:, None] * stride_kn + offs_d[None, :] * stride_kd, mask=mask_n[:, None], other=0.0).to(tl.float16)
        scores = tl.dot(q, tl.trans(k)) * SCALE

        ragged = offs_n[None, :] < row_len[:, None]
        valid = mask_m[:, None] & mask_n[None, :] & ragged
        scores = tl.where(valid, scores, -float("inf"))

        m_ij = tl.max(scores, axis=1)
        m_new = tl.maximum(m_i, m_ij)

        exp_m = tl.exp(m_i - m_new)
        p = tl.exp(scores - m_new[:, None])

        l_new = l_i * exp_m + tl.sum(p, axis=1)

        v = tl.load(V_ptr + offs_n[:, None] * stride_vn + offs_dv[None, :] * stride_vd, mask=mask_n[:, None], other=0.0).to(tl.float16)

        pv = tl.dot(p.to(tl.float16), v)
        acc = acc * exp_m[:, None] + pv

        m_i = m_new
        l_i = l_new

    inv_l = tl.where(l_i > 0.0, 1.0 / l_i, 0.0)
    out = acc * inv_l[:, None]
    tl.store(O_ptr + offs_m[:, None] * stride_om + offs_dv[None, :] * stride_od, out.to(tl.float16), mask=mask_m[:, None])


def ragged_attn(Q: torch.Tensor, K: torch.Tensor, V: torch.Tensor, row_lens: torch.Tensor) -> torch.Tensor:
    if not (Q.is_cuda and K.is_cuda and V.is_cuda and row_lens.is_cuda):
        raise ValueError("All inputs must be CUDA tensors")
    if Q.dtype != torch.float16 or K.dtype != torch.float16 or V.dtype != torch.float16:
        raise ValueError("Q, K, V must be float16")
    if Q.ndim != 2 or K.ndim != 2 or V.ndim != 2 or row_lens.ndim != 1:
        raise ValueError("Invalid input ranks")
    M, D = Q.shape
    N, Dk = K.shape
    Nv, DV = V.shape
    if Dk != D or Nv != N or row_lens.shape[0] != M:
        raise ValueError("Shape mismatch")

    if not Q.is_contiguous():
        Q = Q.contiguous()
    if not K.is_contiguous():
        K = K.contiguous()
    if not V.is_contiguous():
        V = V.contiguous()
    if row_lens.dtype != torch.int32:
        row_lens = row_lens.to(torch.int32)
    if not row_lens.is_contiguous():
        row_lens = row_lens.contiguous()

    O = torch.empty((M, DV), device=Q.device, dtype=torch.float16)

    if M <= 512:
        BLOCK_M = 8
        num_warps = 4
        num_stages = 3
    else:
        BLOCK_M = 16
        num_warps = 8
        num_stages = 3

    BLOCK_N = 128
    grid = (triton.cdiv(M, BLOCK_M),)

    scale = 1.0 / math.sqrt(D)

    _ragged_attn_kernel[grid](
        Q,
        K,
        V,
        O,
        row_lens,
        stride_qm=Q.stride(0),
        stride_qd=Q.stride(1),
        stride_kn=K.stride(0),
        stride_kd=K.stride(1),
        stride_vn=V.stride(0),
        stride_vd=V.stride(1),
        stride_om=O.stride(0),
        stride_od=O.stride(1),
        M=M,
        N=N,
        D=D,
        DV=DV,
        SCALE=scale,
        BLOCK_M=BLOCK_M,
        BLOCK_N=BLOCK_N,
        num_warps=num_warps,
        num_stages=num_stages,
    )
    return O


_SELF_CODE = None
try:
    _p = os.path.abspath(__file__)
    with open(_p, "r", encoding="utf-8") as _f:
        _SELF_CODE = _f.read()
except Exception:
    _SELF_CODE = None


class Solution:
    def solve(self, spec_path: str = None) -> dict:
        if _SELF_CODE is not None:
            return {"code": _SELF_CODE}
        if "__file__" in globals():
            return {"program_path": os.path.abspath(__file__)}
        raise RuntimeError("Unable to provide solution code or program path")