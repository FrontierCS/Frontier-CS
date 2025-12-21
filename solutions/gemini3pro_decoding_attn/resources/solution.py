import torch
import triton
import triton.language as tl

class Solution:
    def solve(self, spec_path: str = None) -> dict:
        code = r"""
import torch
import triton
import triton.language as tl

@triton.jit
def _flash_decode_stage1_kernel(
    Q, K, V,
    Mid_O, Mid_L, Mid_M,
    sm_scale,
    stride_qz, stride_qh, stride_qm, stride_qk,
    stride_kz, stride_kh, stride_kn, stride_kk,
    stride_vz, stride_vh, stride_vn, stride_vk,
    stride_oz, stride_oh, stride_os, stride_om, stride_od,
    stride_lz, stride_lh, stride_ls, stride_lm,
    stride_mz, stride_mh, stride_ms, stride_mm,
    Z, H, N, M, D,
    BLOCK_M: tl.constexpr, BLOCK_N: tl.constexpr, BLOCK_D: tl.constexpr
):
    split_idx = tl.program_id(0)
    off_zh = tl.program_id(1)
    
    off_h = off_zh % H
    off_z = off_zh // H
    
    start_n = split_idx * BLOCK_N
    offs_m = tl.arange(0, BLOCK_M)
    offs_n = start_n + tl.arange(0, BLOCK_N)
    offs_d = tl.arange(0, BLOCK_D)
    
    # Load Q: (Z, H, M, D)
    q_ptr = Q + off_z * stride_qz + off_h * stride_qh
    q_ptrs = q_ptr + offs_m[:, None] * stride_qm + offs_d[None, :] * stride_qk
    mask_m = offs_m < M
    q = tl.load(q_ptrs, mask=mask_m[:, None], other=0.0)
    
    # Load K: (Z, H, N, D)
    k_ptr = K + off_z * stride_kz + off_h * stride_kh
    k_ptrs = k_ptr + offs_n[:, None] * stride_kn + offs_d[None, :] * stride_kk
    mask_n = offs_n < N
    k = tl.load(k_ptrs, mask=mask_n[:, None], other=0.0)
    
    # Compute S = QK^T
    # q: (M, D), k: (N, D) -> s: (M, N)
    s = tl.dot(q, tl.trans(k))
    s *= sm_scale
    s = tl.where(mask_n[None, :], s, float("-inf"))
    
    # Compute stats
    m_i = tl.max(s, 1) # (M,)
    p = tl.exp(s - m_i[:, None])
    l_i = tl.sum(p, 1) # (M,)
    
    # Load V: (Z, H, N, D)
    v_ptr = V + off_z * stride_vz + off_h * stride_vh
    v_ptrs = v_ptr + offs_n[:, None] * stride_vn + offs_d[None, :] * stride_vk
    v = tl.load(v_ptrs, mask=mask_n[:, None], other=0.0)
    
    # Compute Acc = PV
    acc = tl.dot(p.to(tl.float16), v.to(tl.float16))
    
    # Write to temp buffers
    # Mid_O: (Z, H, Splits, M, D)
    off_mid_base = off_z * stride_oz + off_h * stride_oh + split_idx * stride_os
    out_ptrs = Mid_O + off_mid_base + offs_m[:, None] * stride_om + offs_d[None, :] * stride_od
    tl.store(out_ptrs, acc.to(tl.float16), mask=mask_m[:, None])
    
    # Mid_L: (Z, H, Splits, M)
    off_l_base = off_z * stride_lz + off_h * stride_lh + split_idx * stride_ls
    l_ptrs = Mid_L + off_l_base + offs_m * stride_lm
    tl.store(l_ptrs, l_i, mask=mask_m)
    
    # Mid_M: (Z, H, Splits, M)
    off_m_base = off_z * stride_mz + off_h * stride_mh + split_idx * stride_ms
    m_ptrs = Mid_M + off_m_base + offs_m * stride_mm
    tl.store(m_ptrs, m_i, mask=mask_m)

@triton.jit
def _flash_decode_stage2_kernel(
    Mid_O, Mid_L, Mid_M,
    Out,
    stride_oz, stride_oh, stride_os, stride_om, stride_od,
    stride_lz, stride_lh, stride_ls, stride_lm,
    stride_mz, stride_mh, stride_ms, stride_mm,
    stride_outz, stride_outh, stride_outm, stride_outd,
    Z, H, N, M, D,
    split_n,
    BLOCK_M: tl.constexpr, BLOCK_D: tl.constexpr
):
    off_zh = tl.program_id(0)
    off_h = off_zh % H
    off_z = off_zh // H
    
    offs_m = tl.arange(0, BLOCK_M)
    offs_d = tl.arange(0, BLOCK_D)
    
    acc = tl.zeros([BLOCK_M, BLOCK_D], dtype=tl.float32)
    l_sum = tl.zeros([BLOCK_M], dtype=tl.float32)
    m_max = tl.full([BLOCK_M], float("-inf"), dtype=tl.float32)
    
    mid_o_base = Mid_O + off_z * stride_oz + off_h * stride_oh
    mid_l_base = Mid_L + off_z * stride_lz + off_h * stride_lh
    mid_m_base = Mid_M + off_z * stride_mz + off_h * stride_mh
    
    for i in range(split_n):
        # Load stats
        m_ptr = mid_m_base + i * stride_ms + offs_m * stride_mm
        m_i = tl.load(m_ptr, mask=offs_m < M, other=float("-inf"))
        
        l_ptr = mid_l_base + i * stride_ls + offs_m * stride_lm
        l_i = tl.load(l_ptr, mask=offs_m < M, other=0.0)
        
        o_ptr = mid_o_base + i * stride_os + offs_m[:, None] * stride_om + offs_d[None, :] * stride_od
        o_i = tl.load(o_ptr, mask=offs_m[:, None] < M, other=0.0).to(tl.float32)
        
        # Online softmax reduction
        m_new = tl.maximum(m_max, m_i)
        alpha = tl.exp(m_max - m_new)
        beta = tl.exp(m_i - m_new)
        
        acc = acc * alpha[:, None] + o_i * beta[:, None]
        l_sum = l_sum * alpha + l_i * beta
        m_max = m_new
        
    out = acc / l_sum[:, None]
    
    out_ptr = Out + off_z * stride_outz + off_h * stride_outh
    out_ptrs = out_ptr + offs_m[:, None] * stride_outm + offs_d[None, :] * stride_outd
    tl.store(out_ptrs, out.to(tl.float16), mask=offs_m[:, None] < M)

def decoding_attn(Q, K, V):
    Z, H, M, D = Q.shape
    _, _, N, _ = K.shape
    
    # Tuning params
    BLOCK_N = 128
    BLOCK_M = 32 # Covers M=1 efficiently, handles up to 32.
    
    num_splits = (N + BLOCK_N - 1) // BLOCK_N
    
    mid_o = torch.empty((Z, H, num_splits, M, D), dtype=torch.float16, device=Q.device)
    mid_l = torch.empty((Z, H, num_splits, M), dtype=torch.float32, device=Q.device)
    mid_m = torch.empty((Z, H, num_splits, M), dtype=torch.float32, device=Q.device)
    
    sm_scale = 1.0 / (D ** 0.5)
    
    # Stage 1: Partial decoding
    grid1 = (num_splits, Z * H)
    _flash_decode_stage1_kernel[grid1](
        Q, K, V,
        mid_o, mid_l, mid_m,
        sm_scale,
        Q.stride(0), Q.stride(1), Q.stride(2), Q.stride(3),
        K.stride(0), K.stride(1), K.stride(2), K.stride(3),
        V.stride(0), V.stride(1), V.stride(2), V.stride(3),
        mid_o.stride(0), mid_o.stride(1), mid_o.stride(2), mid_o.stride(3), mid_o.stride(4),
        mid_l.stride(0), mid_l.stride(1), mid_l.stride(2), mid_l.stride(3),
        mid_m.stride(0), mid_m.stride(1), mid_m.stride(2), mid_m.stride(3),
        Z, H, N, M, D,
        BLOCK_M=BLOCK_M, BLOCK_N=BLOCK_N, BLOCK_D=D
    )
    
    Out = torch.empty_like(Q)
    
    # Stage 2: Reduction
    grid2 = (Z * H, )
    _flash_decode_stage2_kernel[grid2](
        mid_o, mid_l, mid_m,
        Out,
        mid_o.stride(0), mid_o.stride(1), mid_o.stride(2), mid_o.stride(3), mid_o.stride(4),
        mid_l.stride(0), mid_l.stride(1), mid_l.stride(2), mid_l.stride(3),
        mid_m.stride(0), mid_m.stride(1), mid_m.stride(2), mid_m.stride(3),
        Out.stride(0), Out.stride(1), Out.stride(2), Out.stride(3),
        Z, H, N, M, D,
        num_splits,
        BLOCK_M=BLOCK_M, BLOCK_D=D
    )
    
    return Out
"""
        return {"code": code}
