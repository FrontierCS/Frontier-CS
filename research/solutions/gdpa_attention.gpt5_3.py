import math
import torch
import triton
import triton.language as tl


@triton.jit
def gdpa_fwd_kernel(
    Q_ptr, K_ptr, V_ptr, GQ_ptr, GK_ptr, O_ptr,
    stride_qz, stride_qh, stride_qm, stride_qd,
    stride_kz, stride_kh, stride_kn, stride_kd,
    stride_vz, stride_vh, stride_vn, stride_vd,
    stride_gqz, stride_gqh, stride_gqm, stride_gqd,
    stride_gkz, stride_gkh, stride_gkn, stride_gkd,
    stride_oz, stride_oh, stride_om, stride_od,
    Z, H, M, N, scale,
    BLOCK_M: tl.constexpr, BLOCK_N: tl.constexpr,
    HEAD_DIM: tl.constexpr, VALUE_DIM: tl.constexpr
):
    pid_zh = tl.program_id(0)
    pid_m = tl.program_id(1)

    z = pid_zh // H
    h = pid_zh % H

    offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
    m_mask = offs_m < M

    offs_dq = tl.arange(0, HEAD_DIM)
    offs_dv = tl.arange(0, VALUE_DIM)

    q_base = z * stride_qz + h * stride_qh
    gq_base = z * stride_gqz + h * stride_gqh
    k_base = z * stride_kz + h * stride_kh
    gk_base = z * stride_gkz + h * stride_gkh
    v_base = z * stride_vz + h * stride_vh
    o_base = z * stride_oz + h * stride_oh

    q_ptrs = Q_ptr + q_base + (offs_m[:, None] * stride_qm + offs_dq[None, :] * stride_qd)
    gq_ptrs = GQ_ptr + gq_base + (offs_m[:, None] * stride_gqm + offs_dq[None, :] * stride_gqd)
    q = tl.load(q_ptrs, mask=m_mask[:, None], other=0.0).to(tl.float32)
    gq = tl.load(gq_ptrs, mask=m_mask[:, None], other=0.0).to(tl.float32)
    gate_q = 1.0 / (1.0 + tl.exp(-gq))
    q = q * gate_q

    m_i = tl.full((BLOCK_M,), -float("inf"), dtype=tl.float32)
    l_i = tl.zeros((BLOCK_M,), dtype=tl.float32)
    acc = tl.zeros((BLOCK_M, VALUE_DIM), dtype=tl.float32)

    for start_n in range(0, N, BLOCK_N):
        offs_n = start_n + tl.arange(0, BLOCK_N)
        n_mask = offs_n < N

        k_ptrs = K_ptr + k_base + (offs_n[:, None] * stride_kn + offs_dq[None, :] * stride_kd)
        gk_ptrs = GK_ptr + gk_base + (offs_n[:, None] * stride_gkn + offs_dq[None, :] * stride_gkd)
        v_ptrs = V_ptr + v_base + (offs_n[:, None] * stride_vn + offs_dv[None, :] * stride_vd)

        k = tl.load(k_ptrs, mask=n_mask[:, None], other=0.0).to(tl.float32)
        gk = tl.load(gk_ptrs, mask=n_mask[:, None], other=0.0).to(tl.float32)
        gate_k = 1.0 / (1.0 + tl.exp(-gk))
        k = k * gate_k

        v = tl.load(v_ptrs, mask=n_mask[:, None], other=0.0).to(tl.float32)

        qk = tl.dot(q, tl.trans(k)) * scale
        qk = tl.where(n_mask[None, :], qk, -float("inf"))

        m_ij = tl.maximum(m_i, tl.max(qk, 1))
        p = tl.exp(qk - m_ij[:, None])
        l_ij = tl.sum(p, 1)
        alpha = tl.exp(m_i - m_ij)

        acc = acc * alpha[:, None] + tl.dot(p, v)
        l_i = l_i * alpha + l_ij
        m_i = m_ij

    out = acc / l_i[:, None]
    o_ptrs = O_ptr + o_base + (offs_m[:, None] * stride_om + offs_dv[None, :] * stride_od)
    tl.store(o_ptrs, out.to(tl.float16), mask=m_mask[:, None])


