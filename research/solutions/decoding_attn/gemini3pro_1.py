import torch
import triton
import triton.language as tl
import math
from typing import Dict, Any

class Solution:
    def solve(self, spec_path: str = None) -> Dict[str, Any]:
        kernel_code = r"""
import torch
import triton
import triton.language as tl

@triton.jit
def _fwd_kernel_stage1(
    Q, K, V,
    Mid_O, Mid_L, Mid_M,
    stride_qz, stride_qh, stride_qm, stride_qk,
    stride_kz, stride_kh, stride_kn, stride_kk,
    stride_vz, stride_vh, stride_vn, stride_vk,
    stride_mid_oz, stride_mid_oh, stride_mid_om, stride_mid_on, stride_mid_od,
    stride_mid_lz, stride_mid_lh, stride_mid_lm, stride_mid_ln,
    sm_scale,
    Z, H, M, N, D,
    BLOCK_DMODEL: tl.constexpr,
    BLOCK_N: tl.constexpr
):
    pid_n = tl.program_id(0)
    pid_zhm = tl.program_id(1)
    
    idx_m = pid_zhm % M
    idx_zh = pid_zhm // M
    idx_h = idx_zh % H
    idx_z = idx_zh // H
    
    start_n = pid_n * BLOCK_N
    
    # Offsets for Q: (Z, H, M, D)
    # Stride of Q last dim is stride_qk
    off_q = idx_z * stride_qz + idx_h * stride_qh + idx_m * stride_qm
    offs_d = tl.arange(0, BLOCK_DMODEL)
    mask_d = offs_d < D
    
    # Load Q (1, D)
    q_ptrs = Q + off_q + offs_d * stride_qk
    q = tl.load(q_ptrs, mask=mask_d, other=0.0)
    
    # Offsets for K, V: (Z, H, N, D)
    k_base = K + idx_z * stride_kz + idx_h * stride_kh
    v_base = V + idx_z * stride_vz + idx_h * stride_vh
    
    offs_n = start_n + tl.arange(0, BLOCK_N)
    mask_n = offs_n < N
    
    # Load K block (BLOCK_N, D)
    k_ptrs = k_base + (offs_n[:, None] * stride_kn + offs_d[None, :] * stride_kk)
    k = tl.load(k_ptrs, mask=mask_n[:, None] & mask_d[None, :], other=0.0)
    
    # Compute scores QK^T
    # q: (D,), k: (BLOCK_N, D) -> q*k: (BLOCK_N, D) -> sum: (BLOCK_N,)
    qk = tl.sum(q[None, :] * k, 1)
    qk *= sm_scale
    
    # Mask out of bounds N
    qk = tl.where(mask_n, qk, -float('inf'))
    
    # Compute max and exp
    m_i = tl.max(qk, 0)
    p = tl.exp(qk - m_i)
    l_i = tl.sum(p, 0)
    
    # Load V block (BLOCK_N, D)
    v_ptrs = v_base + (offs_n[:, None] * stride_vn + offs_d[None, :] * stride_vk)
    v = tl.load(v_ptrs, mask=mask_n[:, None] & mask_d[None, :], other=0.0)
    
    # Weighted sum: sum(p * v)
    # p: (BLOCK_N,), v: (BLOCK_N, D)
    acc = tl.sum(p[:, None] * v, 0)
    
    # Store to intermediate buffers
    # Mid_O: (Z, H, M, NUM_BLOCKS, D)
    mid_o_ptr = Mid_O + \
                idx_z * stride_mid_oz + \
                idx_h * stride_mid_oh + \
                idx_m * stride_mid_om + \
                pid_n * stride_mid_on + \
                offs_d * stride_mid_od
                
    tl.store(mid_o_ptr, acc, mask=mask_d)
    
    # Mid_L, Mid_M: (Z, H, M, NUM_BLOCKS)
    mid_stats_offset = idx_z * stride_mid_lz + \
                       idx_h * stride_mid_lh + \
                       idx_m * stride_mid_lm + \
                       pid_n * stride_mid_ln
                       
    tl.store(Mid_L + mid_stats_offset, l_i)
    tl.store(Mid_M + mid_stats_offset, m_i)

@triton.jit
def _fwd_kernel_stage2(
    Mid_O, Mid_L, Mid_M,
    Out,
    stride_mid_oz, stride_mid_oh, stride_mid_om, stride_mid_on, stride_mid_od,
    stride_mid_lz, stride_mid_lh, stride_mid_lm, stride_mid_ln,
    stride_oz, stride_oh, stride_om, stride_od,
    Z, H, M, D, NUM_BLOCKS,
    BLOCK_DMODEL: tl.constexpr
):
    pid = tl.program_id(0)
    # pid covers Z * H * M
    idx_m = pid % M
    idx_zh = pid // M
    idx_h = idx_zh % H
    idx_z = idx_zh // H
    
    offs_d = tl.arange(0, BLOCK_DMODEL)
    mask_d = offs_d < D
    
    # Base pointers for this sequence
    mid_stats_base = idx_z * stride_mid_lz + \
                     idx_h * stride_mid_lh + \
                     idx_m * stride_mid_lm
                     
    mid_o_base = idx_z * stride_mid_oz + \
                 idx_h * stride_mid_oh + \
                 idx_m * stride_mid_om
    
    # Global accumulator
    m_global = -float('inf')
    l_global = 0.0
    acc_global = tl.zeros([BLOCK_DMODEL], dtype=tl.float32)
    
    for i in range(NUM_BLOCKS):
        # Load stats
        m_i = tl.load(Mid_M + mid_stats_base + i * stride_mid_ln)
        l_i = tl.load(Mid_L + mid_stats_base + i * stride_mid_ln)
        
        # Load accumulator
        acc_ptr = Mid_O + mid_o_base + i * stride_mid_on + offs_d * stride_mid_od
        acc_i = tl.load(acc_ptr, mask=mask_d, other=0.0)
        
        # Combine
        m_new = tl.max(m_global, m_i)
        
        alpha = tl.exp(m_global - m_new)
        beta = tl.exp(m_i - m_new)
        
        l_global = l_global * alpha + l_i * beta
        acc_global = acc_global * alpha + acc_i * beta
        m_global = m_new
        
    out = acc_global / l_global
    
    # Store output: (Z, H, M, D)
    out_off = idx_z * stride_oz + idx_h * stride_oh + idx_m * stride_om
    out_ptr = Out + out_off + offs_d * stride_od
    tl.store(out_ptr, out.to(tl.float16), mask=mask_d)

def decoding_attn(Q, K, V):
    Z, H, M, Dq = Q.shape
    _, _, N, Dk = K.shape
    _, _, _, Dv = V.shape
    
    # Ensure dimensions match
    assert Dq == Dk == Dv, "Head dimensions must match"
    D = Dq
    
    BLOCK_N = 128
    
    # Compute block size for D
    BLOCK_DMODEL = 1
    while BLOCK_DMODEL < D:
        BLOCK_DMODEL *= 2
    
    # Number of splits
    NUM_BLOCKS = (N + BLOCK_N - 1) // BLOCK_N
    
    # Allocation for intermediate results
    # Mid_O: (Z, H, M, NUM_BLOCKS, D)
    # Mid_L: (Z, H, M, NUM_BLOCKS)
    # Mid_M: (Z, H, M, NUM_BLOCKS)
    
    Mid_O = torch.empty((Z, H, M, NUM_BLOCKS, D), dtype=torch.float32, device=Q.device)
    Mid_L = torch.empty((Z, H, M, NUM_BLOCKS), dtype=torch.float32, device=Q.device)
    Mid_M = torch.empty((Z, H, M, NUM_BLOCKS), dtype=torch.float32, device=Q.device)
    
    Output = torch.empty((Z, H, M, D), dtype=Q.dtype, device=Q.device)
    
    sm_scale = 1.0 / (D ** 0.5)
    
    # Stage 1: Parallel Compute over N blocks
    grid1 = (NUM_BLOCKS, Z * H * M)
    _fwd_kernel_stage1[grid1](
        Q, K, V,
        Mid_O, Mid_L, Mid_M,
        Q.stride(0), Q.stride(1), Q.stride(2), Q.stride(3),
        K.stride(0), K.stride(1), K.stride(2), K.stride(3),
        V.stride(0), V.stride(1), V.stride(2), V.stride(3),
        Mid_O.stride(0), Mid_O.stride(1), Mid_O.stride(2), Mid_O.stride(3), Mid_O.stride(4),
        Mid_L.stride(0), Mid_L.stride(1), Mid_L.stride(2), Mid_L.stride(3),
        sm_scale,
        Z, H, M, N, D,
        BLOCK_DMODEL=BLOCK_DMODEL,
        BLOCK_N=BLOCK_N,
        num_warps=4,
        num_stages=2
    )
    
    # Stage 2: Reduction
    grid2 = (Z * H * M,)
    _fwd_kernel_stage2[grid2](
        Mid_O, Mid_L, Mid_M,
        Output,
        Mid_O.stride(0), Mid_O.stride(1), Mid_O.stride(2), Mid_O.stride(3), Mid_O.stride(4),
        Mid_L.stride(0), Mid_L.stride(1), Mid_L.stride(2), Mid_L.stride(3),
        Output.stride(0), Output.stride(1), Output.stride(2), Output.stride(3),
        Z, H, M, D, NUM_BLOCKS,
        BLOCK_DMODEL=BLOCK_DMODEL,
        num_warps=4,
        num_stages=2
    )
    
    return Output
"""
        return {"code": kernel_code}