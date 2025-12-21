from typing import Dict

class Solution:
    def solve(self, spec_path: str = None) -> Dict[str, str]:
        code = r"""
import torch
import triton
import triton.language as tl

@triton.jit
def _fwd_kernel(
    Q, K, V, sm_scale,
    Mid_O, Mid_L, Mid_M,
    stride_qz, stride_qh, stride_qm, stride_qk,
    stride_kz, stride_kh, stride_kn, stride_kk,
    stride_vz, stride_vh, stride_vn, stride_vk,
    stride_mo, stride_mh, stride_ms, stride_mv,
    stride_mlz, stride_mlh, stride_mls,
    stride_mmz, stride_mmh, stride_mms,
    Z, H, N_CTX,
    BLOCK_N: tl.constexpr,
    BLOCK_DMODEL: tl.constexpr,
    BLOCK_DV: tl.constexpr,
    SPLIT_K: tl.constexpr
):
    cur_pid = tl.program_id(0)
    
    # Grid: (Z * H * SPLIT_K)
    # Decode pid
    split_k_idx = cur_pid % SPLIT_K
    rem = cur_pid // SPLIT_K
    head_idx = rem % H
    batch_idx = rem // H
    
    # Calculate N range for this split
    total_blocks = tl.cdiv(N_CTX, BLOCK_N)
    blocks_per_split = tl.cdiv(total_blocks, SPLIT_K)
    start_block = split_k_idx * blocks_per_split
    end_block = min((split_k_idx + 1) * blocks_per_split, total_blocks)
    
    # Offsets
    offs_d = tl.arange(0, BLOCK_DMODEL)
    offs_dv = tl.arange(0, BLOCK_DV)
    
    # Load Q: (Z, H, 1, Dq) -> effectively (Dq) for this batch/head
    off_q = batch_idx * stride_qz + head_idx * stride_qh
    q_ptr = Q + off_q + offs_d * stride_qk
    q = tl.load(q_ptr)
    
    # Accumulators
    m_i = -float('inf')
    l_i = 0.0
    acc = tl.zeros([BLOCK_DV], dtype=tl.float32)
    
    # Base Pointers for K and V
    k_base = K + batch_idx * stride_kz + head_idx * stride_kh
    v_base = V + batch_idx * stride_vz + head_idx * stride_vh
    
    # Iterate over assigned blocks
    for block_idx in range(start_block, end_block):
        start_n = block_idx * BLOCK_N
        offs_n = start_n + tl.arange(0, BLOCK_N)
        mask_n = offs_n < N_CTX
        
        # Load K: (BLOCK_N, Dq)
        k_ptrs = k_base + (offs_n[:, None] * stride_kn + offs_d[None, :] * stride_kk)
        k = tl.load(k_ptrs, mask=mask_n[:, None], other=0.0)
        
        # Compute QK^T
        # Q: (Dq), K: (BLOCK_N, Dq)
        # We compute K @ Q_trans -> (BLOCK_N, 1)
        qk = tl.dot(k, q[:, None])
        qk = tl.view(qk, [BLOCK_N])
        
        qk *= sm_scale
        qk = tl.where(mask_n, qk, -float('inf'))
        
        # Online Softmax updates
        current_max = tl.max(qk, 0)
        m_new = tl.maximum(m_i, current_max)
        
        p = tl.exp(qk - m_new)
        alpha = tl.exp(m_i - m_new)
        l_i = l_i * alpha + tl.sum(p, 0)
        
        # Load V: (BLOCK_N, Dv)
        v_ptrs = v_base + (offs_n[:, None] * stride_vn + offs_dv[None, :] * stride_vk)
        v = tl.load(v_ptrs, mask=mask_n[:, None], other=0.0)
        
        # Compute weighted sum
        # p: (BLOCK_N), v: (BLOCK_N, Dv)
        # p @ v -> (Dv)
        p_v = tl.dot(p[None, :].to(v.dtype), v)
        p_v = tl.view(p_v, [BLOCK_DV])
        
        acc = acc * alpha + p_v
        m_i = m_new

    # Store partial results to global memory
    # Mid_O: (Z, H, SPLIT_K, Dv)
    off_mid_o = batch_idx * stride_mo + head_idx * stride_mh + split_k_idx * stride_ms + offs_dv * stride_mv
    tl.store(Mid_O + off_mid_o, acc)
    
    # Mid_L: (Z, H, SPLIT_K)
    off_mid_l = batch_idx * stride_mlz + head_idx * stride_mlh + split_k_idx * stride_mls
    tl.store(Mid_L + off_mid_l, l_i)
    
    # Mid_M: (Z, H, SPLIT_K)
    off_mid_m = batch_idx * stride_mmz + head_idx * stride_mmh + split_k_idx * stride_mms
    tl.store(Mid_M + off_mid_m, m_i)

@triton.jit
def _reduce_kernel(
    Out, Mid_O, Mid_L, Mid_M,
    stride_oz, stride_oh, stride_om, stride_ov,
    stride_mo, stride_mh, stride_ms, stride_mv,
    stride_mlz, stride_mlh, stride_mls,
    stride_mmz, stride_mmh, stride_mms,
    Z, H,
    BLOCK_DV: tl.constexpr,
    SPLIT_K: tl.constexpr
):
    # Grid: (Z * H)
    pid = tl.program_id(0)
    head_idx = pid % H
    batch_idx = pid // H
    
    offs_dv = tl.arange(0, BLOCK_DV)
    
    # Base pointers for this batch/head
    mid_o_ptr = Mid_O + batch_idx * stride_mo + head_idx * stride_mh
    mid_l_ptr = Mid_L + batch_idx * stride_mlz + head_idx * stride_mlh
    mid_m_ptr = Mid_M + batch_idx * stride_mmz + head_idx * stride_mmh
    
    # Global accumulator
    m_global = -float('inf')
    l_global = 0.0
    acc_global = tl.zeros([BLOCK_DV], dtype=tl.float32)
    
    # Iterate over splits to reduce
    for k in range(SPLIT_K):
        m_k = tl.load(mid_m_ptr + k * stride_mms)
        l_k = tl.load(mid_l_ptr + k * stride_mls)
        
        if l_k == 0:
            continue
            
        o_k = tl.load(mid_o_ptr + k * stride_ms + offs_dv * stride_mv)
        
        m_new = tl.maximum(m_global, m_k)
        alpha_global = tl.exp(m_global - m_new)
        alpha_k = tl.exp(m_k - m_new)
        
        l_global = l_global * alpha_global + l_k * alpha_k
        acc_global = acc_global * alpha_global + o_k * alpha_k
        m_global = m_new
        
    # Store final output
    out = acc_global / l_global
    off_out = batch_idx * stride_oz + head_idx * stride_oh + offs_dv * stride_ov
    tl.store(Out + off_out, out.to(Out.dtype.element_ty))

def decoding_attn(Q: torch.Tensor, K: torch.Tensor, V: torch.Tensor) -> torch.Tensor:
    Z, H, M, Dq = Q.shape
    _, _, N, Dv = V.shape
    
    # Block size configuration
    BLOCK_N = 128
    
    # Split-K Heuristic
    # Aim for enough blocks to saturate the GPU (L4 ~60 SMs)
    target_blocks = 64
    base_grid = Z * H
    split_k = max(1, target_blocks // base_grid)
    
    # Limit split_k by available data
    n_blocks = (N + BLOCK_N - 1) // BLOCK_N
    split_k = min(split_k, n_blocks)
    split_k = max(1, split_k)
    
    # Allocate intermediate buffers (Float32 for accumulation precision)
    mid_o = torch.empty((Z, H, split_k, Dv), device=Q.device, dtype=torch.float32)
    mid_l = torch.empty((Z, H, split_k), device=Q.device, dtype=torch.float32)
    mid_m = torch.empty((Z, H, split_k), device=Q.device, dtype=torch.float32)
    
    Out = torch.empty((Z, H, M, Dv), device=Q.device, dtype=Q.dtype)
    
    sm_scale = 1.0 / (Dq ** 0.5)
    
    # Launch Forward Kernel
    grid_fwd = (Z * H * split_k,)
    _fwd_kernel[grid_fwd](
        Q, K, V, sm_scale,
        mid_o, mid_l, mid_m,
        Q.stride(0), Q.stride(1), Q.stride(2), Q.stride(3),
        K.stride(0), K.stride(1), K.stride(2), K.stride(3),
        V.stride(0), V.stride(1), V.stride(2), V.stride(3),
        mid_o.stride(0), mid_o.stride(1), mid_o.stride(2), mid_o.stride(3),
        mid_l.stride(0), mid_l.stride(1), mid_l.stride(2),
        mid_m.stride(0), mid_m.stride(1), mid_m.stride(2),
        Z, H, N,
        BLOCK_N=BLOCK_N, BLOCK_DMODEL=Dq, BLOCK_DV=Dv, SPLIT_K=split_k
    )
    
    # Launch Reduction Kernel
    grid_red = (Z * H,)
    _reduce_kernel[grid_red](
        Out, mid_o, mid_l, mid_m,
        Out.stride(0), Out.stride(1), Out.stride(2), Out.stride(3),
        mid_o.stride(0), mid_o.stride(1), mid_o.stride(2), mid_o.stride(3),
        mid_l.stride(0), mid_l.stride(1), mid_l.stride(2),
        mid_m.stride(0), mid_m.stride(1), mid_m.stride(2),
        Z, H,
        BLOCK_DV=Dv, SPLIT_K=split_k
    )
    
    return Out
"""
        return {"code": code}
