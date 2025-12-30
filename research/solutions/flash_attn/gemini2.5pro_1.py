import torch
import triton
import triton.language as tl
import math

class Solution:
    def solve(self, spec_path: str = None) -> dict:
        kernel_code = """
import math
import torch
import triton
import triton.language as tl

@triton.autotune(
    configs=[
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 64, 'num_stages': 3, 'num_warps': 8}),
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 64, 'num_stages': 4, 'num_warps': 4}),
        triton.Config({'BLOCK_M': 256, 'BLOCK_N': 64, 'num_stages': 3, 'num_warps': 8}),
        triton.Config({'BLOCK_M': 256, 'BLOCK_N': 32, 'num_stages': 3, 'num_warps': 8}),
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 128, 'num_stages': 2, 'num_warps': 8}),
        triton.Config({'BLOCK_M': 64,  'BLOCK_N': 64, 'num_stages': 4, 'num_warps': 4}),
        triton.Config({'BLOCK_M': 64,  'BLOCK_N': 128, 'num_stages': 3, 'num_warps': 4}),
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 32, 'num_stages': 5, 'num_warps': 4}),
    ],
    key=['causal', 'M', 'N', 'Dq', 'Dv'],
)
@triton.jit
def _fwd_kernel(
    Q, K, V, O,
    stride_qz, stride_qh, stride_qm, stride_qd,
    stride_kz, stride_kh, stride_kn, stride_kd,
    stride_vz, stride_vh, stride_vn, stride_vd,
    stride_oz, stride_oh, stride_om, stride_od,
    Z, H, M, N,
    sm_scale,
    Dq: tl.constexpr, Dv: tl.constexpr,
    BLOCK_M: tl.constexpr, BLOCK_N: tl.constexpr,
    causal: tl.constexpr,
):
    start_m = tl.program_id(0)
    off_zh = tl.program_id(1)
    
    q_offset = off_zh * stride_qh
    k_offset = off_zh * stride_kh
    v_offset = off_zh * stride_vh
    o_offset = off_zh * stride_oh

    Q_ptr = Q + q_offset
    K_ptr = K + k_offset
    V_ptr = V + v_offset
    O_ptr = O + o_offset

    acc = tl.zeros([BLOCK_M, Dv], dtype=tl.float32)
    l_i = tl.zeros([BLOCK_M], dtype=tl.float32)
    m_i = tl.full([BLOCK_M], -float('inf'), dtype=tl.float32)

    offs_m = start_m * BLOCK_M + tl.arange(0, BLOCK_M)
    offs_d_q = tl.arange(0, Dq)
    offs_d_v = tl.arange(0, Dv)

    q_ptrs = Q_ptr + (offs_m[:, None] * stride_qm + offs_d_q[None, :] * stride_qd)
    
    q_mask = offs_m[:, None] < M
    q = tl.load(q_ptrs, mask=q_mask, other=0.0)
    q = (q * sm_scale).to(Q.dtype.element_ty)

    end_n = N if not causal else (start_m + 1) * BLOCK_M
    
    for start_n in range(0, end_n, BLOCK_N):
        offs_n = start_n + tl.arange(0, BLOCK_N)
        
        k_ptrs = K_ptr + (offs_d_q[:, None] * stride_kd + offs_n[None, :] * stride_kn)
        k_mask = (offs_n[None, :] < N)
        k = tl.load(k_ptrs, mask=k_mask, other=0.0)
        
        s = tl.dot(q, k)

        if causal:
            s = tl.where(offs_m[:, None] >= offs_n[None, :], s, -float('inf'))

        m_ij = tl.max(s, 1)
        m_i_new = tl.maximum(m_i, m_ij)
        
        alpha = tl.exp(m_i - m_i_new)
        p = tl.exp(s - m_i_new[:, None])
        
        l_i_new = alpha * l_i + tl.sum(p, 1)

        p_casted = p.to(V.dtype.element_ty)
        
        v_ptrs = V_ptr + (offs_d_v[:, None] * stride_vd + offs_n[None, :] * stride_vn)
        v_mask = (offs_n[None, :] < N)
        v = tl.load(v_ptrs, mask=v_mask, other=0.0)
        
        acc = acc * alpha[:, None]
        acc += tl.dot(p_casted, tl.trans(v))

        l_i = l_i_new
        m_i = m_i_new

    acc = acc / l_i[:, None]
    
    o_ptrs = O_ptr + (offs_m[:, None] * stride_om + offs_d_v[None, :] * stride_od)
    o_mask = offs_m[:, None] < M
    tl.store(o_ptrs, acc.to(O.dtype.element_ty), mask=o_mask)


def flash_attn(Q: torch.Tensor, K: torch.Tensor, V: torch.Tensor, causal: bool = True) -> torch.Tensor:
    Z, H, M, Dq = Q.shape
    _, _, N, Dv = V.shape
    
    assert K.shape == (Z, H, N, Dq) and V.shape == (Z, H, N, Dv)
    assert Q.is_cuda and K.is_cuda and V.is_cuda
    assert Q.dtype == torch.float16 and K.dtype == torch.float16 and V.dtype == torch.float16
    
    O = torch.empty((Z, H, M, Dv), device=Q.device, dtype=Q.dtype)

    sm_scale = 1.0 / math.sqrt(Dq)

    grid = lambda META: (triton.cdiv(M, META['BLOCK_M']), Z * H)
    
    _fwd_kernel[grid](
        Q, K, V, O,
        Q.stride(0), Q.stride(1), Q.stride(2), Q.stride(3),
        K.stride(0), K.stride(1), K.stride(2), K.stride(3),
        V.stride(0), V.stride(1), V.stride(2), V.stride(3),
        O.stride(0), O.stride(1), O.stride(2), O.stride(3),
        Z, H, M, N,
        sm_scale,
        Dq=Dq, Dv=Dv,
        causal=causal,
    )
    return O
"""
        return {"code": kernel_code}