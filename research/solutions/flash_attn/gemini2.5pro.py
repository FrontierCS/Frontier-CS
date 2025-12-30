import torch
import triton
import triton.language as tl

class Solution:
    def solve(self, spec_path: str = None) -> dict:
        flash_attn_code = """
import torch
import triton
import triton.language as tl

@triton.autotune(
    configs=[
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 64}, num_warps=4, num_stages=3),
        triton.Config({'BLOCK_M': 256, 'BLOCK_N': 64}, num_warps=8, num_stages=3),
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 128}, num_warps=8, num_stages=3),
        triton.Config({'BLOCK_M': 64, 'BLOCK_N': 64}, num_warps=4, num_stages=4),
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 32}, num_warps=4, num_stages=4),
        triton.Config({'BLOCK_M': 256, 'BLOCK_N': 128}, num_warps=8, num_stages=2),
    ],
    key=['causal', 'M', 'N'],
)
@triton.jit
def _flash_attn_kernel(
    Q, K, V, O,
    stride_qz, stride_qh, stride_qm, stride_qk,
    stride_kz, stride_kh, stride_kn, stride_kk,
    stride_vz, stride_vh, stride_vn, stride_vk,
    stride_oz, stride_oh, stride_om, stride_ok,
    Z, H, N, M,
    Dq, Dv,
    softmax_scale,
    causal: tl.constexpr,
    BLOCK_M: tl.constexpr,
    BLOCK_N: tl.constexpr,
    BLOCK_Dq: tl.constexpr,
    BLOCK_Dv: tl.constexpr,
):
    pid_m = tl.program_id(0)
    pid_zh = tl.program_id(1)
    
    pid_z = pid_zh // H
    pid_h = pid_zh % H
    
    offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
    offs_d = tl.arange(0, BLOCK_Dq)
    
    q_ptrs = Q + pid_z * stride_qz + pid_h * stride_qh + offs_m[:, None] * stride_qm + offs_d[None, :] * stride_qk
    
    m_mask = offs_m < M
    q = tl.load(q_ptrs, mask=m_mask[:, None], other=0.0)
    q = (q * softmax_scale).to(Q.dtype.element_ty)

    m_i = tl.full([BLOCK_M], -float('inf'), dtype=tl.float32)
    l_i = tl.zeros([BLOCK_M], dtype=tl.float32)
    acc = tl.zeros([BLOCK_M, BLOCK_Dv], dtype=tl.float32)
    
    k_ptrs_base = K + pid_z * stride_kz + pid_h * stride_kh
    v_ptrs_base = V + pid_z * stride_vz + pid_h * stride_vh
    
    offs_n = tl.arange(0, BLOCK_N)
    
    loop_end = (pid_m + 1) * BLOCK_M if causal else N
    
    for start_n in range(0, loop_end, BLOCK_N):
        current_offs_n = start_n + offs_n
        n_mask = current_offs_n < N
        
        k_ptrs = k_ptrs_base + (current_offs_n[:, None] * stride_kn + offs_d[None, :] * stride_kk)
        k = tl.load(k_ptrs, mask=n_mask[:, None], other=0.0)

        s = tl.dot(q, k, trans_b=True)
        
        if causal:
            causal_mask = offs_m[:, None] >= current_offs_n[None, :]
            s = tl.where(causal_mask, s, -float('inf'))
        
        m_ij = tl.max(s, axis=1)
        m_new = tl.maximum(m_i, m_ij)
        
        alpha = tl.exp(m_i - m_new)
        p = tl.exp(s.to(tl.float32) - m_new[:, None])
        
        l_i_new = l_i * alpha + tl.sum(p, axis=1)
        
        acc = acc * alpha[:, None]
        
        offs_dv = tl.arange(0, BLOCK_Dv)
        v_ptrs = v_ptrs_base + (current_offs_n[:, None] * stride_vn + offs_dv[None, :] * stride_vk)
        v = tl.load(v_ptrs, mask=n_mask[:, None], other=0.0)
        
        p = p.to(V.dtype.element_ty)
        acc += tl.dot(p, v)
        
        m_i = m_new
        l_i = l_i_new

    l_i_safe = tl.where(l_i == 0, 1.0, l_i)
    acc = acc / l_i_safe[:, None]
    
    offs_dv = tl.arange(0, BLOCK_Dv)
    o_ptrs = O + pid_z * stride_oz + pid_h * stride_oh + offs_m[:, None] * stride_om + offs_dv[None, :] * stride_ok
    tl.store(o_ptrs, acc.to(O.dtype.element_ty), mask=m_mask[:, None])

def flash_attn(Q: torch.Tensor, K: torch.Tensor, V: torch.Tensor, causal: bool = True) -> torch.Tensor:
    Z, H, M, Dq = Q.shape
    _, _, N, _ = K.shape
    _, _, _, Dv = V.shape
    
    O = torch.empty((Z, H, M, Dv), device=Q.device, dtype=Q.dtype)

    softmax_scale = Dq**-0.5
    
    grid = lambda meta: (triton.cdiv(M, meta['BLOCK_M']), Z * H)

    _flash_attn_kernel[grid](
        Q, K, V, O,
        Q.stride(0), Q.stride(1), Q.stride(2), Q.stride(3),
        K.stride(0), K.stride(1), K.stride(2), K.stride(3),
        V.stride(0), V.stride(1), V.stride(2), V.stride(3),
        O.stride(0), O.stride(1), O.stride(2), O.stride(3),
        Z, H, N, M,
        Dq, Dv,
        softmax_scale,
        causal=causal,
        BLOCK_Dq=Dq,
        BLOCK_Dv=Dv,
    )
    return O
"""
        return {"code": flash_attn_code}