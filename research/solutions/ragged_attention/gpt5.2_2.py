import textwrap

_KERNEL_CODE = textwrap.dedent(
    r"""
import math
import torch
import triton
import triton.language as tl

@triton.jit
def _ragged_attn_fwd(
    Q_ptr, K_ptr, V_ptr, O_ptr, ROW_LENS_ptr,
    stride_qm, stride_qd,
    stride_kn, stride_kd,
    stride_vn, stride_vd,
    stride_om, stride_od,
    M,
    N: tl.constexpr, D: tl.constexpr, DV: tl.constexpr,
    BM: tl.constexpr, BN: tl.constexpr,
    SCALE: tl.constexpr,
):
    pid_m = tl.program_id(0)

    offs_m = pid_m * BM + tl.arange(0, BM)
    row_mask = offs_m < M

    row_len = tl.load(ROW_LENS_ptr + offs_m, mask=row_mask, other=0).to(tl.int32)
    row_len = tl.minimum(row_len, N)
    row_active = row_mask & (row_len > 0)

    offs_d = tl.arange(0, D)
    q_ptrs = Q_ptr + offs_m[:, None] * stride_qm + offs_d[None, :] * stride_qd
    q = tl.load(q_ptrs, mask=row_mask[:, None], other=0.0).to(tl.float16)

    m_i = tl.full([BM], -float("inf"), tl.float32)
    m_i = tl.where(row_active, m_i, 0.0)
    l_i = tl.zeros([BM], tl.float32)
    acc = tl.zeros([BM, DV], tl.float32)

    offs_dv = tl.arange(0, DV)

    for start_n in tl.static_range(0, N, BN):
        offs_n = start_n + tl.arange(0, BN)
        n_mask = offs_n < N

        k_ptrs = K_ptr + offs_n[:, None] * stride_kn + offs_d[None, :] * stride_kd
        k = tl.load(k_ptrs, mask=n_mask[:, None], other=0.0).to(tl.float16)

        # [BM, BN]
        scores = tl.dot(q, tl.trans(k)) * SCALE

        kv_mask = n_mask[None, :] & (offs_n[None, :] < row_len[:, None]) & row_active[:, None]
        scores = tl.where(kv_mask, scores, -float("inf"))

        m_ij = tl.max(scores, axis=1)
        m_new = tl.where(row_active, tl.maximum(m_i, m_ij), 0.0)

        alpha = tl.where(row_active, tl.exp(m_i - m_new), 0.0)
        p = tl.exp(scores - m_new[:, None])
        p = tl.where(kv_mask, p, 0.0)

        l_new = l_i * alpha + tl.sum(p, axis=1)

        v_ptrs = V_ptr + offs_n[:, None] * stride_vn + offs_dv[None, :] * stride_vd
        v = tl.load(v_ptrs, mask=n_mask[:, None], other=0.0).to(tl.float16)

        p_fp16 = p.to(tl.float16)
        acc = acc * alpha[:, None] + tl.dot(p_fp16, v)

        m_i = m_new
        l_i = l_new

    denom = l_i[:, None]
    out = tl.where(denom > 0, acc / denom, 0.0).to(tl.float16)

    o_ptrs = O_ptr + offs_m[:, None] * stride_om + offs_dv[None, :] * stride_od
    tl.store(o_ptrs, out, mask=row_mask[:, None])


def ragged_attn(Q: torch.Tensor, K: torch.Tensor, V: torch.Tensor, row_lens: torch.Tensor) -> torch.Tensor:
    assert Q.is_cuda and K.is_cuda and V.is_cuda and row_lens.is_cuda
    assert Q.dtype == torch.float16 and K.dtype == torch.float16 and V.dtype == torch.float16
    assert Q.ndim == 2 and K.ndim == 2 and V.ndim == 2 and row_lens.ndim == 1
    M, D = Q.shape
    N, Dk = K.shape
    assert D == Dk
    assert V.shape[0] == N
    DV = V.shape[1]
    assert row_lens.shape[0] == M

    O = torch.empty((M, DV), device=Q.device, dtype=torch.float16)

    # Heuristic: more parallelism for smaller M; more reuse for larger M
    if M <= 512:
        BM = 8
        num_warps = 4
        num_stages = 3
    else:
        BM = 16
        num_warps = 8
        num_stages = 4

    BN = 128
    scale = 1.0 / math.sqrt(D)

    grid = (triton.cdiv(M, BM),)

    _ragged_attn_fwd[grid](
        Q, K, V, O, row_lens,
        Q.stride(0), Q.stride(1),
        K.stride(0), K.stride(1),
        V.stride(0), V.stride(1),
        O.stride(0), O.stride(1),
        M,
        N=N, D=D, DV=DV,
        BM=BM, BN=BN,
        SCALE=scale,
        num_warps=num_warps,
        num_stages=num_stages,
    )
    return O
"""
).lstrip()


class Solution:
    def solve(self, spec_path: str = None) -> dict:
        return {"code": _KERNEL_CODE}