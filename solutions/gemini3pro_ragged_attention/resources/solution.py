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
def _ragged_attn_kernel(
    Q, K, V, RowLens, O,
    stride_qm, stride_qd,
    stride_kn, stride_kd,
    stride_vn, stride_vd,
    stride_om, stride_od,
    sm_scale,
    M, N,
    BLOCK_M: tl.constexpr, BLOCK_N: tl.constexpr,
    BLOCK_D: tl.constexpr, BLOCK_DV: tl.constexpr
):
    pid = tl.program_id(0)
    start_m = pid * BLOCK_M
    off_m = start_m + tl.arange(0, BLOCK_M)
    
    # Mask for valid queries
    m_mask = off_m < M
    
    # Load row lengths
    # row_lens: (M,)
    rl = tl.load(RowLens + off_m, mask=m_mask, other=0)
    
    # Offsets for D/Dv
    off_d = tl.arange(0, BLOCK_D)
    off_dv = tl.arange(0, BLOCK_DV)
    
    # Load Q block
    # Q: (M, D)
    q_ptrs = Q + (off_m[:, None] * stride_qm + off_d[None, :] * stride_qd)
    q = tl.load(q_ptrs, mask=m_mask[:, None], other=0.0)
    
    # Apply scaling to Q
    q = q * sm_scale
    
    # Initialize accumulators for streaming softmax
    # m_i: running max, initialized to -inf
    # l_i: running sum, initialized to 0
    # acc: output accumulator, initialized to 0
    m_i = tl.full([BLOCK_M], float("-inf"), dtype=tl.float32)
    l_i = tl.zeros([BLOCK_M], dtype=tl.float32)
    acc = tl.zeros([BLOCK_M, BLOCK_DV], dtype=tl.float32)
    
    # Iterate over K and V blocks
    for start_n in range(0, N, BLOCK_N):
        cols = start_n + tl.arange(0, BLOCK_N)
        
        # Mask for physical K/V bounds
        k_mask = cols < N
        
        # Load K block
        # K: (N, D). Load as (BLOCK_N, BLOCK_D)
        k_ptrs = K + (cols[:, None] * stride_kn + off_d[None, :] * stride_kd)
        k = tl.load(k_ptrs, mask=k_mask[:, None], other=0.0)
        
        # Load V block
        # V: (N, Dv). Load as (BLOCK_N, BLOCK_DV)
        v_ptrs = V + (cols[:, None] * stride_vn + off_dv[None, :] * stride_vd)
        v = tl.load(v_ptrs, mask=k_mask[:, None], other=0.0)
        
        # Compute scores: Q @ K.T
        # Q: (BLOCK_M, D), K: (BLOCK_N, D) -> (BLOCK_M, BLOCK_N)
        qk = tl.dot(q, tl.trans(k))
        
        # Apply ragged mask
        # Valid if col < row_len[row] AND col < N
        ragged_mask = (cols[None, :] < rl[:, None]) & k_mask[None, :]
        qk = tl.where(ragged_mask, qk, float("-inf"))
        
        # Streaming Softmax Update
        m_curr = tl.max(qk, 1) # Max in current block
        m_new = tl.maximum(m_i, m_curr)
        
        alpha = tl.exp(m_i - m_new)
        p = tl.exp(qk - m_new[:, None])
        
        # Update accumulator: acc = acc * alpha + p @ v
        acc = acc * alpha[:, None]
        # p: (BLOCK_M, BLOCK_N), v: (BLOCK_N, BLOCK_DV) -> (BLOCK_M, BLOCK_DV)
        # Cast p to fp16 for tensor core accumulation
        acc += tl.dot(p.to(tl.float16), v)
        
        # Update running sum: l = l * alpha + sum(p)
        l_i = l_i * alpha + tl.sum(p, 1)
        
        # Update running max
        m_i = m_new

    # Finalize Output
    # O = acc / l_i
    # Handle potentially empty rows (though row_lens > 0 usually)
    # If l_i is 0, result is NaN/Inf, but valid inputs prevent this
    o = acc / l_i[:, None]
    
    # Store Output
    o_ptrs = O + (off_m[:, None] * stride_om + off_dv[None, :] * stride_od)
    tl.store(o_ptrs, o.to(tl.float16), mask=m_mask[:, None])

def ragged_attn(Q: torch.Tensor, K: torch.Tensor, V: torch.Tensor, row_lens: torch.Tensor) -> torch.Tensor:
    M, D = Q.shape
    N, _ = K.shape
    _, Dv = V.shape
    
    # Ensure inputs are contiguous if necessary, though strides handle it
    # Output tensor
    O = torch.empty((M, Dv), device=Q.device, dtype=torch.float16)
    
    # Block sizes
    # L4 has decent shared memory. 
    # BLOCK_M=128, BLOCK_N=64, D=64 fits well.
    # Num stages=2 keeps shared memory usage safe.
    BLOCK_M = 128
    BLOCK_N = 64
    BLOCK_D = 64
    BLOCK_DV = 64
    
    # Validate D/Dv match block sizes (assumed 64 based on spec)
    
    grid = (triton.cdiv(M, BLOCK_M), 1, 1)
    sm_scale = 1.0 / (D ** 0.5)
    
    _ragged_attn_kernel[grid](
        Q, K, V, row_lens, O,
        Q.stride(0), Q.stride(1),
        K.stride(0), K.stride(1),
        V.stride(0), V.stride(1),
        O.stride(0), O.stride(1),
        sm_scale,
        M, N,
        BLOCK_M=BLOCK_M, BLOCK_N=BLOCK_N,
        BLOCK_D=BLOCK_D, BLOCK_DV=BLOCK_DV,
        num_warps=4,
        num_stages=2
    )
    
    return O
"""
        return {"code": code}
