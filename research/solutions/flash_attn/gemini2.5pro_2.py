import torch
import triton

class Solution:
    def solve(self, spec_path: str = None) -> dict:
        flash_attention_code = r"""
import torch
import triton
import triton.language as tl

@triton.autotune(
    configs=[
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 64, 'num_warps': 4, 'num_stages': 2}),
        triton.Config({'BLOCK_M': 256, 'BLOCK_N': 32, 'num_warps': 4, 'num_stages': 3}),
        triton.Config({'BLOCK_M': 256, 'BLOCK_N': 64, 'num_warps': 8, 'num_stages': 3}),
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 128, 'num_warps': 8, 'num_stages': 3}),
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 64, 'num_warps': 8, 'num_stages': 4}),
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 32, 'num_warps': 4, 'num_stages': 4}),
        triton.Config({'BLOCK_M': 64, 'BLOCK_N': 128, 'num_warps': 4, 'num_stages': 3}),
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 128, 'num_warps': 4, 'num_stages': 4}),
    ],
    key=['M', 'N', 'Dq', 'Dv', 'IS_CAUSAL'],
)
@triton.jit
def _fwd_kernel(
    Q, K, V, O,
    s_qz, s_qh, s_qm, s_qd,
    s_kz, s_kh, s_kn, s_kd,
    s_vz, s_vh, s_vn, s_vd,
    s_oz, s_oh, s_om, s_od,
    Z, H, M, N,
    softmax_scale,
    IS_CAUSAL: tl.constexpr,
    Dq: tl.constexpr,
    Dv: tl.constexpr,
    BLOCK_M: tl.constexpr,
    BLOCK_N: tl.constexpr,
):
    pid_m = tl.program_id(0)
    pid_zh = tl.program_id(1)
    
    pid_z = pid_zh // H
    pid_h = pid_zh % H

    q_base = Q + pid_z * s_qz + pid_h * s_qh
    k_base = K + pid_z * s_kz + pid_h * s_kh
    v_base = V + pid_z * s_vz + pid_h * s_vh
    o_base = O + pid_z * s_oz + pid_h * s_oh

    offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
    offs_n_init = tl.arange(0, BLOCK_N)
    offs_d_qk = tl.arange(0, Dq)
    offs_d_v = tl.arange(0, Dv)

    q_ptrs = q_base + offs_m[:, None] * s_qm + offs_d_qk[None, :] * s_qd
    
    acc = tl.zeros([BLOCK_M, Dv], dtype=tl.float32)
    m_i = tl.full([BLOCK_M], value=-float('inf'), dtype=tl.float32)
    l_i = tl.zeros([BLOCK_M], dtype=tl.float32)

    mask_m = offs_m < M
    q = tl.load(q_ptrs, mask=mask_m[:, None], other=0.0)

    end_n = (pid_m + 1) * BLOCK_M if IS_CAUSAL else N
    
    for start_n in range(0, end_n, BLOCK_N):
        offs_n = start_n + offs_n_init
        
        k_ptrs = k_base + offs_d_qk[:, None] * s_kd + offs_n[None, :] * s_kn
        v_ptrs = v_base + offs_n[:, None] * s_vn + offs_d_v[None, :] * s_vd

        mask_n = offs_n < N
        k = tl.load(k_ptrs, mask=mask_n[None, :], other=0.0)
        v = tl.load(v_ptrs, mask=mask_n[:, None], other=0.0)
        
        s = tl.dot(q, k)
        s = s * softmax_scale
        
        if IS_CAUSAL:
            s = tl.where(offs_m[:, None] >= offs_n[None, :], s, -float('inf'))

        m_j = tl.max(s, axis=1)
        m_new = tl.maximum(m_i, m_j)
        
        alpha = tl.exp(m_i - m_new)
        p = tl.exp(s - m_new[:, None])
        
        l_i_new = alpha * l_i + tl.sum(p, axis=1)
        
        acc = acc * alpha[:, None]
        p_typed = p.to(v.dtype)
        acc = acc + tl.dot(p_typed, v)
        
        l_i = l_i_new
        m_i = m_new

    l_i_reciprocal = 1.0 / l_i
    l_i_reciprocal = tl.where(l_i == 0, 0.0, l_i_reciprocal)
    o = acc * l_i_reciprocal[:, None]
    
    o_ptrs = o_base + offs_m[:, None] * s_om + offs_d_v[None, :] * s_od
    tl.store(o_ptrs, o.to(O.dtype.element_ty), mask=mask_m[:, None])


def flash_attn(Q: torch.Tensor, K: torch.Tensor, V: torch.Tensor, causal: bool = True) -> torch.Tensor:
    """
    Flash attention computation with optional causal masking.
    
    Args:
        Q: Input tensor of shape (Z, H, M, Dq) - query tensor (float16)
        K: Input tensor of shape (Z, H, N, Dq) - key tensor (float16)
        V: Input tensor of shape (Z, H, N, Dv) - value tensor (float16)
        causal: Whether to apply causal masking (default True)
    
    Returns:
        Output tensor of shape (Z, H, M, Dv) - attention output (float16)
    """
    Z, H, M, Dq = Q.shape
    _, _, N, Dv = V.shape
    
    O = torch.empty((Z, H, M, Dv), device=Q.device, dtype=Q.dtype)
    
    softmax_scale = Dq ** -0.5
    
    grid = lambda META: (triton.cdiv(M, META['BLOCK_M']), Z * H)
    
    _fwd_kernel[grid](
        Q, K, V, O,
        Q.stride(0), Q.stride(1), Q.stride(2), Q.stride(3),
        K.stride(0), K.stride(1), K.stride(2), K.stride(3),
        V.stride(0), V.stride(1), V.stride(2), V.stride(3),
        O.stride(0), O.stride(1), O.stride(2), O.stride(3),
        Z, H, M, N,
        softmax_scale,
        IS_CAUSAL=causal,
        Dq=Dq,
        Dv=Dv
    )
    
    return O
"""
        return {"code": flash_attention_code}