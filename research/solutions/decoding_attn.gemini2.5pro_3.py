import torch
import triton
import triton.language as tl
import math

class Solution:
    def solve(self, spec_path: str = None) -> dict:
        kernel_code = """
import torch
import triton
import triton.language as tl

@triton.autotune(
    configs=[
        triton.Config({'BLOCK_N': 64}, num_warps=2),
        triton.Config({'BLOCK_N': 128}, num_warps=2),
        triton.Config({'BLOCK_N': 256}, num_warps=4),
        triton.Config({'BLOCK_N': 512}, num_warps=4),
        triton.Config({'BLOCK_N': 1024}, num_warps=8),
    ],
    key=['N_CTX', 'D_HEAD'],
)
@triton.jit
def _decoding_attn_kernel(
    # Pointers to matrices
    Q, K, V, O,
    # Stride variables for tensors
    stride_qz, stride_qh, stride_qm, stride_qd,
    stride_kz, stride_kh, stride_kn, stride_kd,
    stride_vz, stride_vh, stride_vn, stride_vd,
    stride_oz, stride_oh, stride_om, stride_od,
    # Other metadata
    Z, H, N_CTX,
    # Compile-time constants
    D_HEAD: tl.constexpr,
    BLOCK_N: tl.constexpr,
):
    \"\"\"
    Triton kernel for single-query attention. Fuses score computation,
    softmax, and value aggregation into a single pass over K and V.
    \"\"\"
    # Each program instance computes attention for one attention head.
    # The grid is 1D, so we recover the Z and H indices from the program ID.
    pid = tl.program_id(0)
    h = pid % H
    z = pid // H

    # Pointers to the start of the data for this (z, h) pair.
    q_ptr = Q + z * stride_qz + h * stride_qh
    k_ptr = K + z * stride_kz + h * stride_kh
    v_ptr = V + z * stride_vz + h * stride_vh
    o_ptr = O + z * stride_oz + h * stride_oh

    # Load the single query vector for this head.
    # It's small (D_HEAD=64) and can be kept in registers.
    offs_d = tl.arange(0, D_HEAD)
    q = tl.load(q_ptr + offs_d)
    
    # Use float32 for accumulators to maintain precision.
    q = q.to(tl.float32)
    acc = tl.zeros([D_HEAD], dtype=tl.float32)
    m_i = -float('inf')  # Running max for stable softmax
    l_i = 0.0            # Running sum for stable softmax

    # Scale factor for dot products.
    sm_scale = (D_HEAD * 1.0) ** -0.5

    # Loop over the key/value sequence in blocks of size BLOCK_N.
    # This is the main loop for the reduction over the sequence length.
    for start_n in range(0, N_CTX, BLOCK_N):
        # Offsets for the current block of K and V.
        offs_n = start_n + tl.arange(0, BLOCK_N)
        mask_n = offs_n < N_CTX
        
        # Load a block of K. Shape: (BLOCK_N, D_HEAD)
        k_ptrs = k_ptr + offs_n[:, None] * stride_kn + offs_d[None, :]
        k = tl.load(k_ptrs, mask=mask_n[:, None], other=0.0)
        
        # Compute scores for the current block: S = Q @ K^T.
        s_ij = tl.sum(q[None, :] * k.to(tl.float32), 1) * sm_scale
        s_ij = tl.where(mask_n, s_ij, -float('inf'))
        
        # --- Online softmax calculation ---
        # 1. Get the max of the current block scores
        m_ij = tl.max(s_ij, 0)
        # 2. Find the new global max
        m_new = tl.maximum(m_i, m_ij)
        # 3. Rescale the running sum and accumulator
        alpha = tl.exp(m_i - m_new)
        acc = acc * alpha
        l_i = l_i * alpha
        # 4. Compute probabilities for the current block
        p_ij = tl.exp(s_ij - m_new)
        # 5. Update the running sum
        l_i += tl.sum(p_ij, 0)
        
        # 6. Load the corresponding block of V. Shape: (BLOCK_N, D_HEAD)
        v_ptrs = v_ptr + offs_n[:, None] * stride_vn + offs_d[None, :]
        v = tl.load(v_ptrs, mask=mask_n[:, None], other=0.0)
        
        # 7. Update the accumulator with the weighted values (p @ V).
        p_ij = p_ij.to(v.dtype)
        acc += tl.sum(p_ij[:, None] * v.to(tl.float32), 0)
        
        # 8. Update the global max
        m_i = m_new

    # Final normalization of the accumulator.
    # Add a small epsilon to l_i to avoid division by zero.
    l_i = tl.where(l_i == 0.0, 1.0, l_i)
    acc = acc / l_i
    
    # Store the final output.
    o_ptrs = o_ptr + offs_d
    tl.store(o_ptrs, acc.to(Q.dtype.element_ty))


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
    # Extract dimensions from input tensors.
    Z, H, M, Dq = Q.shape
    _Z, _H, N, _Dq = K.shape
    __Z, __H, _N, Dv = V.shape
    
    # This kernel is specialized for the decoding case (M=1).
    assert M == 1, "The 'M' dimension of Q must be 1 for this decoding kernel."
    assert Dq == Dv, "Query and Value head dimensions must be equal."
    
    # Create the output tensor.
    O = torch.empty((Z, H, M, Dv), device=Q.device, dtype=Q.dtype)

    # The grid size is the total number of attention heads to compute.
    grid = (Z * H,)

    # Launch the Triton kernel.
    _decoding_attn_kernel[grid](
        Q, K, V, O,
        Q.stride(0), Q.stride(1), Q.stride(2), Q.stride(3),
        K.stride(0), K.stride(1), K.stride(2), K.stride(3),
        V.stride(0), V.stride(1), V.stride(2), V.stride(3),
        O.stride(0), O.stride(1), O.stride(2), O.stride(3),
        Z, H, N,
        D_HEAD=Dq,
    )
    
    return O
"""
        return {"code": kernel_code}
