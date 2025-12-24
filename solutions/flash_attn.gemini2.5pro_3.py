import textwrap

class Solution:
    def solve(self, spec_path: str = None) -> dict:
        code = textwrap.dedent("""
import torch
import triton
import triton.language as tl
import math

@triton.jit
def _flash_attn_kernel(
    Q_ptr, K_ptr, V_ptr, O_ptr,
    stride_qz, stride_qh, stride_qm, stride_qd,
    stride_kz, stride_kh, stride_kn, stride_kd,
    stride_vz, stride_vh, stride_vn, stride_vd,
    stride_oz, stride_oh, stride_om, stride_od,
    M, N,
    sm_scale,
    causal: tl.constexpr,
    BLOCK_M: tl.constexpr,
    BLOCK_N: tl.constexpr,
    D_HEAD: tl.constexpr,
):
    # This program computes a single block of the output matrix O.
    # The grid is 2D: (Z * H, cdiv(M, BLOCK_M)).
    # pid_zh identifies the batch and head.
    # pid_m_block identifies the block of rows in the M dimension.
    
    pid_m_block = tl.program_id(1)
    pid_zh = tl.program_id(0)

    # Compute offsets for the current block of queries
    start_m = pid_m_block * BLOCK_M
    offs_m = start_m + tl.arange(0, BLOCK_M)
    offs_d = tl.arange(0, D_HEAD)

    # Pointers to the current block of Q
    q_ptrs = Q_ptr + pid_zh * stride_qh + offs_m[:, None] * stride_qm + offs_d[None, :] * stride_qd
    
    # Initialize accumulator, and online softmax statistics
    acc = tl.zeros([BLOCK_M, D_HEAD], dtype=tl.float32)
    m_i = tl.full([BLOCK_M], -float('inf'), dtype=tl.float32)
    l_i = tl.zeros([BLOCK_M], dtype=tl.float32)
    
    # Load Q. Mask out rows that are beyond the actual sequence length M.
    q_mask = offs_m[:, None] < M
    q = tl.load(q_ptrs, mask=q_mask, other=0.0)

    # Base pointers for K and V for the current batch/head
    k_ptrs_base = K_ptr + pid_zh * stride_kh
    v_ptrs_base = V_ptr + pid_zh * stride_vh

    # Loop over blocks of K and V
    # If causal, the M-th query can only attend to the first M keys.
    # This is handled by adjusting the loop end.
    loop_end = N
    if causal:
        loop_end = (pid_m_block + 1) * BLOCK_M

    for start_n in range(0, loop_end, BLOCK_N):
        offs_n = start_n + tl.arange(0, BLOCK_N)
        
        # Pointers to the current block of K and V
        k_ptrs = k_ptrs_base + offs_n[:, None] * stride_kn + offs_d[None, :] * stride_kd
        v_ptrs = v_ptrs_base + offs_n[:, None] * stride_vn + offs_d[None, :] * stride_vd
        
        # Load K and V. Mask out columns beyond the actual sequence length N.
        k_mask = offs_n[:, None] < N
        k = tl.load(k_ptrs, mask=k_mask, other=0.0)
        v = tl.load(v_ptrs, mask=k_mask, other=0.0)
        
        # Compute scaled dot-product S = Q * K^T * sm_scale
        s_ij = tl.dot(q, tl.trans(k)) * sm_scale
        
        # Apply causal mask. Zeros out scores for keys that are "in the future".
        if causal:
            causal_mask = offs_m[:, None] >= offs_n[None, :]
            s_ij = tl.where(causal_mask, s_ij, -float('inf'))
            
        # --- Online softmax calculation ---
        # 1. Find the new maximum of the current scores
        m_ij = tl.max(s_ij, axis=1)
        # 2. Rescale previous max and find the new overall max
        m_new = tl.maximum(m_i, m_ij)
        # 3. Rescale previous sum and accumulator
        alpha = tl.exp(m_i - m_new)
        acc = acc * alpha[:, None]
        l_i = l_i * alpha
        # 4. Compute probabilities for the current block
        p_ij = tl.exp(s_ij - m_new[:, None])
        # 5. Update sum and accumulator
        l_i += tl.sum(p_ij, axis=1)
        acc += tl.dot(p_ij.to(Q_ptr.dtype.element_ty), v)
        # 6. Update the max for the next iteration
        m_i = m_new

    # Final normalization of the accumulator
    o = acc / l_i[:, None]
    
    # Write the output block to global memory
    o_ptrs = O_ptr + pid_zh * stride_oh + offs_m[:, None] * stride_om + offs_d[None, :] * stride_od
    o_mask = offs_m[:, None] < M
    tl.store(o_ptrs, o.to(O_ptr.dtype.element_ty), mask=o_mask)

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
    
    assert Dq == Dv, "This implementation requires head dimensions of Q and V to be equal."
    D_HEAD = Dq
    
    O = torch.empty((Z, H, M, D_HEAD), device=Q.device, dtype=Q.dtype)

    # Tuning parameters for the Triton kernel
    BLOCK_M = 128
    BLOCK_N = 64
    
    # The grid is 2D, with Z*H programs in the first dimension,
    # and M / BLOCK_M programs in the second dimension.
    grid = (Z * H, triton.cdiv(M, BLOCK_M))
    
    sm_scale = 1.0 / math.sqrt(D_HEAD)
    
    # Launch the Triton kernel.
    # It's important to pass strides for correct memory access.
    # Meta-parameters like block sizes and causal flag are passed as constexpr.
    _flash_attn_kernel[grid](
        Q, K, V, O,
        Q.stride(0), Q.stride(1), Q.stride(2), Q.stride(3),
        K.stride(0), K.stride(1), K.stride(2), K.stride(3),
        V.stride(0), V.stride(1), V.stride(2), V.stride(3),
        O.stride(0), O.stride(1), O.stride(2), O.stride(3),
        M, N,
        sm_scale,
        causal=causal,
        BLOCK_M=BLOCK_M,
        BLOCK_N=BLOCK_N,
        D_HEAD=D_HEAD,
        num_warps=4,
        num_stages=3
    )
    
    return O
""")
        return {"code": code}
