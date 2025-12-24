import torch
import triton
import triton.language as tl
import os

@triton.autotune(
    configs=[
        triton.Config({'BLOCK_M': 32, 'BLOCK_N': 64, 'D_HEAD_SPLIT': 1}, num_warps=4),
        triton.Config({'BLOCK_M': 64, 'BLOCK_N': 64, 'D_HEAD_SPLIT': 1}, num_warps=4),
        triton.Config({'BLOCK_M': 32, 'BLOCK_N': 128, 'D_HEAD_SPLIT': 1}, num_warps=4),
        triton.Config({'BLOCK_M': 64, 'BLOCK_N': 128, 'D_HEAD_SPLIT': 1}, num_warps=4),
        triton.Config({'BLOCK_M': 32, 'BLOCK_N': 64, 'D_HEAD_SPLIT': 2}, num_warps=4),
        triton.Config({'BLOCK_M': 64, 'BLOCK_N': 64, 'D_HEAD_SPLIT': 2}, num_warps=4),
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 64, 'D_HEAD_SPLIT': 1}, num_warps=8),
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 128, 'D_HEAD_SPLIT': 1}, num_warps=8),
    ],
    key=['M', 'N', 'Dq', 'Dv'],
)
@triton.jit
def _gdpa_attn_kernel(
    Q, K, V, GQ, GK, Out,
    stride_qz, stride_qh, stride_qm, stride_qd,
    stride_kz, stride_kh, stride_kn, stride_kd,
    stride_vz, stride_vh, stride_vn, stride_vd,
    stride_gqz, stride_gqh, stride_gqm, stride_gqd,
    stride_gkz, stride_gkh, stride_gkn, stride_gkd,
    stride_oz, stride_oh, stride_om, stride_od,
    Z, H, M, N, Dq, Dv,
    scale: tl.constexpr,
    BLOCK_M: tl.constexpr,
    BLOCK_N: tl.constexpr,
    D_HEAD_SPLIT: tl.constexpr,
):
    pid_bh = tl.program_id(0)
    pid_m = tl.program_id(1)
    pid_split = tl.program_id(2)
    
    batch_id = pid_bh // H
    head_id = pid_bh % H
    
    Dq_PER_SPLIT = Dq // D_HEAD_SPLIT
    split_start = pid_split * Dq_PER_SPLIT
    split_end = split_start + Dq_PER_SPLIT
    
    offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
    offs_n = tl.arange(0, BLOCK_N)
    offs_dq = split_start + tl.arange(0, Dq_PER_SPLIT)
    offs_dv = tl.arange(0, Dv)
    
    m_mask = offs_m < M
    n_mask = tl.arange(0, BLOCK_N) < N
    dq_mask = tl.arange(0, Dq_PER_SPLIT) < Dq_PER_SPLIT
    dv_mask = tl.arange(0, Dv) < Dv
    
    Q_ptr = Q + batch_id * stride_qz + head_id * stride_qh + offs_m[:, None] * stride_qm + offs_dq[None, :] * stride_qd
    GQ_ptr = GQ + batch_id * stride_gqz + head_id * stride_gqh + offs_m[:, None] * stride_gqm + offs_dq[None, :] * stride_gqd
    
    q = tl.load(Q_ptr, mask=m_mask[:, None] & dq_mask[None, :], other=0.0).to(tl.float32)
    gq = tl.load(GQ_ptr, mask=m_mask[:, None] & dq_mask[None, :], other=0.0).to(tl.float32)
    q_gated = q * (1.0 / (1.0 + tl.exp(-gq)))
    
    max_m = tl.full([BLOCK_M], float('-inf'), dtype=tl.float32)
    sum_m = tl.zeros([BLOCK_M], dtype=tl.float32)
    out_acc = tl.zeros([BLOCK_M, Dv], dtype=tl.float32)
    
    for start_n in range(0, N, BLOCK_N):
        start_n = tl.multiple_of(start_n, BLOCK_N)
        offs_n_curr = start_n + offs_n
        
        K_ptr = K + batch_id * stride_kz + head_id * stride_kh + offs_n_curr[None, :] * stride_kn + offs_dq[:, None] * stride_kd
        GK_ptr = GK + batch_id * stride_gkz + head_id * stride_gkh + offs_n_curr[None, :] * stride_gkn + offs_dq[:, None] * stride_gkd
        
        k = tl.load(K_ptr, mask=n_mask[None, :] & dq_mask[:, None], other=0.0).to(tl.float32)
        gk = tl.load(GK_ptr, mask=n_mask[None, :] & dq_mask[:, None], other=0.0).to(tl.float32)
        k_gated = k * (1.0 / (1.0 + tl.exp(-gk)))
        
        V_ptr = V + batch_id * stride_vz + head_id * stride_vh + offs_n_curr[:, None] * stride_vn + offs_dv[None, :] * stride_vd
        v = tl.load(V_ptr, mask=n_mask[:, None] & dv_mask[None, :], other=0.0).to(tl.float32)
        
        scores = tl.dot(q_gated, k_gated, trans_b=True) * scale
        scores = tl.where(n_mask[None, :], scores, float('-inf'))
        
        m_curr = tl.max(scores, axis=1)
        m_new = tl.maximum(max_m, m_curr)
        alpha = tl.exp(max_m - m_new)
        beta = tl.exp(m_curr - m_new)
        
        scores_scaled = tl.exp(scores - m_new[:, None])
        scores_scaled = tl.where(n_mask[None, :], scores_scaled, 0.0)
        
        sum_m = sum_m * alpha + tl.sum(scores_scaled, axis=1)
        out_acc = out_acc * alpha[:, None] + tl.dot(scores_scaled.to(tl.float16), v, trans_a=False, trans_b=False).to(tl.float32)
        max_m = m_new
    
    out_acc = out_acc / sum_m[:, None]
    
    Out_ptr = Out + batch_id * stride_oz + head_id * stride_oh + offs_m[:, None] * stride_om + offs_dv[None, :] * stride_od
    
    if D_HEAD_SPLIT == 1:
        tl.store(Out_ptr, out_acc.to(tl.float16), mask=m_mask[:, None] & dv_mask[None, :])
    else:
        tl.atomic_add(Out_ptr, out_acc.to(tl.float16), mask=m_mask[:, None] & dv_mask[None, :])

