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
    sm_scale,
    stride_qz, stride_qh, stride_qm, stride_qk,
    stride_kz, stride_kh, stride_kn, stride_kk,
    stride_vz, stride_vh, stride_vn, stride_vk,
    stride_mo_z, stride_mo_h, stride_mo_m, stride_mo_s, stride_mo_d,
    stride_ml_z, stride_ml_h, stride_ml_m, stride_ml_s,
    Z, H, M, N_CTX,
    BLOCK_N: tl.constexpr,
    BLOCK_DMODEL: tl.constexpr,
    SPLIT_K: tl.constexpr
):
    pid_0 = tl.program_id(0) # split idx
    pid_1 = tl.program_id(1) # batch * head * m

    m_idx = pid_1 % M
    temp = pid_1 // M
    h_idx = temp % H
    z_idx = temp // H

    # Pointers
    q_ptr = Q + z_idx * stride_qz + h_idx * stride_qh + m_idx * stride_qm
    k_base = K + z_idx * stride_kz + h_idx * stride_kh
    v_base = V + z_idx * stride_vz + h_idx * stride_vh

    # Load Q: (1, D)
    offs_d = tl.arange(0, BLOCK_DMODEL)
    q = tl.load(q_ptr + offs_d * stride_qk)[None, :]

    # Split logic
    chunk_size = tl.cdiv(N_CTX, SPLIT_K)
    start_n = pid_0 * chunk_size
    end_n = tl.minimum(start_n + chunk_size, N_CTX)

    m_i = -float('inf')
    l_i = 0.0
    acc = tl.zeros([1, BLOCK_DMODEL], dtype=tl.float32)

    for offs_n_base in range(start_n, end_n, BLOCK_N):
        offs_n = offs_n_base + tl.arange(0, BLOCK_N)
        mask_n = offs_n < end_n
        
        # Load K: (BLOCK_N, D)
        k_ptr = k_base + (offs_n[:, None] * stride_kn + offs_d[None, :] * stride_kk)
        k = tl.load(k_ptr, mask=mask_n[:, None], other=0.0)
        
        # QK^T: (1, D) x (D, BLOCK_N) -> (1, BLOCK_N)
        qk = tl.dot(q, tl.trans(k))
        qk *= sm_scale
        qk = tl.where(mask_n[None, :], qk, -float('inf'))
        
        m_curr = tl.max(qk, 1) # (1,)
        m_new = tl.maximum(m_i, m_curr)
        
        alpha = tl.exp(m_i - m_new)
        beta = tl.exp(qk - m_new) # (1, BLOCK_N)
        
        l_i = l_i * alpha + tl.sum(beta, 1)
        
        # Load V: (BLOCK_N, D)
        v_ptr = v_base + (offs_n[:, None] * stride_vn + offs_d[None, :] * stride_vk)
        v = tl.load(v_ptr, mask=mask_n[:, None], other=0.0)
        
        # Acc: (1, BLOCK_N) x (BLOCK_N, D) -> (1, D)
        p = beta.to(tl.float16)
        wv = tl.dot(p, v)
        
        acc = acc * alpha + wv
        m_i = m_new

    # Store
    off_zhm = z_idx * stride_mo_z + h_idx * stride_mo_h + m_idx * stride_mo_m
    off_s = pid_0 * stride_mo_s
    mid_o_ptr = Mid_O + off_zhm + off_s + offs_d * stride_mo_d
    
    off_zhm_l = z_idx * stride_ml_z + h_idx * stride_ml_h + m_idx * stride_ml_m
    off_s_l = pid_0 * stride_ml_s
    mid_l_ptr = Mid_L + off_zhm_l + off_s_l
    mid_m_ptr = Mid_M + off_zhm_l + off_s_l

    tl.store(mid_o_ptr, acc[0, :])
    tl.store(mid_l_ptr, l_i)
    tl.store(mid_m_ptr, m_i)

