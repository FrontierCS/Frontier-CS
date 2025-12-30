import torch
import triton
import triton.language as tl
import math

class Solution:
    def solve(self, spec_path: str = None) -> dict:
        code = """
import torch
import triton
import triton.language as tl
import math

@triton.jit
def flash_kernel(
    Q, K, V, O,
    stride_qb, stride_qm, stride_qd,
    stride_kb, stride_kn, stride_kd,
    stride_vb, stride_vn, stride_vd,
    stride_ob, stride_om, stride_od,
    M, N, Dq, Dv,
    scale: tl.float32,
    causal: tl.int32,
    BLOCK_M: tl.constexpr,
    BLOCK_N: tl.constexpr
):
    pid_b = tl.program_id(0)
    pid_m = tl.program_id(1)
    offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
    m_mask = offs_m < M
    q_offsets = (pid_b, pid_m * BLOCK_M, 0)
    q_ptr = tl.make_block_ptr(
        base=Q,
        shape=(M, N, Dq),  # Note: shape uses M, N but actually B is implicit in strides
        strides=(stride_qb, stride_qm, stride_qd),
        offsets=q_offsets,
        block_shape=(1, BLOCK_M, Dq),
        order=(0, 1, 2)
    )
    q = tl.load(q_ptr, boundary_check=(False, True, False), other=0.0)
    q = tl.cast(q[0], tl.float32)
    q = tl.where(m_mask[:, None], q, 0.0)
    m = tl.full((BLOCK_M,), float('-inf'), tl.float32)
    m = tl.where(m_mask, m, 0.0)
    l = tl.zeros((BLOCK_M,), tl.float32)
    o_acc = tl.zeros((BLOCK_M, Dv), tl.float32)
    offs_n_base = tl.arange(0, BLOCK_N)
    # First pass: compute stats
    for start_n in range(0, N, BLOCK_N):
        offs_n = start_n + offs_n_base
        n_mask = offs_n < N
        k_offsets = (pid_b, start_n, 0)
        k_ptr = tl.make_block_ptr(
            base=K,
            shape=(M, N, Dq),
            strides=(stride_kb, stride_kn, stride_kd),
            offsets=k_offsets,
            block_shape=(1, BLOCK_N, Dq),
            order=(0, 1, 2)
        )
        k = tl.load(k_ptr, boundary_check=(False, True, False), other=0.0)
        k = tl.cast(k[0], tl.float32)
        k = tl.where(n_mask[:, None], k, 0.0)
        s = tl.dot(q, tl.trans(k)) * scale
        if causal:
            q_pos = offs_m[:, None]
            k_pos = offs_n[None, :]
            imask = k_pos > q_pos
            s = tl.where(imask, float('-inf'), s)
        m_s = tl.max(s, axis=1)
        m_s = tl.where(m_mask, m_s, float('-inf'))
        m_new = tl.maximum(m, m_s)
        p = tl.exp(s - m_new[:, None]) * m_mask[:, None].to(tl.float32)
        l_new = l * tl.exp(m - m_new) + tl.sum(p, axis=1)
        m = m_new
        l = l_new
    # Second pass: compute output
    for start_n in range(0, N, BLOCK_N):
        offs_n = start_n + offs_n_base
        n_mask = offs_n < N
        k_offsets = (pid_b, start_n, 0)
        k_ptr = tl.make_block_ptr(
            base=K,
            shape=(M, N, Dq),
            strides=(stride_kb, stride_kn, stride_kd),
            offsets=k_offsets,
            block_shape=(1, BLOCK_N, Dq),
            order=(0, 1, 2)
        )
        k = tl.load(k_ptr, boundary_check=(False, True, False), other=0.0)
        k = tl.cast(k[0], tl.float32)
        k = tl.where(n_mask[:, None], k, 0.0)
        s = tl.dot(q, tl.trans(k)) * scale
        if causal:
            q_pos = offs_m[:, None]
            k_pos = offs_n[None, :]
            imask = k_pos > q_pos
            s = tl.where(imask, float('-inf'), s)
        p = tl.exp(s - m[:, None]) * m_mask[:, None].to(tl.float32)
        v_offsets = (pid_b, start_n, 0)
        v_ptr = tl.make_block_ptr(
            base=V,
            shape=(M, N, Dv),
            strides=(stride_vb, stride_vn, stride_vd),
            offsets=v_offsets,
            block_shape=(1, BLOCK_N, Dv),
            order=(0, 1, 2)
        )
        v = tl.load(v_ptr, boundary_check=(False, True, False), other=0.0)
        v = tl.cast(v[0], tl.float32)
        v = tl.where(n_mask[:, None], v, 0.0)
        o_delta = tl.dot(p, v)
        o_acc += o_delta
    o_final = tl.where(l[:, None] > 0, o_acc / l[:, None], 0.0)
    o_out = tl.cast(o_final, tl.float16)
    o_offsets = (pid_b, pid_m * BLOCK_M, 0)
    o_ptr = tl.make_block_ptr(
        base=O,
        shape=(M, N, Dv),
        strides=(stride_ob, stride_om, stride_od),
        offsets=o_offsets,
        block_shape=(1, BLOCK_M, Dv),
        order=(0, 1, 2)
    )
    tl.store(o_ptr, tl.expand_dims(o_out, 0), boundary_check=(False, True, False))

def flash_attn(Q: torch.Tensor, K: torch.Tensor, V: torch.Tensor, causal: bool = True) -> torch.Tensor:
    Z, H, M, Dq = Q.shape
    _, _, N, Dv = V.shape
    B = Z * H
    q = Q.view(B, M, Dq)
    k = K.view(B, N, Dq)
    v = V.view(B, N, Dv)
    o = torch.empty(B, M, Dv, dtype=torch.float16, device=Q.device)
    scale = 1.0 / math.sqrt(Dq)
    BLOCK_M = 128
    BLOCK_N = 128
    grid = (B, (M + BLOCK_M - 1) // BLOCK_M)
    flash_kernel[grid](
        q, k, v, o,
        stride_qb=q.stride(0), stride_qm=q.stride(1), stride_qd=q.stride(2),
        stride_kb=k.stride(0), stride_kn=k.stride(1), stride_kd=k.stride(2),
        stride_vb=v.stride(0), stride_vn=v.stride(1), stride_vd=v.stride(2),
        stride_ob=o.stride(0), stride_om=o.stride(1), stride_od=o.stride(2),
        M=M, N=N, Dq=Dq, Dv=Dv,
        scale=scale,
        causal=int(causal),
        BLOCK_M=BLOCK_M,
        BLOCK_N=BLOCK_N
    )
    out = o.view(Z, H, M, Dv)
    return out
"""
        return {"code": code}