def gdpa_attn(Q: torch.Tensor, K: torch.Tensor, V: torch.Tensor, GQ: torch.Tensor, GK: torch.Tensor) -> torch.Tensor:
    Z, H, M, Dq = Q.shape
    _, _, N, _ = K.shape
    _, _, _, Dv = V.shape
    
    scale = 1.0 / (Dq ** 0.5)
    
    Out = torch.empty((Z, H, M, Dv), device=Q.device, dtype=Q.dtype)
    
    grid = lambda META: (
        Z * H,
        triton.cdiv(M, META['BLOCK_M']),
        META['D_HEAD_SPLIT'],
    )
    
    _gdpa_attn_kernel[grid](
        Q, K, V, GQ, GK, Out,
        Q.stride(0), Q.stride(1), Q.stride(2), Q.stride(3),
        K.stride(0), K.stride(1), K.stride(2), K.stride(3),
        V.stride(0), V.stride(1), V.stride(2), V.stride(3),
        GQ.stride(0), GQ.stride(1), GQ.stride(2), GQ.stride(3),
        GK.stride(0), GK.stride(1), GK.stride(2), GK.stride(3),
        Out.stride(0), Out.stride(1), Out.stride(2), Out.stride(3),
        Z, H, M, N, Dq, Dv,
        scale
    )
    
    return Out

class Solution:
    def solve(self, spec_path: str = None) -> dict:
        return {"code": self._get_code()}
    
    def _get_code(self):
        import inspect
        return inspect.getsource(gdpa_attn) + "\n" + inspect.getsource(Solution)
