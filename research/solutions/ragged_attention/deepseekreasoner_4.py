import torch
import triton
import triton.language as tl
from typing import Optional
import math

@triton.jit
def _ragged_attn_fwd_kernel(
    Q, K, V, O,
    row_lens,
    stride_qm, stride_qd,
    stride_km, stride_kd,
    stride_vm, stride_vd,
    stride_om, stride_od,
    M, N, D, Dv,
    scale: tl.constexpr,
    BM: tl.constexpr,
    BN: tl.constexpr,
    BD: tl.constexpr,
    BDV: tl.constexpr,
    USE_FLOAT32_ACC: tl.constexpr = True,
):
    pid_m = tl.program_id(0)
    pid_n = tl.program_id(1)
    pid_batch = tl.program_id(2)
    
    offs_m = pid_m * BM + tl.arange(0, BM)
    offs_n = pid_n * BN + tl.arange(0, BN)
    offs_d = tl.arange(0, BD)
    offs_dv = tl.arange(0, BDV)
    
    q_ptrs = Q + offs_m[:, None] * stride_qm + offs_d[None, :] * stride_qd
    k_ptrs = K + offs_n[:, None] * stride_km + offs_d[None, :] * stride_kd
    v_ptrs = V + offs_n[:, None] * stride_vm + offs_dv[None, :] * stride_vd
    
    acc_dtype = tl.float32 if USE_FLOAT32_ACC else tl.float16
    m_i = tl.full([BM], float('-inf'), dtype=acc_dtype)
    l_i = tl.zeros([BM], dtype=acc_dtype)
    o_i = tl.zeros([BM, BDV], dtype=acc_dtype)
    
    row_len_ptr = row_lens + offs_m
    row_len_i = tl.load(row_len_ptr, mask=offs_m < M, other=0)
    
    q = tl.load(q_ptrs, mask=(offs_m[:, None] < M) & (offs_d[None, :] < D), other=0.0)
    q = q.to(acc_dtype)
    
    for start_n in range(0, N, BN):
        n_idx = start_n + offs_n
        k = tl.load(k_ptrs + start_n * stride_km, mask=(n_idx[:, None] < N) & (offs_d[None, :] < D), other=0.0)
        k = k.to(acc_dtype)
        
        scores = tl.dot(q, tl.trans(k))
        scores = scores * scale
        
        mask = n_idx[None, :] < row_len_i[:, None]
        scores = tl.where(mask, scores, float('-inf'))
        
        m_ij = tl.maximum(m_i[:, None], tl.max(scores, axis=1))
        p = tl.exp(scores - m_ij[:, None])
        
        alpha = tl.exp(m_i - m_ij)
        l_ij = l_i * alpha + tl.sum(p, axis=1)
        
        v = tl.load(v_ptrs + start_n * stride_vm, mask=(n_idx[:, None] < N) & (offs_dv[None, :] < Dv), other=0.0)
        v = v.to(acc_dtype)
        
        o_i = o_i * (l_i / l_ij)[:, None] * alpha[:, None] + tl.dot(p, v) / l_ij[:, None]
        
        m_i = m_ij
        l_i = l_ij
    
    o_ptrs = O + offs_m[:, None] * stride_om + offs_dv[None, :] * stride_od
    tl.store(o_ptrs, o_i.to(O.dtype.element_ty), mask=(offs_m[:, None] < M) & (offs_dv[None, :] < Dv))

def ragged_attn(Q: torch.Tensor, K: torch.Tensor, V: torch.Tensor, row_lens: torch.Tensor) -> torch.Tensor:
    assert Q.dtype == torch.float16
    assert K.dtype == torch.float16
    assert V.dtype == torch.float16
    assert row_lens.dtype in [torch.int32, torch.int64]
    assert Q.is_cuda and K.is_cuda and V.is_cuda and row_lens.is_cuda
    
    M, D = Q.shape
    N, D_k = K.shape
    N_v, Dv = V.shape
    assert D == D_k, f"Q dim {D} != K dim {D_k}"
    assert N == N_v, f"K rows {N} != V rows {N_v}"
    
    O = torch.empty((M, Dv), device=Q.device, dtype=Q.dtype)
    
    scale = 1.0 / math.sqrt(D)
    
    BM, BN, BD, BDV = 64, 64, 64, 64
    
    if D <= 64:
        BD = 32
    if Dv <= 64:
        BDV = 32
    
    grid = (
        triton.cdiv(M, BM),
        triton.cdiv(N, BN),
        1
    )
    
    _ragged_attn_fwd_kernel[grid](
        Q, K, V, O,
        row_lens,
        Q.stride(0), Q.stride(1),
        K.stride(0), K.stride(1),
        V.stride(0), V.stride(1),
        O.stride(0), O.stride(1),
        M, N, D, Dv,
        scale,
        BM=BM,
        BN=BN,
        BD=BD,
        BDV=BDV,
        USE_FLOAT32_ACC=True,
        num_warps=4 if BD <= 32 else 8,
        num_stages=3,
    )
    
    return O

