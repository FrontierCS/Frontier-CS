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
        # Basic configs with increasing block sizes
        triton.Config({'BLOCK_N': 32}, num_warps=2, num_stages=1),
        triton.Config({'BLOCK_N': 64}, num_warps=2, num_stages=1),
        triton.Config({'BLOCK_N': 128}, num_warps=4, num_stages=1),
        triton.Config({'BLOCK_N': 256}, num_warps=4, num_stages=1),
        triton.Config({'BLOCK_N': 512}, num_warps=8, num_stages=1),
        # Configs with more pipeline stages to hide memory latency
        triton.Config({'BLOCK_N': 64}, num_warps=4, num_stages=2),
        triton.Config({'BLOCK_N': 128}, num_warps=4, num_stages=2),
        triton.Config({'BLOCK_N': 256}, num_warps=8, num_stages=2),
        triton.Config({'BLOCK_N': 128}, num_warps=4, num_stages=3),
    ],
    key=['N', 'D_HEAD'],
)
@triton.jit
def _decoding_attn_kernel(
    Q, K, V, O,
    stride_qz, stride_qh, stride_qm, stride_qd,
    stride_kz, stride_kh, stride_kn, stride_kd,
    stride_vz, stride_vh, stride_vn, stride_vd,
    stride_oz, stride_oh, stride_om, stride_od,
    Z, H, N,
    D_HEAD: tl.constexpr,
    sm_scale,
    BLOCK_N: tl.constexpr,
):
    # Each program instance computes the attention for one query vector (M=1), for one head.
    # The grid is 1D, with size Z * H.
    # pid_zh is the unique identifier for the (batch, head) pair.
    pid_zh = tl.program_id(0)
    pid_z = pid_zh // H
    pid_h = pid_zh % H

    # Offset pointers to the correct batch and head for Q, K, V, O tensors.
    # We are processing M=0, so stride_qm and stride_om are not used in indexing.
    q_offset = pid_z * stride_qz + pid_h * stride_qh
    k_offset = pid_z * stride_kz + pid_h * stride_kh
    v_offset = pid_z * stride_vz + pid_h * stride_vh
    o_offset = pid_z * stride_oz + pid_h * stride_oh
    
    Q_ptr = Q + q_offset
    K_ptr = K + k_offset
    V_ptr = V + v_offset
    O_ptr = O + o_offset

    # Load the single query vector. D_HEAD is assumed to be a power of two.
    offs_d = tl.arange(0, D_HEAD)
    q = tl.load(Q_ptr + offs_d * stride_qd).to(tl.float32)

    # Initialize accumulator and online softmax statistics.
    # All computations are done in float32 for numerical stability.
    acc = tl.zeros([D_HEAD], dtype=tl.float32)
    m_i = tl.full([1], -float('inf'), dtype=tl.float32) # running max
    l_i = tl.zeros([1], dtype=tl.float32) # running sum of exps

    # Loop over the key/value sequence in blocks of BLOCK_N.
    for start_n in range(0, N, BLOCK_N):
        # -- 1. Load a block of K --
        offs_n = start_n + tl.arange(0, BLOCK_N)
        mask_n = offs_n < N
        
        # Pointers to the current block of K.
        k_ptrs = K_ptr + offs_n[:, None] * stride_kn + offs_d[None, :] * stride_kd
        # Load K, masking for sequences not perfectly divisible by BLOCK_N.
        k = tl.load(k_ptrs, mask=mask_n[:, None], other=0.0)

        # -- 2. Compute scores S = Q @ K.T --
        # This is equivalent to (q.unsqueeze(0) @ k.T).T
        s = tl.sum(q[None, :] * k, 1) * sm_scale
        # Mask out-of-bound scores to -inf before softmax.
        s = tl.where(mask_n, s, -float('inf'))

        # -- 3. Online softmax update --
        # Find the new maximum score.
        m_curr = tl.max(s, 0)
        m_new = tl.maximum(m_i, m_curr)
        
        # Rescale old statistics (l_i, acc) using the new max.
        alpha = tl.exp(m_i - m_new)
        # Compute new probabilities, scaled by the new max.
        p = tl.exp(s - m_new)
        
        # Update the normalization factor.
        l_i = l_i * alpha + tl.sum(p, 0)

        # -- 4. Update accumulator --
        # Rescale the accumulator.
        acc = acc * alpha
        
        # Load the corresponding block of V.
        v_ptrs = V_ptr + offs_n[:, None] * stride_vn + offs_d[None, :] * stride_vd
        v = tl.load(v_ptrs, mask=mask_n[:, None], other=0.0)
        
        # Update accumulator with weighted V values.
        # p is cast to the dtype of V for the dot product.
        p_f16 = p.to(V.dtype.element_ty)
        # pv = p.T @ v; p is (1, BLOCK_N), v is (BLOCK_N, D_HEAD) -> pv is (1, D_HEAD)
        pv = tl.dot(p_f16[None, :], v)
        acc += tl.squeeze(pv, 0)

        # Update the running max for the next iteration.
        m_i = m_new

    # Finalize the output by dividing by the total normalization factor.
    # Add a small epsilon to l_i to avoid division by zero if all scores are -inf.
    acc = acc / (l_i + 1e-6)
    
    # Store the final result back to memory.
    tl.store(O_ptr + offs_d * stride_od, acc.to(O.dtype.element_ty))


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
    _Z, _H, N, _Dq = K.shape
    _Z_v, _H_v, _N_v, Dv = V.shape

    # This kernel is specialized for M=1 (decoding).
    assert M == 1, "This kernel only supports M=1 (decoding)."
    # For simplicity of the kernel, we assume Dq=Dv=D_HEAD.
    assert Dq == Dv, "Query and Value head dimensions must be equal."
    
    # Allocate output tensor.
    O = torch.empty((Z, H, M, Dv), device=Q.device, dtype=Q.dtype)
    
    # Softmax scaling factor.
    sm_scale = 1.0 / (Dq ** 0.5)

    # The grid is 1D, with one program instance per (batch, head) pair.
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
        sm_scale=sm_scale,
    )

    return O
"""
        return {"code": kernel_code}