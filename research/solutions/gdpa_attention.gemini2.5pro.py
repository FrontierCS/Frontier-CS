import torch

class Solution:
    def solve(self, spec_path: str = None) -> dict:
        gdpa_attn_code = """
import torch
import triton
import triton.language as tl

@triton.autotune(
    configs=[
        triton.Config({'BLOCK_M': 64, 'BLOCK_N': 64, 'num_warps': 4, 'num_stages': 2}),
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 32, 'num_warps': 4, 'num_stages': 3}),
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 64, 'num_warps': 4, 'num_stages': 3}),
        triton.Config({'BLOCK_M': 64, 'BLOCK_N': 128, 'num_warps': 4, 'num_stages': 3}),
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 128, 'num_warps': 4, 'num_stages': 3}),
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 64, 'num_warps': 8, 'num_stages': 2}),
        triton.Config({'BLOCK_M': 64, 'BLOCK_N': 128, 'num_warps': 8, 'num_stages': 2}),
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 128, 'num_warps': 8, 'num_stages': 2}),
        triton.Config({'BLOCK_M': 256, 'BLOCK_N': 64, 'num_warps': 8, 'num_stages': 3}),
        triton.Config({'BLOCK_M': 64, 'BLOCK_N': 256, 'num_warps': 8, 'num_stages': 3}),
    ],
    key=['M', 'N'],
)
@triton.jit
def _gdpa_attn_kernel(
    Q_ptr, K_ptr, V_ptr, GQ_ptr, GK_ptr, O_ptr,
    stride_qz, stride_qh, stride_qm, stride_qd,
    stride_kz, stride_kh, stride_kn, stride_kd,
    stride_vz, stride_vh, stride_vn, stride_vd,
    stride_gqz, stride_gqh, stride_gqm, stride_gqd,
    stride_gkz, stride_gkh, stride_gkn, stride_gkd,
    stride_oz, stride_oh, stride_om, stride_od,
    Z, H, M, N,
    Dq: tl.constexpr, Dv: tl.constexpr,
    BLOCK_M: tl.constexpr, BLOCK_N: tl.constexpr,
):
    pid_m = tl.program_id(1)
    pid_zh = tl.program_id(0)
    
    pid_z = pid_zh // H
    pid_h = pid_zh % H

    offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
    offs_n = tl.arange(0, BLOCK_N)
    offs_d_q = tl.arange(0, Dq)
    offs_d_v = tl.arange(0, Dv)

    Q_batch_head_ptr = Q_ptr + pid_z * stride_qz + pid_h * stride_qh
    K_batch_head_ptr = K_ptr + pid_z * stride_kz + pid_h * stride_kh
    V_batch_head_ptr = V_ptr + pid_z * stride_vz + pid_h * stride_vh
    GQ_batch_head_ptr = GQ_ptr + pid_z * stride_gqz + pid_h * stride_gqh
    GK_batch_head_ptr = GK_ptr + pid_z * stride_gkz + pid_h * stride_gkh
    O_batch_head_ptr = O_ptr + pid_z * stride_oz + pid_h * stride_oh
    
    mask_m = offs_m < M

    q_ptrs = Q_batch_head_ptr + (offs_m[:, None] * stride_qm + offs_d_q[None, :] * stride_qd)
    gq_ptrs = GQ_batch_head_ptr + (offs_m[:, None] * stride_gqm + offs_d_q[None, :] * stride_gqd)

    q = tl.load(q_ptrs, mask=mask_m[:, None], other=0.0)
    gq = tl.load(gq_ptrs, mask=mask_m[:, None], other=0.0)
    
    qg = q * tl.sigmoid(gq.to(tl.float32)).to(q.dtype)

    scale = (Dq ** -0.5)
    
    acc = tl.zeros([BLOCK_M, Dv], dtype=tl.float32)
    l_i = tl.zeros([BLOCK_M], dtype=tl.float32)
    m_i = tl.full([BLOCK_M], value=float('-inf'), dtype=tl.float32)

    for start_n in range(0, tl.cdiv(N, BLOCK_N)):
        start_n_offset = start_n * BLOCK_N
        current_offs_n = start_n_offset + offs_n
        mask_n = current_offs_n < N

        k_ptrs = K_batch_head_ptr + (offs_d_q[:, None] * stride_kd + current_offs_n[None, :] * stride_kn)
        gk_ptrs = GK_batch_head_ptr + (offs_d_q[:, None] * stride_gkd + current_offs_n[None, :] * stride_gkn)
        
        k = tl.load(k_ptrs, mask=mask_n[None, :], other=0.0)
        gk = tl.load(gk_ptrs, mask=mask_n[None, :], other=0.0)
        
        kg = k * tl.sigmoid(gk.to(tl.float32)).to(k.dtype)

        v_ptrs = V_batch_head_ptr + (current_offs_n[:, None] * stride_vn + offs_d_v[None, :] * stride_vd)
        v = tl.load(v_ptrs, mask=mask_n[:, None], other=0.0)
        
        s = tl.dot(qg, kg)
        s *= scale
        s = tl.where(mask_m[:, None] & mask_n[None, :], s, float('-inf'))
        
        m_i_chunk = tl.max(s, 1)
        m_i_new = tl.maximum(m_i, m_i_chunk)
        
        alpha = tl.exp(m_i - m_i_new)
        p = tl.exp(s - m_i_new[:, None])
        
        acc *= alpha[:, None]
        l_i = l_i * alpha + tl.sum(p, 1)
        
        p = p.to(v.dtype)
        acc += tl.dot(p, v)
        
        m_i = m_i_new

    l_i_safe = tl.where(l_i > 0, l_i, 1.0)
    acc = acc / l_i_safe[:, None]
    
    acc = acc.to(O_ptr.dtype.element_ty)
    o_ptrs = O_batch_head_ptr + (offs_m[:, None] * stride_om + offs_d_v[None, :] * stride_od)
    tl.store(o_ptrs, acc, mask=mask_m[:, None])


def gdpa_attn(Q: torch.Tensor, K: torch.Tensor, V: torch.Tensor, GQ: torch.Tensor, GK: torch.Tensor) -> torch.Tensor:
    Z, H, M, Dq = Q.shape
    _, _, N, _ = K.shape
    _, _, _, Dv = V.shape
    
    assert Q.is_cuda and K.is_cuda and V.is_cuda and GQ.is_cuda and GK.is_cuda
    assert Q.dtype == torch.float16 and K.dtype == torch.float16 and V.dtype == torch.float16
    assert GQ.dtype == torch.float16 and GK.dtype == torch.float16

    O = torch.empty((Z, H, M, Dv), device=Q.device, dtype=Q.dtype)

    grid = lambda meta: (Z * H, triton.cdiv(M, meta['BLOCK_M']))

    _gdpa_attn_kernel[grid](
        Q, K, V, GQ, GK, O,
        Q.stride(0), Q.stride(1), Q.stride(2), Q.stride(3),
        K.stride(0), K.stride(1), K.stride(2), K.stride(3),
        V.stride(0), V.stride(1), V.stride(2), V.stride(3),
        GQ.stride(0), GQ.stride(1), GQ.stride(2), GQ.stride(3),
        GK.stride(0), GK.stride(1), GK.stride(2), GK.stride(3),
        O.stride(0), O.stride(1), O.stride(2), O.stride(3),
        Z, H, M, N,
        Dq=Dq, Dv=Dv
    )

    return O
"""
        return {"code": gdpa_attn_code}
