class Solution:
    def solve(self, spec_path: str = None) -> dict:
        code = """
import torch
import triton
import triton.language as tl
import math

@triton.jit
def attention_kernel(
    Q_ptr, GQ_ptr, K_ptr, GK_ptr, V_ptr, O_ptr,
    stride_qz, stride_qh, stride_qm, stride_qd,
    stride_kz, stride_kh, stride_kn, stride_kd,
    stride_vz, stride_vh, stride_vn, stride_vd,
    stride_oz, stride_oh, stride_om, stride_od,
    M, N, Dq, Dv,
    scale,
    BLOCK_M: tl.constexpr,
    BLOCK_N: tl.constexpr,
    D_MODEL: tl.constexpr
):
    pid_z = tl.program_id(0)
    pid_h = tl.program_id(1)
    pid_m = tl.program_id(2)
    block_m = tl.arange(0, BLOCK_M)
    offs_m = pid_m * BLOCK_M + block_m
    offs_d = tl.arange(0, D_MODEL)
    q_offsets = (offs_m[:, None] * stride_qm + offs_d[None, :] * stride_qd).to(tl.int32)
    q_base = (Q_ptr + pid_z * stride_qz + pid_h * stride_qh).to(tl.int32)
    q_ptrs = q_base + q_offsets
    m_mask = offs_m < M
    q_mask = m_mask[:, None] & (offs_d[None, :] < Dq)
    q = tl.load(q_ptrs, mask=q_mask, other=0.0, dtype=tl.float16)
    gq_base = (GQ_ptr + pid_z * stride_qz + pid_h * stride_qh).to(tl.int32)
    gq_ptrs = gq_base + q_offsets
    gq = tl.load(gq_ptrs, mask=q_mask, other=0.0, dtype=tl.float16)
    qg = q * tl.sigmoid(gq)
    o = tl.zeros((BLOCK_M, D_MODEL), dtype=tl.float32)
    l = tl.zeros((BLOCK_M,), dtype=tl.float32)
    m = tl.full((BLOCK_M,), -1e9, dtype=tl.float32)
    start_n = 0
    while start_n < N:
        block_n = tl.arange(0, BLOCK_N)
        offs_n_current = start_n + block_n
        n_mask = offs_n_current < N
        k_offsets = (offs_n_current[:, None] * stride_kn + offs_d[None, :] * stride_kd).to(tl.int32)
        k_base = (K_ptr + pid_z * stride_kz + pid_h * stride_kh).to(tl.int32)
        k_ptrs = k_base + k_offsets
        k_mask = n_mask[:, None] & (offs_d[None, :] < Dq)
        k = tl.load(k_ptrs, mask=k_mask, other=0.0, dtype=tl.float16)
        gk_base = (GK_ptr + pid_z * stride_kz + pid_h * stride_kh).to(tl.int32)
        gk_ptrs = gk_base + k_offsets
        gk = tl.load(gk_ptrs, mask=k_mask, other=0.0, dtype=tl.float16)
        kg = k * tl.sigmoid(gk)
        v_offsets = (offs_n_current[:, None] * stride_vn + offs_d[None, :] * stride_vd).to(tl.int32)
        v_base = (V_ptr + pid_z * stride_vz + pid_h * stride_vh).to(tl.int32)
        v_ptrs = v_base + v_offsets
        v_mask = n_mask[:, None] & (offs_d[None, :] < Dv)
        v = tl.load(v_ptrs, mask=v_mask, other=0.0, dtype=tl.float16)
        s = tl.dot(qg.to(tl.float32), tl.trans(kg.to(tl.float32))) * scale
        s = tl.where(n_mask[None, :], s, -1e9)
        m_curr = tl.max(s, 1)
        m_new = tl.maximum(m, m_curr)
        p = tl.exp(s - m_new[:, None])
        o_delta = tl.dot(p, v.to(tl.float32))
        exp_scale = tl.exp(m - m_new)
        o = o * exp_scale[:, None] + o_delta
        l_curr = tl.sum(p, 1)
        l = l * exp_scale + l_curr
        m = m_new
        start_n += BLOCK_N
    o_final = tl.where(m_mask[:, None], o / l[:, None], 0.0)
    offs_dv = tl.arange(0, D_MODEL)
    o_offsets = (offs_m[:, None] * stride_om + offs_dv[None, :] * stride_od).to(tl.int32)
    o_base = (O_ptr + pid_z * stride_oz + pid_h * stride_oh).to(tl.int32)
    o_ptrs = o_base + o_offsets
    o_mask = m_mask[:, None] & (offs_dv[None, :] < Dv)
    tl.store(o_ptrs, o_final.to(tl.float16), mask=o_mask)

def gdpa_attn(Q: torch.Tensor, K: torch.Tensor, V: torch.Tensor, GQ: torch.Tensor, GK: torch.Tensor) -> torch.Tensor:
    Z, H, M, Dq = Q.shape
    _, _, N, _ = K.shape
    _, _, _, Dv = V.shape
    scale = 1 / math.sqrt(Dq)
    O = torch.empty((Z, H, M, Dv), dtype=Q.dtype, device=Q.device)
    BLOCK_M = 128
    BLOCK_N = 64
    D_MODEL = 64
    num_blocks_m = (M + BLOCK_M - 1) // BLOCK_M
    grid = (Z, H, num_blocks_m)
    stride_qz = Q.stride(0)
    stride_qh = Q.stride(1)
    stride_qm = Q.stride(2)
    stride_qd = Q.stride(3)
    stride_kz = K.stride(0)
    stride_kh = K.stride(1)
    stride_kn = K.stride(2)
    stride_kd = K.stride(3)
    stride_vz = V.stride(0)
    stride_vh = V.stride(1)
    stride_vn = V.stride(2)
    stride_vd = V.stride(3)
    stride_oz = O.stride(0)
    stride_oh = O.stride(1)
    stride_om = O.stride(2)
    stride_od = O.stride(3)
    attention_kernel[grid](
        Q, GQ, K, GK, V, O,
        stride_qz, stride_qh, stride_qm, stride_qd,
        stride_kz, stride_kh, stride_kn, stride_kd,
        stride_vz, stride_vh, stride_vn, stride_vd,
        stride_oz, stride_oh, stride_om, stride_od,
        M, N, Dq, Dv,
        scale,
        BLOCK_M=BLOCK_M,
        BLOCK_N=BLOCK_N,
        D_MODEL=D_MODEL,
    )
    return O
"""
        return {"code": code}