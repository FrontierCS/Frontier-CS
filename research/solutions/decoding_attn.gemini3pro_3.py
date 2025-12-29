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
def _fwd_kernel_split(
    Q, K, V, sm_scale,
    Mid_O, Mid_m, Mid_d,
    stride_Q_z, stride_Q_h, stride_Q_d,
    stride_K_z, stride_K_h, stride_K_n, stride_K_d,
    stride_V_z, stride_V_h, stride_V_n, stride_V_d,
    stride_Mid_O_z, stride_Mid_O_h, stride_Mid_O_s, stride_Mid_O_d,
    stride_Mid_m_z, stride_Mid_m_h, stride_Mid_m_s,
    stride_Mid_d_z, stride_Mid_d_h, stride_Mid_d_s,
    Z, H, N, 
    HEAD_DIM_Q: tl.constexpr, HEAD_DIM_V: tl.constexpr, 
    BLOCK_N: tl.constexpr
):
    split_idx = tl.program_id(0)
    zh_idx = tl.program_id(1)
    z_idx = zh_idx // H
    h_idx = zh_idx % H
    
    # Load Q (Z, H, Dq)
    q_ptr = Q + z_idx * stride_Q_z + h_idx * stride_Q_h
    q_offs = tl.arange(0, HEAD_DIM_Q)
    q = tl.load(q_ptr + q_offs * stride_Q_d)
    
    # Define K/V block
    start_n = split_idx * BLOCK_N
    offs_n = start_n + tl.arange(0, BLOCK_N)
    mask_n = offs_n < N
    
    # Load K (Z, H, N, Dq)
    k_base = K + z_idx * stride_K_z + h_idx * stride_K_h
    k_ptrs = k_base + (offs_n[:, None] * stride_K_n + q_offs[None, :] * stride_K_d)
    k = tl.load(k_ptrs, mask=mask_n[:, None], other=0.0)
    
    # Compute scores QK^T
    qk = tl.sum(q[None, :] * k, axis=1)
    qk *= sm_scale
    
    # Masking
    qk = tl.where(mask_n, qk, float("-inf"))
    
    # Local Softmax
    m_i = tl.max(qk, 0)
    p = tl.exp(qk - m_i)
    d_i = tl.sum(p, 0)
    
    # Load V (Z, H, N, Dv)
    v_base = V + z_idx * stride_V_z + h_idx * stride_V_h
    v_offs_d = tl.arange(0, HEAD_DIM_V)
    v_ptrs = v_base + (offs_n[:, None] * stride_V_n + v_offs_d[None, :] * stride_V_d)
    v = tl.load(v_ptrs, mask=mask_n[:, None], other=0.0)
    
    # Compute weighted sum
    o_i = tl.sum(p[:, None] * v, axis=0)
    
    # Write intermediate results
    mid_m_ptr = Mid_m + z_idx * stride_Mid_m_z + h_idx * stride_Mid_m_h + split_idx * stride_Mid_m_s
    tl.store(mid_m_ptr, m_i)
    
    mid_d_ptr = Mid_d + z_idx * stride_Mid_d_z + h_idx * stride_Mid_d_h + split_idx * stride_Mid_d_s
    tl.store(mid_d_ptr, d_i)
    
    mid_o_ptr = Mid_O + z_idx * stride_Mid_O_z + h_idx * stride_Mid_O_h + split_idx * stride_Mid_O_s + v_offs_d * stride_Mid_O_d
    tl.store(mid_o_ptr, o_i)

