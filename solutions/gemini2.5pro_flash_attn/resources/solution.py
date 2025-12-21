import torch
import triton
import triton.language as tl
import inspect

_flash_attn_kernel_code = """
import torch
import triton
import triton.language as tl

@triton.autotune(
    configs=[
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 64, 'num_stages': 3}, num_warps=4),
        triton.Config({'BLOCK_M': 64, 'BLOCK_N': 128, 'num_stages': 3}, num_warps=4),
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 128, 'num_stages': 3}, num_warps=4),
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 32, 'num_stages': 4}, num_warps=4),
        triton.Config({'BLOCK_M': 64, 'BLOCK_N': 32, 'num_stages': 5}, num_warps=2),
        triton.Config({'BLOCK_M': 32, 'BLOCK_N': 64, 'num_stages': 5}, num_warps=2),
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 64, 'num_stages': 2}, num_warps=8),
        triton.Config({'BLOCK_M': 256, 'BLOCK_N': 64, 'num_stages': 3}, num_warps=8),
        triton.Config({'BLOCK_M': 64, 'BLOCK_N': 256, 'num_stages': 3}, num_warps=8),
        triton.Config({'BLOCK_M': 256, 'BLOCK_N': 128, 'num_stages': 3}, num_warps=8),
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 256, 'num_stages': 3}, num_warps=8),
    ],
    key=['N_CTX', 'D_HEAD', 'causal'],
)
@triton.jit
def _flash_attn_kernel(
    Q_ptr, K_ptr, V_ptr, O_ptr,
    stride_qz, stride_qh, stride_qm, stride_qd,
    stride_kz, stride_kh, stride_kn, stride_kd,
    stride_vz, stride_vh, stride_vn, stride_vd,
    stride_oz, stride_oh, stride_om, stride_od,
    Z, H, N_CTX,
    D_HEAD: tl.constexpr,
    BLOCK_M: tl.constexpr,
    BLOCK_N: tl.constexpr,
    causal: tl.constexpr,
):
    # Grid and program IDs
    pid_m = tl.program_id(0)
    pid_batch_head = tl.program_id(1)

    pid_z = pid_batch_head // H
    pid_h = pid_batch_head % H

    # Offsets
    start_m = pid_m * BLOCK_M
    offs_m = start_m + tl.arange(0, BLOCK_M)
    offs_d = tl.arange(0, D_HEAD)
    offs_n = tl.arange(0, BLOCK_N)

    # Base pointers
    q_base_ptr = Q_ptr + pid_z * stride_qz + pid_h * stride_qh
    k_base_ptr = K_ptr + pid_z * stride_kz + pid_h * stride_kh
    v_base_ptr = V_ptr + pid_z * stride_vz + pid_h * stride_vh
    o_base_ptr = O_ptr + pid_z * stride_oz + pid_h * stride_oh

    # Load Q
    q_ptrs = q_base_ptr + (offs_m[:, None] * stride_qm + offs_d[None, :] * stride_qd)
    q_mask = offs_m[:, None] < N_CTX
    q = tl.load(q_ptrs, mask=q_mask, other=0.0)

    # Initialize accumulators for streaming softmax
    m_i = tl.full([BLOCK_M], value=float('-inf'), dtype=tl.float32)
    l_i = tl.zeros([BLOCK_M], dtype=tl.float32)
    acc = tl.zeros([BLOCK_M, D_HEAD], dtype=tl.float32)
    
    sm_scale = 1.0 / (D_HEAD ** 0.5)

    # Determine loop boundary for causal attention
    loop_end = N_CTX
    if causal:
        loop_end = (start_m + BLOCK_M)
        
    for start_n in range(0, loop_end, BLOCK_N):
        current_offs_n = start_n + offs_n
        
        # Load K (transposed)
        k_ptrs = k_base_ptr + (offs_d[:, None] * stride_kd + current_offs_n[None, :] * stride_kn)
        k_mask = current_offs_n[None, :] < N_CTX
        k = tl.load(k_ptrs, mask=k_mask, other=0.0)
        
        # Load V
        v_ptrs = v_base_ptr + (current_offs_n[:, None] * stride_vn + offs_d[None, :] * stride_vd)
        v_mask = current_offs_n[:, None] < N_CTX
        v = tl.load(v_ptrs, mask=v_mask, other=0.0)

        # Compute S = Q @ K
        s = tl.dot(q, k)
        s *= sm_scale

        if causal:
            causal_mask = offs_m[:, None] >= current_offs_n[None, :]
            s = tl.where(causal_mask, s, float('-inf'))

        # Streaming softmax update
        m_ij = tl.max(s, axis=1)
        p = tl.exp(s - m_ij[:, None])
        l_ij = tl.sum(p, axis=1)

        m_new = tl.maximum(m_i, m_ij)
        alpha = tl.exp(m_i - m_new)
        beta = tl.exp(m_ij - m_new)
        l_new = alpha * l_i + beta * l_ij

        p_scaled = beta[:, None] * p
        acc = acc * alpha[:, None]
        acc += tl.dot(p_scaled.to(Q_ptr.dtype.element_ty), v)

        l_i = l_new
        m_i = m_new

    # Final normalization
    o = acc / l_i[:, None]
    
    # Store O
    o_ptrs = o_base_ptr + (offs_m[:, None] * stride_om + offs_d[None, :] * stride_od)
    tl.store(o_ptrs, o.to(Q_ptr.dtype.element_ty), mask=q_mask)

def flash_attn(Q: torch.Tensor, K: torch.Tensor, V: torch.Tensor, causal: bool = True) -> torch.Tensor:
    Z, H, M, D_HEAD = Q.shape
    
    # Ensure tensors are contiguous
    Q = Q.contiguous()
    K = K.contiguous()
    V = V.contiguous()

    O = torch.empty_like(Q)

    grid = lambda META: (triton.cdiv(M, META['BLOCK_M']), Z * H)
    
    _flash_attn_kernel[grid](
        Q, K, V, O,
        Q.stride(0), Q.stride(1), Q.stride(2), Q.stride(3),
        K.stride(0), K.stride(1), K.stride(2), K.stride(3),
        V.stride(0), V.stride(1), V.stride(2), V.stride(3),
        O.stride(0), O.stride(1), O.stride(2), O.stride(3),
        Z, H, M,
        D_HEAD=D_HEAD,
        causal=causal,
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
        return {"code": _flash_attn_kernel_code}
