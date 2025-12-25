import torch
import triton
import triton.language as tl


@triton.jit
def _ragged_attn_fwd_kernel(
    Q, K, V, Out,
    stride_qm, stride_qd,
    stride_kn, stride_kd,
    stride_vn, stride_vd,
    stride_om, stride_od,
    row_lens_ptr,
    M, N, D, Dv,
    BLOCK_M: tl.constexpr, BLOCK_N: tl.constexpr,
    BLOCK_D: tl.constexpr, BLOCK_DV: tl.constexpr,
    USE_INITIAL_MASK: tl.constexpr
):
    pid_m = tl.program_id(0)
    pid_n = tl.program_id(1)
    
    offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
    offs_n = pid_n * BLOCK_N + tl.arange(0, BLOCK_N)
    offs_d = tl.arange(0, BLOCK_D)
    offs_dv = tl.arange(0, BLOCK_DV)
    
    m_mask = offs_m < M
    q_ptrs = Q + offs_m[:, None] * stride_qm + offs_d[None, :] * stride_qd
    q = tl.load(q_ptrs, mask=m_mask[:, None] & (offs_d[None, :] < D), other=0.0)
    
    row_len_ptrs = row_lens_ptr + offs_m
    row_lens = tl.load(row_len_ptrs, mask=m_mask, other=0)
    
    m_i = tl.zeros([BLOCK_M], dtype=tl.float32) - float('inf')
    l_i = tl.zeros([BLOCK_M], dtype=tl.float32)
    acc_o = tl.zeros([BLOCK_M, BLOCK_DV], dtype=tl.float32)
    
    for start_n in range(0, N, BLOCK_N):
        n = start_n + offs_n
        n_mask = n < N
        
        k_ptrs = K + n[:, None] * stride_kn + offs_d[None, :] * stride_kd
        k = tl.load(k_ptrs, mask=n_mask[:, None] & (offs_d[None, :] < D), other=0.0)
        
        v_ptrs = V + n[:, None] * stride_vn + offs_dv[None, :] * stride_vd
        v = tl.load(v_ptrs, mask=n_mask[:, None] & (offs_dv[None, :] < Dv), other=0.0)
        
        scores = tl.zeros([BLOCK_M, BLOCK_N], dtype=tl.float32)
        if USE_INITIAL_MASK:
            for i in range(BLOCK_M):
                if m_mask[i]:
                    row_len = tl.minimum(row_lens[i], N)
                    col_mask = n < row_len
                    scores_i = tl.dot(q[i], tl.trans(k))
                    scores_i = tl.where(col_mask, scores_i, float('-inf'))
                    scores = tl.where(tl.arange(0, BLOCK_M)[:, None] == i, 
                                    scores_i[None, :], scores)
        else:
            q_scaled = q * (1.0 / tl.sqrt(D * 1.0))
            scores = tl.dot(q_scaled, tl.trans(k))
            
            row_mask = tl.expand_dims(m_mask, 1) & tl.expand_dims(n_mask, 0)
            row_len_mask = tl.expand_dims(offs_m, 1) < tl.expand_dims(row_lens, 1)
            n_mask_expanded = tl.expand_dims(n, 0) < tl.expand_dims(row_lens, 1)
            scores = tl.where(row_mask & row_len_mask & n_mask_expanded, scores, float('-inf'))
        
        m_ij = tl.max(scores, 1)
        m_ij = tl.where(m_mask, m_ij, float('-inf'))
        m_new = tl.maximum(m_i, m_ij)
        
        alpha = tl.exp(m_i - m_new)
        beta = tl.exp(m_ij - m_new)
        
        p = tl.exp(scores - m_new[:, None])
        p_sum = tl.sum(p, 1)
        l_new = alpha * l_i + beta * p_sum
        
        acc_o_scale = l_i / l_new
        p_scale = beta / l_new
        
        acc_o = acc_o * acc_o_scale[:, None]
        
        p = p * p_scale[:, None]
        acc_o += tl.dot(p.to(tl.float16), v)
        
        m_i = m_new
        l_i = l_new
    
    out_ptrs = Out + offs_m[:, None] * stride_om + offs_dv[None, :] * stride_od
    tl.store(out_ptrs, acc_o.to(tl.float16), 
             mask=m_mask[:, None] & (offs_dv[None, :] < Dv))


