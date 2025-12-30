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
def _flash_attn_fwd_kernel(
    Q, K, V, sm_scale,
    Out,
    stride_qz, stride_qh, stride_qm, stride_qk,
    stride_kz, stride_kh, stride_kn, stride_kk,
    stride_vz, stride_vh, stride_vn, stride_vk,
    stride_oz, stride_oh, stride_om, stride_on,
    Z, H, N_CTX,
    BLOCK_M: tl.constexpr, BLOCK_N: tl.constexpr, BLOCK_DMODEL: tl.constexpr,
    IS_CAUSAL: tl.constexpr
):
    start_m = tl.program_id(0)
    off_hz = tl.program_id(1)
    
    off_z = off_hz // H
    off_h = off_hz % H
    
    # Offsets for pointers
    q_offset = off_z * stride_qz + off_h * stride_qh
    k_offset = off_z * stride_kz + off_h * stride_kh
    v_offset = off_z * stride_vz + off_h * stride_vh
    o_offset = off_z * stride_oz + off_h * stride_oh

    # Block pointers
    Q_ptr = Q + q_offset
    K_ptr = K + k_offset
    V_ptr = V + v_offset
    O_ptr = Out + o_offset

    # Offsets for dimensions
    offs_m = start_m * BLOCK_M + tl.arange(0, BLOCK_M)
    offs_n_base = tl.arange(0, BLOCK_N)
    offs_k = tl.arange(0, BLOCK_DMODEL)

    # Q Pointers
    Q_ptrs = Q_ptr + (offs_m[:, None] * stride_qm + offs_k[None, :] * stride_qk)
    O_ptrs = O_ptr + (offs_m[:, None] * stride_om + offs_k[None, :] * stride_on)

    # Load Q
    # If M is not multiple of BLOCK_M, mask load
    q = tl.load(Q_ptrs, mask=offs_m[:, None] < N_CTX, other=0.0)

    # Accumulators
    m_i = tl.zeros([BLOCK_M], dtype=tl.float32) - float("inf")
    l_i = tl.zeros([BLOCK_M], dtype=tl.float32)
    acc = tl.zeros([BLOCK_M, BLOCK_DMODEL], dtype=tl.float32)

    qk_scale = sm_scale

    # Loop bounds
    # Process blocks of K, V
    hi = N_CTX
    if IS_CAUSAL:
        hi = (start_m + 1) * BLOCK_M
        if hi > N_CTX:
            hi = N_CTX

    for start_n in range(0, hi, BLOCK_N):
        offs_n = start_n + offs_n_base
        
        # Load K (transposed for dot: D x BN)
        # offs_k (D, 1) * stride_kk + offs_n (1, BN) * stride_kn
        K_ptrs = K_ptr + (offs_k[:, None] * stride_kk + offs_n[None, :] * stride_kn)
        k = tl.load(K_ptrs, mask=offs_n[None, :] < N_CTX, other=0.0)
        
        # Load V (BN x D)
        # offs_n (BN, 1) * stride_vn + offs_k (1, D) * stride_vk
        V_ptrs = V_ptr + (offs_n[:, None] * stride_vn + offs_k[None, :] * stride_vk)
        v = tl.load(V_ptrs, mask=offs_n[:, None] < N_CTX, other=0.0)

        # Compute qk
        qk = tl.dot(q, k)
        qk *= qk_scale
        
        # Masking
        mask_n = offs_n[None, :] < N_CTX
        if IS_CAUSAL:
            mask_c = offs_m[:, None] >= offs_n[None, :]
            qk = tl.where(mask_c & mask_n, qk, float("-inf"))
        else:
            qk = tl.where(mask_n, qk, float("-inf"))

        # Online Softmax
        m_i_new = tl.max(qk, 1)
        m_i_new = tl.maximum(m_i, m_i_new)
        
        alpha = tl.exp(m_i - m_i_new)
        p = tl.exp(qk - m_i_new[:, None])
        
        l_i = l_i * alpha + tl.sum(p, 1)
        
        # Update accumulator
        acc = acc * alpha[:, None]
        # p is fp32, v is fp16. cast p to fp16 for tensor core dot
        acc += tl.dot(p.to(tl.float16), v)
        
        m_i = m_i_new

    # Finalize
    acc = acc / l_i[:, None]
    
    # Store
    tl.store(O_ptrs, acc.to(tl.float16), mask=offs_m[:, None] < N_CTX)

def flash_attn(Q: torch.Tensor, K: torch.Tensor, V: torch.Tensor, causal: bool = True) -> torch.Tensor:
    # Q: (Z, H, M, D)
    # K: (Z, H, N, D)
    # V: (Z, H, N, D)
    
    Z, H, M, D = Q.shape
    N = K.shape[2]
    
    # Allocate Output
    Out = torch.empty_like(Q)
    
    sm_scale = 1.0 / (D ** 0.5)
    
    # Tuning parameters
    BLOCK_M = 128
    BLOCK_N = 64
    BLOCK_DMODEL = D
    
    grid = (triton.cdiv(M, BLOCK_M), Z * H)
    
    _flash_attn_fwd_kernel[grid](
        Q, K, V, sm_scale,
        Out,
        Q.stride(0), Q.stride(1), Q.stride(2), Q.stride(3),
        K.stride(0), K.stride(1), K.stride(2), K.stride(3),
        V.stride(0), V.stride(1), V.stride(2), V.stride(3),
        Out.stride(0), Out.stride(1), Out.stride(2), Out.stride(3),
        Z, H, M,
        BLOCK_M=BLOCK_M, BLOCK_N=BLOCK_N, BLOCK_DMODEL=BLOCK_DMODEL,
        IS_CAUSAL=causal,
        num_warps=4,
        num_stages=4
    )
    
    return Out
"""
        return {"code": code}