def gdpa_attn(Q: torch.Tensor, K: torch.Tensor, V: torch.Tensor, GQ: torch.Tensor, GK: torch.Tensor) -> torch.Tensor:
    if Q.device.type != "cuda":
        Qg = Q * torch.sigmoid(GQ)
        Kg = K * torch.sigmoid(GK)
        scale = 1.0 / math.sqrt(Q.shape[-1])
        attn = torch.softmax(torch.matmul(Qg, Kg.transpose(-2, -1)) * scale, dim=-1)
        O = torch.matmul(attn, V)
        return O.to(dtype=Q.dtype)

    assert Q.is_cuda and K.is_cuda and V.is_cuda and GQ.is_cuda and GK.is_cuda, "All inputs must be CUDA tensors"
    assert Q.dtype == torch.float16 and K.dtype == torch.float16 and V.dtype == torch.float16 and GQ.dtype == torch.float16 and GK.dtype == torch.float16, "All inputs must be float16"
    assert Q.shape[:3] == GQ.shape[:3] and Q.shape[3] == GQ.shape[3], "GQ shape mismatch"
    assert K.shape[:3] == GK.shape[:3] and K.shape[3] == GK.shape[3], "GK shape mismatch"
    Z, H, M, Dq = Q.shape
    Zk, Hk, N, Dqk = K.shape
    assert Z == Zk and H == Hk and Dq == Dqk, "Q and K must agree on Z, H, D"
    Zv, Hv, Nv, Dv = V.shape
    assert Z == Zv and H == Hv and N == Nv, "K and V must agree on Z, H, N"
    scale = 1.0 / math.sqrt(Dq)

    O = torch.empty((Z, H, M, Dv), device=Q.device, dtype=torch.float16)

    grid = (Z * H, triton.cdiv(M, 128))

    num_warps = 4 if (Dq <= 64 and Dv <= 64) else 8
    gdpa_fwd_kernel[grid](
        Q, K, V, GQ, GK, O,
        Q.stride(0), Q.stride(1), Q.stride(2), Q.stride(3),
        K.stride(0), K.stride(1), K.stride(2), K.stride(3),
        V.stride(0), V.stride(1), V.stride(2), V.stride(3),
        GQ.stride(0), GQ.stride(1), GQ.stride(2), GQ.stride(3),
        GK.stride(0), GK.stride(1), GK.stride(2), GK.stride(3),
        O.stride(0), O.stride(1), O.stride(2), O.stride(3),
        Z, H, M, N, scale,
        BLOCK_M=128, BLOCK_N=64,
        HEAD_DIM=Dq, VALUE_DIM=Dv,
        num_warps=num_warps, num_stages=2
    )
    return O


