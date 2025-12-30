import torch
import triton
import triton.language as tl

class Solution:
    def solve(self, spec_path: str = None) -> dict:
        kernel_code = """
import torch
import triton
import triton.language as tl

@triton.autotune(
    configs=[
        triton.Config({'BLOCK_N': 64}, num_warps=2, num_stages=3),
        triton.Config({'BLOCK_N': 128}, num_warps=2, num_stages=2),
        triton.Config({'BLOCK_N': 128}, num_warps=4, num_stages=2),
        triton.Config({'BLOCK_N': 256}, num_warps=4, num_stages=2),
        triton.Config({'BLOCK_N': 256}, num_warps=8, num_stages=3),
        triton.Config({'BLOCK_N': 512}, num_warps=4, num_stages=2),
        triton.Config({'BLOCK_N': 512}, num_warps=8, num_stages=2),
        triton.Config({'BLOCK_N': 1024}, num_warps=8, num_stages=2),
    ],
    key=['N', 'D_HEAD_KQ', 'D_HEAD_V'],
)
@triton.jit
def _decoding_attn_kernel(
    Q, K, V, O,
    sm_scale,
    stride_qz, stride_qh, stride_qm, stride_qd,
    stride_kz, stride_kh, stride_kn, stride_kd,
    stride_vz, stride_vh, stride_vn, stride_vd,
    stride_oz, stride_oh, stride_om, stride_od,
    Z, H, N,
    D_HEAD_KQ: tl.constexpr,
    D_HEAD_V: tl.constexpr,
    BLOCK_N: tl.constexpr,
):
    \"\"\"
    Triton kernel for decoding attention.
    Computes attention for a single query vector per head against a sequence of keys/values.
    This kernel is launched with a 1D grid of size Z * H.
    Each instance computes the output for one attention head.
    \"\"\"
    # 1. Get program IDs and calculate batch/head indices
    pid_zh = tl.program_id(0)
    pid_z = pid_zh // H
    pid_h = pid_zh % H

    # 2. Setup pointers to the start of the relevant slices
    q_offset = pid_z * stride_qz + pid_h * stride_qh
    k_offset = pid_z * stride_kz + pid_h * stride_kh
    v_offset = pid_z * stride_vz + pid_h * stride_vh
    o_offset = pid_z * stride_oz + pid_h * stride_oh

    Q_ptr = Q + q_offset
    K_ptr = K + k_offset
    V_ptr = V + v_offset
    O_ptr = O + o_offset

    # 3. Load query vector and initialize accumulators
    # q is loaded once, converted to float32, and reused across all K/V blocks
    offs_d_kq = tl.arange(0, D_HEAD_KQ)
    q = tl.load(Q_ptr + offs_d_kq * stride_qd).to(tl.float32)

    # Accumulators for online softmax calculation, in high precision
    acc = tl.zeros([D_HEAD_V], dtype=tl.float32)
    l_i = tl.zeros([1], dtype=tl.float32)
    m_i = tl.full([1], -float('inf'), dtype=tl.float32)

    # 4. Main loop over the sequence length N in blocks
    for start_n in range(0, N, BLOCK_N):
        # -- a. Define offsets and mask for the current block
        offs_n = start_n + tl.arange(0, BLOCK_N)
        mask_n = offs_n < N

        # -- b. Load a block of keys (K)
        k_ptrs = K_ptr + (offs_n[:, None] * stride_kn + offs_d_kq[None, :] * stride_kd)
        k = tl.load(k_ptrs, mask=mask_n[:, None], other=0.0)

        # -- c. Compute scores S = Q @ K.T
        s_j = tl.sum(q[None, :] * k.to(tl.float32), axis=1) * sm_scale
        # Mask out-of-bounds scores before max operation
        s_j = tl.where(mask_n, s_j, -float('inf'))

        # -- d. Update softmax statistics (m, l)
        m_j = tl.max(s_j, axis=0)
        m_new = tl.maximum(m_i, m_j)
        
        alpha = tl.exp(m_i - m_new)
        p_j = tl.exp(s_j - m_new)
        
        l_i = l_i * alpha + tl.sum(p_j, axis=0)

        # -- e. Rescale the accumulator
        acc = acc * alpha

        # -- f. Load a block of values (V)
        offs_d_v = tl.arange(0, D_HEAD_V)
        v_ptrs = V_ptr + (offs_n[:, None] * stride_vn + offs_d_v[None, :] * stride_vd)
        v = tl.load(v_ptrs, mask=mask_n[:, None], other=0.0)

        # -- g. Update accumulator with the contribution of the current block
        p_j = p_j.to(v.dtype)
        acc += tl.dot(p_j[None, :], v)
        
        # -- h. Update the max value for the next iteration
        m_i = m_new

    # 5. Finalize the output
    # Normalize the accumulator by the softmax denominator
    o = acc / l_i
    
    # 6. Store the final output vector
    offs_d_out = tl.arange(0, D_HEAD_V)
    o_ptrs = O_ptr + offs_d_out * stride_od
    tl.store(o_ptrs, o.to(O.dtype.element_tl))


def decoding_attn(Q: torch.Tensor, K: torch.Tensor, V: torch.Tensor) -> torch.Tensor:
    \"\"\"
    Decoding attention computation.
    
    Args:
        Q: Input tensor of shape (Z, H, M, Dq) - query tensor (float16)
        K: Input tensor of shape (Z, H, N, Dq) - key tensor (float16)
        V: Input tensor of shape (Z, H, N, Dv) - value tensor (float16)
    
    Returns:
        Output tensor of shape (Z, H, M, Dv) - attention output (float16)
    \"\"\"
    # 1. Get tensor shapes
    Z, H, M, Dq = Q.shape
    _, _, N, _ = K.shape
    _, _, _, Dv = V.shape

    # This kernel is specialized for M=1 (single query per head)
    assert M == 1, "This kernel is specialized for M=1 decoding."
    
    # 2. Allocate output tensor
    O = torch.empty((Z, H, M, Dv), device=Q.device, dtype=Q.dtype)

    # 3. Set up grid and scaling factor
    # Grid is 1D, with one program per batch entry and head
    grid = (Z * H,)
    sm_scale = Dq**-0.5

    # 4. Launch the Triton kernel
    _decoding_attn_kernel[grid](
        Q, K, V, O,
        sm_scale,
        Q.stride(0), Q.stride(1), Q.stride(2), Q.stride(3),
        K.stride(0), K.stride(1), K.stride(2), K.stride(3),
        V.stride(0), V.stride(1), V.stride(2), V.stride(3),
        O.stride(0), O.stride(1), O.stride(2), O.stride(3),
        Z, H, N,
        D_HEAD_KQ=Dq,
        D_HEAD_V=Dv,
    )
    
    # 5. Return the result
    return O
"""
        return {"code": kernel_code}