class Solution:
    def solve(self, spec_path: str = None) -> dict:
        return {
            "code": """
import torch
import triton
import triton.language as tl
from typing import Optional
import math

@triton.jit
def _ragged_attn_fwd_kernel(
    Q, K, V, O,
    row_lens,
    stride_qm, stride_qd,
    stride_km, stride_kd,
    stride_vm, stride_vd,
    stride_om, stride_od,
    M, N, D, Dv,
    scale: tl.constexpr,
    BM: tl.constexpr,
    BN: tl.constexpr,
    BD: tl.constexpr,
    BDV: tl.constexpr,
    USE_FLOAT32_ACC: tl.constexpr = True,
):
    pid_m = tl.program_id(0)
    pid_n = tl.program_id(1)
    
    offs_m = pid_m * BM + tl.arange(0, BM)
    offs_n = pid_n * BN + tl.arange(0, BN)
    offs_d = tl.arange(0, BD)
    offs_dv = tl.arange(0, BDV)
    
    q_ptrs = Q + offs_m[:, None] * stride_qm + offs_d[None, :] * stride_qd
    k_ptrs = K + offs_n[:, None] * stride_km + offs_d[None, :] * stride_kd
    v_ptrs = V + offs_n[:, None] * stride_vm + offs_dv[None, :] * stride_vd
    
    acc_dtype = tl.float32 if USE_FLOAT32_ACC else tl.float16
    m_i = tl.full([BM], float('-inf'), dtype=acc_dtype)
    l_i = tl.zeros([BM], dtype=acc_dtype)
    o_i = tl.zeros([BM, BDV], dtype=acc_dtype)
    
    row_len_ptr = row_lens + offs_m
    row_len_i = tl.load(row_len_ptr, mask=offs_m < M, other=0)
    
    q = tl.load(q_ptrs, mask=(offs_m[:, None] < M) & (offs_d[None, :] < D), other=0.0)
    q = q.to(acc_dtype)
    
    n_blocks = tl.cdiv(N, BN)
    
    for pid_n in range(n_blocks):
        start_n = pid_n * BN
        n_idx = start_n + offs_n
        
        k = tl.load(k_ptrs + start_n * stride_km, mask=(n_idx[:, None] < N) & (offs_d[None, :] < D), other=0.0)
        k = k.to(acc_dtype)
        
        scores = tl.dot(q, tl.trans(k))
        scores = scores * scale
        
        mask = n_idx[None, :] < row_len_i[:, None]
        scores = tl.where(mask, scores, float('-inf'))
        
        m_ij = tl.max(scores, axis=1)
        m_ij = tl.maximum(m_i, m_ij)
        p = tl.exp(scores - m_ij[:, None])
        
        alpha = tl.exp(m_i - m_ij)
        l_ij = l_i * alpha + tl.sum(p, axis=1)
        
        v = tl.load(v_ptrs + start_n * stride_vm, mask=(n_idx[:, None] < N) & (offs_dv[None, :] < Dv), other=0.0)
        v = v.to(acc_dtype)
        
        o_i = o_i * (l_i / l_ij)[:, None] * alpha[:, None] + tl.dot(p, v) / l_ij[:, None]
        
        m_i = m_ij
        l_i = l_ij
    
    o_ptrs = O + offs_m[:, None] * stride_om + offs_dv[None, :] * stride_od
    tl.store(o_ptrs, o_i.to(O.dtype.element_ty), mask=(offs_m[:, None] < M) & (offs_dv[None, :] < Dv))

def ragged_attn(Q: torch.Tensor, K: torch.Tensor, V: torch.Tensor, row_lens: torch.Tensor) -> torch.Tensor:
    assert Q.dtype == torch.float16
    assert K.dtype == torch.float16
    assert V.dtype == torch.float16
    assert row_lens.dtype in [torch.int32, torch.int64]
    assert Q.is_cuda and K.is_cuda and V.is_cuda and row_lens.is_cuda
    
    M, D = Q.shape
    N, D_k = K.shape
    N_v, Dv = V.shape
    assert D == D_k, f"Q dim {D} != K dim {D_k}"
    assert N == N_v, f"K rows {N} != V rows {N_v}"
    
    O = torch.empty((M, Dv), device=Q.device, dtype=Q.dtype)
    
    scale = 1.0 / math.sqrt(D)
    
    BM, BN = 64, 64
    if M <= 512:
        BM = 32
    if N <= 512:
        BN = 32
    
    BD = min(64, triton.next_power_of_2(D))
    BDV = min(64, triton.next_power_of_2(Dv))
    
    if BD > D:
        BD = D
    if BDV > Dv:
        BDV = Dv
    
    grid = (
        triton.cdiv(M, BM),
        triton.cdiv(N, BN),
    )
    
    _ragged_attn_fwd_kernel[grid](
        Q, K, V, O,
        row_lens,
        Q.stride(0), Q.stride(1),
        K.stride(0), K.stride(1),
        V.stride(0), V.stride(1),
        O.stride(0), O.stride(1),
        M, N, D, Dv,
        scale,
        BM=BM,
        BN=BN,
        BD=BD,
        BDV=BDV,
        USE_FLOAT32_ACC=True,
        num_warps=4 if BD <= 32 and BDV <= 32 else 8,
        num_stages=3,
    )
    
    return O
"""
        }