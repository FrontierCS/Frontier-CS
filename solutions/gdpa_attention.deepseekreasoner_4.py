import torch
import triton
import triton.language as tl
from typing import Optional, Tuple

@triton.jit
def _gdpa_attn_forward_kernel(
    # Pointers to matrices
    Q_ptr, K_ptr, V_ptr, GQ_ptr, GK_ptr, O_ptr,
    # Tensor dimensions
    Z, H, M, N, Dq, Dv,
    # Strides
    stride_qz, stride_qh, stride_qm, stride_qd,
    stride_kz, stride_kh, stride_kn, stride_kd,
    stride_vz, stride_vh, stride_vn, stride_vd,
    stride_gqz, stride_gqh, stride_gqm, stride_gqd,
    stride_gkz, stride_gkh, stride_gkn, stride_gkd,
    stride_oz, stride_oh, stride_om, stride_od,
    # Meta-parameters
    BLOCK_M: tl.constexpr,
    BLOCK_N: tl.constexpr,
    BLOCK_Dq: tl.constexpr,
    BLOCK_Dv: tl.constexpr,
    SCALE: tl.constexpr,
    USE_MASK: tl.constexpr,
):
    # Program ID
    pid_bh = tl.program_id(0)  # batch*head
    pid_m = tl.program_id(1)   # query position
    
    # Decompose batch and head
    batch_id = pid_bh // H
    head_id = pid_bh % H
    
    # Offsets for this block
    offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
    offs_n = tl.arange(0, BLOCK_N)
    offs_dq = tl.arange(0, BLOCK_Dq)
    offs_dv = tl.arange(0, BLOCK_Dv)
    
    # Initialize pointers for Q and GQ
    q_ptrs = (
        Q_ptr
        + batch_id * stride_qz
        + head_id * stride_qh
        + (offs_m[:, None] * stride_qm + offs_dq[None, :] * stride_qd)
    )
    gq_ptrs = (
        GQ_ptr
        + batch_id * stride_gqz
        + head_id * stride_gqh
        + (offs_m[:, None] * stride_gqm + offs_dq[None, :] * stride_gqd)
    )
    
    # Load Q and GQ blocks
    q_block = tl.load(q_ptrs, mask=offs_m[:, None] < M, other=0.0)
    gq_block = tl.load(gq_ptrs, mask=offs_m[:, None] < M, other=0.0)
    
    # Apply gating to Q: Qg = Q * sigmoid(GQ)
    q_gated = q_block * tl.sigmoid(gq_block)
    
    # Initialize accumulators
    m_i = tl.full([BLOCK_M], float("-inf"), dtype=tl.float32)
    l_i = tl.zeros([BLOCK_M], dtype=tl.float32)
    acc = tl.zeros([BLOCK_M, BLOCK_Dv], dtype=tl.float32)
    
    # Loop over K/V blocks
    for start_n in range(0, N, BLOCK_N):
        start_n = tl.multiple_of(start_n, BLOCK_N)
        offs_n_curr = start_n + offs_n
        
        # Load K and GK blocks
        k_ptrs = (
            K_ptr
            + batch_id * stride_kz
            + head_id * stride_kh
            + (offs_n_curr[None, :] * stride_kn + offs_dq[:, None] * stride_kd)
        )
        gk_ptrs = (
            GK_ptr
            + batch_id * stride_gkz
            + head_id * stride_gkh
            + (offs_n_curr[None, :] * stride_gkn + offs_dq[:, None] * stride_gkd)
        )
        
        k_block = tl.load(k_ptrs, mask=offs_n_curr[None, :] < N, other=0.0)
        gk_block = tl.load(gk_ptrs, mask=offs_n_curr[None, :] < N, other=0.0)
        
        # Apply gating to K: Kg = K * sigmoid(GK)
        k_gated = k_block * tl.sigmoid(gk_block)
        
        # Compute attention scores
        scores = tl.dot(q_gated, k_gated, trans_b=True) * SCALE
        
        # Load V block
        v_ptrs = (
            V_ptr
            + batch_id * stride_vz
            + head_id * stride_vh
            + (offs_n_curr[:, None] * stride_vn + offs_dv[None, :] * stride_vd)
        )
        v_block = tl.load(v_ptrs, mask=offs_n_curr[:, None] < N, other=0.0)
        
        # Update m_i and l_i using online softmax
        m_i_new = tl.maximum(m_i, tl.max(scores, axis=1))
        alpha = tl.exp(m_i - m_i_new)
        beta = tl.exp(scores - m_i_new[:, None])
        
        l_i_new = alpha * l_i + tl.sum(beta, axis=1)
        
        # Update accumulators
        acc = acc * alpha[:, None] + tl.dot(beta.to(tl.float16), v_block)
        
        # Update m_i and l_i
        m_i = m_i_new
        l_i = l_i_new
    
    # Normalize accumulators
    acc = acc / l_i[:, None]
    
    # Write output
    o_ptrs = (
        O_ptr
        + batch_id * stride_oz
        + head_id * stride_oh
        + (offs_m[:, None] * stride_om + offs_dv[None, :] * stride_od)
    )
    tl.store(o_ptrs, acc, mask=offs_m[:, None] < M)

def gdpa_attn(
    Q: torch.Tensor,
    K: torch.Tensor,
    V: torch.Tensor,
    GQ: torch.Tensor,
    GK: torch.Tensor,
) -> torch.Tensor:
    """
    GDPA attention computation with gated Q and K tensors.
    """
    # Check input shapes
    Z, H, M, Dq = Q.shape
    _, _, N, _ = K.shape
    _, _, _, Dv = V.shape
    
    # Allocate output tensor
    O = torch.empty((Z, H, M, Dv), dtype=Q.dtype, device=Q.device)
    
    # Compute scale factor
    scale = 1.0 / (Dq ** 0.5)
    
    # Choose block sizes based on dimensions
    BLOCK_M = 128 if M >= 1024 else 64
    BLOCK_N = 128 if N >= 1024 else 64
    BLOCK_Dq = min(128, Dq)
    BLOCK_Dv = min(128, Dv)
    
    # Grid configuration
    grid = (Z * H, triton.cdiv(M, BLOCK_M))
    
    # Launch kernel
    _gdpa_attn_forward_kernel[grid](
        Q, K, V, GQ, GK, O,
        Z, H, M, N, Dq, Dv,
        Q.stride(0), Q.stride(1), Q.stride(2), Q.stride(3),
        K.stride(0), K.stride(1), K.stride(2), K.stride(3),
        V.stride(0), V.stride(1), V.stride(2), V.stride(3),
        GQ.stride(0), GQ.stride(1), GQ.stride(2), GQ.stride(3),
        GK.stride(0), GK.stride(1), GK.stride(2), GK.stride(3),
        O.stride(0), O.stride(1), O.stride(2), O.stride(3),
        BLOCK_M=BLOCK_M,
        BLOCK_N=BLOCK_N,
        BLOCK_Dq=BLOCK_Dq,
        BLOCK_Dv=BLOCK_Dv,
        SCALE=scale,
        USE_MASK=False,
        num_warps=4,
        num_stages=3,
    )
    
    return O

class Solution:
    def solve(self, spec_path: str = None) -> dict:
        return {"code": self._get_code()}
    
    @staticmethod
    def _get_code() -> str:
        import inspect
        return inspect.getsource(gdpa_attn)
