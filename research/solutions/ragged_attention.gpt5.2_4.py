import textwrap

_KERNEL_CODE = r'''
import math
import torch
import triton
import triton.language as tl


@triton.jit
def _ragged_attn_fwd(
    Q_ptr, K_ptr, V_ptr, O_ptr, RL_ptr,
    stride_qm: tl.constexpr, stride_qd: tl.constexpr,
    stride_kn: tl.constexpr, stride_kd: tl.constexpr,
    stride_vn: tl.constexpr, stride_vd: tl.constexpr,
    stride_om: tl.constexpr, stride_od: tl.constexpr,
    M: tl.constexpr, N: tl.constexpr,
    D: tl.constexpr, DV: tl.constexpr,
    SCALE: tl.constexpr,
    BLOCK_M: tl.constexpr, BLOCK_N: tl.constexpr,
):
    pid_m = tl.program_id(0)
    offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
    mask_m = offs_m < M

    row_lens = tl.load(RL_ptr + offs_m, mask=mask_m, other=0).to(tl.int32)

    offs_d = tl.arange(0, D)
    q = tl.load(Q_ptr + offs_m[:, None] * stride_qm + offs_d[None, :] * stride_qd, mask=mask_m[:, None], other=0.0).to(tl.float16)

    m_i = tl.where(row_lens > 0, tl.full([BLOCK_M], -float("inf"), tl.float32), tl.zeros([BLOCK_M], tl.float32))
    l_i = tl.zeros([BLOCK_M], tl.float32)
    acc = tl.zeros([BLOCK_M, DV], tl.float32)

    offs_dv = tl.arange(0, DV)

    for start_n in range(0, N, BLOCK_N):
        offs_n = start_n + tl.arange(0, BLOCK_N)
        mask_n = offs_n < N

        k = tl.load(K_ptr + offs_n[:, None] * stride_kn + offs_d[None, :] * stride_kd, mask=mask_n[:, None], other=0.0).to(tl.float16)
        v = tl.load(V_ptr + offs_n[:, None] * stride_vn + offs_dv[None, :] * stride_vd, mask=mask_n[:, None], other=0.0).to(tl.float16)

        scores = tl.dot(q, tl.trans(k)).to(tl.float32) * SCALE

        valid = (offs_n[None, :] < row_lens[:, None]) & mask_m[:, None] & mask_n[None, :]
        scores = tl.where(valid, scores, -float("inf"))

        row_max = tl.max(scores, axis=1)
        m_new = tl.maximum(m_i, row_max)

        alpha = tl.exp(m_i - m_new)
        p = tl.exp(scores - m_new[:, None])
        l_new = l_i * alpha + tl.sum(p, axis=1)

        p16 = p.to(tl.float16)
        acc = acc * alpha[:, None] + tl.dot(p16, v).to(tl.float32)

        m_i = m_new
        l_i = l_new

    l_safe = tl.where(l_i > 0, l_i, 1.0)
    out = acc / l_safe[:, None]
    out = tl.where((l_i > 0)[:, None] & mask_m[:, None], out, 0.0).to(tl.float16)

    tl.store(O_ptr + offs_m[:, None] * stride_om + offs_dv[None, :] * stride_od, out, mask=mask_m[:, None])


def ragged_attn(Q: torch.Tensor, K: torch.Tensor, V: torch.Tensor, row_lens: torch.Tensor) -> torch.Tensor:
    if not (Q.is_cuda and K.is_cuda and V.is_cuda and row_lens.is_cuda):
        raise ValueError("All inputs must be CUDA tensors")
    if Q.dtype != torch.float16 or K.dtype != torch.float16 or V.dtype != torch.float16:
        raise ValueError("Q, K, V must be float16")
    if Q.ndim != 2 or K.ndim != 2 or V.ndim != 2:
        raise ValueError("Q, K, V must be 2D tensors")
    if row_lens.ndim != 1:
        raise ValueError("row_lens must be 1D tensor")

    M, D = Q.shape
    N, Dk = K.shape
    Nv, DV = V.shape
    if Dk != D:
        raise ValueError("K.shape[1] must equal Q.shape[1]")
    if Nv != N:
        raise ValueError("V.shape[0] must equal K.shape[0]")
    if row_lens.shape[0] != M:
        raise ValueError("row_lens.shape[0] must equal Q.shape[0]")

    O = torch.empty((M, DV), device=Q.device, dtype=torch.float16)

    stride_qm, stride_qd = Q.stride()
    stride_kn, stride_kd = K.stride()
    stride_vn, stride_vd = V.stride()
    stride_om, stride_od = O.stride()

    scale = 1.0 / math.sqrt(D)

    BLOCK_M = 16
    BLOCK_N = 256
    num_warps = 8
    num_stages = 4

    grid = (triton.cdiv(M, BLOCK_M),)
    _ragged_attn_fwd[grid](
        Q, K, V, O, row_lens,
        stride_qm=stride_qm, stride_qd=stride_qd,
        stride_kn=stride_kn, stride_kd=stride_kd,
        stride_vn=stride_vn, stride_vd=stride_vd,
        stride_om=stride_om, stride_od=stride_od,
        M=M, N=N,
        D=D, DV=DV,
        SCALE=scale,
        BLOCK_M=BLOCK_M, BLOCK_N=BLOCK_N,
        num_warps=num_warps, num_stages=num_stages,
    )
    return O
'''

class Solution:
    def solve(self, spec_path: str = None) -> dict:
        return {"code": textwrap.dedent(_KERNEL_CODE).lstrip()}