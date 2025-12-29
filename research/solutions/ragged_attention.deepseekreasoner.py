import torch
import triton
import triton.language as tl
import math
from typing import Optional, Tuple

@triton.autotune(
    configs=[
        triton.Config({'BM': 64, 'BN': 64, 'BD': 32, 'BDV': 32}, num_stages=3, num_warps=8),
        triton.Config({'BM': 128, 'BN': 64, 'BD': 32, 'BDV': 32}, num_stages=3, num_warps=8),
        triton.Config({'BM': 64, 'BN': 128, 'BD': 32, 'BDV': 32}, num_stages=3, num_warps=8),
        triton.Config({'BM': 128, 'BN': 128, 'BD': 32, 'BDV': 32}, num_stages=3, num_warps=8),
        triton.Config({'BM': 64, 'BN': 64, 'BD': 64, 'BDV': 64}, num_stages=3, num_warps=8),
        triton.Config({'BM': 128, 'BN': 64, 'BD': 64, 'BDV': 64}, num_stages=3, num_warps=8),
        triton.Config({'BM': 64, 'BN': 128, 'BD': 64, 'BDV': 64}, num_stages=3, num_warps=8),
    ],
    key=['M', 'N', 'D', 'Dv'],
)
@triton.jit
def _ragged_attention_kernel(
    Q_ptr, K_ptr, V_ptr, O_ptr, 
    row_lens_ptr,
    M, N, D, Dv,
    stride_qm, stride_qd,
    stride_kn, stride_kd,
    stride_vn, stride_vd,
    stride_om, stride_od,
    scale: tl.constexpr,
    BM: tl.constexpr,
    BN: tl.constexpr,
    BD: tl.constexpr,
    BDV: tl.constexpr,
):
    pid_m = tl.program_id(0)
    pid_n = tl.program_id(1)
    
    offs_m = pid_m * BM + tl.arange(0, BM)
    offs_n = pid_n * BN + tl.arange(0, BN)
    
    mask_m = offs_m < M
    mask_n = offs_n < N
    
    m_idx = offs_m[:, None]
    n_idx = offs_n[None, :]
    
    row_lens = tl.load(row_lens_ptr + offs_m, mask=mask_m, other=0)
    row_lens_expanded = row_lens[:, None]
    
    acc = tl.zeros((BM, Dv), dtype=tl.float32)
    m_i = tl.full((BM,), float('-inf'), dtype=tl.float32)
    l_i = tl.zeros((BM,), dtype=tl.float32)
    
    D_block = tl.cdiv(D, BD)
    for d_block in range(D_block):
        d_offs = d_block * BD + tl.arange(0, BD)
        d_mask = d_offs < D
        
        q_ptrs = Q_ptr + m_idx * stride_qm + d_offs[None, :] * stride_qd
        q = tl.load(q_ptrs, mask=mask_m[:, None] & d_mask[None, :], other=0.0)
        
        k_ptrs = K_ptr + n_idx * stride_kn + d_offs[:, None] * stride_kd
        k = tl.load(k_ptrs, mask=mask_n[None, :] & d_mask[:, None], other=0.0)
        
        s_block = tl.dot(q, k, allow_tf32=False)
        if d_block == 0:
            s = s_block * scale
        else:
            s += s_block * scale
    
    row_mask = n_idx < row_lens_expanded
    s_masked = tl.where(row_mask, s, float('-inf'))
    
    m_ij = tl.max(s_masked, axis=1)
    m_new = tl.maximum(m_i, m_ij)
    
    alpha = tl.exp(m_i - m_new)
    p = tl.exp(s_masked - m_new[:, None])
    
    l_new = alpha * l_i + tl.sum(p, axis=1)
    
    l_i = l_new
    m_i = m_new
    
    Dv_block = tl.cdiv(Dv, BDV)
    for dv_block in range(Dv_block):
        dv_offs = dv_block * BDV + tl.arange(0, BDV)
        dv_mask = dv_offs < Dv
        
        v_ptrs = V_ptr + n_idx * stride_vn + dv_offs[None, :] * stride_vd
        v = tl.load(v_ptrs, mask=mask_n[None, :] & dv_mask[None, :], other=0.0)
        
        p_expanded = p[:, :, None]
        v_expanded = v[None, :, :]
        
        acc_block = tl.sum(p_expanded * v_expanded, axis=1)
        
        acc_offs = dv_offs
        acc_ptrs = acc + offs_m[:, None] * Dv + acc_offs[None, :]
        current_acc = tl.load(acc_ptrs, mask=mask_m[:, None] & dv_mask[None, :], other=0.0)
        new_acc = alpha[:, None] * current_acc + acc_block
        
        tl.store(acc_ptrs, new_acc, mask=mask_m[:, None] & dv_mask[None, :])
    
    tl.debug_barrier()
    
    if pid_n == tl.num_programs(1) - 1:
        l_i_safe = tl.where(l_i > 0, l_i, 1.0)
        acc_normalized = acc / l_i_safe[:, None]
        
        for dv_block in range(Dv_block):
            dv_offs = dv_block * BDV + tl.arange(0, BDV)
            dv_mask = dv_offs < Dv
            
            out_ptrs = O_ptr + offs_m[:, None] * stride_om + dv_offs[None, :] * stride_od
            tl.store(out_ptrs, acc_normalized[:, dv_offs].to(tl.float16), 
                    mask=mask_m[:, None] & dv_mask[None, :])

