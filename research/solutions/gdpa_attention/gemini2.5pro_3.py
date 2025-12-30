import torch
import triton
import triton.language as tl
import math

_GDPA_ATTN_KERNEL_CODE = """
import torch
import triton
import triton.language as tl
import math

@triton.autotune(
    configs=[
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 64, 'BLOCK_Dq': 64, 'BLOCK_Dv': 64}, num_stages=4, num_warps=4),
        triton.Config({'BLOCK_M': 256, 'BLOCK_N': 64, 'BLOCK_Dq': 64, 'BLOCK_Dv': 64}, num_stages=3, num_warps=8),
        triton.Config({'BLOCK_M': 64, 'BLOCK_N': 256, 'BLOCK_Dq': 64, 'BLOCK_Dv': 64}, num_stages=3, num_warps=8),
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 128, 'BLOCK_Dq': 64, 'BLOCK_Dv': 64}, num_stages=3, num_warps=8),
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 64, 'BLOCK_Dq': 64, 'BLOCK_Dv': 64}, num_stages=3, num_warps=8),
        triton.Config({'BLOCK_M': 64, 'BLOCK_N': 128, 'BLOCK_Dq': 64, 'BLOCK_Dv': 64}, num_stages=4, num_warps=4),
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 32, 'BLOCK_Dq': 64, 'BLOCK_Dv': 64}, num_stages=5, num_warps=4),
        triton.Config({'BLOCK_M': 64, 'BLOCK_N': 32, 'BLOCK_Dq': 64, 'BLOCK_Dv': 64}, num_stages=5, num_warps=4),
        triton.Config({'BLOCK_M': 256, 'BLOCK_N': 128, 'BLOCK_Dq': 64, 'BLOCK_Dv': 64}, num_stages=3, num_warps=8),
    ],
    key=['M', 'N', 'Dq', 'Dv'],
)
@triton.jit
def _gdpa_forward_kernel(
    Q_ptr, K_ptr, V_ptr, GQ_ptr, GK_ptr, O_ptr,
    q_stride_z, q_stride_h, q_stride_m, q_stride_d,
    k_stride_z, k_stride_h, k_stride_n, k_stride_d,
    v_stride_z, v_stride_h, v_stride_n, v_stride_d,
    gq_stride_z, gq_stride_h, gq_stride_m, gq_stride_d,
    gk_stride_z, gk_stride_h, gk_stride_n, gk_stride_d,
    o_stride_z, o_stride_h, o_stride_m, o_stride_d,
    Z, H, M, N,
    Dq, Dv,
    scale,
    BLOCK_M: tl.constexpr, BLOCK_N: tl.constexpr,
    BLOCK_Dq: tl.constexpr, BLOCK_Dv: tl.constexpr
):
    pid_m = tl.program_id(0)
    pid_zh = tl.program_id(1)
    
    pid_z = pid_zh // H
    pid_h = pid_zh % H

    Q_ptr += pid_z * q_stride_z + pid_h * q_stride_h
    K_ptr += pid_z * k_stride_z + pid_h * k_stride_h
    V_ptr += pid_z * v_stride_z + pid_h * v_stride_h
    GQ_ptr += pid_z * gq_stride_z + pid_h * gq_stride_h
    GK_ptr += pid_z * gk_stride_z + pid_h * gk_stride_h
    O_ptr += pid_z * o_stride_z + pid_h * o_stride_h

    offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
    offs_d_q = tl.arange(0, BLOCK_Dq)
    offs_d_v = tl.arange(0, BLOCK_Dv)
    
    q_ptrs = Q_ptr + (offs_m[:, None] * q_stride_m + offs_d_q[None, :] * q_stride_d)
    gq_ptrs = GQ_ptr + (offs_m[:, None] * gq_stride_m + offs_d_q[None, :] * gq_stride_d)
    
    m_mask = offs_m < M
    q = tl.load(q_ptrs, mask=m_mask[:, None], other=0.0)
    gq = tl.load(gq_ptrs, mask=m_mask[:, None], other=0.0)
    qg = (q * tl.sigmoid(gq.to(tl.float32))).to(q.dtype)
    
    acc = tl.zeros([BLOCK_M, BLOCK_Dv], dtype=tl.float32)
    m_i = tl.zeros([BLOCK_M], dtype=tl.float32) - float('inf')
    l_i = tl.zeros([BLOCK_M], dtype=tl.float32)

    for start_n in range(0, N, BLOCK_N):
        offs_n = start_n + tl.arange(0, BLOCK_N)
        n_mask = offs_n < N

        k_ptrs = K_ptr + (offs_n[None, :] * k_stride_n + offs_d_q[:, None] * k_stride_d)
        gk_ptrs = GK_ptr + (offs_n[None, :] * gk_stride_n + offs_d_q[:, None] * gk_stride_d)
        v_ptrs = V_ptr + (offs_n[:, None] * v_stride_n + offs_d_v[None, :] * v_stride_d)

        k = tl.load(k_ptrs, mask=n_mask[None, :], other=0.0)
        gk = tl.load(gk_ptrs, mask=n_mask[None, :], other=0.0)
        kg = (k * tl.sigmoid(gk.to(tl.float32))).to(k.dtype)
        
        v = tl.load(v_ptrs, mask=n_mask[:, None], other=0.0)

        s = tl.dot(qg, kg) * scale
        s = tl.where(n_mask[None, :], s, -float('inf'))

        m_i_new = tl.maximum(m_i, tl.max(s, 1))
        p_new = tl.exp(s - m_i_new[:, None])
        alpha = tl.exp(m_i - m_i_new)
        
        l_i = alpha * l_i + tl.sum(p_new, 1)
        
        acc = acc * alpha[:, None]
        
        p_new = p_new.to(v.dtype)
        acc += tl.dot(p_new, v)
        
        m_i = m_i_new

    acc = acc / l_i[:, None]

    o_ptrs = O_ptr + (offs_m[:, None] * o_stride_m + offs_d_v[None, :] * o_stride_d)
    tl.store(o_ptrs, acc.to(Q_ptr.dtype.element_ty), mask=m_mask[:, None])


def gdpa_attn(Q: torch.Tensor, K: torch.Tensor, V: torch.Tensor, GQ: torch.Tensor, GK: torch.Tensor) -> torch.Tensor:
    Z, H, M, Dq = Q.shape
    _, _, N, Dv = V.shape
    
    O = torch.empty((Z, H, M, Dv), device=Q.device, dtype=V.dtype)
    
    scale = 1.0 / math.sqrt(Dq)
    
    def grid(metas):
        return (triton.cdiv(M, metas['BLOCK_M']), Z * H)

    _gdpa_forward_kernel[grid](
        Q, K, V, GQ, GK, O,
        Q.stride(0), Q.stride(1), Q.stride(2), Q.stride(3),
        K.stride(0), K.stride(1), K.stride(2), K.stride(3),
        V.stride(0), V.stride(1), V.stride(2), V.stride(3),
        GQ.stride(0), GQ.stride(1), GQ.stride(2), GQ.stride(3),
        GK.stride(0), GK.stride(1), GK.stride(2), GK.stride(3),
        O.stride(0), O.stride(1), O.stride(2), O.stride(3),
        Z, H, M, N,
        Dq, Dv,
        scale,
    )
    return O
"""

class Solution:
    def solve(self, spec_path: str = None) -> dict:
        """
        Returns a dict with either:
        - {"code": "python_code_string"}
        - {"program_path": "path/to/kernel.py"}
        """
        return {"code": _GDPA_ATTN_KERNEL_CODE}