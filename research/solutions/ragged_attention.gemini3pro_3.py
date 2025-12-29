import torch
import triton
import triton.language as tl

class Solution:
    def solve(self, spec_path: str = None) -> dict:
        code = """
import torch
import triton
import triton.language as tl

@triton.jit
def _ragged_attn_kernel(
    Q, K, V, RowLens, Out,
    stride_qm, stride_qd,
    stride_kn, stride_kd,
    stride_vn, stride_vd,
    stride_om, stride_od,
    sm_scale,
    M, N,
    BLOCK_M: tl.constexpr, BLOCK_N: tl.constexpr,
    BLOCK_DMODEL: tl.constexpr, BLOCK_DVALUE: tl.constexpr
):
    # Program ID and offsets
    start_m = tl.program_id(0)
    offs_m = start_m * BLOCK_M + tl.arange(0, BLOCK_M)
    
    # Boundary mask for Query rows
    m_mask = offs_m < M

    # Load row lengths for the current block of queries
    # row_lens: (M,)
    rl = tl.load(RowLens + offs_m, mask=m_mask, other=0)
    
    # Q pointers and loading
    offs_d = tl.arange(0, BLOCK_DMODEL)
    q_ptrs = Q + (offs_m[:, None] * stride_qm + offs_d[None, :] * stride_qd)
    # Load Q, mask with m_mask and D dimensions
    q = tl.load(q_ptrs, mask=m_mask[:, None] & (offs_d[None, :] < BLOCK_DMODEL), other=0.0)
    q = q * sm_scale
    
    # Initialize streaming softmax accumulators
    # m_i: max score so far
    # l_i: sum of exponentials so far
    # acc: accumulated output
    m_i = tl.full([BLOCK_M], float("-inf"), dtype=tl.float32)
    l_i = tl.zeros([BLOCK_M], dtype=tl.float32)
    acc = tl.zeros([BLOCK_M, BLOCK_DVALUE], dtype=tl.float32)
    
    offs_n = tl.arange(0, BLOCK_N)
    offs_dv = tl.arange(0, BLOCK_DVALUE)
    
    # Loop over K/V blocks
    # We iterate over the full range 0..N.
    # Masking handles the ragged nature.
    for start_n in range(0, N, BLOCK_N):
        cols = start_n + offs_n
        
        # Create masks
        # 1. Physical boundary: cols < N
        # 2. Ragged boundary: cols < row_lens[i]
        # Broadcast cols to (BLOCK_M, BLOCK_N)
        k_mask_n = cols < N
        ragged_mask = cols[None, :] < rl[:, None]
        mask = k_mask_n[None, :] & ragged_mask
        
        # Load K block
        # Shape: (BLOCK_N, D)
        k_ptrs = K + (cols[:, None] * stride_kn + offs_d[None, :] * stride_kd)
        k = tl.load(k_ptrs, mask=k_mask_n[:, None] & (offs_d[None, :] < BLOCK_DMODEL), other=0.0)
        
        # Compute scores: Q @ K.T
        # q: (BLOCK_M, D), k: (BLOCK_N, D) -> result (BLOCK_M, BLOCK_N)
        qk = tl.dot(q, tl.trans(k))
        
        # Apply mask (set invalid scores to -inf)
        qk = tl.where(mask, qk, float("-inf"))
        
        # --- Online Softmax Update ---
        
        # 1. Compute current block max
        m_curr = tl.max(qk, 1)
        
        # 2. Update global max
        m_new = tl.maximum(m_i, m_curr)
        
        # 3. Compute scaling factors
        alpha = tl.exp(m_i - m_new)
        p = tl.exp(qk - m_new[:, None])
        
        # 4. Update normalization sum
        l_new = l_i * alpha + tl.sum(p, 1)
        
        # 5. Accumulate output
        # Load V block
        v_ptrs = V + (cols[:, None] * stride_vn + offs_dv[None, :] * stride_vd)
        v = tl.load(v_ptrs, mask=k_mask_n[:, None] & (offs_dv[None, :] < BLOCK_DVALUE), other=0.0)
        
        # Rescale accumulator
        acc = acc * alpha[:, None]
        # Add new contribution: p @ v
        # p is fp32, cast to fp16 for mixed precision dot if needed, or keep precision.
        # Standard: cast P to fp16 for tensor core MMA
        acc += tl.dot(p.to(tl.float16), v)
        
        # Update running stats
        l_i = l_new
        m_i = m_new

    # Finalize
    # Normalize by l_i
    # Handle potentially zero l_i (if row_lens was 0, though inputs usually > 0)
    l_i = tl.where(l_i == 0.0, 1.0, l_i)
    out = acc / l_i[:, None]
    
    # Store output
    out_ptrs = Out + (offs_m[:, None] * stride_om + offs_dv[None, :] * stride_od)
    tl.store(out_ptrs, out.to(tl.float16), mask=m_mask[:, None] & (offs_dv[None, :] < BLOCK_DVALUE))

def ragged_attn(Q: torch.Tensor, K: torch.Tensor, V: torch.Tensor, row_lens: torch.Tensor) -> torch.Tensor:
    M, D = Q.shape
    N, _ = K.shape
    _, Dv = V.shape
    
    # Allocate output
    O = torch.empty((M, Dv), device=Q.device, dtype=torch.float16)
    
    # Tuning parameters
    # BLOCK_M=128, BLOCK_N=64 works well for medium sized D=64
    BLOCK_M = 128
    BLOCK_N = 64
    num_warps = 4
    num_stages = 3
    
    # Grid configuration
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
        BLOCK_DMODEL=D, BLOCK_DVALUE=Dv,
        num_warps=num_warps, num_stages=num_stages
    )
    
    return O
"""
        return {"code": code}