@triton.jit
def _reduce_kernel(
    Mid_O, Mid_L, Mid_M, O,
    stride_mo_z, stride_mo_h, stride_mo_m, stride_mo_s, stride_mo_d,
    stride_ml_z, stride_ml_h, stride_ml_m, stride_ml_s,
    stride_oz, stride_oh, stride_om, stride_od,
    Z, H, M,
    BLOCK_DMODEL: tl.constexpr,
    SPLIT_K: tl.constexpr
):
    pid = tl.program_id(0)
    m_idx = pid % M
    temp = pid // M
    h_idx = temp % H
    z_idx = temp // H

    offs_d = tl.arange(0, BLOCK_DMODEL)
    
    acc = tl.zeros([BLOCK_DMODEL], dtype=tl.float32)
    m_global = -float('inf')
    l_global = 0.0

    off_zhm_l = z_idx * stride_ml_z + h_idx * stride_ml_h + m_idx * stride_ml_m
    off_zhm_o = z_idx * stride_mo_z + h_idx * stride_mo_h + m_idx * stride_mo_m

    for s in range(SPLIT_K):
        idx_l = off_zhm_l + s * stride_ml_s
        m_s = tl.load(Mid_M + idx_l)
        l_s = tl.load(Mid_L + idx_l)
        
        idx_o = off_zhm_o + s * stride_mo_s + offs_d * stride_mo_d
        o_s = tl.load(Mid_O + idx_o)

        m_new = tl.maximum(m_global, m_s)
        if m_new == -float('inf'):
            continue
            
        alpha = tl.exp(m_global - m_new)
        beta = tl.exp(m_s - m_new)
        
        l_global = l_global * alpha + l_s * beta
        acc = acc * alpha + o_s * beta
        m_global = m_new

    o_ptr = O + z_idx*stride_oz + h_idx*stride_oh + m_idx*stride_om + offs_d*stride_od
    tl.store(o_ptr, (acc / l_global).to(tl.float16))

def decoding_attn(Q, K, V):
    Z, H, M, D = Q.shape
    _, _, N, _ = K.shape
    
    # Heuristics
    BLOCK_N = 128
    # Target 256 programs to fill GPU
    total_programs = Z * H * M
    target_programs = 256 
    split_k = max(1, target_programs // total_programs)
    split_k = min(split_k, 64)
    split_k = min(split_k, max(1, N // BLOCK_N))

    # Buffers
    Mid_O = torch.empty((Z, H, M, split_k, D), dtype=torch.float32, device=Q.device)
    Mid_L = torch.empty((Z, H, M, split_k), dtype=torch.float32, device=Q.device)
    Mid_M = torch.empty((Z, H, M, split_k), dtype=torch.float32, device=Q.device)
    O = torch.empty((Z, H, M, D), dtype=Q.dtype, device=Q.device)
    
    sm_scale = 1.0 / (D ** 0.5)

    _fwd_kernel_stage1[(split_k, Z * H * M)](
        Q, K, V,
        Mid_O, Mid_L, Mid_M,
        sm_scale,
        Q.stride(0), Q.stride(1), Q.stride(2), Q.stride(3),
        K.stride(0), K.stride(1), K.stride(2), K.stride(3),
        V.stride(0), V.stride(1), V.stride(2), V.stride(3),
        Mid_O.stride(0), Mid_O.stride(1), Mid_O.stride(2), Mid_O.stride(3), Mid_O.stride(4),
        Mid_L.stride(0), Mid_L.stride(1), Mid_L.stride(2), Mid_L.stride(3),
        Z, H, M, N,
        BLOCK_N=BLOCK_N,
        BLOCK_DMODEL=D,
        SPLIT_K=split_k
    )

    _reduce_kernel[(Z * H * M,)](
        Mid_O, Mid_L, Mid_M, O,
        Mid_O.stride(0), Mid_O.stride(1), Mid_O.stride(2), Mid_O.stride(3), Mid_O.stride(4),
        Mid_L.stride(0), Mid_L.stride(1), Mid_L.stride(2), Mid_L.stride(3),
        O.stride(0), O.stride(1), O.stride(2), O.stride(3),
        Z, H, M,
        BLOCK_DMODEL=D,
        SPLIT_K=split_k
    )
    
    return O
"""
        return {"code": code}