def ragged_attn(Q: torch.Tensor, K: torch.Tensor, V: torch.Tensor, row_lens: torch.Tensor) -> torch.Tensor:
    assert Q.dim() == 2 and K.dim() == 2 and V.dim() == 2
    assert Q.size(1) == K.size(1), "Q and K must have same feature dimension"
    assert K.size(0) == V.size(0), "K and V must have same sequence length"
    assert row_lens.size(0) == Q.size(0), "row_lens must match Q batch dimension"
    assert Q.dtype == torch.float16 and K.dtype == torch.float16 and V.dtype == torch.float16
    
    M, D = Q.shape
    N, D = K.shape
    _, Dv = V.shape
    
    O = torch.empty((M, Dv), device=Q.device, dtype=Q.dtype)
    
    scale = 1.0 / math.sqrt(D)
    
    grid = (triton.cdiv(M, 64), triton.cdiv(N, 64))
    
    _ragged_attention_kernel[grid](
        Q, K, V, O, row_lens,
        M, N, D, Dv,
        Q.stride(0), Q.stride(1),
        K.stride(0), K.stride(1),
        V.stride(0), V.stride(1),
        O.stride(0), O.stride(1),
        scale=scale,
        BM=64, BN=64, BD=32, BDV=32
    )
    
    return O

