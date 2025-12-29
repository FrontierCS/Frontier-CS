import torch
import triton
import triton.language as tl

_KERNEL_CODE = """
import torch
import triton
import triton.language as tl

@triton.autotune(
    configs=[
        triton.Config({'BLOCK_M': 64, 'BLOCK_N': 64}, num_stages=4, num_warps=4),
        triton.Config({'BLOCK_M': 64, 'BLOCK_N': 64}, num_stages=3, num_warps=8),
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 64}, num_stages=3, num_warps=4),
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 64}, num_stages=2, num_warps=8),
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 32}, num_stages=4, num_warps=4),
        triton.Config({'BLOCK_M': 64, 'BLOCK_N': 128}, num_stages=3, num_warps=4),
        triton.Config({'BLOCK_M': 64, 'BLOCK_N': 128}, num_stages=2, num_warps=8),
        triton.Config({'BLOCK_M': 32, 'BLOCK_N': 128}, num_stages=4, num_warps=4),
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 128}, num_stages=2, num_warps=8),
    ],
    key=['M', 'N', 'Dq', 'Dv'],
)
@triton.jit
def _gdpa_attn_forward_kernel(
    Q, K, V, GQ, GK, O,
    stride_qz, stride_qh, stride_qm, stride_qd,
    stride_kz, stride_kh, stride_kn, stride_kd,
    stride_vz, stride_vh, stride_vn, stride_vd,
    stride_oz, stride_oh, stride_om, stride_od,
    Z, H, M, N,
    sm_scale,
    # Meta-parameters are passed as constexpr
    Dq: tl.constexpr, 
    Dv: tl.constexpr,
    BLOCK_M: tl.constexpr, 
    BLOCK_N: tl.constexpr
):
    '''
    Triton kernel for Gated Dot-Product Attention forward pass.
    '''
    # Get program IDs to identify the current running block
    start_m = tl.program_id(1)
    off_zh = tl.program_id(0)

    # Create offsets for the current block
    offs_m = start_m * BLOCK_M + tl.arange(0, BLOCK_M)
    offs_n = tl.arange(0, BLOCK_N)
    offs_dq = tl.arange(0, Dq)
    offs_dv = tl.arange(0, Dv)

    # Create pointers to the input and output tensors
    # We assume that Q/GQ and K/GK have the same strides due to identical shapes
    q_ptrs = Q + off_zh * stride_qh + offs_m[:, None] * stride_qm + offs_dq[None, :] * stride_qd
    gq_ptrs = GQ + off_zh * stride_qh + offs_m[:, None] * stride_qm + offs_dq[None, :] * stride_qd
    
    k_base_ptr = K + off_zh * stride_kh
    gk_base_ptr = GK + off_zh * stride_kh
    v_base_ptr = V + off_zh * stride_vh
    
    o_ptrs = O + off_zh * stride_oh + offs_m[:, None] * stride_om + offs_dv[None, :] * stride_od

    # Initialize accumulator and softmax statistics
    acc = tl.zeros([BLOCK_M, Dv], dtype=tl.float32)
    l_i = tl.full([BLOCK_M], -float('inf'), dtype=tl.float32)
    m_i = tl.zeros([BLOCK_M], dtype=tl.float32)
    
    # Load and gate the query block (Qg)
    mask_m = offs_m < M
    q = tl.load(q_ptrs, mask=mask_m[:, None], other=0.0)
    gq = tl.load(gq_ptrs, mask=mask_m[:, None], other=0.0)

    # Sigmoid(x) = 1 / (1 + exp(-x))
    # Computation is done in float32 for stability
    gq_fp32 = gq.to(tl.float32)
    gq_gate = 1.0 / (1.0 + tl.exp(-gq_fp32))
    qg = q * gq_gate.to(q.dtype)

    # Main loop over the key/value sequence
    for start_n in range(0, N, BLOCK_N):
        offs_n_curr = start_n + offs_n
        mask_n = offs_n_curr < N
        
        # Load and gate the key block (Kg)
        k_ptrs = k_base_ptr + offs_n_curr[:, None] * stride_kn + offs_dq[None, :] * stride_kd
        gk_ptrs = gk_base_ptr + offs_n_curr[:, None] * stride_kn + offs_dq[None, :] * stride_kd
        
        k = tl.load(k_ptrs, mask=mask_n[:, None], other=0.0)
        gk = tl.load(gk_ptrs, mask=mask_n[:, None], other=0.0)
        
        gk_fp32 = gk.to(tl.float32)
        gk_gate = 1.0 / (1.0 + tl.exp(-gk_fp32))
        kg = k * gk_gate.to(k.dtype)
        
        # Compute attention scores (S = Qg @ Kg.T)
        s = tl.dot(qg, tl.trans(kg))
        s *= sm_scale
        
        # Apply causal/padding mask
        s = tl.where(mask_m[:, None] & mask_n[None, :], s, -float('inf'))

        # Online softmax update
        m_ij = tl.max(s, 1)
        m_new = tl.maximum(l_i, m_ij)
        s_exp = tl.exp(s - m_new[:, None])
        alpha = tl.exp(l_i - m_new)
        m_i_new = alpha * m_i + tl.sum(s_exp, 1)
        
        # Load value block
        v_ptrs = v_base_ptr + offs_n_curr[:, None] * stride_vn + offs_dv[None, :] * stride_vd
        v = tl.load(v_ptrs, mask=mask_n[:, None], other=0.0)
        
        # Update accumulator
        alpha_broadcast = alpha[:, None]
        acc *= alpha_broadcast
        s_exp = s_exp.to(v.dtype)
        acc += tl.dot(s_exp, v)
        
        # Update softmax statistics
        m_i = m_i_new
        l_i = m_new

    # Final normalization
    acc = acc * (1.0 / m_i)[:, None]
    
    # Store the result
    tl.store(o_ptrs, acc.to(O.dtype.element_ty), mask=mask_m[:, None])

def gdpa_attn(Q: torch.Tensor, K: torch.Tensor, V: torch.Tensor, GQ: torch.Tensor, GK: torch.Tensor) -> torch.Tensor:
    """
    GDPA attention computation with gated Q and K tensors.
    
    Args:
        Q: Input tensor of shape (Z, H, M, Dq) - query tensor (float16)
        K: Input tensor of shape (Z, H, N, Dq) - key tensor (float16)
        V: Input tensor of shape (Z, H, N, Dv) - value tensor (float16)
        GQ: Input tensor of shape (Z, H, M, Dq) - query gate tensor (float16)
        GK: Input tensor of shape (Z, H, N, Dq) - key gate tensor (float16)
    
    Returns:
        Output tensor of shape (Z, H, M, Dv) - attention output (float16)
    """
    Z, H, M, Dq = Q.shape
    _, _, N, _ = K.shape
    _, _, _, Dv = V.shape
    
    O = torch.empty((Z, H, M, Dv), device=Q.device, dtype=Q.dtype)
    sm_scale = 1.0 / (Dq**0.5)
    
    grid = lambda META: (Z * H, triton.cdiv(M, META['BLOCK_M']))
    
    # Launch the Triton kernel
    _gdpa_attn_forward_kernel[grid](
        Q, K, V, GQ, GK, O,
        Q.stride(0), Q.stride(1), Q.stride(2), Q.stride(3),
        K.stride(0), K.stride(1), K.stride(2), K.stride(3),
        V.stride(0), V.stride(1), V.stride(2), V.stride(3),
        O.stride(0), O.stride(1), O.stride(2), O.stride(3),
        Z, H, M, N,
        sm_scale,
        Dq=Dq, 
        Dv=Dv
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
        return {"code": _KERNEL_CODE}