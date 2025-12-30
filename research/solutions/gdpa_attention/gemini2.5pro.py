import torch
import triton
import triton.language as tl

class Solution:
    def solve(self, spec_path: str = None) -> dict:
        code = """
import torch
import triton
import triton.language as tl

@triton.autotune(
    configs=[
        triton.Config({'BLOCK_M': 64, 'BLOCK_N': 64}, num_warps=4, num_stages=4),
        triton.Config({'BLOCK_M': 64, 'BLOCK_N': 64}, num_warps=8, num_stages=3),
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 64}, num_warps=4, num_stages=3),
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 64}, num_warps=8, num_stages=3),
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 32}, num_warps=4, num_stages=4),
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 32}, num_warps=8, num_stages=2),
        triton.Config({'BLOCK_M': 64, 'BLOCK_N': 128}, num_warps=4, num_stages=3),
        triton.Config({'BLOCK_M': 64, 'BLOCK_N': 128}, num_warps=8, num_stages=2),
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 128}, num_warps=8, num_stages=2),
    ],
    key=['M', 'N', 'Dq', 'Dv'],
)
@triton.jit
def _gdpa_attn_fwd_kernel(
    # Pointers to Tensors
    Q_ptr, K_ptr, V_ptr, GQ_ptr, GK_ptr, O_ptr,
    # Stride variables for B, M/N, D tensors
    stride_qb, stride_qm, stride_qd,
    stride_kb, stride_kn, stride_kd,
    stride_vb, stride_vn, stride_vd,
    stride_gqb, stride_gqm, stride_gqd,
    stride_gkb, stride_gkn, stride_gkd,
    stride_ob, stride_om, stride_od,
    # Other variables
    M, N,
    sm_scale,
    # Meta-parameters
    BLOCK_M: tl.constexpr, BLOCK_N: tl.constexpr,
    BLOCK_Dq: tl.constexpr, BLOCK_Dv: tl.constexpr,
):
    start_m = tl.program_id(0)
    off_b = tl.program_id(1)

    # Compute offsets
    offs_m = start_m * BLOCK_M + tl.arange(0, BLOCK_M)
    offs_n = tl.arange(0, BLOCK_N)
    offs_d_q = tl.arange(0, BLOCK_Dq)
    offs_d_v = tl.arange(0, BLOCK_Dv)

    # Pointers to Q, GQ
    q_base_ptr = Q_ptr + off_b * stride_qb
    gq_base_ptr = GQ_ptr + off_b * stride_gqb
    q_ptrs = q_base_ptr + (offs_m[:, None] * stride_qm + offs_d_q[None, :] * stride_qd)
    gq_ptrs = gq_base_ptr + (offs_m[:, None] * stride_gqm + offs_d_q[None, :] * stride_gqd)

    # Pointers to K, GK, V bases
    K_base_ptr = K_ptr + off_b * stride_kb
    GK_base_ptr = GK_ptr + off_b * stride_gkb
    V_base_ptr = V_ptr + off_b * stride_vb
    
    # Initialize accumulator and softmax stats
    acc = tl.zeros([BLOCK_M, BLOCK_Dv], dtype=tl.float32)
    l_i = tl.zeros([BLOCK_M], dtype=tl.float32)
    m_i = tl.full([BLOCK_M], value=float('-inf'), dtype=tl.float32)

    # Load Q and GQ for this block
    mask_m = offs_m < M
    q = tl.load(q_ptrs, mask=mask_m[:, None], other=0.0)
    gq = tl.load(gq_ptrs, mask=mask_m[:, None], other=0.0)
    
    # Gating for Q
    gq_sig = tl.sigmoid(gq.to(tl.float32))
    q_gated = q * gq_sig.to(q.dtype)

    # Loop over K, V blocks
    for start_n in range(0, N, BLOCK_N):
        current_offs_n = start_n + offs_n
        mask_n = current_offs_n < N
        
        # -- Load K and GK (transposed) --
        k_ptrs = K_base_ptr + (offs_d_q[:, None] * stride_kd + current_offs_n[None, :] * stride_kn)
        gk_ptrs = GK_base_ptr + (offs_d_q[:, None] * stride_gkd + current_offs_n[None, :] * stride_gkn)
        
        k = tl.load(k_ptrs, mask=mask_n[None, :], other=0.0)
        gk = tl.load(gk_ptrs, mask=mask_n[None, :], other=0.0)
        
        # Gating for K
        gk_sig = tl.sigmoid(gk.to(tl.float32))
        k_gated = k * gk_sig.to(k.dtype)
        
        # -- Compute S = Qg @ Kg.T --
        s = tl.dot(q_gated, k_gated)
        s *= sm_scale
        
        s = tl.where(mask_m[:, None] & mask_n[None, :], s, float('-inf'))
        
        # -- Online Softmax --
        m_i_new = tl.maximum(m_i, tl.max(s, 1))
        alpha = tl.exp(m_i - m_i_new)
        p = tl.exp(s - m_i_new[:, None])
        
        l_i_new = l_i * alpha + tl.sum(p, 1)
        
        acc = acc * alpha[:, None]
        
        # -- Load V --
        v_ptrs = V_base_ptr + (current_offs_n[:, None] * stride_vn + offs_d_v[None, :] * stride_vd)
        v = tl.load(v_ptrs, mask=mask_n[:, None], other=0.0)
        
        # -- Update acc --
        acc += tl.dot(p.to(v.dtype), v)
        
        m_i = m_i_new
        l_i = l_i_new
    
    # Final normalization
    l_i_safe = tl.where(l_i == 0, 1.0, l_i)
    acc = acc / l_i_safe[:, None]
    
    # Write output
    out_base_ptr = O_ptr + off_b * stride_ob
    out_ptrs = out_base_ptr + (offs_m[:, None] * stride_om + offs_d_v[None, :] * stride_od)
    tl.store(out_ptrs, acc.to(O_ptr.dtype.element_ty), mask=mask_m[:, None])

def gdpa_attn(Q: torch.Tensor, K: torch.Tensor, V: torch.Tensor, GQ: torch.Tensor, GK: torch.Tensor) -> torch.Tensor:
    Z, H, M, Dq = Q.shape
    _, _, N, Dv = V.shape

    # Reshape and ensure contiguity
    Q_reshaped = Q.reshape(-1, M, Dq).contiguous()
    K_reshaped = K.reshape(-1, N, Dq).contiguous()
    V_reshaped = V.reshape(-1, N, Dv).contiguous()
    GQ_reshaped = GQ.reshape(-1, M, Dq).contiguous()
    GK_reshaped = GK.reshape(-1, N, Dq).contiguous()
    
    O = torch.empty((Z * H, M, Dv), device=Q.device, dtype=Q.dtype)

    grid = lambda meta: (triton.cdiv(M, meta['BLOCK_M']), Q_reshaped.shape[0])
    sm_scale = 1.0 / (Dq**0.5)

    _gdpa_attn_fwd_kernel[grid](
        Q_reshaped, K_reshaped, V_reshaped, GQ_reshaped, GK_reshaped, O,
        Q_reshaped.stride(0), Q_reshaped.stride(1), Q_reshaped.stride(2),
        K_reshaped.stride(0), K_reshaped.stride(1), K_reshaped.stride(2),
        V_reshaped.stride(0), V_reshaped.stride(1), V_reshaped.stride(2),
        GQ_reshaped.stride(0), GQ_reshaped.stride(1), GQ_reshaped.stride(2),
        GK_reshaped.stride(0), GK_reshaped.stride(1), GK_reshaped.stride(2),
        O.stride(0), O.stride(1), O.stride(2),
        M, N,
        sm_scale,
        BLOCK_Dq=Dq,
        BLOCK_Dv=Dv,
    )

    return O.view(Z, H, M, Dv)
"""
        return {"code": code}