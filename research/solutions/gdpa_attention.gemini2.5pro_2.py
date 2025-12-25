import torch
import triton
import triton.language as tl

class Solution:
    def solve(self, spec_path: str = None) -> dict:
        kernel_code = """
import torch
import triton
import triton.language as tl

@triton.autotune(
    configs=[
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 64}, num_stages=3, num_warps=8),
        triton.Config({'BLOCK_M': 64, 'BLOCK_N': 64}, num_stages=4, num_warps=4),
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 32}, num_stages=4, num_warps=4),
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 128}, num_stages=3, num_warps=8),
        triton.Config({'BLOCK_M': 64, 'BLOCK_N': 128}, num_stages=3, num_warps=8),
        triton.Config({'BLOCK_M': 256, 'BLOCK_N': 64}, num_stages=3, num_warps=8),
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 64}, num_stages=2, num_warps=4),
        triton.Config({'BLOCK_M': 256, 'BLOCK_N': 128}, num_stages=3, num_warps=8),
    ],
    key=['M', 'N', 'Dq', 'Dv'],
)
@triton.jit
def _gdpa_kernel(
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
    start_m = tl.program_id(1)
    zh_id = tl.program_id(0)
    
    z = zh_id // H
    h = zh_id % H
    
    offs_m = start_m * BLOCK_M + tl.arange(0, BLOCK_M)
    offs_d_q = tl.arange(0, Dq)
    offs_d_v = tl.arange(0, Dv)

    Q_base_ptr = Q_ptr + z * stride_qz + h * stride_qh
    K_base_ptr = K_ptr + z * stride_kz + h * stride_kh
    V_base_ptr = V_ptr + z * stride_vz + h * stride_vh
    GQ_base_ptr = GQ_ptr + z * stride_gqz + h * stride_gqh
    GK_base_ptr = GK_ptr + z * stride_gkz + h * stride_gkh

    m_mask = offs_m < M
    q_offs = offs_m[:, None] * stride_qm + offs_d_q[None, :] * stride_qd
    gq_offs = offs_m[:, None] * stride_gqm + offs_d_q[None, :] * stride_gqd
    q = tl.load(Q_base_ptr + q_offs, mask=m_mask[:, None], other=0.0)
    gq = tl.load(GQ_base_ptr + gq_offs, mask=m_mask[:, None], other=0.0)
    
    q_gated = q * tl.sigmoid(gq.to(tl.float32)).to(q.dtype)
    
    acc = tl.zeros([BLOCK_M, Dv], dtype=tl.float32)
    l_i = tl.full([BLOCK_M], value=float('-inf'), dtype=tl.float32)
    m_i = tl.zeros([BLOCK_M], dtype=tl.float32)

    scale = (1.0 / Dq**0.5)

    for start_n in range(0, tl.cdiv(N, BLOCK_N)):
        offs_n = start_n * BLOCK_N + tl.arange(0, BLOCK_N)
        n_mask = offs_n < N

        k_offs = offs_n[:, None] * stride_kn + offs_d_q[None, :] * stride_kd
        gk_offs = offs_n[:, None] * stride_gkn + offs_d_q[None, :] * stride_kd
        k = tl.load(K_base_ptr + k_offs, mask=n_mask[:, None], other=0.0)
        gk = tl.load(GK_base_ptr + gk_offs, mask=n_mask[:, None], other=0.0)
        
        k_gated = k * tl.sigmoid(gk.to(tl.float32)).to(k.dtype)
        
        s_ij = tl.dot(q_gated, tl.trans(k_gated))
        s_ij *= scale
        s_ij = tl.where(m_mask[:, None] & n_mask[None, :], s_ij, float('-inf'))
        
        m_ij = tl.maximum(l_i, tl.max(s_ij, 1))
        p_ij = tl.exp(s_ij - m_ij[:, None])
        sum_p_ij = tl.sum(p_ij, 1)
        
        scale_old = tl.exp(l_i - m_ij)
        acc = acc * scale_old[:, None]
        m_i = m_i * scale_old
        
        v_offs = offs_n[:, None] * stride_vn + offs_d_v[None, :] * stride_vd
        v = tl.load(V_base_ptr + v_offs, mask=n_mask[:, None], other=0.0)
        
        p_ij = p_ij.to(v.dtype)
        acc += tl.dot(p_ij, v)
        
        m_i += sum_p_ij
        l_i = m_ij
        
    output = tl.where(m_i[:, None] == 0, 0, acc / m_i[:, None])
    
    O_base_ptr = O_ptr + z * stride_oz + h * stride_oh
    o_offs = offs_m[:, None] * stride_om + offs_d_v[None, :] * stride_od
    tl.store(O_base_ptr + o_offs, output.to(O_ptr.dtype.element_ty), mask=m_mask[:, None])

def gdpa_attn(Q: torch.Tensor, K: torch.Tensor, V: torch.Tensor, GQ: torch.Tensor, GK: torch.Tensor) -> torch.Tensor:
    Z, H, M, Dq = Q.shape
    _, _, N, Dv = V.shape
    
    assert Dq == K.shape[3] and Dv == V.shape[3] and GK.shape == K.shape and GQ.shape == Q.shape

    O = torch.empty((Z, H, M, Dv), device=Q.device, dtype=Q.dtype)

    grid = lambda meta: (Z * H, triton.cdiv(M, meta['BLOCK_M']))

    _gdpa_kernel[grid](
        Q, K, V, GQ, GK, O,
        Q.stride(0), Q.stride(1), Q.stride(2), Q.stride(3),
        K.stride(0), K.stride(1), K.stride(2), K.stride(3),
        V.stride(0), V.stride(1), V.stride(2), V.stride(3),
        GQ.stride(0), GQ.stride(1), GQ.stride(2), GQ.stride(3),
        GK.stride(0), GK.stride(1), GK.stride(2), GK.stride(3),
        O.stride(0), O.stride(1), O.stride(2), O.stride(3),
        Z, H, M, N,
        Dq=Dq, Dv=Dv,
    )
    return O
"""
        return {"code": kernel_code}
