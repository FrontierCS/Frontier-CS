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
def _fwd_kernel_stage1(
    Q, K, V,
    Mid_O, Mid_L, Mid_M,
    stride_qz, stride_qh, stride_qm, stride_qk,
    stride_kz, stride_kh, stride_kn, stride_kk,
    stride_vz, stride_vh, stride_vn, stride_vk,
    stride_mo_b, stride_mo_s, stride_mo_d,
    stride_ml_b, stride_ml_s,
    Z, H, M, N,
    sm_scale,
    BLOCK_N: tl.constexpr,
    BLOCK_DMODEL: tl.constexpr
):
    batch_id = tl.program_id(0)
    split_id = tl.program_id(1)
    
    m_idx = batch_id % M
    rem = batch_id // M
    h_idx = rem % H
    z_idx = rem // H
    
    # Q Offset
    off_q = z_idx * stride_qz + h_idx * stride_qh + m_idx * stride_qm
    
    # K/V Base Offsets (broadcast over N)
    off_k_base = z_idx * stride_kz + h_idx * stride_kh
    off_v_base = z_idx * stride_vz + h_idx * stride_vh
    
    # Load Q
    offs_d = tl.arange(0, BLOCK_DMODEL)
    q = tl.load(Q + off_q + offs_d * stride_qk)
    
    # K/V Block offsets
    start_n = split_id * BLOCK_N
    offs_n = start_n + tl.arange(0, BLOCK_N)
    mask_n = offs_n < N
    
    # Load K
    k_ptrs = K + off_k_base + (offs_n[:, None] * stride_kn + offs_d[None, :] * stride_kk)
    k = tl.load(k_ptrs, mask=mask_n[:, None], other=0.0)
    
    # Compute QK^T
    # q: (D,), k: (BLOCK_N, D) -> qk: (BLOCK_N,)
    qk = tl.sum(q[None, :] * k, axis=1)
    qk *= sm_scale
    qk = tl.where(mask_n, qk, float("-inf"))
    
    # Compute Softmax Partials
    m_i = tl.max(qk, 0)
    p = tl.exp(qk - m_i)
    l_i = tl.sum(p, 0)
    
    # Load V
    v_ptrs = V + off_v_base + (offs_n[:, None] * stride_vn + offs_d[None, :] * stride_vk)
    v = tl.load(v_ptrs, mask=mask_n[:, None], other=0.0)
    
    # Compute Weighted Sum (Acc)
    # p: (BLOCK_N,), v: (BLOCK_N, D) -> acc: (D,)
    acc = tl.sum(p[:, None] * v, axis=0)
    
    # Store Partials
    off_mid_o = batch_id * stride_mo_b + split_id * stride_mo_s
    off_mid_l = batch_id * stride_ml_b + split_id * stride_ml_s
    
    tl.store(Mid_M + off_mid_l, m_i)
    tl.store(Mid_L + off_mid_l, l_i)
    tl.store(Mid_O + off_mid_o + offs_d * stride_mo_d, acc)

@triton.jit
def _fwd_kernel_stage2(
    Mid_O, Mid_L, Mid_M,
    Out,
    stride_mo_b, stride_mo_s, stride_mo_d,
    stride_ml_b, stride_ml_s,
    stride_o_z, stride_o_h, stride_o_m, stride_o_d,
    Z, H, M,
    NUM_SPLITS,
    BLOCK_DMODEL: tl.constexpr
):
    batch_id = tl.program_id(0)
    
    m_idx = batch_id % M
    rem = batch_id // M
    h_idx = rem % H
    z_idx = rem // H
    
    off_out = z_idx * stride_o_z + h_idx * stride_o_h + m_idx * stride_o_m
    
    offs_d = tl.arange(0, BLOCK_DMODEL)
    
    global_m = float("-inf")
    global_l = 0.0
    global_acc = tl.zeros([BLOCK_DMODEL], dtype=tl.float32)
    
    for s in range(0, NUM_SPLITS):
        off_l = batch_id * stride_ml_b + s * stride_ml_s
        off_o = batch_id * stride_mo_b + s * stride_mo_s
        
        m_i = tl.load(Mid_M + off_l)
        l_i = tl.load(Mid_L + off_l)
        acc_i = tl.load(Mid_O + off_o + offs_d * stride_mo_d)
        
        new_m = tl.maximum(global_m, m_i)
        
        alpha = tl.exp(global_m - new_m)
        beta = tl.exp(m_i - new_m)
        
        global_m = new_m
        global_l = global_l * alpha + l_i * beta
        global_acc = global_acc * alpha + acc_i * beta
        
    out = global_acc / global_l
    tl.store(Out + off_out + offs_d * stride_o_d, out.to(tl.float16))

def decoding_attn(Q: torch.Tensor, K: torch.Tensor, V: torch.Tensor) -> torch.Tensor:
    Z, H, M, D = Q.shape
    _, _, N, _ = K.shape
    
    # Configuration
    BLOCK_N = 128
    NUM_SPLITS = (N + BLOCK_N - 1) // BLOCK_N
    batch_size = Z * H * M
    
    # Allocate intermediate buffers
    # Mid buffers flatten Z, H, M into first dim
    Mid_O = torch.empty((batch_size, NUM_SPLITS, D), dtype=torch.float32, device=Q.device)
    Mid_L = torch.empty((batch_size, NUM_SPLITS), dtype=torch.float32, device=Q.device)
    Mid_M = torch.empty((batch_size, NUM_SPLITS), dtype=torch.float32, device=Q.device)
    
    # Output buffer
    Out = torch.empty((Z, H, M, D), dtype=torch.float16, device=Q.device)
    
    sm_scale = 1.0 / (D ** 0.5)
    
    # Stage 1: Partial Attention
    _fwd_kernel_stage1[(batch_size, NUM_SPLITS)](
        Q, K, V,
        Mid_O, Mid_L, Mid_M,
        Q.stride(0), Q.stride(1), Q.stride(2), Q.stride(3),
        K.stride(0), K.stride(1), K.stride(2), K.stride(3),
        V.stride(0), V.stride(1), V.stride(2), V.stride(3),
        Mid_O.stride(0), Mid_O.stride(1), Mid_O.stride(2),
        Mid_L.stride(0), Mid_L.stride(1),
        Z, H, M, N,
        sm_scale,
        BLOCK_N=BLOCK_N,
        BLOCK_DMODEL=D,
        num_warps=4,
        num_stages=2
    )
    
    # Stage 2: Reduction
    _fwd_kernel_stage2[(batch_size,)](
        Mid_O, Mid_L, Mid_M,
        Out,
        Mid_O.stride(0), Mid_O.stride(1), Mid_O.stride(2),
        Mid_L.stride(0), Mid_L.stride(1),
        Out.stride(0), Out.stride(1), Out.stride(2), Out.stride(3),
        Z, H, M,
        NUM_SPLITS,
        BLOCK_DMODEL=D,
        num_warps=4,
        num_stages=2
    )
    
    return Out
"""
        return {"code": code}