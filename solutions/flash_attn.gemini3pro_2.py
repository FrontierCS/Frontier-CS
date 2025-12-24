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

@triton.jit
def _flash_attn_fwd_kernel(
    Q, K, V, sm_scale,
    Out,
    stride_qz, stride_qh, stride_qm, stride_qk,
    stride_kz, stride_kh, stride_kn, stride_kk,
    stride_vz, stride_vh, stride_vn, stride_vk,
    stride_oz, stride_oh, stride_om, stride_on,
    Z, H, M, N,
    BLOCK_M: tl.constexpr, BLOCK_N: tl.constexpr,
    D_Q: tl.constexpr, D_V: tl.constexpr,
    BLOCK_D_Q: tl.constexpr, BLOCK_D_V: tl.constexpr,
    IS_CAUSAL: tl.constexpr
):
    # Program IDs
    start_m = tl.program_id(0)
    off_h = tl.program_id(1)
    off_z = tl.program_id(2)

    # Tensor pointers calculation
    q_offset = off_z * stride_qz + off_h * stride_qh
    k_offset = off_z * stride_kz + off_h * stride_kh
    v_offset = off_z * stride_vz + off_h * stride_vh
    o_offset = off_z * stride_oz + off_h * stride_oh

    # Block offsets
    offs_m = start_m * BLOCK_M + tl.arange(0, BLOCK_M)
    offs_k = tl.arange(0, BLOCK_D_Q)
    offs_v = tl.arange(0, BLOCK_D_V)
    
    # Q Pointers
    q_ptrs = Q + q_offset + (offs_m[:, None] * stride_qm + offs_k[None, :] * stride_qk)
    
    # Load Q
    # Apply masking for sequence length M and dimension D_Q
    q = tl.load(q_ptrs, mask=(offs_m[:, None] < M) & (offs_k[None, :] < D_Q), other=0.0)

    # Initialize accumulators
    m_i = tl.zeros([BLOCK_M], dtype=tl.float32) - float("inf")
    l_i = tl.zeros([BLOCK_M], dtype=tl.float32)
    acc = tl.zeros([BLOCK_M, BLOCK_D_V], dtype=tl.float32)

    qk_scale = sm_scale

    # Loop bounds for causal or non-causal
    lo = 0
    hi = N
    if IS_CAUSAL:
        hi = (start_m + 1) * BLOCK_M
        if hi > N:
            hi = N

    # Helper pointers
    k_base = K + k_offset
    v_base = V + v_offset
    offs_n_base = tl.arange(0, BLOCK_N)

    # Inner loop over K, V blocks
    for start_n in range(lo, hi, BLOCK_N):
        cols_n = start_n + offs_n_base
        
        # Load K (BLOCK_D_Q, BLOCK_N) -- Transposed for dot(Q, K)
        k_ptrs = k_base + (offs_k[:, None] * stride_kk + cols_n[None, :] * stride_kn)
        k = tl.load(k_ptrs, mask=(cols_n[None, :] < N) & (offs_k[:, None] < D_Q), other=0.0)

        # Load V (BLOCK_N, BLOCK_D_V)
        v_ptrs = v_base + (cols_n[:, None] * stride_vn + offs_v[None, :] * stride_vk)
        v = tl.load(v_ptrs, mask=(cols_n[:, None] < N) & (offs_v[None, :] < D_V), other=0.0)

        # Compute Attention Score: QK = Q @ K.T
        qk = tl.dot(q, k)
        qk *= qk_scale

        # Apply Causal Mask
        if IS_CAUSAL:
            # Mask if the current block overlaps with or exceeds the diagonal
            if start_n + BLOCK_N > start_m * BLOCK_M:
                 mask = offs_m[:, None] >= cols_n[None, :]
                 qk = tl.where(mask, qk, float("-inf"))
        
        # Online Softmax Update
        m_i_new = tl.max(qk, 1)
        alpha = tl.exp(m_i - m_i_new)
        p = tl.exp(qk - m_i_new[:, None])
        
        # Accumulate Output
        acc = acc * alpha[:, None] + tl.dot(p, v)
        l_i = l_i * alpha + tl.sum(p, 1)
        m_i = m_i_new

    # Finalize Output
    acc = acc / l_i[:, None]
    
    # Store Output
    o_ptrs = Out + o_offset + (offs_m[:, None] * stride_om + offs_v[None, :] * stride_on)
    tl.store(o_ptrs, acc.to(tl.float16), mask=(offs_m[:, None] < M) & (offs_v[None, :] < D_V))

def flash_attn(Q, K, V, causal=True):
    Z, H, M, Dq = Q.shape
    _, _, N, Dv = V.shape
    
    # Allocate Output
    Out = torch.empty((Z, H, M, Dv), device=Q.device, dtype=Q.dtype)
    
    # Scaling factor
    sm_scale = 1.0 / math.sqrt(Dq)
    
    # Tuning configurations for L4
    BLOCK_M = 128
    BLOCK_N = 64
    BLOCK_D_Q = triton.next_power_of_2(Dq)
    BLOCK_D_V = triton.next_power_of_2(Dv)
    
    # Adjust block size for larger head dimensions to manage shared memory/register pressure
    if Dq > 64:
        BLOCK_M = 64
        
    num_warps = 4
    num_stages = 4
    
    # Grid: (M blocks, Heads, Batch)
    grid = (triton.cdiv(M, BLOCK_M), H, Z)
    
    _flash_attn_fwd_kernel[grid](
        Q, K, V, sm_scale,
        Out,
        Q.stride(0), Q.stride(1), Q.stride(2), Q.stride(3),
        K.stride(0), K.stride(1), K.stride(2), K.stride(3),
        V.stride(0), V.stride(1), V.stride(2), V.stride(3),
        Out.stride(0), Out.stride(1), Out.stride(2), Out.stride(3),
        Z, H, M, N,
        BLOCK_M=BLOCK_M, BLOCK_N=BLOCK_N,
        D_Q=Dq, D_V=Dv,
        BLOCK_D_Q=BLOCK_D_Q, BLOCK_D_V=BLOCK_D_V,
        IS_CAUSAL=causal,
        num_warps=num_warps,
        num_stages=num_stages
    )
    return Out
"""
        return {"code": code}
