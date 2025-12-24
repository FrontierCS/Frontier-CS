import torch
import triton
import triton.language as tl

class Solution:
  def solve(self, spec_path: str = None) -> dict:
    flash_attention_code = """
import torch
import triton
import triton.language as tl

@triton.jit
def _attn_forward_kernel(
    Q, K, V, O,
    sm_scale,
    stride_qz, stride_qh, stride_qm, stride_qd,
    stride_kz, stride_kh, stride_kn, stride_kd,
    stride_vz, stride_vh, stride_vn, stride_vd,
    stride_oz, stride_oh, stride_om, stride_od,
    Z, H, M, N,
    D_HEAD_Q, D_HEAD_V,
    IS_CAUSAL: tl.constexpr,
    BLOCK_M: tl.constexpr,
    BLOCK_N: tl.constexpr,
    BLOCK_D_Q: tl.constexpr,
    BLOCK_D_V: tl.constexpr,
):
    # Grid and Program IDs
    pid_z = tl.program_id(0)
    pid_h = tl.program_id(1)
    pid_m = tl.program_id(2)

    # Offsets for the current program
    start_m = pid_m * BLOCK_M
    offs_m = start_m + tl.arange(0, BLOCK_M)
    offs_d_q = tl.arange(0, BLOCK_D_Q)
    offs_d_v = tl.arange(0, BLOCK_D_V)

    # Pointers to Q, K, V
    q_ptrs = Q + pid_z * stride_qz + pid_h * stride_qh + (offs_m[:, None] * stride_qm + offs_d_q[None, :] * stride_qd)
    k_ptrs_base = K + pid_z * stride_kz + pid_h * stride_kh
    v_ptrs_base = V + pid_z * stride_vz + pid_h * stride_vh

    # Initialize accumulator and softmax stats
    acc = tl.zeros([BLOCK_M, BLOCK_D_V], dtype=tl.float32)
    l_i = tl.zeros([BLOCK_M], dtype=tl.float32)
    m_i = tl.full([BLOCK_M], -float("inf"), dtype=tl.float32)

    # Load Q block once
    q_mask = offs_m[:, None] < M
    q = tl.load(q_ptrs, mask=q_mask, other=0.0)

    # Loop over K, V blocks
    loop_end = N if not IS_CAUSAL else tl.minimum((start_m + BLOCK_M), N)
    for start_n in range(0, loop_end, BLOCK_N):
        offs_n = start_n + tl.arange(0, BLOCK_N)

        # Load K block (transposed layout for dot product)
        k_ptrs = k_ptrs_base + (offs_d_q[:, None] * stride_kd + offs_n[None, :] * stride_kn)
        k_mask = offs_n[None, :] < N
        k = tl.load(k_ptrs, mask=k_mask, other=0.0)
        
        # Compute S = Q @ K.T
        s = tl.dot(q, k)
        s *= sm_scale
        
        if IS_CAUSAL:
            s += tl.where(offs_m[:, None] >= offs_n[None, :], 0, -float("inf"))

        # Online softmax update
        m_block = tl.max(s, axis=1)
        m_new = tl.maximum(m_i, m_block)
        
        p_scale = tl.exp(m_i - m_new)
        acc *= p_scale[:, None]
        l_i *= p_scale
        
        p = tl.exp(s - m_new[:, None])
        l_i += tl.sum(p, axis=1)
        
        # Load V block
        v_ptrs = v_ptrs_base + (offs_n[:, None] * stride_vn + offs_d_v[None, :] * stride_vd)
        v_mask = offs_n[:, None] < N
        v = tl.load(v_ptrs, mask=v_mask, other=0.0)
        
        p = p.to(V.dtype.element_ty)
        acc += tl.dot(p, v)
        
        m_i = m_new

    # Final normalization and store
    l_i_safe = tl.where(l_i == 0, 1, l_i)
    acc = acc / l_i_safe[:, None]

    o_ptrs = O + pid_z * stride_oz + pid_h * stride_oh + (offs_m[:, None] * stride_om + offs_d_v[None, :] * stride_od)
    o_mask = offs_m[:, None] < M
    tl.store(o_ptrs, acc.to(O.dtype.element_ty), mask=o_mask)

def flash_attn(Q: torch.Tensor, K: torch.Tensor, V: torch.Tensor, causal: bool = True) -> torch.Tensor:
    \"\"\"
    Flash attention computation with optional causal masking.
    
    Args:
        Q: Input tensor of shape (Z, H, M, Dq) - query tensor (float16)
        K: Input tensor of shape (Z, H, N, Dq) - key tensor (float16)
        V: Input tensor of shape (Z, H, N, Dv) - value tensor (float16)
        causal: Whether to apply causal masking (default True)
    
    Returns:
        Output tensor of shape (Z, H, M, Dv) - attention output (float16)
    \"\"\"
    Z, H, M, D_HEAD_Q = Q.shape
    _, _, N, D_HEAD_V = V.shape
    
    O = torch.empty((Z, H, M, D_HEAD_V), device=Q.device, dtype=Q.dtype)

    sm_scale = 1.0 / (D_HEAD_Q ** 0.5)

    # Heuristically chosen block sizes
    BLOCK_M = 128
    BLOCK_N = 64
    
    grid = (Z, H, triton.cdiv(M, BLOCK_M))

    _attn_forward_kernel[grid](
        Q, K, V, O,
        sm_scale,
        Q.stride(0), Q.stride(1), Q.stride(2), Q.stride(3),
        K.stride(0), K.stride(1), K.stride(2), K.stride(3),
        V.stride(0), V.stride(1), V.stride(2), V.stride(3),
        O.stride(0), O.stride(1), O.stride(2), O.stride(3),
        Z, H, M, N,
        D_HEAD_Q, D_HEAD_V,
        IS_CAUSAL=causal,
        BLOCK_M=BLOCK_M,
        BLOCK_N=BLOCK_N,
        BLOCK_D_Q=D_HEAD_Q,
        BLOCK_D_V=D_HEAD_V,
        num_warps=4,
        num_stages=3
    )
    return O
"""
    return {"code": flash_attention_code}
