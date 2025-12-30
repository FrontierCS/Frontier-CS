import torch

class Solution:
    def solve(self, spec_path: str = None) -> dict:
        code = r"""
import torch
import triton
import triton.language as tl

@triton.jit
def _flash_attn_fwd_kernel(
    Q, K, V, sm_scale,
    Out,
    stride_qz, stride_qh, stride_qm, stride_qk,
    stride_kz, stride_kh, stride_kn, stride_kk,
    stride_vz, stride_vh, stride_vn, stride_vk,
    stride_oz, stride_oh, stride_om, stride_on,
    Z, H, M_CTX, N_CTX,
    BLOCK_M: tl.constexpr, BLOCK_N: tl.constexpr, 
    BLOCK_DQ: tl.constexpr, BLOCK_DV: tl.constexpr,
    IS_CAUSAL: tl.constexpr
):
    start_m = tl.program_id(0)
    off_hz = tl.program_id(1)
    
    q_offset_z = off_hz // H
    q_offset_h = off_hz % H
    
    # Base pointers for the specific batch/head
    q_ptr = Q + (q_offset_z * stride_qz + q_offset_h * stride_qh)
    k_ptr = K + (q_offset_z * stride_kz + q_offset_h * stride_kh)
    v_ptr = V + (q_offset_z * stride_vz + q_offset_h * stride_vh)
    o_ptr = Out + (q_offset_z * stride_oz + q_offset_h * stride_oh)

    # Offsets
    offs_m = start_m * BLOCK_M + tl.arange(0, BLOCK_M)
    offs_n = tl.arange(0, BLOCK_N)
    offs_d_q = tl.arange(0, BLOCK_DQ)
    offs_d_v = tl.arange(0, BLOCK_DV)

    # Load Q: (BLOCK_M, DQ)
    # Memory layout: [M, D] based on strides
    q_ptrs = q_ptr + (offs_m[:, None] * stride_qm + offs_d_q[None, :] * stride_qk)
    q = tl.load(q_ptrs, mask=offs_m[:, None] < M_CTX, other=0.0)

    # Initialize stats and accumulator
    m_i = tl.zeros([BLOCK_M], dtype=tl.float32) - float("inf")
    l_i = tl.zeros([BLOCK_M], dtype=tl.float32)
    acc = tl.zeros([BLOCK_M, BLOCK_DV], dtype=tl.float32)

    qk_scale = sm_scale

    # Loop setup
    # If causal, we loop up to (start_m + 1) * BLOCK_M, clamped to N_CTX
    lo = 0
    hi = N_CTX
    if IS_CAUSAL:
        hi = (start_m + 1) * BLOCK_M
        if hi > N_CTX:
            hi = N_CTX

    # Pre-compute pointer bases for K and V
    # K is loaded transposed for dot: (DQ, BLOCK_N)
    # Stride math: offs_d_q * stride_kk (rows) + offs_n * stride_kn (cols)
    kt_base_ptr = k_ptr + offs_d_q[:, None] * stride_kk
    
    # V is loaded normally: (BLOCK_N, DV)
    # Stride math: offs_n * stride_vn (rows) + offs_d_v * stride_vk (cols)
    v_base_ptr = v_ptr + offs_d_v[None, :] * stride_vk

    for start_n in range(lo, hi, BLOCK_N):
        # Load K block
        kt_ptrs = kt_base_ptr + (start_n + offs_n[None, :]) * stride_kn
        k_mask = (start_n + offs_n[None, :]) < N_CTX
        k = tl.load(kt_ptrs, mask=k_mask, other=0.0)

        # QK = Q @ K^T
        qk = tl.dot(q, k)
        qk *= qk_scale

        # Causal Masking
        if IS_CAUSAL:
            # Mask where query index (m) < key index (n)
            # m range: offs_m
            # n range: start_n + offs_n
            mask = offs_m[:, None] >= (start_n + offs_n[None, :])
            qk = tl.where(mask, qk, float("-inf"))
        
        # Online Softmax
        m_i_new = tl.max(qk, 1)
        m_i_new = tl.maximum(m_i_new, m_i)
        
        p = tl.exp(qk - m_i_new[:, None])
        alpha = tl.exp(m_i - m_i_new)
        
        l_i = l_i * alpha + tl.sum(p, 1)
        
        # Update accumulator
        acc = acc * alpha[:, None]
        
        # Load V block
        v_ptrs = v_base_ptr + (start_n + offs_n[:, None]) * stride_vn
        v_mask = (start_n + offs_n[:, None]) < N_CTX
        v = tl.load(v_ptrs, mask=v_mask, other=0.0)
        
        # Accumulate weighted values
        p = p.to(tl.float16)
        acc += tl.dot(p, v)
        
        m_i = m_i_new
    
    # Final normalization
    acc = acc / l_i[:, None]
    
    # Store result
    o_ptrs = o_ptr + (offs_m[:, None] * stride_om + offs_d_v[None, :] * stride_on)
    tl.store(o_ptrs, acc.to(tl.float16), mask=offs_m[:, None] < M_CTX)

def flash_attn(Q: torch.Tensor, K: torch.Tensor, V: torch.Tensor, causal: bool = True) -> torch.Tensor:
    Z, H, M, Dq = Q.shape
    _, _, N, _ = K.shape
    Dv = V.shape[-1]
    
    O = torch.empty((Z, H, M, Dv), dtype=Q.dtype, device=Q.device)
    
    # Tuning for L4
    BLOCK_M = 128
    BLOCK_N = 64
    num_warps = 4
    num_stages = 3
    
    grid = (triton.cdiv(M, BLOCK_M), Z * H)
    sm_scale = 1.0 / (Dq ** 0.5)
    
    _flash_attn_fwd_kernel[grid](
        Q, K, V, sm_scale,
        O,
        Q.stride(0), Q.stride(1), Q.stride(2), Q.stride(3),
        K.stride(0), K.stride(1), K.stride(2), K.stride(3),
        V.stride(0), V.stride(1), V.stride(2), V.stride(3),
        O.stride(0), O.stride(1), O.stride(2), O.stride(3),
        Z, H, M, N,
        BLOCK_M=BLOCK_M, BLOCK_N=BLOCK_N, 
        BLOCK_DQ=Dq, BLOCK_DV=Dv,
        IS_CAUSAL=causal,
        num_warps=num_warps,
        num_stages=num_stages,
    )
    return O
"""
        return {"code": code}