class Solution:
    def solve(self, spec_path: str = None) -> dict:
        return {"code": """
import torch
import triton
import triton.language as tl
import math
from typing import Optional, Tuple

@triton.autotune(
    configs=[
        triton.Config({'BM': 64, 'BN': 64, 'BD': 32, 'BDV': 32}, num_stages=3, num_warps=8),
        triton.Config({'BM': 128, 'BN': 64, 'BD': 32, 'BDV': 32}, num_stages=3, num_warps=8),
        triton.Config({'BM': 64, 'BN': 128, 'BD': 32, 'BDV': 32}, num_stages=3, num_warps=8),
        triton.Config({'BM': 128, 'BN': 128, 'BD': 32, 'BDV': 32}, num_stages=3, num_warps=8),
        triton.Config({'BM': 64, 'BN': 64, 'BD': 64, 'BDV': 64}, num_stages=3, num_warps=8),
        triton.Config({'BM': 128, 'BN': 64, 'BD': 64, 'BDV': 64}, num_stages=3, num_warps=8),
        triton.Config({'BM': 64, 'BN': 128, 'BD': 64, 'BDV': 64}, num_stages=3, num_warps=8),
    ],
    key=['M', 'N', 'D', 'Dv'],
)
@triton.jit
def _ragged_attention_kernel(
    Q_ptr, K_ptr, V_ptr, O_ptr, 
    row_lens_ptr,
    M, N, D, Dv,
    stride_qm, stride_qd,
    stride_kn, stride_kd,
    stride_vn, stride_vd,
    stride_om, stride_od,
    scale: tl.constexpr,
    BM: tl.constexpr,
    BN: tl.constexpr,
    BD: tl.constexpr,
    BDV: tl.constexpr,
):
    pid_m = tl.program_id(0)
    pid_n = tl.program_id(1)
    
    offs_m = pid_m * BM + tl.arange(0, BM)
    offs_n = pid_n * BN + tl.arange(0, BN)
    
    mask_m = offs_m < M
    mask_n = offs_n < N
    
    m_idx = offs_m[:, None]
    n_idx = offs_n[None, :]
    
    row_lens = tl.load(row_lens_ptr + offs_m, mask=mask_m, other=0)
    row_lens_expanded = row_lens[:, None]
    
    acc = tl.zeros((BM, Dv), dtype=tl.float32)
    m_i = tl.full((BM,), float('-inf'), dtype=tl.float32)
    l_i = tl.zeros((BM,), dtype=tl.float32)
    
    D_block = tl.cdiv(D, BD)
    for d_block in range(D_block):
        d_offs = d_block * BD + tl.arange(0, BD)
        d_mask = d_offs < D
        
        q_ptrs = Q_ptr + m_idx * stride_qm + d_offs[None, :] * stride_qd
        q = tl.load(q_ptrs, mask=mask_m[:, None] & d_mask[None, :], other=0.0)
        
        k_ptrs = K_ptr + n_idx * stride_kn + d_offs[:, None] * stride_kd
        k = tl.load(k_ptrs, mask=mask_n[None, :] & d_mask[:, None], other=0.0)
        
        s_block = tl.dot(q, k, allow_tf32=False)
        if d_block == 0:
            s = s_block * scale
        else:
            s += s_block * scale
    
    row_mask = n_idx < row_lens_expanded
    s_masked = tl.where(row_mask, s, float('-inf'))
    
    m_ij = tl.max(s_masked, axis=1)
    m_new = tl.maximum(m_i, m_ij)
    
    alpha = tl.exp(m_i - m_new)
    p = tl.exp(s_masked - m_new[:, None])
    
    l_new = alpha * l_i + tl.sum(p, axis=1)
    
    l_i = l_new
    m_i = m_new
    
    Dv_block = tl.cdiv(Dv, BDV)
    for dv_block in range(Dv_block):
        dv_offs = dv_block * BDV + tl.arange(0, BDV)
        dv_mask = dv_offs < Dv
        
        v_ptrs = V_ptr + n_idx * stride_vn + dv_offs[None, :] * stride_vd
        v = tl.load(v_ptrs, mask=mask_n[None, :] & dv_mask[None, :], other=0.0)
        
        p_expanded = p[:, :, None]
        v_expanded = v[None, :, :]
        
        acc_block = tl.sum(p_expanded * v_expanded, axis=1)
        
        acc_offs = dv_offs
        acc_ptrs = acc + offs_m[:, None] * Dv + acc_offs[None, :]
        current_acc = tl.load(acc_ptrs, mask=mask_m[:, None] & dv_mask[None, :], other=0.0)
        new_acc = alpha[:, None] * current_acc + acc_block
        
        tl.store(acc_ptrs, new_acc, mask=mask_m[:, None] & dv_mask[None, :])
    
    tl.debug_barrier()
    
    if pid_n == tl.num_programs(1) - 1:
        l_i_safe = tl.where(l_i > 0, l_i, 1.0)
        acc_normalized = acc / l_i_safe[:, None]
        
        for dv_block in range(Dv_block):
            dv_offs = dv_block * BDV + tl.arange(0, BDV)
            dv_mask = dv_offs < Dv
            
            out_ptrs = O_ptr + offs_m[:, None] * stride_om + dv_offs[None, :] * stride_od
            tl.store(out_ptrs, acc_normalized[:, dv_offs].to(tl.float16), 
                    mask=mask_m[:, None] & dv_mask[None, :])

def ragged_attn(Q: torch.Tensor, K: torch.Tensor, V: torch.Tensor, row_lens: torch.Tensor) -> torch.Tensor:
    assert Q.dim() == 2 and K.dim() == 2 and V.dim() == 2
    assert Q.size(1) == K.size(1), "Q and K must have same feature dimension"
    assert K.size(0) == V.size(0), "K and V must have same sequence length"
    assert row_lens.size(0) == Q.size(0), "row_lens must match Q batch dimension"
    assert Q.dtype == torch.float16 and K.dtype == torch.float16 and V.dtype == torch.float16
    
    M, D = Q.shape
    N, D = K.shape
    _, Dv = V.shape
    
    O = torch.empty((M, Dv), device=Q.device, dtype=Q.dtype)
    
    scale = 1.0 / math.sqrt(D)
    
    grid = (triton.cdiv(M, 64), triton.cdiv(N, 64))
    
    _ragged_attention_kernel[grid](
        Q, K, V, O, row_lens,
        M, N, D, Dv,
        Q.stride(0), Q.stride(1),
        K.stride(0), K.stride(1),
        V.stride(0), V.stride(1),
        O.stride(0), O.stride(1),
        scale=scale,
        BM=64, BN=64, BD=32, BDV=32
    )
    
    return O
"""}