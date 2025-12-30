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

    q_offset = off_z * stride_qz + off_h * stride_qh
    k_offset = off_z * stride_kz + off_h * stride_kh
    v_offset = off_z * stride_vz + off_h * stride_vh
    o_offset = off_z * stride_oz + off_h * stride_oh

    # Q block pointer
    # Memory layout: (M, D)
    Q_block_ptr = tl.make_block_ptr(
        base=Q + q_offset,
        shape=(N_CTX, BLOCK_DMODEL),
        strides=(stride_qm, stride_qk),
        offsets=(start_m * BLOCK_M, 0),
        block_shape=(BLOCK_M, BLOCK_DMODEL),
        order=(1, 0)
    )
    
    # K block pointer
    # Memory layout: (N, D). 
    # For dot(Q, K^T), we want K block to be (D, N) abstractly, 
    # but efficient dot usually prefers loading (N, D) or (D, N) depending on impl.
    # Triton's dot(a, b) expects a=(M, K), b=(K, N).
    # Here Q=(BLOCK_M, D). So we want K loaded as (D, BLOCK_N).
    # To load (D, BLOCK_N) from (N, D) memory, we treat dimension 0 as D (stride_kk)
    # and dimension 1 as N (stride_kn).
    K_block_ptr = tl.make_block_ptr(
        base=K + k_offset,
        shape=(BLOCK_DMODEL, N_CTX),
        strides=(stride_kk, stride_kn),
        offsets=(0, 0),
        block_shape=(BLOCK_DMODEL, BLOCK_N),
        order=(0, 1)
    )

    # V block pointer
    # Memory layout: (N, D)
    V_block_ptr = tl.make_block_ptr(
        base=V + v_offset,
        shape=(N_CTX, BLOCK_DMODEL),
        strides=(stride_vn, stride_vk),
        offsets=(0, 0),
        block_shape=(BLOCK_N, BLOCK_DMODEL),
        order=(1, 0)
    )

    # Initialize accumulators
    m_i = tl.zeros([BLOCK_M], dtype=tl.float32) - float("inf")
    l_i = tl.zeros([BLOCK_M], dtype=tl.float32)
    acc = tl.zeros([BLOCK_M, BLOCK_DMODEL], dtype=tl.float32)

    # Load Q
    q = tl.load(Q_block_ptr)

    # Loop range
    # If causal, we iterate up to the block that includes the diagonal.
    # The last relevant block of N is where (start_n+1)*BLOCK_N > start_m*BLOCK_M
    lo = 0
    hi = (start_m + 1) * BLOCK_M if IS_CAUSAL else N_CTX
    
    for start_n in range(lo, hi, BLOCK_N):
        # Load K, V
        k = tl.load(K_block_ptr)
        v = tl.load(V_block_ptr)
        
        # Compute attention scores
        # q: (BLOCK_M, D), k: (D, BLOCK_N) -> qk: (BLOCK_M, BLOCK_N)
        qk = tl.dot(q, k)
        
        if IS_CAUSAL:
            # Masking
            # If the current K block is strictly left of the diagonal, no mask needed.
            # Condition: Max col index < Min row index
            # start_n + BLOCK_N <= start_m * BLOCK_M
            if start_n + BLOCK_N <= start_m * BLOCK_M:
                pass
            else:
                offs_m = start_m * BLOCK_M + tl.arange(0, BLOCK_M)
                offs_n = start_n + tl.arange(0, BLOCK_N)
                mask = offs_m[:, None] >= offs_n[None, :]
                qk = tl.where(mask, qk, float("-inf"))
        
        qk *= sm_scale
        
        # Online softmax
        m_i_new = tl.max(qk, 1)
        m_i_new = tl.maximum(m_i, m_i_new)
        
        alpha = tl.exp(m_i - m_i_new)
        p = tl.exp(qk - m_i_new[:, None])
        
        # Update accumulator
        acc = acc * alpha[:, None]
        # p: (BLOCK_M, BLOCK_N), v: (BLOCK_N, D) -> (BLOCK_M, D)
        acc += tl.dot(p.to(tl.float16), v)
        
        # Update sum exp
        l_i = l_i * alpha + tl.sum(p, 1)
        m_i = m_i_new
        
        # Advance pointers
        K_block_ptr = tl.advance(K_block_ptr, (0, BLOCK_N))
        V_block_ptr = tl.advance(V_block_ptr, (BLOCK_N, 0))

    # Normalize
    acc = acc / l_i[:, None]
    
    # Store
    O_block_ptr = tl.make_block_ptr(
        base=Out + o_offset,
        shape=(N_CTX, BLOCK_DMODEL),
        strides=(stride_om, stride_on),
        offsets=(start_m * BLOCK_M, 0),
        block_shape=(BLOCK_M, BLOCK_DMODEL),
        order=(1, 0)
    )
    tl.store(O_block_ptr, acc.to(tl.float16))

def flash_attn(Q, K, V, causal=True):
    Z, H, N_CTX, D_HEAD = Q.shape
    
    Out = torch.empty_like(Q)
    sm_scale = 1.0 / (D_HEAD ** 0.5)
    
    # Configuration
    BLOCK_M = 128
    BLOCK_N = 64
    BLOCK_DMODEL = triton.next_power_of_2(D_HEAD)
    
    num_warps = 4
    num_stages = 4
    
    grid = (triton.cdiv(N_CTX, BLOCK_M), Z * H)
    
    _flash_attn_fwd_kernel[grid](
        Q, K, V, sm_scale,
        Out,
        Q.stride(0), Q.stride(1), Q.stride(2), Q.stride(3),
        K.stride(0), K.stride(1), K.stride(2), K.stride(3),
        V.stride(0), V.stride(1), V.stride(2), V.stride(3),
        Out.stride(0), Out.stride(1), Out.stride(2), Out.stride(3),
        Z, H, N_CTX,
        BLOCK_M=BLOCK_M, BLOCK_N=BLOCK_N, BLOCK_DMODEL=BLOCK_DMODEL,
        IS_CAUSAL=causal,
        num_warps=num_warps,
        num_stages=num_stages
    )
    
    return Out
"""
        return {"code": code}