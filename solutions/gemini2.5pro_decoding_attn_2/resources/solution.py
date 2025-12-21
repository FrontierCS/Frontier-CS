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
import math

@triton.autotune(
    configs=[
        triton.Config({'BLOCK_N': 32}, num_warps=2),
        triton.Config({'BLOCK_N': 64}, num_warps=2),
        triton.Config({'BLOCK_N': 64}, num_warps=4),
        triton.Config({'BLOCK_N': 128}, num_warps=4),
        triton.Config({'BLOCK_N': 256}, num_warps=4),
        triton.Config({'BLOCK_N': 256}, num_warps=8),
        triton.Config({'BLOCK_N': 512}, num_warps=8),
        triton.Config({'BLOCK_N': 1024}, num_warps=8),
    ],
    key=['N', 'Dq', 'Dv'],
)
@triton.jit
def _decoding_attn_fwd_kernel(
    # Pointers to Tensors
    Q, K, V, O,
    # Stride information for each tensor
    stride_qz, stride_qh, stride_qm, stride_qd,
    stride_kz, stride_kh, stride_kn, stride_kd,
    stride_vz, stride_vh, stride_vn, stride_vd,
    stride_oz, stride_oh, stride_om, stride_od,
    # Matrix dimensions
    Z, H, M, N,
    # Compile-time constants
    Dq: tl.constexpr,
    Dv: tl.constexpr,
    BLOCK_N: tl.constexpr,
):
    # Program IDs for the grid (Z*H, M)
    pid_zh = tl.program_id(0)
    pid_m = tl.program_id(1)

    # Calculate batch and head indices
    z = pid_zh // H
    h = pid_zh % H

    # Pointers to the start of rows for Q, O for the current (z, h, m)
    q_offset = z * stride_qz + h * stride_qh + pid_m * stride_qm
    o_offset = z * stride_oz + h * stride_oh + pid_m * stride_om
    # Pointers to the start of matrices for K, V for the current (z, h)
    k_offset = z * stride_kz + h * stride_kh
    v_offset = z * stride_vz + h * stride_vh

    Q_ptr = Q + q_offset
    O_ptr = O + o_offset
    K_ptr = K + k_offset
    V_ptr = V + v_offset

    # Attention scaling factor
    sm_scale = 1.0 / (Dq ** 0.5)

    # Load the single query vector for this program instance
    q_ptrs = Q_ptr + tl.arange(0, Dq)
    q = tl.load(q_ptrs).to(tl.float32)

    # Initialize accumulator and online softmax statistics
    acc = tl.zeros([Dv], dtype=tl.float32)
    m_i = -float("inf")
    l_i = 0.0

    # Loop over the key/value sequence length N in blocks of size BLOCK_N
    offs_n = tl.arange(0, BLOCK_N)
    for start_n in range(0, N, BLOCK_N):
        current_offs_n = start_n + offs_n
        # Mask for the last block to avoid out-of-bounds access
        k_mask = current_offs_n[:, None] < N

        # Load a block of K
        k_ptrs = K_ptr + current_offs_n[:, None] * stride_kn + tl.arange(0, Dq)[None, :]
        k = tl.load(k_ptrs, mask=k_mask, other=0.0).to(tl.float32)

        # Compute scores S = Q @ K^T for the block
        s = tl.sum(q[None, :] * k, axis=1) * sm_scale
        # Apply mask to scores to handle padding
        s = tl.where(current_offs_n < N, s, -float("inf"))

        # --- Online softmax update ---
        # Find new max score for the block
        m_i_new = tl.maximum(m_i, tl.max(s, axis=0))
        # Correctly scaled exponentiation
        p = tl.exp(s - m_i_new)
        # Rescale previous sum of exps
        alpha = tl.exp(m_i - m_i_new)
        l_i_new = alpha * l_i + tl.sum(p, axis=0)

        # --- Update accumulator ---
        # Rescale previous accumulator
        acc = acc * alpha
        # Load a block of V
        v_ptrs = V_ptr + current_offs_n[:, None] * stride_vn + tl.arange(0, Dv)[None, :]
        v = tl.load(v_ptrs, mask=k_mask, other=0.0)  # load as float16
        # Cast probabilities to float16 and compute weighted sum
        p = p.to(tl.float16)
        acc += tl.dot(tl.trans(p[:, None]), v)

        # Update softmax statistics for the next iteration
        m_i = m_i_new
        l_i = l_i_new

    # Final normalization of the accumulator
    acc = tl.ravel(acc)
    o = acc / l_i

    # Store the final output vector
    o_ptrs = O_ptr + tl.arange(0, Dv)
    tl.store(o_ptrs, o.to(tl.float16))


def decoding_attn(Q: torch.Tensor, K: torch.Tensor, V: torch.Tensor) -> torch.Tensor:
    Z, H, M, Dq = Q.shape
    _, _, N, _ = K.shape
    _, _, _, Dv = V.shape

    assert K.shape[3] == Dq and V.shape[3] == Dv, "Head dimensions of K/V must match Q"
    assert K.shape[2] == N and V.shape[2] == N, "Sequence lengths of K and V must match"

    O = torch.empty((Z, H, M, Dv), dtype=Q.dtype, device=Q.device)

    grid = (Z * H, M)
    
    _decoding_attn_fwd_kernel[grid](
        Q, K, V, O,
        Q.stride(0), Q.stride(1), Q.stride(2), Q.stride(3),
        K.stride(0), K.stride(1), K.stride(2), K.stride(3),
        V.stride(0), V.stride(1), V.stride(2), V.stride(3),
        O.stride(0), O.stride(1), O.stride(2), O.stride(3),
        Z, H, M, N,
        Dq=Dq, Dv=Dv,
    )

    return O
"""
        return {"code": kernel_code}
