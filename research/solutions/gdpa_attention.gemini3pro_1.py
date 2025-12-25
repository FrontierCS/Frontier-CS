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
def _gdpa_attn_kernel(
    Q, K, V, GQ, GK, Out,
    stride_qz, stride_qh, stride_qm, stride_qk,
    stride_kz, stride_kh, stride_kn, stride_kk,
    stride_vz, stride_vh, stride_vn, stride_vk,
    stride_oz, stride_oh, stride_om, stride_on,
    Z, H, M, N, D,
    sm_scale,
    BLOCK_M: tl.constexpr, 
    BLOCK_N: tl.constexpr, 
    BLOCK_D: tl.constexpr
):
    # Grid identification
    pid_m = tl.program_id(0)
    pid_hz = tl.program_id(1)
    
    off_h = pid_hz % H
    off_z = pid_hz // H
    
    # Tensor base pointers for the current head
    q_base = Q + off_z * stride_qz + off_h * stride_qh
    gq_base = GQ + off_z * stride_qz + off_h * stride_qh
    k_base = K + off_z * stride_kz + off_h * stride_kh
    gk_base = GK + off_z * stride_kz + off_h * stride_kh
    v_base = V + off_z * stride_vz + off_h * stride_vh
    out_base = Out + off_z * stride_oz + off_h * stride_oh
    
    # Block offsets
    offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
    offs_n = tl.arange(0, BLOCK_N)
    offs_d = tl.arange(0, BLOCK_D)
    
    # Bounds checking masks
    mask_m = offs_m < M
    mask_d = offs_d < D
    
    # Load Q block and GQ block
    # Q shape: (M, D), Block: (BLOCK_M, BLOCK_D)
    q_ptrs = q_base + offs_m[:, None] * stride_qm + offs_d[None, :] * stride_qk
    gq_ptrs = gq_base + offs_m[:, None] * stride_qm + offs_d[None, :] * stride_qk
    
    q = tl.load(q_ptrs, mask=(mask_m[:, None] & mask_d[None, :]), other=0.0)
    gq = tl.load(gq_ptrs, mask=(mask_m[:, None] & mask_d[None, :]), other=0.0)
    
    # Apply gating to Q: Q_g = Q * sigmoid(GQ)
    q = q * tl.sigmoid(gq)
    
    # Scale Q for scaled dot product
    q = (q * sm_scale).to(tl.float16)
    
    # Initialize running statistics for softmax
    m_i = tl.zeros([BLOCK_M], dtype=tl.float32) - float("inf")
    l_i = tl.zeros([BLOCK_M], dtype=tl.float32)
    acc = tl.zeros([BLOCK_M, BLOCK_D], dtype=tl.float32)
    
    # Loop over K, V blocks
    for start_n in range(0, N, BLOCK_N):
        offs_n_curr = start_n + offs_n
        mask_n = offs_n_curr < N
        
        # Load K and GK
        # We load K transposed as (BLOCK_D, BLOCK_N) to optimize dot product Q(M,D) @ K(D,N)
        # K stored as (N, D), so we swap indices in pointer arithmetic
        k_ptrs = k_base + offs_d[:, None] * stride_kk + offs_n_curr[None, :] * stride_kn
        gk_ptrs = gk_base + offs_d[:, None] * stride_kk + offs_n_curr[None, :] * stride_kn
        
        k = tl.load(k_ptrs, mask=(mask_d[:, None] & mask_n[None, :]), other=0.0)
        gk = tl.load(gk_ptrs, mask=(mask_d[:, None] & mask_n[None, :]), other=0.0)
        
        # Apply gating to K: K_g = K * sigmoid(GK)
        k = k * tl.sigmoid(gk)
        
        # Compute attention scores: S = Q_g @ K_g^T
        qk = tl.dot(q, k)
        
        # Mask out padded columns if N is not a multiple of BLOCK_N
        if N % BLOCK_N != 0:
            qk = tl.where(mask_n[None, :], qk, float("-inf"))
            
        # Online Softmax update
        m_curr = tl.max(qk, 1)
        m_new = tl.maximum(m_i, m_curr)
        
        alpha = tl.exp(m_i - m_new)
        p = tl.exp(qk - m_new[:, None])
        
        l_i = l_i * alpha + tl.sum(p, 1)
        m_i = m_new
        
        # Rescale accumulator
        acc = acc * alpha[:, None]
        
        # Load V block
        # V shape (N, D), Block (BLOCK_N, BLOCK_D)
        v_ptrs = v_base + offs_n_curr[:, None] * stride_vn + offs_d[None, :] * stride_vk
        v = tl.load(v_ptrs, mask=(mask_n[:, None] & mask_d[None, :]), other=0.0)
        
        # Accumulate weighted V: acc += P @ V
        acc += tl.dot(p.to(tl.float16), v)
        
    # Finalize output
    # O = acc / l_i
    acc = acc / l_i[:, None]
    
    # Store result
    out_ptrs = out_base + offs_m[:, None] * stride_om + offs_d[None, :] * stride_on
    tl.store(out_ptrs, acc.to(tl.float16), mask=(mask_m[:, None] & mask_d[None, :]))

def gdpa_attn(Q, K, V, GQ, GK):
    # Dimensions
    Z, H, M, D = Q.shape
    _, _, N, _ = K.shape
    
    # Kernel configuration
    # L4 GPU optimization: 128x64 blocks typically perform well
    BLOCK_M = 128
    BLOCK_N = 64
    BLOCK_D = triton.next_power_of_2(D)
    num_warps = 4
    num_stages = 2
    
    # Scale factor
    sm_scale = 1.0 / (D ** 0.5)
    
    # Output tensor
    Out = torch.empty((Z, H, M, D), dtype=Q.dtype, device=Q.device)
    
    # Grid
    grid = (triton.cdiv(M, BLOCK_M), Z * H)
    
    # Launch kernel
    _gdpa_attn_kernel[grid](
        Q, K, V, GQ, GK, Out,
        Q.stride(0), Q.stride(1), Q.stride(2), Q.stride(3),
        K.stride(0), K.stride(1), K.stride(2), K.stride(3),
        V.stride(0), V.stride(1), V.stride(2), V.stride(3),
        Out.stride(0), Out.stride(1), Out.stride(2), Out.stride(3),
        Z, H, M, N, D,
        sm_scale,
        BLOCK_M=BLOCK_M, BLOCK_N=BLOCK_N, BLOCK_D=BLOCK_D,
        num_warps=num_warps, num_stages=num_stages
    )
    
    return Out
"""
        return {"code": code}
