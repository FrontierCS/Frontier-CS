import torch

class Solution:
    def solve(self, spec_path: str = None) -> dict:
        kernel_code = """
import torch
import triton
import triton.language as tl

@triton.autotune(
    configs=[
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 64, 'num_warps': 4, 'num_stages': 2}),
        triton.Config({'BLOCK_M': 64, 'BLOCK_N': 128, 'num_warps': 4, 'num_stages': 2}),
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 128, 'num_warps': 8, 'num_stages': 2}),
        triton.Config({'BLOCK_M': 256, 'BLOCK_N': 64, 'num_warps': 8, 'num_stages': 3}),
        triton.Config({'BLOCK_M': 64, 'BLOCK_N': 256, 'num_warps': 8, 'num_stages': 3}),
        triton.Config({'BLOCK_M': 256, 'BLOCK_N': 128, 'num_warps': 8, 'num_stages': 3}),
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 256, 'num_warps': 8, 'num_stages': 3}),
        triton.Config({'BLOCK_M': 256, 'BLOCK_N': 256, 'num_warps': 8, 'num_stages': 4}),
        triton.Config({'BLOCK_M': 64, 'BLOCK_N': 64, 'num_warps': 4, 'num_stages': 2}),
        triton.Config({'BLOCK_M': 32, 'BLOCK_N': 128, 'num_warps': 4, 'num_stages': 2}),
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 32, 'num_warps': 4, 'num_stages': 2}),
    ],
    key=['M', 'N', 'causal', 'Dq', 'Dv'],
)
@triton.jit
def _flash_attn_kernel(
    Q, K, V, O,
    stride_qz, stride_qh, stride_qm, stride_qd,
    stride_kz, stride_kh, stride_kn, stride_kd,
    stride_vz, stride_vh, stride_vn, stride_vd,
    stride_oz, stride_oh, stride_om, stride_od,
    Z, H, M, N,
    sm_scale,
    Dq: tl.constexpr,
    Dv: tl.constexpr,
    causal: tl.constexpr,
    BLOCK_M: tl.constexpr,
    BLOCK_N: tl.constexpr,
):
    # Program IDs
    pid_m = tl.program_id(1)
    pid_zh = tl.program_id(0)
    pid_z = pid_zh // H
    pid_h = pid_zh % H
    
    start_m = pid_m * BLOCK_M

    # Pointers to bases of Q, K, V, O
    q_base_ptr = Q + pid_z * stride_qz + pid_h * stride_qh
    k_base_ptr = K + pid_z * stride_kz + pid_h * stride_kh
    v_base_ptr = V + pid_z * stride_vz + pid_h * stride_vh
    o_base_ptr = O + pid_z * stride_oz + pid_h * stride_oh

    # Offsets for the current block
    offs_m = start_m + tl.arange(0, BLOCK_M)
    offs_d_qk = tl.arange(0, Dq)
    offs_d_v = tl.arange(0, Dv)

    # Load Q block
    q_ptrs = q_base_ptr + offs_m[:, None] * stride_qm + offs_d_qk[None, :] * stride_qd
    mask_m = offs_m < M
    q = tl.load(q_ptrs, mask=mask_m[:, None], other=0.0)

    # Initialize accumulator and softmax statistics
    acc = tl.zeros([BLOCK_M, Dv], dtype=tl.float32)
    m_i = tl.full([BLOCK_M], -float("inf"), dtype=tl.float32)
    l_i = tl.zeros([BLOCK_M], dtype=tl.float32)

    # Loop over K and V blocks
    start_n = 0
    loop_end = (start_m + BLOCK_M) if causal else N
    offs_n_base = tl.arange(0, BLOCK_N)

    while start_n < loop_end:
        # Offsets for K and V blocks
        offs_n = start_n + offs_n_base
        mask_n = offs_n < N

        # Pointers to K and V blocks
        k_ptrs = k_base_ptr + offs_n[None, :] * stride_kn + offs_d_qk[:, None] * stride_kd
        v_ptrs = v_base_ptr + offs_n[:, None] * stride_vn + offs_d_v[None, :] * stride_vd
        
        # Load K and V blocks
        k = tl.load(k_ptrs, mask=mask_n[None, :], other=0.0)
        v = tl.load(v_ptrs, mask=mask_n[:, None], other=0.0)
        
        # Compute scaled dot-product attention scores
        s_ij = tl.dot(q, tl.trans(k))
        s_ij *= sm_scale
        
        # Apply causal mask
        if causal:
            s_ij += tl.where(offs_m[:, None] >= offs_n[None, :], 0, -float("inf"))

        # Mask out padding tokens
        s_ij = tl.where(mask_m[:, None], s_ij, -float("inf"))

        # Streaming softmax update
        m_ij = tl.max(s_ij, 1)
        m_new = tl.maximum(m_i, m_ij)
        
        alpha = tl.exp(m_i - m_new)
        p_ij = tl.exp(s_ij - m_new[:, None])
        
        l_i_new = l_i * alpha + tl.sum(p_ij, 1)
        
        # Update accumulator
        acc *= alpha[:, None]
        p_ij_casted = p_ij.to(V.dtype.element_ty)
        acc += tl.dot(p_ij_casted, v)
        
        # Update softmax statistics for next iteration
        l_i = l_i_new
        m_i = m_new

        start_n += BLOCK_N
    
    # Final normalization
    l_i = tl.where(mask_m, l_i, 1.0) # Avoid division by zero for padding tokens
    l_i_reciprocal = 1.0 / l_i
    acc = acc * l_i_reciprocal[:, None]
    
    # Store output block
    o_ptrs = o_base_ptr + offs_m[:, None] * stride_om + offs_d_v[None, :] * stride_od
    tl.store(o_ptrs, acc.to(O.dtype.element_ty), mask=mask_m[:, None])


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
    _, _, N, _ = K.shape
    _, _, _, Dv = V.shape
    
    assert Q.is_cuda and K.is_cuda and V.is_cuda, "Input tensors must be on a CUDA device"
    assert Q.dtype == torch.float16 and K.dtype == torch.float16 and V.dtype == torch.float16, "Input tensors must be of type float16"
    
    O = torch.empty_like(Q, device=Q.device, dtype=Q.dtype)
    
    sm_scale = 1.0 / (Dq ** 0.5)

    def grid(meta):
        return (Z * H, triton.cdiv(M, meta['BLOCK_M']))

    _flash_attn_kernel[grid](
        Q, K, V, O,
        Q.stride(0), Q.stride(1), Q.stride(2), Q.stride(3),
        K.stride(0), K.stride(1), K.stride(2), K.stride(3),
        V.stride(0), V.stride(1), V.stride(2), V.stride(3),
        O.stride(0), O.stride(1), O.stride(2), O.stride(3),
        Z, H, M, N,
        sm_scale,
        Dq=Dq,
        Dv=Dv,
        causal=causal,
    )
    return O
"""
        return {"code": kernel_code}
