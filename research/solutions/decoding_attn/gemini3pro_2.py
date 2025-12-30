import torch
import triton
import triton.language as tl

class Solution:
    def solve(self, spec_path: str = None) -> dict:
        code = r"""
import torch
import triton
import triton.language as tl
import math

@triton.autotune(
    configs=[
        triton.Config({'BLOCK_N': 128}, num_warps=4, num_stages=3),
        triton.Config({'BLOCK_N': 64}, num_warps=4, num_stages=3),
        triton.Config({'BLOCK_N': 256}, num_warps=8, num_stages=3),
    ],
    key=['chunk_size', 'HEAD_DIM']
)
@triton.jit
def _decoding_split_kernel(
    Q, K, V, Sm_scale,
    L, Out,
    stride_qz, stride_qh, stride_qm, stride_qk,
    stride_kz, stride_kh, stride_kn, stride_kk,
    stride_vz, stride_vh, stride_vn, stride_vk,
    stride_lz, stride_lh, stride_lm, stride_ls,
    stride_oz, stride_oh, stride_om, stride_os, stride_od,
    Z, H, M, N,
    NUM_SPLITS,
    HEAD_DIM: tl.constexpr,
    BLOCK_N: tl.constexpr,
    chunk_size: tl.constexpr
):
    pid = tl.program_id(0)
    
    # Grid is flattened: Z * H * M * NUM_SPLITS
    split_idx = pid % NUM_SPLITS
    temp = pid // NUM_SPLITS
    m_idx = temp % M
    temp = temp // M
    h_idx = temp % H
    z_idx = temp // H
    
    start_n = split_idx * chunk_size
    if start_n >= N:
        return
        
    end_n = min(start_n + chunk_size, N)

    # Q offsets: (Z, H, M, D)
    off_q = z_idx * stride_qz + h_idx * stride_qh + m_idx * stride_qm
    q_ptr = Q + off_q + tl.arange(0, HEAD_DIM) * stride_qk
    
    # Load Q, cast to F32 for accumulation
    q = tl.load(q_ptr).to(tl.float32)
    q_scaled = q * Sm_scale
    
    # Accumulators
    m_i = -float('inf')
    l_i = 1.0
    acc = tl.zeros([HEAD_DIM], dtype=tl.float32)
    
    # Pointers to K, V
    off_k = z_idx * stride_kz + h_idx * stride_kh
    off_v = z_idx * stride_vz + h_idx * stride_vh
    k_ptr_base = K + off_k
    v_ptr_base = V + off_v
    
    # Iterate over chunks of K/V
    for start_block in range(start_n, end_n, BLOCK_N):
        # Offsets for current block
        offs_n = start_block + tl.arange(0, BLOCK_N)
        mask_n = offs_n < end_n
        
        # Load K: (BLOCK_N, D)
        # Address: base + n * stride_kn + d * stride_kk
        k_ptrs = k_ptr_base + (offs_n[:, None] * stride_kn + tl.arange(0, HEAD_DIM)[None, :] * stride_kk)
        k = tl.load(k_ptrs, mask=mask_n[:, None], other=0.0).to(tl.float32)
        
        # Compute scores: Q * K^T -> (BLOCK_N,)
        qk = tl.sum(q_scaled[None, :] * k, axis=1)
        qk = tl.where(mask_n, qk, -float('inf'))
        
        # Online Softmax
        m_curr = tl.max(qk, 0)
        m_new = tl.maximum(m_i, m_curr)
        
        alpha = tl.exp(m_i - m_new)
        beta = tl.exp(qk - m_new)
        
        # Load V: (BLOCK_N, D)
        v_ptrs = v_ptr_base + (offs_n[:, None] * stride_vn + tl.arange(0, HEAD_DIM)[None, :] * stride_vk)
        v = tl.load(v_ptrs, mask=mask_n[:, None], other=0.0).to(tl.float32)
        
        # Update Accumulators
        p = beta.to(tl.float32)
        acc = acc * alpha + tl.sum(p[:, None] * v, axis=0)
        l_i = l_i * alpha + tl.sum(p)
        m_i = m_new

    # Store partials
    # LSE = m_i + log(l_i)
    lse = m_i + tl.log(l_i)
    
    # Store O_part = acc / l_i (locally normalized)
    out_val = acc / l_i
    
    # Out ptrs: (Z, H, M, SPLIT, D)
    off_out = z_idx * stride_oz + h_idx * stride_oh + m_idx * stride_om + split_idx * stride_os
    out_ptrs = Out + off_out + tl.arange(0, HEAD_DIM) * stride_od
    tl.store(out_ptrs, out_val)
    
    # L ptrs: (Z, H, M, SPLIT)
    off_l = z_idx * stride_lz + h_idx * stride_lh + m_idx * stride_lm + split_idx * stride_ls
    tl.store(L + off_l, lse)

@triton.jit
def _decoding_reduce_kernel(
    Out_partials, L_partials, Out_final,
    stride_oz, stride_oh, stride_om, stride_os, stride_od,
    stride_lz, stride_lh, stride_lm, stride_ls,
    stride_foz, stride_foh, stride_fom, stride_fod,
    Z, H, M,
    HEAD_DIM: tl.constexpr,
    SPLIT_K: tl.constexpr
):
    pid = tl.program_id(0)
    # Grid: Z * H * M
    m_idx = pid % M
    temp = pid // M
    h_idx = temp % H
    z_idx = temp // H
    
    # Base pointers
    l_ptr_base = L_partials + z_idx * stride_lz + h_idx * stride_lh + m_idx * stride_lm
    o_ptr_base = Out_partials + z_idx * stride_oz + h_idx * stride_oh + m_idx * stride_om
    
    # 1. Find max LSE across splits
    lse_max = -float('inf')
    for i in range(SPLIT_K):
        l_val = tl.load(l_ptr_base + i * stride_ls)
        if l_val > lse_max:
            lse_max = l_val
            
    # 2. Accumulate weighted partial outputs
    acc = tl.zeros([HEAD_DIM], dtype=tl.float32)
    total_w = 0.0
    offs_d = tl.arange(0, HEAD_DIM)
    
    for i in range(SPLIT_K):
        l_val = tl.load(l_ptr_base + i * stride_ls)
        w = tl.exp(l_val - lse_max)
        total_w += w
        
        o_ptr = o_ptr_base + i * stride_os + offs_d * stride_od
        o_val = tl.load(o_ptr).to(tl.float32)
        acc += o_val * w
        
    final = acc / total_w
    
    # Store final result
    out_ptr = Out_final + z_idx * stride_foz + h_idx * stride_foh + m_idx * stride_fom + offs_d * stride_fod
    tl.store(out_ptr, final.to(tl.float16))

def decoding_attn(Q: torch.Tensor, K: torch.Tensor, V: torch.Tensor) -> torch.Tensor:
    Z, H, M, Dq = Q.shape
    _, _, N, Dv = V.shape
    
    # Determine Split-K factor based on occupancy
    num_sms = 58  # L4 GPU
    target_occupancy = num_sms * 2
    base_blocks = Z * H * M
    
    split_k = 1
    if base_blocks < target_occupancy:
        split_k = target_occupancy // base_blocks
        # Limit splits based on N (min block size 256)
        max_splits = max(1, N // 256)
        split_k = min(split_k, max_splits)
        # Limit max splits
        split_k = min(split_k, 64)
        split_k = max(split_k, 1)
    
    chunk_size = (N + split_k - 1) // split_k
    
    # Allocate intermediate buffers (F32 for precision)
    L_part = torch.empty((Z, H, M, split_k), dtype=torch.float32, device=Q.device)
    O_part = torch.empty((Z, H, M, split_k, Dq), dtype=torch.float32, device=Q.device)
    
    sm_scale = 1.0 / math.sqrt(Dq)
    
    # Launch Split-K Kernel
    grid = (Z * H * M * split_k,)
    _decoding_split_kernel[grid](
        Q, K, V, sm_scale,
        L_part, O_part,
        Q.stride(0), Q.stride(1), Q.stride(2), Q.stride(3),
        K.stride(0), K.stride(1), K.stride(2), K.stride(3),
        V.stride(0), V.stride(1), V.stride(2), V.stride(3),
        L_part.stride(0), L_part.stride(1), L_part.stride(2), L_part.stride(3),
        O_part.stride(0), O_part.stride(1), O_part.stride(2), O_part.stride(3), O_part.stride(4),
        Z, H, M, N,
        split_k,
        HEAD_DIM=Dq,
        chunk_size=chunk_size
    )
    
    # Allocate Final Output
    Out = torch.empty((Z, H, M, Dq), dtype=torch.float16, device=Q.device)
    
    # Launch Reduction Kernel
    grid_red = (Z * H * M,)
    _decoding_reduce_kernel[grid_red](
        O_part, L_part, Out,
        O_part.stride(0), O_part.stride(1), O_part.stride(2), O_part.stride(3), O_part.stride(4),
        L_part.stride(0), L_part.stride(1), L_part.stride(2), L_part.stride(3),
        Out.stride(0), Out.stride(1), Out.stride(2), Out.stride(3),
        Z, H, M,
        HEAD_DIM=Dq,
        SPLIT_K=split_k
    )
    
    return Out
"""
        return {"code": code}