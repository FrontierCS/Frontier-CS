import textwrap

KERNEL_CODE = textwrap.dedent(r"""
import math
import torch
import triton
import triton.language as tl


@triton.jit
def _flash_attn_fwd(
    Q_ptr, K_ptr, V_ptr, O_ptr,
    stride_qz: tl.constexpr, stride_qh: tl.constexpr, stride_qm: tl.constexpr, stride_qd: tl.constexpr,
    stride_kz: tl.constexpr, stride_kh: tl.constexpr, stride_kn: tl.constexpr, stride_kd: tl.constexpr,
    stride_vz: tl.constexpr, stride_vh: tl.constexpr, stride_vn: tl.constexpr, stride_vd: tl.constexpr,
    stride_oz: tl.constexpr, stride_oh: tl.constexpr, stride_om: tl.constexpr, stride_od: tl.constexpr,
    H: tl.constexpr,
    M: tl.constexpr,
    N: tl.constexpr,
    DQ: tl.constexpr,
    DV: tl.constexpr,
    SCALE_LOG2E: tl.constexpr,
    CAUSAL: tl.constexpr,
    BM: tl.constexpr,
    BN: tl.constexpr,
    BDV: tl.constexpr,
):
    pid_m = tl.program_id(0)
    pid_bh = tl.program_id(1)

    z = pid_bh // H
    h = pid_bh - z * H

    start_m = pid_m * BM

    q_bh = Q_ptr + z * stride_qz + h * stride_qh
    k_bh = K_ptr + z * stride_kz + h * stride_kh
    v_bh = V_ptr + z * stride_vz + h * stride_vh
    o_bh = O_ptr + z * stride_oz + h * stride_oh

    tl.multiple_of(stride_qd, 8)
    tl.multiple_of(stride_kd, 8)
    tl.multiple_of(stride_vd, 8)
    tl.multiple_of(stride_od, 8)

    offs_m = start_m + tl.arange(0, BM)
    offs_d = tl.arange(0, DQ)

    q_ptrs = q_bh + offs_m[:, None] * stride_qm + offs_d[None, :] * stride_qd
    q = tl.load(q_ptrs, mask=offs_m[:, None] < M, other=0.0).to(tl.float16)

    m_i = tl.full([BM], -float("inf"), tl.float32)
    l_i = tl.zeros([BM], tl.float32)
    acc = tl.zeros([BM, BDV], tl.float32)

    for start_n in range(0, N, BN):
        offs_n = start_n + tl.arange(0, BN)

        k_ptrs = k_bh + offs_n[None, :] * stride_kn + offs_d[:, None] * stride_kd
        k = tl.load(k_ptrs, other=0.0).to(tl.float16)

        qk = tl.dot(q, k, out_dtype=tl.float32)
        qk = qk * SCALE_LOG2E

        if CAUSAL:
            causal_mask = offs_n[None, :] <= offs_m[:, None]
            qk = tl.where(causal_mask, qk, -1.0e9)

        m_ij = tl.max(qk, axis=1)
        m_new = tl.maximum(m_i, m_ij)

        alpha = tl.math.exp2(m_i - m_new)
        p = tl.math.exp2(qk - m_new[:, None])

        l_i = l_i * alpha + tl.sum(p, axis=1)
        acc = acc * alpha[:, None]

        offs_dv = tl.arange(0, BDV)
        v_ptrs = v_bh + offs_n[:, None] * stride_vn + offs_dv[None, :] * stride_vd
        v = tl.load(v_ptrs, mask=offs_dv[None, :] < DV, other=0.0).to(tl.float16)

        acc += tl.dot(p.to(tl.float16), v, out_dtype=tl.float32)
        m_i = m_new

    out = acc / l_i[:, None]
    out = out.to(tl.float16)

    offs_dv = tl.arange(0, BDV)
    o_ptrs = o_bh + offs_m[:, None] * stride_om + offs_dv[None, :] * stride_od
    tl.store(o_ptrs, out, mask=(offs_m[:, None] < M) & (offs_dv[None, :] < DV))


def flash_attn(Q: torch.Tensor, K: torch.Tensor, V: torch.Tensor, causal: bool = True) -> torch.Tensor:
    assert Q.is_cuda and K.is_cuda and V.is_cuda
    assert Q.dtype == torch.float16 and K.dtype == torch.float16 and V.dtype == torch.float16
    assert Q.ndim == 4 and K.ndim == 4 and V.ndim == 4

    Z, H, M, DQ = Q.shape
    Zk, Hk, N, DQk = K.shape
    Zv, Hv, Nv, DV = V.shape
    assert Zk == Z and Zv == Z
    assert Hk == H and Hv == H
    assert N == Nv
    assert DQk == DQ

    if DQ not in (16, 32, 64, 128):
        raise ValueError(f"Unsupported DQ={DQ}")
    if DV <= 64:
        BDV = 64
    elif DV <= 128:
        BDV = 128
    else:
        raise ValueError(f"Unsupported DV={DV}")

    BM = 64
    BN = 128
    if M % BM != 0 or N % BN != 0:
        # still works with masking, but keep meta consistent; pick smaller blocks if needed
        BM = 32 if M % 32 == 0 else 16
        BN = 64 if N % 64 == 0 else 32

    O = torch.empty((Z, H, M, DV), device=Q.device, dtype=torch.float16)

    scale_log2e = (1.0 / math.sqrt(DQ)) * 1.4426950408889634  # log2(e)

    grid = (triton.cdiv(M, BM), Z * H)

    num_warps = 4
    if BM >= 128:
        num_warps = 8
    num_stages = 4

    _flash_attn_fwd[grid](
        Q, K, V, O,
        Q.stride(0), Q.stride(1), Q.stride(2), Q.stride(3),
        K.stride(0), K.stride(1), K.stride(2), K.stride(3),
        V.stride(0), V.stride(1), V.stride(2), V.stride(3),
        O.stride(0), O.stride(1), O.stride(2), O.stride(3),
        H=H,
        M=M,
        N=N,
        DQ=DQ,
        DV=DV,
        SCALE_LOG2E=scale_log2e,
        CAUSAL=causal,
        BM=BM,
        BN=BN,
        BDV=BDV,
        num_warps=num_warps,
        num_stages=num_stages,
    )
    return O
""")


class Solution:
    def solve(self, spec_path: str = None) -> dict:
        return {"code": KERNEL_CODE}
