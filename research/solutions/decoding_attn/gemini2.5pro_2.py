import torch
import triton
import triton.language as tl

@triton.autotune(
    configs=[
        triton.Config({'BLOCK_N': 32}, num_stages=5, num_warps=2),
        triton.Config({'BLOCK_N': 64}, num_stages=4, num_warps=4),
        triton.Config({'BLOCK_N': 128}, num_stages=3, num_warps=4),
        triton.Config({'BLOCK_N': 256}, num_stages=3, num_warps=8),
        triton.Config({'BLOCK_N': 128}, num_stages=4, num_warps=8),
        triton.Config({'BLOCK_N': 64}, num_stages=5, num_warps=8),
    ],
    key=['N', 'D_HEAD', 'D_VALUE'],
)
@triton.jit
def _decoding_attn_kernel(
    Q, K, V, O,
    s_qz, s_qh, s_qm, s_qd,
    s_kz, s_kh, s_kn, s_kd,
    s_vz, s_vh, s_vn, s_vd,
    s_oz, s_oh, s_om, s_od,
    Z, H, N,
    D_HEAD: tl.constexpr,
    D_VALUE: tl.constexpr,
    BLOCK_N: tl.constexpr,
):
    """
    Triton kernel for single-query attention (decoding).
    Each program instance computes the attention for one head across the entire key/value sequence.
    The grid is 1D, with size Z * H.
    """
    # 1. Identify the specific head this program instance is responsible for.
    pid_zh = tl.program_id(0)
    pid_z = pid_zh // H
    pid_h = pid_zh % H

    # 2. Compute pointers to the start of the Q, K, V, and O tensors for this head.
    # Since M=1, the offset for the M dimension is always 0.
    q_offset = pid_z * s_qz + pid_h * s_qh
    k_offset = pid_z * s_kz + pid_h * s_kh
    v_offset = pid_z * s_vz + pid_h * s_vh
    o_offset = pid_z * s_oz + pid_h * s_oh

    Q_ptr = Q + q_offset
    K_ptr = K + k_offset
    V_ptr = V + v_offset
    O_ptr = O + o_offset

    # 3. Initialize accumulators for the online softmax algorithm.
    # `l_acc`: the denominator of the softmax (sum of exponentials).
    # `m_acc`: the running maximum of the scores, for numerical stability.
    # `o_acc`: the accumulator for the output vector.
    l_acc = tl.zeros([1], dtype=tl.float32)
    m_acc = -float('inf') * tl.ones([1], dtype=tl.float32)
    o_acc = tl.zeros([D_VALUE], dtype=tl.float32)

    # 4. Load the single query vector for this head.
    # This is done once per program instance.
    scale = (D_HEAD ** -0.5)
    offs_d_head = tl.arange(0, D_HEAD)
    q = tl.load(Q_ptr + offs_d_head * s_qd, mask=offs_d_head < D_HEAD, other=0.0).to(tl.float32)

    # 5. Main loop: Iterate over the key/value sequence in blocks of BLOCK_N.
    offs_n = tl.arange(0, BLOCK_N)
    for start_n in range(0, N, BLOCK_N):
        # -- a. Define the current block of sequence indices and a mask for padding.
        current_offs_n = start_n + offs_n
        mask_n = current_offs_n < N
        
        # -- b. Load a block of K and compute scores S = (Q @ K^T) * scale.
        k_ptrs = K_ptr + current_offs_n[:, None] * s_kn + offs_d_head[None, :] * s_kd
        k = tl.load(k_ptrs, mask=mask_n[:, None], other=0.0).to(tl.float32)
        s = tl.sum(q[None, :] * k, axis=1) * scale
        s = tl.where(mask_n, s, -float('inf')) # Apply mask to scores.

        # -- c. Update softmax statistics using the new block of scores.
        m_curr = tl.max(s, axis=0)
        m_new = tl.maximum(m_acc, m_curr)
        alpha = tl.exp(m_acc - m_new)
        p = tl.exp(s - m_new)
        l_new = alpha * l_acc + tl.sum(p, axis=0)

        # -- d. Load the corresponding block of V.
        offs_d_value = tl.arange(0, D_VALUE)
        v_ptrs = V_ptr + current_offs_n[:, None] * s_vn + offs_d_value[None, :] * s_vd
        v = tl.load(v_ptrs, mask=mask_n[:, None], other=0.0)

        # -- e. Rescale the old accumulator and add the contribution from the new block.
        o_acc = o_acc * alpha
        p_typed = p.to(v.dtype)
        o_update = tl.dot(p_typed[None, :], v)
        o_acc += tl.squeeze(o_update, axis=0)
        
        # -- f. Update stats for the next iteration.
        l_acc = l_new
        m_acc = m_new

    # 6. Finalize the output by normalizing with the final softmax denominator.
    o_acc = o_acc / l_acc
    
    # 7. Store the final output vector to global memory.
    offs_d_value = tl.arange(0, D_VALUE)
    o_ptrs = O_ptr + offs_d_value * s_od
    tl.store(o_ptrs, o_acc.to(O.dtype.element_ty), mask=offs_d_value < D_VALUE)


def decoding_attn(Q: torch.Tensor, K: torch.Tensor, V: torch.Tensor) -> torch.Tensor:
    """
    Decoding attention computation.
    
    Args:
        Q: Input tensor of shape (Z, H, M, Dq) - query tensor (float16)
        K: Input tensor of shape (Z, H, N, Dq) - key tensor (float16)
        V: Input tensor of shape (Z, H, N, Dv) - value tensor (float16)
    
    Returns:
        Output tensor of shape (Z, H, M, Dv) - attention output (float16)
    """
    Z, H, M, Dq = Q.shape
    _, _, N, _ = K.shape
    _, _, _, Dv = V.shape
    
    # This implementation is specialized for decoding, where the query sequence length is 1.
    assert M == 1, "M dimension (query sequence length) must be 1 for this decoding attention implementation"
    
    # Create the output tensor with the correct shape and data type.
    O = torch.empty((Z, H, M, Dv), device=Q.device, dtype=V.dtype)

    # The grid is 1D, with each program instance handling one attention head.
    grid = (Z * H, )

    # Launch the Triton kernel.
    _decoding_attn_kernel[grid](
        Q, K, V, O,
        Q.stride(0), Q.stride(1), Q.stride(2), Q.stride(3),
        K.stride(0), K.stride(1), K.stride(2), K.stride(3),
        V.stride(0), V.stride(1), V.stride(2), V.stride(3),
        O.stride(0), O.stride(1), O.stride(2), O.stride(3),
        Z, H, N,
        D_HEAD=Dq, D_VALUE=Dv,
    )
    return O


class Solution:
    def solve(self, spec_path: str = None) -> dict:
        """
        This method is not used in the evaluation but is part of the API.
        The evaluator directly imports and uses the `decoding_attn` function.
        """
        # This function is not expected to be called in this setup.
        # The primary deliverable is the `decoding_attn` function in the global scope.
        pass