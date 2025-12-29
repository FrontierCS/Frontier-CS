import torch
import triton
import triton.language as tl
import os
from typing import Optional

@triton.jit
def _ragged_attention_forward_kernel(
    Q, K, V, O, row_lens,
    stride_qm, stride_qd,
    stride_kn, stride_kd,
    stride_vn, stride_vd,
    stride_om, stride_od,
    M, N, D, Dv,
    scale,
    BLOCK_M: tl.constexpr, BLOCK_N: tl.constexpr,
    BLOCK_D: tl.constexpr, BLOCK_DV: tl.constexpr,
    USE_ACCUM_FP32: tl.constexpr,
):
    """
    Ragged attention kernel with block tiling and streaming softmax.
    """
    pid = tl.program_id(0)
    pid_m = pid // tl.cdiv(Dv, BLOCK_DV)
    pid_v = pid % tl.cdiv(Dv, BLOCK_DV)
    
    m_start = pid_m * BLOCK_M
    m_end = tl.minimum(m_start + BLOCK_M, M)
    v_start = pid_v * BLOCK_DV
    v_end = tl.minimum(v_start + BLOCK_DV, Dv)
    
    offsets_m = m_start + tl.arange(0, BLOCK_M)
    offsets_v = v_start + tl.arange(0, BLOCK_DV)
    offsets_d = tl.arange(0, BLOCK_D)
    
    mask_m = offsets_m < M
    mask_v = offsets_v < Dv
    mask_d = offsets_d < D
    
    row_lens_ptr = row_lens + offsets_m
    row_lens_vals = tl.load(row_lens_ptr, mask=mask_m, other=0)
    
    m_i = tl.full((BLOCK_M,), float('-inf'), dtype=tl.float32)
    l_i = tl.zeros((BLOCK_M,), dtype=tl.float32)
    acc = tl.zeros((BLOCK_M, BLOCK_DV), dtype=tl.float32)
    
    q_ptr = Q + offsets_m[:, None] * stride_qm + offsets_d[None, :] * stride_qd
    q = tl.load(q_ptr, mask=mask_m[:, None] & mask_d[None, :], other=0.0).to(tl.float32)
    
    for n_start in range(0, N, BLOCK_N):
        n_end = tl.minimum(n_start + BLOCK_N, N)
        offsets_n = n_start + tl.arange(0, BLOCK_N)
        mask_n = offsets_n < N
        
        k_ptr = K + offsets_n[:, None] * stride_kn + offsets_d[None, :] * stride_kd
        k = tl.load(k_ptr, mask=mask_n[:, None] & mask_d[None, :], other=0.0).to(tl.float32)
        
        scores = tl.dot(q, tl.trans(k)) * scale
        
        row_mask = offsets_n[None, :] < row_lens_vals[:, None]
        block_mask = mask_n[None, :] & mask_m[:, None]
        mask = row_mask & block_mask
        scores = tl.where(mask, scores, float('-inf'))
        
        m_ij = tl.maximum(m_i[:, None], tl.max(scores, axis=1))
        p = tl.exp(scores - m_ij[:, None])
        p = tl.where(mask, p, 0.0)
        
        l_ij = tl.exp(m_i - m_ij) * l_i + tl.sum(p, axis=1)
        
        v_ptr = V + offsets_n[:, None] * stride_vn + offsets_v[None, :] * stride_vd
        v = tl.load(v_ptr, mask=mask_n[:, None] & mask_v[None, :], other=0.0).to(tl.float32)
        
        p_acc = p.to(tl.float32)
        v_acc = v.to(tl.float32)
        acc_scale = tl.exp(m_i - m_ij)[:, None]
        acc = acc * acc_scale + tl.dot(p_acc, v_acc)
        
        m_i = m_ij
        l_i = l_ij
    
    acc = acc / l_i[:, None]
    
    o_ptr = O + offsets_m[:, None] * stride_om + offsets_v[None, :] * stride_od
    tl.store(o_ptr, acc.to(Q.dtype.element_ty), mask=mask_m[:, None] & mask_v[None, :])