def ragged_attn(Q: torch.Tensor, K: torch.Tensor, V: torch.Tensor, 
                row_lens: torch.Tensor) -> torch.Tensor:
    M, D = Q.shape
    N, _ = K.shape
    _, Dv = V.shape
    
    assert Q.dtype == torch.float16
    assert K.dtype == torch.float16
    assert V.dtype == torch.float16
    assert Q.is_cuda and K.is_cuda and V.is_cuda
    assert row_lens.is_cuda
    assert row_lens.shape == (M,)
    
    Out = torch.empty((M, Dv), device=Q.device, dtype=torch.float16)
    
    BLOCK_M = 32
    BLOCK_N = 64
    BLOCK_D = 32 if D >= 32 else 16
    BLOCK_DV = 32 if Dv >= 32 else 16
    
    grid = (triton.cdiv(M, BLOCK_M), 1)
    
    _ragged_attn_fwd_kernel[grid](
        Q, K, V, Out,
        Q.stride(0), Q.stride(1),
        K.stride(0), K.stride(1),
        V.stride(0), V.stride(1),
        Out.stride(0), Out.stride(1),
        row_lens,
        M, N, D, Dv,
        BLOCK_M=BLOCK_M, BLOCK_N=BLOCK_N,
        BLOCK_D=BLOCK_D, BLOCK_DV=BLOCK_DV,
        USE_INITIAL_MASK=False,
        num_warps=4,
        num_stages=3
    )
    
    return Out


