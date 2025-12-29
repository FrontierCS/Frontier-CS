import torch

class Solution:
    def solve(self, spec_path: str = None) -> dict:
        """
        Returns a dict with the Python code for the Triton kernel.
        """
        kernel_code = """
import torch
import triton
import triton.language as tl

@triton.autotune(
    configs=[
        # Basic configurations for various block sizes
        triton.Config({'BLOCK_N': 64}, num_warps=2, num_stages=4),
        triton.Config({'BLOCK_N': 128}, num_warps=4, num_stages=3),
        triton.Config({'BLOCK_N': 256}, num_warps=4, num_stages=3),
        
        # Larger block sizes with more warps
        triton.Config({'BLOCK_N': 512}, num_warps=8, num_stages=3),
        triton.Config({'BLOCK_N': 1024}, num_warps=8, num_stages=3),
        
        # Alternative configurations to explore the design space
        triton.Config({'BLOCK_N': 256}, num_warps=8, num_stages=4),
        triton.Config({'BLOCK_N': 512}, num_warps=4, num_stages=4),
        triton.Config({'BLOCK_N': 128}, num_warps=8, num_stages=2),
        
        # Configurations for very long sequences
        triton.Config({'BLOCK_N': 2048}, num_warps=16, num_stages=2),
    ],
    key=['N'],
)
@triton.jit
def _decoding_attn_kernel(
    Q, K, V, O,
    stride_qz, stride_qh, stride_qm, stride_qd,
    stride_kz, stride_kh, stride_kn, stride_kd,
    stride_vz, stride_vh, stride_vn, stride_vd,
    stride_oz, stride_oh, stride_om, stride_od,
    Z, H, N,
    Dq: tl.constexpr,
    Dv: tl.constexpr,
    BLOCK_N: tl.constexpr,
):
    # Each program instance computes attention for one head.
    # The grid is 1D, so we map the program ID to batch and head indices.
    pid = tl.program_id(0)
    pid_z = pid // H
    pid_h = pid % H

    # Pointers to the start of the data for the current head.
    q_offset = pid_z * stride_qz + pid_h * stride_qh
    k_offset = pid_z * stride_kz + pid_h * stride_kh
    v_offset = pid_z * stride_vz + pid_h * stride_vh
    o_offset = pid_z * stride_oz + pid_h * stride_oh

    q_ptr = Q + q_offset
    k_ptr = K + k_offset
    v_ptr = V + v_offset
    o_ptr = O + o_offset

    # Load the query vector q. It's small and used repeatedly.
    offs_d = tl.arange(0, Dq)
    q = tl.load(q_ptr + offs_d * stride_qd).to(tl.float32)

    # Initialize accumulators for the online softmax algorithm.
    # `acc` holds the numerator, `l_i` the denominator.
    # `m_i` is the running maximum for numerical stability.
    acc = tl.zeros([Dv], dtype=tl.float32)
    m_i = -float('inf')
    l_i = 0.0
    
    # Pre-compute the scaling factor for attention.
    sm_scale = 1.0 / (Dq ** 0.5)

    # Main loop over the sequence length N, processing in blocks.
    offs_n = tl.arange(0, BLOCK_N)
    for start_n in range(0, tl.cdiv(N, BLOCK_N)):
        current_offs_n = offs_n + start_n * BLOCK_N
        mask_n = current_offs_n < N
        
        # Load a block of keys K.
        k_ptrs = k_ptr + current_offs_n[:, None] * stride_kn + offs_d[None, :] * stride_kd
        k = tl.load(k_ptrs, mask=mask_n[:, None], other=0.0).to(tl.float32)
        
        # Compute scores s = q @ k.T
        # This is a batch of dot products between q and rows of k.
        s = tl.sum(q[None, :] * k, axis=1)
        s *= sm_scale
        
        # Mask out scores for padding tokens.
        s = tl.where(mask_n, s, -float('inf'))
        
        # --- Online Softmax ---
        # 1. Find new maximum score for the current block.
        m_i_new = tl.maximum(m_i, tl.max(s, axis=0))
        
        # 2. Rescale previous accumulator and sum of exponentials.
        alpha = tl.exp(m_i - m_i_new)
        acc = acc * alpha
        l_i = l_i * alpha
        
        # 3. Compute probabilities for the current block and update l_i.
        p = tl.exp(s - m_i_new)
        l_i += tl.sum(p, axis=0)
        
        # 4. Load the corresponding block of values V.
        offs_dv = tl.arange(0, Dv)
        v_ptrs = v_ptr + current_offs_n[:, None] * stride_vn + offs_dv[None, :] * stride_vd
        v = tl.load(v_ptrs, mask=mask_n[:, None], other=0.0).to(tl.float32)
        
        # 5. Update accumulator with weighted values.
        # p is (BLOCK_N,), v is (BLOCK_N, Dv). We need p.T @ v.
        # This is done by broadcasting p and summing over the N dimension.
        p_casted = p.to(v.dtype)
        acc += tl.sum(p_casted[:, None] * v, axis=0)
        
        # 6. Update the running maximum.
        m_i = m_i_new

    # Finalize the output by dividing by the sum of exponentials.
    o = acc / l_i

    # Store the final output vector.
    offs_dv = tl.arange(0, Dv)
    tl.store(o_ptr + offs_dv * stride_od, o.to(Q.dtype.element_ty))


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
    Z, H, M, Dq = Q.shape
    _, _, N, _ = K.shape
    _, _, _, Dv = V.shape
    
    assert M == 1, "This kernel is optimized for decoding attention where M=1 (one query)."
    
    # Create the output tensor.
    O = torch.empty((Z, H, M, Dv), device=Q.device, dtype=Q.dtype)

    # The grid is 1D, with one program per attention head.
    grid = (Z * H,)

    # Launch the Triton kernel.
    _decoding_attn_kernel[grid](
        Q, K, V, O,
        Q.stride(0), Q.stride(1), Q.stride(2), Q.stride(3),
        K.stride(0), K.stride(1), K.stride(2), K.stride(3),
        V.stride(0), V.stride(1), V.stride(2), V.stride(3),
        O.stride(0), O.stride(1), O.stride(2), O.stride(3),
        Z, H, N,
        Dq=Dq,
        Dv=Dv,
    )
    return O
"""
        return {"code": kernel_code}