def ragged_attn(
    Q: torch.Tensor, 
    K: torch.Tensor, 
    V: torch.Tensor, 
    row_lens: torch.Tensor
) -> torch.Tensor:
    """
    Ragged attention computation.
    
    Args:
        Q: Query tensor of shape (M, D) - query features (float16)
        K: Key tensor of shape (N, D) - key features (float16)
        V: Value tensor of shape (N, Dv) - value features (float16)
        row_lens: Row lengths tensor of shape (M,) - number of valid K/V rows per Q row (int32 or int64)
    
    Returns:
        Output tensor of shape (M, Dv) - attention output (float16)
    """
    assert Q.is_cuda and K.is_cuda and V.is_cuda and row_lens.is_cuda
    assert Q.dim() == 2 and K.dim() == 2 and V.dim() == 2
    assert Q.size(1) == K.size(1), "Q and K must have same feature dimension D"
    assert K.size(0) == V.size(0), "K and V must have same sequence length N"
    
    M, D = Q.shape
    N, D = K.shape
    Nv, Dv = V.shape
    assert Nv == N, "V must have same sequence length as K"
    
    if row_lens.dtype != torch.int32:
        row_lens = row_lens.to(torch.int32)
    
    O = torch.empty((M, Dv), device=Q.device, dtype=Q.dtype)
    
    scale = 1.0 / (D ** 0.5)
    
    BLOCK_M = 64
    BLOCK_N = 64
    BLOCK_D = 64 if D >= 64 else 32
    BLOCK_DV = 64 if Dv >= 64 else 32
    
    if D > 128:
        BLOCK_D = 32
    if Dv > 128:
        BLOCK_DV = 32
    
    grid = (triton.cdiv(M, BLOCK_M) * triton.cdiv(Dv, BLOCK_DV),)
    
    kernel_config = {
        'Q': Q, 'K': K, 'V': V, 'O': O, 'row_lens': row_lens,
        'stride_qm': Q.stride(0), 'stride_qd': Q.stride(1),
        'stride_kn': K.stride(0), 'stride_kd': K.stride(1),
        'stride_vn': V.stride(0), 'stride_vd': V.stride(1),
        'stride_om': O.stride(0), 'stride_od': O.stride(1),
        'M': M, 'N': N, 'D': D, 'Dv': Dv,
        'scale': scale,
        'BLOCK_M': BLOCK_M, 'BLOCK_N': BLOCK_N,
        'BLOCK_D': BLOCK_D, 'BLOCK_DV': BLOCK_DV,
        'USE_ACCUM_FP32': True,
    }
    
    _ragged_attention_forward_kernel[grid](**kernel_config)
    
    return O

