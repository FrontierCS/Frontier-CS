import torch
import triton

class Solution:
    def solve(self, spec_path: str = None) -> dict:
        code = """
import torch
import triton
import triton.language as tl

@triton.autotune(
    configs=[
        # Basic configs
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 64, 'num_stages': 4, 'num_warps': 4}),
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 64, 'num_stages': 3, 'num_warps': 8}),
        triton.Config({'BLOCK_M': 64, 'BLOCK_N': 64, 'num_stages': 4, 'num_warps': 4}),
        
        # Larger blocks for longer sequences
        triton.Config({'BLOCK_M': 256, 'BLOCK_N': 64, 'num_stages': 3, 'num_warps': 8}),
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 128, 'num_stages': 3, 'num_warps': 8}),
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 128, 'num_stages': 2, 'num_warps': 8}),

        # Smaller blocks
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 32, 'num_stages': 5, 'num_warps': 4}),
        triton.Config({'BLOCK_M': 64, 'BLOCK_N': 32, 'num_stages': 5, 'num_warps': 2}),
    ],
    key=['M', 'N', 'Dq', 'Dv', 'causal'],
)
@triton.jit
def _flash_attn_kernel(
    Q, K, V, O,
    stride_qz, stride_qh, stride_qm, stride_qd,
    stride_kz, stride_kh, stride_kn, stride_kd,
    stride_vz, stride_vh, stride_vn, stride_vd,
    stride_oz, stride_oh, stride_om, stride_od,
    Z, H, M, N,
    Dq, Dv,
    sm_scale,
    CAUSAL: tl.constexpr,
    BLOCK_M: tl.constexpr,
    BLOCK_N: tl.constexpr,
):
    # Program IDs
    pid_m_block = tl.program_id(0)
    pid_batch_head = tl.program_id(1)

    # Decompose batch and head IDs
    pid_z = pid_batch_head // H
    pid_h = pid_batch_head % H

    # Pointers to the start of the current batch and head
    q_ptr = Q + pid_z * stride_qz + pid_h * stride_qh
    k_ptr = K + pid_z * stride_kz + pid_h * stride_kh
    v_ptr = V + pid_z * stride_vz + pid_h * stride_vh
    o_ptr = O + pid_z * stride_oz + pid_h * stride_oh

    # Per-CTA state
    start_m = pid_m_block * BLOCK_M
    offs_m = start_m + tl.arange(0, BLOCK_M)
    offs_d = tl.arange(0, Dq)
    offs_dv = tl.arange(0, Dv)

    # Initialize accumulator, softmax normalization stats (l, m)
    acc = tl.zeros([BLOCK_M, Dv], dtype=tl.float32)
    l_i = tl.zeros([BLOCK_M], dtype=tl.float32)
    m_i = tl.full([BLOCK_M], value=-float('inf'), dtype=tl.float32)

    # Load Q block once
    q_ptrs = q_ptr + offs_m[:, None] * stride_qm + offs_d[None, :] * stride_qd
    q_mask = offs_m[:, None] < M
    q = tl.load(q_ptrs, mask=q_mask, other=0.0)

    # Set loop bounds for K/V blocks
    loop_end = N
    if CAUSAL:
        # For causal attention, we only iterate up to the current query block
        loop_end = tl.minimum((start_m + BLOCK_M), N)
    
    # Inner loop over K and V blocks
    for start_n in range(0, loop_end, BLOCK_N):
        # -- Load K block --
        offs_n = start_n + tl.arange(0, BLOCK_N)
        k_ptrs = k_ptr + offs_n[None, :] * stride_kn + offs_d[:, None] * stride_kd
        k_mask = offs_n[None, :] < N
        k = tl.load(k_ptrs, mask=k_mask, other=0.0)

        # -- Compute S = Q @ K.T --
        s = tl.dot(q, k)
        s *= sm_scale

        if CAUSAL:
            s = tl.where(offs_m[:, None] >= offs_n[None, :], s, -float('inf'))
        
        # -- Online softmax update --
        # 1. Find new max
        m_ij = tl.max(s, 1)
        m_new = tl.maximum(m_i, m_ij)
        
        # 2. Correct scores and compute probabilities
        alpha = tl.exp(m_i - m_new)
        s_scaled = s - m_new[:, None]
        p = tl.exp(s_scaled)
        
        # 3. Update sum of probabilities (l)
        l_ij = tl.sum(p, 1)
        l_new = alpha * l_i + l_ij
        
        # 4. Update accumulator (o)
        # -- Load V block --
        v_ptrs = v_ptr + offs_n[:, None] * stride_vn + offs_dv[None, :] * stride_vd
        v_mask = offs_n[:, None] < N
        v = tl.load(v_ptrs, mask=v_mask, other=0.0)
        
        # Rescale old accumulator
        acc *= alpha[:, None]
        
        # Add new value, weighted by probabilities
        p_typed = p.to(V.dtype.element_ty)
        acc += tl.dot(p_typed, v)
        
        # 5. Update l and m for next iteration
        l_i = l_new
        m_i = m_new

    # Final normalization of the accumulator
    # Check for l_i > 0 to avoid division by zero
    l_i_safe = tl.where(l_i > 0, l_i, 1.0)
    acc = acc / l_i_safe[:, None]
    
    # -- Store O block --
    o_ptrs = o_ptr + offs_m[:, None] * stride_om + offs_dv[None, :] * stride_od
    o_mask = offs_m[:, None] < M
    tl.store(o_ptrs, acc.to(O.dtype.element_ty), mask=o_mask)

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
    
    # Ensure tensor shapes are valid
    assert K.shape == (Z, H, N, Dq), "K shape mismatch"
    assert V.shape == (Z, H, N, Dv), "V shape mismatch"
    assert Q.is_cuda and K.is_cuda and V.is_cuda, "Inputs must be on CUDA"
    assert Q.dtype == torch.float16 and K.dtype == torch.float16 and V.dtype == torch.float16, "Inputs must be float16"

    # Output tensor
    O = torch.empty((Z, H, M, Dv), device=Q.device, dtype=Q.dtype)

    # Softmax scale factor
    sm_scale = 1.0 / (Dq ** 0.5)

    # Grid definition for kernel launch
    grid = lambda META: (
        triton.cdiv(M, META['BLOCK_M']),
        Z * H,
    )
    
    # Launch the Triton kernel
    _flash_attn_kernel[grid](
        Q, K, V, O,
        Q.stride(0), Q.stride(1), Q.stride(2), Q.stride(3),
        K.stride(0), K.stride(1), K.stride(2), K.stride(3),
        V.stride(0), V.stride(1), V.stride(2), V.stride(3),
        O.stride(0), O.stride(1), O.stride(2), O.stride(3),
        Z, H, M, N,
        Dq, Dv,
        sm_scale,
        CAUSAL=causal,
    )
    
    return O
"""
        return {"code": code}