class Solution:
    def solve(self, spec_path: str = None) -> dict:
        code = """
import torch
import triton
import triton.language as tl


@triton.jit
def _ragged_attn_fwd_kernel(
    Q, K, V, Out,
    stride_qm, stride_qd,
    stride_kn, stride_kd,
    stride_vn, stride_vd,
    stride_om, stride_od,
    row_lens_ptr,
    M, N, D, Dv,
    BLOCK_M: tl.constexpr, BLOCK_N: tl.constexpr,
    BLOCK_D: tl.constexpr, BLOCK_DV: tl.constexpr,
    USE_INITIAL_MASK: tl.constexpr
):
    pid_m = tl.program_id(0)
    pid_n = tl.program_id(1)
    
    offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
    offs_n = pid_n * BLOCK_N + tl.arange(0, BLOCK_N)
    offs_d = tl.arange(0, BLOCK_D)
    offs_dv = tl.arange(0, BLOCK_DV)
    
    m_mask = offs_m < M
    q_ptrs = Q + offs_m[:, None] * stride_qm + offs_d[None, :] * stride_qd
    q = tl.load(q_ptrs, mask=m_mask[:, None] & (offs_d[None, :] < D), other=0.0)
    
    row_len_ptrs = row_lens_ptr + offs_m
    row_lens = tl.load(row_len_ptrs, mask=m_mask, other=0)
    
    m_i = tl.zeros([BLOCK_M], dtype=tl.float32) - float('inf')
    l_i = tl.zeros([BLOCK_M], dtype=tl.float32)
    acc_o = tl.zeros([BLOCK_M, BLOCK_DV], dtype=tl.float32)
    
    for start_n in range(0, N, BLOCK_N):
        n = start_n + offs_n
        n_mask = n < N
        
        k_ptrs = K + n[:, None] * stride_kn + offs_d[None, :] * stride_kd
        k = tl.load(k_ptrs, mask=n_mask[:, None] & (offs_d[None, :] < D), other=0.0)
        
        v_ptrs = V + n[:, None] * stride_vn + offs_dv[None, :] * stride_vd
        v = tl.load(v_ptrs, mask=n_mask[:, None] & (offs_dv[None, :] < Dv), other=0.0)
        
        scores = tl.zeros([BLOCK_M, BLOCK_N], dtype=tl.float32)
        if USE_INITIAL_MASK:
            for i in range(BLOCK_M):
                if m_mask[i]:
                    row_len = tl.minimum(row_lens[i], N)
                    col_mask = n < row_len
                    scores_i = tl.dot(q[i], tl.trans(k))
                    scores_i = tl.where(col_mask, scores_i, float('-inf'))
                    scores = tl.where(tl.arange(0, BLOCK_M)[:, None] == i, 
                                    scores_i[None, :], scores)
        else:
            q_scaled = q * (1.0 / tl.sqrt(D * 1.0))
            scores = tl.dot(q_scaled, tl.trans(k))
            
            row_mask = tl.expand_dims(m_mask, 1) & tl.expand_dims(n_mask, 0)
            row_len_mask = tl.expand_dims(offs_m, 1) < tl.expand_dims(row_lens, 1)
            n_mask_expanded = tl.expand_dims(n, 0) < tl.expand_dims(row_lens, 1)
            scores = tl.where(row_mask & row_len_mask & n_mask_expanded, scores, float('-inf'))
        
        m_ij = tl.max(scores, 1)
        m_ij = tl.where(m_mask, m_ij, float('-inf'))
        m_new = tl.maximum(m_i, m_ij)
        
        alpha = tl.exp(m_i - m_new)
        beta = tl.exp(m_ij - m_new)
        
        p = tl.exp(scores - m_new[:, None])
        p_sum = tl.sum(p, 1)
        l_new = alpha * l_i + beta * p_sum
        
        acc_o_scale = l_i / l_new
        p_scale = beta / l_new
        
        acc_o = acc_o * acc_o_scale[:, None]
        
        p = p * p_scale[:, None]
        acc_o += tl.dot(p.to(tl.float16), v)
        
        m_i = m_new
        l_i = l_new
    
    out_ptrs = Out + offs_m[:, None] * stride_om + offs_dv[None, :] * stride_od
    tl.store(out_ptrs, acc_o.to(tl.float16), 
             mask=m_mask[:, None] & (offs_dv[None, :] < Dv))


def ragged_attn(Q: torch.Tensor, K: torch.Tensor, V: torch.Tensor, 
                row_lens: torch.Tensor) -> torch.Tensor:
    M, D = Q.shape
    N, _ = K.shape
    _, Dv = V.shape
    
    assert Q.dtype == torch.float16
    assert K.dtype == torch.float16
    assert V.dtype == torch.float16
    assert Q.is_cuda and K.is_cuda and V.is_cuda
    assert row_lens.is_cuda
    assert row_lens.shape == (M,)
    
    Out = torch.empty((M, Dv), device=Q.device, dtype=torch.float16)
    
    BLOCK_M = 32
    BLOCK_N = 64
    BLOCK_D = 32 if D >= 32 else 16
    BLOCK_DV = 32 if Dv >= 32 else 16
    
    grid = (triton.cdiv(M, BLOCK_M), 1)
    
    _ragged_attn_fwd_kernel[grid](
        Q, K, V, Out,
        Q.stride(0), Q.stride(1),
        K.stride(0), K.stride(1),
        V.stride(0), V.stride(1),
        Out.stride(0), Out.stride(1),
        row_lens,
        M, N, D, Dv,
        BLOCK_M=BLOCK_M, BLOCK_N=BLOCK_N,
        BLOCK_D=BLOCK_D, BLOCK_DV=BLOCK_DV,
        USE_INITIAL_MASK=False,
        num_warps=4,
        num_stages=3
    )
    
    return Out
"""
        return {"code": code}