class Solution:
    def solve(self, spec_path: str = None) -> dict:
        code = '''import torch
import triton
import triton.language as tl
import os
from typing import Optional

@triton.jit
def _ragged_attention_forward_kernel(
    Q, K, V, O, row_lens,
    stride_qm, stride_qd,
    stride_kn, stride_kd,
    stride_vn, stride_vd,
    stride_om, stride_od,
    M, N, D, Dv,
    scale,
    BLOCK_M: tl.constexpr, BLOCK_N: tl.constexpr,
    BLOCK_D: tl.constexpr, BLOCK_DV: tl.constexpr,
    USE_ACCUM_FP32: tl.constexpr,
):
    """
    Ragged attention kernel with block tiling and streaming softmax.
    """
    pid = tl.program_id(0)
    pid_m = pid // tl.cdiv(Dv, BLOCK_DV)
    pid_v = pid % tl.cdiv(Dv, BLOCK_DV)
    
    m_start = pid_m * BLOCK_M
    m_end = tl.minimum(m_start + BLOCK_M, M)
    v_start = pid_v * BLOCK_DV
    v_end = tl.minimum(v_start + BLOCK_DV, Dv)
    
    offsets_m = m_start + tl.arange(0, BLOCK_M)
    offsets_v = v_start + tl.arange(0, BLOCK_DV)
    offsets_d = tl.arange(0, BLOCK_D)
    
    mask_m = offsets_m < M
    mask_v = offsets_v < Dv
    mask_d = offsets_d < D
    
    row_lens_ptr = row_lens + offsets_m
    row_lens_vals = tl.load(row_lens_ptr, mask=mask_m, other=0)
    
    m_i = tl.full((BLOCK_M,), float('-inf'), dtype=tl.float32)
    l_i = tl.zeros((BLOCK_M,), dtype=tl.float32)
    acc = tl.zeros((BLOCK_M, BLOCK_DV), dtype=tl.float32)
    
    q_ptr = Q + offsets_m[:, None] * stride_qm + offsets_d[None, :] * stride_qd
    q = tl.load(q_ptr, mask=mask_m[:, None] & mask_d[None, :], other=0.0).to(tl.float32)
    
    for n_start in range(0, N, BLOCK_N):
        n_end = tl.minimum(n_start + BLOCK_N, N)
        offsets_n = n_start + tl.arange(0, BLOCK_N)
        mask_n = offsets_n < N
        
        k_ptr = K + offsets_n[:, None] * stride_kn + offsets_d[None, :] * stride_kd
        k = tl.load(k_ptr, mask=mask_n[:, None] & mask_d[None, :], other=0.0).to(tl.float32)
        
        scores = tl.dot(q, tl.trans(k)) * scale
        
        row_mask = offsets_n[None, :] < row_lens_vals[:, None]
        block_mask = mask_n[None, :] & mask_m[:, None]
        mask = row_mask & block_mask
        scores = tl.where(mask, scores, float('-inf'))
        
        m_ij = tl.maximum(m_i[:, None], tl.max(scores, axis=1))
        p = tl.exp(scores - m_ij[:, None])
        p = tl.where(mask, p, 0.0)
        
        l_ij = tl.exp(m_i - m_ij) * l_i + tl.sum(p, axis=1)
        
        v_ptr = V + offsets_n[:, None] * stride_vn + offsets_v[None, :] * stride_vd
        v = tl.load(v_ptr, mask=mask_n[:, None] & mask_v[None, :], other=0.0).to(tl.float32)
        
        p_acc = p.to(tl.float32)
        v_acc = v.to(tl.float32)
        acc_scale = tl.exp(m_i - m_ij)[:, None]
        acc = acc * acc_scale + tl.dot(p_acc, v_acc)
        
        m_i = m_ij
        l_i = l_ij
    
    acc = acc / l_i[:, None]
    
    o_ptr = O + offsets_m[:, None] * stride_om + offsets_v[None, :] * stride_od
    tl.store(o_ptr, acc.to(Q.dtype.element_ty), mask=mask_m[:, None] & mask_v[None, :])

def ragged_attn(
    Q: torch.Tensor, 
    K: torch.Tensor, 
    V: torch.Tensor, 
    row_lens: torch.Tensor
) -> torch.Tensor:
    """
    Ragged attention computation.
    
    Args:
        Q: Query tensor of shape (M, D) - query features (float16)
        K: Key tensor of shape (N, D) - key features (float16)
        V: Value tensor of shape (N, Dv) - value features (float16)
        row_lens: Row lengths tensor of shape (M,) - number of valid K/V rows per Q row (int32 or int64)
    
    Returns:
        Output tensor of shape (M, Dv) - attention output (float16)
    """
    assert Q.is_cuda and K.is_cuda and V.is_cuda and row_lens.is_cuda
    assert Q.dim() == 2 and K.dim() == 2 and V.dim() == 2
    assert Q.size(1) == K.size(1), "Q and K must have same feature dimension D"
    assert K.size(0) == V.size(0), "K and V must have same sequence length N"
    
    M, D = Q.shape
    N, D = K.shape
    Nv, Dv = V.shape
    assert Nv == N, "V must have same sequence length as K"
    
    if row_lens.dtype != torch.int32:
        row_lens = row_lens.to(torch.int32)
    
    O = torch.empty((M, Dv), device=Q.device, dtype=Q.dtype)
    
    scale = 1.0 / (D ** 0.5)
    
    BLOCK_M = 64
    BLOCK_N = 64
    BLOCK_D = 64 if D >= 64 else 32
    BLOCK_DV = 64 if Dv >= 64 else 32
    
    if D > 128:
        BLOCK_D = 32
    if Dv > 128:
        BLOCK_DV = 32
    
    grid = (triton.cdiv(M, BLOCK_M) * triton.cdiv(Dv, BLOCK_DV),)
    
    kernel_config = {
        'Q': Q, 'K': K, 'V': V, 'O': O, 'row_lens': row_lens,
        'stride_qm': Q.stride(0), 'stride_qd': Q.stride(1),
        'stride_kn': K.stride(0), 'stride_kd': K.stride(1),
        'stride_vn': V.stride(0), 'stride_vd': V.stride(1),
        'stride_om': O.stride(0), 'stride_od': O.stride(1),
        'M': M, 'N': N, 'D': D, 'Dv': Dv,
        'scale': scale,
        'BLOCK_M': BLOCK_M, 'BLOCK_N': BLOCK_N,
        'BLOCK_D': BLOCK_D, 'BLOCK_DV': BLOCK_DV,
        'USE_ACCUM_FP32': True,
    }
    
    _ragged_attention_forward_kernel[grid](**kernel_config)
    
    return O'''
    
        return {"code": code}