@triton.jit
def _reduce_kernel(
    Mid_O, Mid_m, Mid_d, Out,
    stride_Mid_O_z, stride_Mid_O_h, stride_Mid_O_s, stride_Mid_O_d,
    stride_Mid_m_z, stride_Mid_m_h, stride_Mid_m_s,
    stride_Mid_d_z, stride_Mid_d_h, stride_Mid_d_s,
    stride_Out_z, stride_Out_h, stride_Out_d,
    Z, H, NUM_SPLITS, 
    HEAD_DIM_V: tl.constexpr
):
    zh_idx = tl.program_id(0)
    z_idx = zh_idx // H
    h_idx = zh_idx % H
    
    m_base = Mid_m + z_idx * stride_Mid_m_z + h_idx * stride_Mid_m_h
    d_base = Mid_d + z_idx * stride_Mid_d_z + h_idx * stride_Mid_d_h
    o_base = Mid_O + z_idx * stride_Mid_O_z + h_idx * stride_Mid_O_h
    
    # Global Max
    m_global = float("-inf")
    for s in range(NUM_SPLITS):
        m_s = tl.load(m_base + s * stride_Mid_m_s)
        if m_s > m_global:
            m_global = m_s
            
    # Aggregation
    d_global = 0.0
    acc_o = tl.zeros([HEAD_DIM_V], dtype=tl.float32)
    offs_d = tl.arange(0, HEAD_DIM_V)
    
    for s in range(NUM_SPLITS):
        m_s = tl.load(m_base + s * stride_Mid_m_s)
        d_s = tl.load(d_base + s * stride_Mid_d_s)
        
        w = tl.exp(m_s - m_global)
        d_global += d_s * w
        
        o_ptr = o_base + s * stride_Mid_O_s + offs_d * stride_Mid_O_d
        o_s = tl.load(o_ptr)
        acc_o += o_s * w
        
    out = acc_o / d_global
    
    out_ptr = Out + z_idx * stride_Out_z + h_idx * stride_Out_h + offs_d * stride_Out_d
    tl.store(out_ptr, out.to(tl.float16))

def decoding_attn(Q, K, V):
    # Q: (Z, H, M, Dq)
    # K: (Z, H, N, Dq)
    # V: (Z, H, N, Dv)
    Z, H, M, Dq = Q.shape
    _, _, N, _ = K.shape
    _, _, _, Dv = V.shape
    
    # Split-K configuration for high occupancy on decoding (M=1 usually)
    BLOCK_N = 128
    num_splits = (N + BLOCK_N - 1) // BLOCK_N
    
    # Intermediate buffers in float32 for stability
    mid_m = torch.empty((Z, H, num_splits), dtype=torch.float32, device=Q.device)
    mid_d = torch.empty((Z, H, num_splits), dtype=torch.float32, device=Q.device)
    mid_o = torch.empty((Z, H, num_splits, Dv), dtype=torch.float32, device=Q.device)
    
    output = torch.empty((Z, H, M, Dv), dtype=torch.float16, device=Q.device)
    sm_scale = 1.0 / (Dq ** 0.5)
    
    # Loop over M (query tokens). Usually M=1 for decoding.
    for m in range(M):
        q_slice = Q[:, :, m, :] # (Z, H, Dq)
        out_slice = output[:, :, m, :] # (Z, H, Dv)
        
        # Phase 1: Local Attention
        grid_fwd = (num_splits, Z * H)
        _fwd_kernel_split[grid_fwd](
            q_slice, K, V, sm_scale,
            mid_o, mid_m, mid_d,
            q_slice.stride(0), q_slice.stride(1), q_slice.stride(2),
            K.stride(0), K.stride(1), K.stride(2), K.stride(3),
            V.stride(0), V.stride(1), V.stride(2), V.stride(3),
            mid_o.stride(0), mid_o.stride(1), mid_o.stride(2), mid_o.stride(3),
            mid_m.stride(0), mid_m.stride(1), mid_m.stride(2),
            mid_d.stride(0), mid_d.stride(1), mid_d.stride(2),
            Z, H, N,
            HEAD_DIM_Q=Dq, HEAD_DIM_V=Dv,
            BLOCK_N=BLOCK_N
        )
        
        # Phase 2: Reduction
        grid_reduce = (Z * H, )
        _reduce_kernel[grid_reduce](
            mid_o, mid_m, mid_d, out_slice,
            mid_o.stride(0), mid_o.stride(1), mid_o.stride(2), mid_o.stride(3),
            mid_m.stride(0), mid_m.stride(1), mid_m.stride(2),
            mid_d.stride(0), mid_d.stride(1), mid_d.stride(2),
            out_slice.stride(0), out_slice.stride(1), out_slice.stride(2),
            Z, H, num_splits, 
            HEAD_DIM_V=Dv
        )
        
    return output
"""
        return {"code": code}