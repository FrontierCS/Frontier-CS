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
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 64}, num_warps=4, num_stages=4),
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 64}, num_warps=8, num_stages=3),
        triton.Config({'BLOCK_M': 64, 'BLOCK_N': 64}, num_warps=4, num_stages=4),
    ],
    key=['N_CTX', 'BLOCK_DMODEL'],
)
@triton.jit
def _flash_attn_fwd_kernel(
    Q, K, V, sm_scale,
    Out,
    stride_qz, stride_qh, stride_qm, stride_qk,
    stride_kz, stride_kh, stride_kn, stride_kk,
    stride_vz, stride_vh, stride_vn, stride_vk,
    stride_oz, stride_oh, stride_om, stride_on,
    Z, H, N_CTX,
    BLOCK_M: tl.constexpr, BLOCK_N: tl.constexpr,
    BLOCK_DMODEL: tl.constexpr,
    CAUSAL: tl.constexpr
):
    start_m = tl.program_id(0)
    off_hz = tl.program_id(1)
    
    off_z = off_hz // H
    off_h = off_hz % H
    
    q_offset = off_z * stride_qz + off_h * stride_qh
    k_offset = off_z * stride_kz + off_h * stride_kh
    v_offset = off_z * stride_vz + off_h * stride_vh
    o_offset = off_z * stride_oz + off_h * stride_oh

    # Q Block: (BLOCK_M, BLOCK_DMODEL)
    Q_ptr = tl.make_block_ptr(
        base=Q + q_offset,
        shape=(N_CTX, BLOCK_DMODEL),
        strides=(stride_qm, stride_qk),
        offsets=(start_m * BLOCK_M, 0),
        block_shape=(BLOCK_M, BLOCK_DMODEL),
        order=(1, 0)
    )
    
    # K Block: Transposed to (BLOCK_DMODEL, BLOCK_N) for dot product
    # Logic: K is (N, D), we load (D, N) chunks transposed
    K_ptr = tl.make_block_ptr(
        base=K + k_offset,
        shape=(BLOCK_DMODEL, N_CTX),
        strides=(stride_kk, stride_kn),
        offsets=(0, 0),
        block_shape=(BLOCK_DMODEL, BLOCK_N),
        order=(0, 1)
    )
    
    # V Block: (BLOCK_N, BLOCK_DMODEL)
    V_ptr = tl.make_block_ptr(
        base=V + v_offset,
        shape=(N_CTX, BLOCK_DMODEL),
        strides=(stride_vn, stride_vk),
        offsets=(0, 0),
        block_shape=(BLOCK_N, BLOCK_DMODEL),
        order=(1, 0)
    )

    # Accumulators
    m_i = tl.zeros([BLOCK_M], dtype=tl.float32) - float("inf")
    l_i = tl.zeros([BLOCK_M], dtype=tl.float32) + 1.0
    acc = tl.zeros([BLOCK_M, BLOCK_DMODEL], dtype=tl.float32)
    
    # Load Q
    q = tl.load(Q_ptr)
    
    # Loop bounds
    lo = 0
    hi = (start_m + 1) * BLOCK_M if CAUSAL else N_CTX
    if CAUSAL and hi > N_CTX:
        hi = N_CTX

    for start_n in range(lo, hi, BLOCK_N):
        start_n = tl.multiple_of(start_n, BLOCK_N)
        
        # Load K
        k = tl.load(K_ptr)
        
        # Compute QK^T
        qk = tl.dot(q, k)
        
        # Causal Masking
        if CAUSAL:
            # Check if block overlaps diagonal
            if start_n + BLOCK_N > start_m * BLOCK_M:
                offs_m = start_m * BLOCK_M + tl.arange(0, BLOCK_M)
                offs_n = start_n + tl.arange(0, BLOCK_N)
                mask = offs_m[:, None] >= offs_n[None, :]
                qk = tl.where(mask, qk, float("-inf"))
        
        qk *= sm_scale
        
        # Online Softmax
        m_ij = tl.max(qk, 1)
        m_new = tl.maximum(m_i, m_ij)
        alpha = tl.exp(m_i - m_new)
        p = tl.exp(qk - m_new[:, None])
        
        l_new = alpha * l_i + tl.sum(p, 1)
        
        # Update Accumulator
        v = tl.load(V_ptr)
        acc = acc * alpha[:, None]
        p = p.to(tl.float16)
        acc += tl.dot(p, v)
        
        # Update stats
        l_i = l_new
        m_i = m_new
        
        # Advance pointers
        K_ptr = tl.advance(K_ptr, (0, BLOCK_N))
        V_ptr = tl.advance(V_ptr, (BLOCK_N, 0))

    # Epilogue
    acc = acc / l_i[:, None]
    acc = acc.to(tl.float16)
    
    O_ptr = tl.make_block_ptr(
        base=Out + o_offset,
        shape=(N_CTX, BLOCK_DMODEL),
        strides=(stride_om, stride_on),
        offsets=(start_m * BLOCK_M, 0),
        block_shape=(BLOCK_M, BLOCK_DMODEL),
        order=(1, 0)
    )
    tl.store(O_ptr, acc)

def flash_attn(Q, K, V, causal=True):
    Z, H, N_CTX, D_HEAD = Q.shape
    
    # Ensure inputs are contiguous
    if not Q.is_contiguous(): Q = Q.contiguous()
    if not K.is_contiguous(): K = K.contiguous()
    if not V.is_contiguous(): V = V.contiguous()
    
    Out = torch.empty_like(Q)
    sm_scale = 1.0 / math.sqrt(D_HEAD)
    
    def grid(META):
        return ((N_CTX + META['BLOCK_M'] - 1) // META['BLOCK_M'], Z * H)
    
    _flash_attn_fwd_kernel[grid](
        Q, K, V, sm_scale,
        Out,
        Q.stride(0), Q.stride(1), Q.stride(2), Q.stride(3),
        K.stride(0), K.stride(1), K.stride(2), K.stride(3),
        V.stride(0), V.stride(1), V.stride(2), V.stride(3),
        Out.stride(0), Out.stride(1), Out.stride(2), Out.stride(3),
        Z, H, N_CTX,
        BLOCK_DMODEL=D_HEAD,
        CAUSAL=causal
    )
    
    return Out
"""
        return {"code": code}