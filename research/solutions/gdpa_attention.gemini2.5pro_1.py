import torch
import triton
import triton.language as tl

class Solution:
    def solve(self, spec_path: str = None) -> dict:
        gdpa_code = r"""
import torch
import triton
import triton.language as tl

@triton.autotune(
    configs=[
        # Basic configurations
        triton.Config({'BLOCK_M': 64, 'BLOCK_N': 64, 'BLOCK_Dq': 64, 'BLOCK_Dv': 64, 'num_warps': 4, 'num_stages': 2}),
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 64, 'BLOCK_Dq': 64, 'BLOCK_Dv': 64, 'num_warps': 4, 'num_stages': 3}),
        triton.Config({'BLOCK_M': 64, 'BLOCK_N': 128, 'BLOCK_Dq': 64, 'BLOCK_Dv': 64, 'num_warps': 4, 'num_stages': 3}),
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 32, 'BLOCK_Dq': 64, 'BLOCK_Dv': 64, 'num_warps': 4, 'num_stages': 4}),
        
        # Configurations with more warps for better latency hiding
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 64, 'BLOCK_Dq': 64, 'BLOCK_Dv': 64, 'num_warps': 8, 'num_stages': 2}),
        triton.Config({'BLOCK_M': 64, 'BLOCK_N': 128, 'BLOCK_Dq': 64, 'BLOCK_Dv': 64, 'num_warps': 8, 'num_stages': 2}),
        
        # Larger block sizes for increased data reuse
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 128, 'BLOCK_Dq': 64, 'BLOCK_Dv': 64, 'num_warps': 8, 'num_stages': 3}),
        triton.Config({'BLOCK_M': 256, 'BLOCK_N': 64, 'BLOCK_Dq': 64, 'BLOCK_Dv': 64, 'num_warps': 8, 'num_stages': 3}),

        # Deeper pipeline stages
        triton.Config({'BLOCK_M': 64, 'BLOCK_N': 64, 'BLOCK_Dq': 64, 'BLOCK_Dv': 64, 'num_warps': 4, 'num_stages': 4}),
    ],
    key=['M', 'N', 'Dq', 'Dv'],
)
@triton.jit
def _gdpa_attn_fwd_kernel(
    Q, K, V, GQ, GK, O,
    stride_qz, stride_qh, stride_qm, stride_qd,
    stride_kz, stride_kh, stride_kn, stride_kd,
    stride_vz, stride_vh, stride_vn, stride_vd,
    stride_gqz, stride_gqh, stride_gqm, stride_gqd,
    stride_gkz, stride_gkh, stride_gkn, stride_gkd,
    stride_oz, stride_oh, stride_om, stride_od,
    Z, H, M, N,
    Dq: tl.constexpr, Dv: tl.constexpr,
    SCALE: tl.constexpr,
    BLOCK_M: tl.constexpr, BLOCK_N: tl.constexpr,
    BLOCK_Dq: tl.constexpr, BLOCK_Dv: tl.constexpr,
):
    """
    Triton kernel for Gated Dot-Product Attention.
    """
    # Program IDs for grid dimensions
    pid_m = tl.program_id(0)
    pid_zh = tl.program_id(1)
    
    # Decompose batch and head IDs
    pid_z = pid_zh // H
    pid_h = pid_zh % H

    # Offsets for the current block
    offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
    offs_n = tl.arange(0, BLOCK_N)
    offs_d = tl.arange(0, BLOCK_Dq)
    offs_dv = tl.arange(0, BLOCK_Dv)

    # Pointers to Q and GQ tiles
    q_ptrs = Q + pid_z * stride_qz + pid_h * stride_qh + (offs_m[:, None] * stride_qm + offs_d[None, :] * stride_qd)
    gq_ptrs = GQ + pid_z * stride_gqz + pid_h * stride_gqh + (offs_m[:, None] * stride_gqm + offs_d[None, :] * stride_gqd)
    
    # Boundary masks for sequence length M
    mask_m = offs_m < M

    # Load Q and GQ, apply gate
    # Load with masking for robustness, although problem spec ensures alignment
    q = tl.load(q_ptrs, mask=mask_m[:, None], other=0.0)
    gq = tl.load(gq_ptrs, mask=mask_m[:, None], other=0.0)
    
    # Apply sigmoid gate to Q, upcasting for precision
    q_gated = q * tl.sigmoid(gq.to(tl.float32))

    # Initialize accumulators for streaming softmax
    m_i = tl.full([BLOCK_M], -float('inf'), dtype=tl.float32)
    l_i = tl.zeros([BLOCK_M], dtype=tl.float32)
    acc = tl.zeros([BLOCK_M, BLOCK_Dv], dtype=tl.float32)

    # Loop over blocks of K, GK, and V
    for start_n in range(0, N, BLOCK_N):
        current_offs_n = start_n + offs_n
        mask_n = current_offs_n < N

        # Pointers to K, GK, and V tiles
        k_ptrs = K + pid_z * stride_kz + pid_h * stride_kh + (current_offs_n[:, None] * stride_kn + offs_d[None, :] * stride_kd)
        gk_ptrs = GK + pid_z * stride_gkz + pid_h * stride_gkh + (current_offs_n[:, None] * stride_gkn + offs_d[None, :] * stride_gkd)
        v_ptrs = V + pid_z * stride_vz + pid_h * stride_vh + (current_offs_n[:, None] * stride_vn + offs_dv[None, :] * stride_vd)

        # Load K and GK
        k = tl.load(k_ptrs, mask=mask_n[:, None], other=0.0)
        gk = tl.load(gk_ptrs, mask=mask_n[:, None], other=0.0)
        
        # Apply sigmoid gate to K
        k_gated = k * tl.sigmoid(gk.to(tl.float32))
        
        # Compute scaled dot-product scores
        s_ij = tl.dot(q_gated, k_gated) * SCALE
        
        # Mask scores for padded tokens to -inf for correct softmax
        s_ij = tl.where(mask_m[:, None] & mask_n[None, :], s_ij, -float('inf'))
        
        # --- Streaming softmax computation ---
        # 1. Compute new max for the current block
        m_ij = tl.max(s_ij, 1)
        # 2. Update overall max
        m_new = tl.maximum(m_i, m_ij)
        # 3. Rescale previous accumulator and sum based on new max
        p_scale = tl.exp(m_i - m_new)
        acc = acc * p_scale[:, None]
        l_i = l_i * p_scale
        
        # 4. Compute probabilities for the current block
        p_ij = tl.exp(s_ij - m_new[:, None])
        # 5. Update sum of probabilities
        l_ij = tl.sum(p_ij, 1)
        l_i += l_ij
        
        # 6. Load V and update output accumulator
        v = tl.load(v_ptrs, mask=mask_n[:, None], other=0.0)
        p_ij = p_ij.to(v.dtype) # Cast probabilities to V's dtype for matmul
        acc += tl.dot(p_ij, v)
        
        # 7. Update max for the next iteration
        m_i = m_new

    # Final normalization of the output accumulator
    l_i_safe = tl.where(l_i == 0, 1.0, l_i)
    acc = acc / l_i_safe[:, None]
    
    # Pointers to the output tensor
    o_ptrs = O + pid_z * stride_oz + pid_h * stride_oh + (offs_m[:, None] * stride_om + offs_dv[None, :] * stride_od)
    # Store the final result
    tl.store(o_ptrs, acc.to(O.dtype.element_ty), mask=mask_m[:, None])

def gdpa_attn(Q: torch.Tensor, K: torch.Tensor, V: torch.Tensor, GQ: torch.Tensor, GK: torch.Tensor) -> torch.Tensor:
    Z, H, M, Dq = Q.shape
    _, _, N, Dv = V.shape
    
    # Create the output tensor
    O = torch.empty((Z, H, M, Dv), device=Q.device, dtype=Q.dtype)
    
    # Grid definition function for Triton JIT
    def grid(meta):
        return (triton.cdiv(M, meta['BLOCK_M']), Z * H)

    # Attention scale factor
    SCALE = 1.0 / (Dq ** 0.5)

    # Launch the Triton kernel
    _gdpa_attn_fwd_kernel[grid](
        Q, K, V, GQ, GK, O,
        Q.stride(0), Q.stride(1), Q.stride(2), Q.stride(3),
        K.stride(0), K.stride(1), K.stride(2), K.stride(3),
        V.stride(0), V.stride(1), V.stride(2), V.stride(3),
        GQ.stride(0), GQ.stride(1), GQ.stride(2), GQ.stride(3),
        GK.stride(0), GK.stride(1), GK.stride(2), GK.stride(3),
        O.stride(0), O.stride(1), O.stride(2), O.stride(3),
        Z, H, M, N,
        Dq=Dq, Dv=Dv,
        SCALE=SCALE
    )
    return O
"""
        return {"code": gdpa_code}