class Solution:
    def solve(self, spec_path: str = None) -> dict:
        code = '''
import math
import torch
import triton
import triton.language as tl


@triton.jit
def gdpa_fwd_kernel(
    Q_ptr, K_ptr, V_ptr, GQ_ptr, GK_ptr, O_ptr,
    stride_qz, stride_qh, stride_qm, stride_qd,
    stride_kz, stride_kh, stride_kn, stride_kd,
    stride_vz, stride_vh, stride_vn, stride_vd,
    stride_gqz, stride_gqh, stride_gqm, stride_gqd,
    stride_gkz, stride_gkh, stride_gkn, stride_gkd,
    stride_oz, stride_oh, stride_om, stride_od,
    Z, H, M, N, scale,
    BLOCK_M: tl.constexpr, BLOCK_N: tl.constexpr,
    HEAD_DIM: tl.constexpr, VALUE_DIM: tl.constexpr
):
    pid_zh = tl.program_id(0)
    pid_m = tl.program_id(1)

    z = pid_zh // H
    h = pid_zh % H

    offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
    m_mask = offs_m < M

    offs_dq = tl.arange(0, HEAD_DIM)
    offs_dv = tl.arange(0, VALUE_DIM)

    q_base = z * stride_qz + h * stride_qh
    gq_base = z * stride_gqz + h * stride_gqh
    k_base = z * stride_kz + h * stride_kh
    gk_base = z * stride_gkz + h * stride_gkh
    v_base = z * stride_vz + h * stride_vh
    o_base = z * stride_oz + h * stride_oh

    q_ptrs = Q_ptr + q_base + (offs_m[:, None] * stride_qm + offs_dq[None, :] * stride_qd)
    gq_ptrs = GQ_ptr + gq_base + (offs_m[:, None] * stride_gqm + offs_dq[None, :] * stride_gqd)
    q = tl.load(q_ptrs, mask=m_mask[:, None], other=0.0).to(tl.float32)
    gq = tl.load(gq_ptrs, mask=m_mask[:, None], other=0.0).to(tl.float32)
    gate_q = 1.0 / (1.0 + tl.exp(-gq))
    q = q * gate_q

    m_i = tl.full((BLOCK_M,), -float("inf"), dtype=tl.float32)
    l_i = tl.zeros((BLOCK_M,), dtype=tl.float32)
    acc = tl.zeros((BLOCK_M, VALUE_DIM), dtype=tl.float32)

    for start_n in range(0, N, BLOCK_N):
        offs_n = start_n + tl.arange(0, BLOCK_N)
        n_mask = offs_n < N

        k_ptrs = K_ptr + k_base + (offs_n[:, None] * stride_kn + offs_dq[None, :] * stride_kd)
        gk_ptrs = GK_ptr + gk_base + (offs_n[:, None] * stride_gkn + offs_dq[None, :] * stride_gkd)
        v_ptrs = V_ptr + v_base + (offs_n[:, None] * stride_vn + offs_dv[None, :] * stride_vd)

        k = tl.load(k_ptrs, mask=n_mask[:, None], other=0.0).to(tl.float32)
        gk = tl.load(gk_ptrs, mask=n_mask[:, None], other=0.0).to(tl.float32)
        gate_k = 1.0 / (1.0 + tl.exp(-gk))
        k = k * gate_k

        v = tl.load(v_ptrs, mask=n_mask[:, None], other=0.0).to(tl.float32)

        qk = tl.dot(q, tl.trans(k)) * scale
        qk = tl.where(n_mask[None, :], qk, -float("inf"))

        m_ij = tl.maximum(m_i, tl.max(qk, 1))
        p = tl.exp(qk - m_ij[:, None])
        l_ij = tl.sum(p, 1)
        alpha = tl.exp(m_i - m_ij)

        acc = acc * alpha[:, None] + tl.dot(p, v)
        l_i = l_i * alpha + l_ij
        m_i = m_ij

    out = acc / l_i[:, None]
    o_ptrs = O_ptr + o_base + (offs_m[:, None] * stride_om + offs_dv[None, :] * stride_od)
    tl.store(o_ptrs, out.to(tl.float16), mask=m_mask[:, None])


def gdpa_attn(Q: torch.Tensor, K: torch.Tensor, V: torch.Tensor, GQ: torch.Tensor, GK: torch.Tensor) -> torch.Tensor:
    if Q.device.type != "cuda":
        Qg = Q * torch.sigmoid(GQ)
        Kg = K * torch.sigmoid(GK)
        scale = 1.0 / math.sqrt(Q.shape[-1])
        attn = torch.softmax(torch.matmul(Qg, Kg.transpose(-2, -1)) * scale, dim=-1)
        O = torch.matmul(attn, V)
        return O.to(dtype=Q.dtype)

    assert Q.is_cuda and K.is_cuda and V.is_cuda and GQ.is_cuda and GK.is_cuda, "All inputs must be CUDA tensors"
    assert Q.dtype == torch.float16 and K.dtype == torch.float16 and V.dtype == torch.float16 and GQ.dtype == torch.float16 and GK.dtype == torch.float16, "All inputs must be float16"
    assert Q.shape[:3] == GQ.shape[:3] and Q.shape[3] == GQ.shape[3], "GQ shape mismatch"
    assert K.shape[:3] == GK.shape[:3] and K.shape[3] == GK.shape[3], "GK shape mismatch"
    Z, H, M, Dq = Q.shape
    Zk, Hk, N, Dqk = K.shape
    assert Z == Zk and H == Hk and Dq == Dqk, "Q and K must agree on Z, H, D"
    Zv, Hv, Nv, Dv = V.shape
    assert Z == Zv and H == Hv and N == Nv, "K and V must agree on Z, H, N"
    scale = 1.0 / math.sqrt(Dq)

    O = torch.empty((Z, H, M, Dv), device=Q.device, dtype=torch.float16)

    grid = (Z * H, triton.cdiv(M, 128))

    num_warps = 4 if (Dq <= 64 and Dv <= 64) else 8
    gdpa_fwd_kernel[grid](
        Q, K, V, GQ, GK, O,
        Q.stride(0), Q.stride(1), Q.stride(2), Q.stride(3),
        K.stride(0), K.stride(1), K.stride(2), K.stride(3),
        V.stride(0), V.stride(1), V.stride(2), V.stride(3),
        GQ.stride(0), GQ.stride(1), GQ.stride(2), GQ.stride(3),
        GK.stride(0), GK.stride(1), GK.stride(2), GK.stride(3),
        O.stride(0), O.stride(1), O.stride(2), O.stride(3),
        Z, H, M, N, scale,
        BLOCK_M=128, BLOCK_N=64,
        HEAD_DIM=Dq, VALUE_DIM=Dv,
        num_warps=num_warps, num_stages=2
    )
    return O
'''
        return {"code": code}