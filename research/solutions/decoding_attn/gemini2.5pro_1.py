class Solution:
    def solve(self, spec_path: str = None) -> dict:
        """
        Returns a dict with either:
        - {"code": "python_code_string"}
        - {"program_path": "path/to/kernel.py"}
        """
        kernel_code = r"""
import torch
import triton
import triton.language as tl


@triton.autotune(
    configs=[
        triton.Config({'BLOCK_N': 64}, num_warps=2, num_stages=4),
        triton.Config({'BLOCK_N': 128}, num_warps=2, num_stages=4),
        triton.Config({'BLOCK_N': 256}, num_warps=4, num_stages=3),
        triton.Config({'BLOCK_N': 256}, num_warps=4, num_stages=4),
        triton.Config({'BLOCK_N': 512}, num_warps=4, num_stages=3),
        triton.Config({'BLOCK_N': 512}, num_warps=8, num_stages=2),
        triton.Config({'BLOCK_N': 1024}, num_warps=8, num_stages=2),
        triton.Config({'BLOCK_N': 1024}, num_warps=8, num_stages=3),
    ],
    key=['N', 'D_HEAD_Q', 'D_HEAD_V'],
)
@triton.jit
def _decoding_attn_kernel(
    Q, K, V, O,
    stride_qz, stride_qh, stride_qm, stride_qd,
    stride_kz, stride_kh, stride_kn, stride_kd,
    stride_vz, stride_vh, stride_vn, stride_vd,
    stride_oz, stride_oh, stride_om, stride_od,
    Z, H, N,
    D_HEAD_Q: tl.constexpr,
    D_HEAD_V: tl.constexpr,
    BLOCK_N: tl.constexpr,
):
    # This kernel computes attention for a single query (M=1) against a sequence of keys/values.
    # Each program instance handles one head for one batch item.
    program_id = tl.program_id(0)
    head_idx = program_id % H
    batch_idx = program_id // H

    # Pointers to the start of the relevant tensors for this head and batch
    q_offset = batch_idx * stride_qz + head_idx * stride_qh
    Q_ptr = Q + q_offset
    k_offset = batch_idx * stride_kz + head_idx * stride_kh
    K_ptr = K + k_offset
    v_offset = batch_idx * stride_vz + head_idx * stride_vh
    V_ptr = V + v_offset
    o_offset = batch_idx * stride_oz + head_idx * stride_oh
    O_ptr = O + o_offset

    # Load the query vector. It's of size D_HEAD_Q.
    q_d_offsets = tl.arange(0, D_HEAD_Q)
    q = tl.load(Q_ptr + q_d_offsets * stride_qd, mask=q_d_offsets < D_HEAD_Q)

    # Online softmax statistics and output accumulator, use float32 for precision.
    m = -float('inf')
    l = 0.0
    acc = tl.zeros([D_HEAD_V], dtype=tl.float32)

    # Attention scaling factor
    sm_scale = 1.0 / (D_HEAD_Q ** 0.5)

    # Main loop over the sequence length N in blocks of BLOCK_N
    for start_n in range(0, N, BLOCK_N):
        # -- 1. Compute scores S = Q @ K^T --
        n_offsets = start_n + tl.arange(0, BLOCK_N)
        n_mask = n_offsets < N

        # Load a block of K vectors
        k_d_offsets = tl.arange(0, D_HEAD_Q)
        k_ptrs = K_ptr + (n_offsets[:, None] * stride_kn + k_d_offsets[None, :] * stride_kd)
        k = tl.load(k_ptrs, mask=n_mask[:, None] & (k_d_offsets[None, :] < D_HEAD_Q))

        # Compute dot products: q is (D_HEAD_Q), k is (BLOCK_N, D_HEAD_Q) -> s is (BLOCK_N)
        s = tl.sum(q[None, :] * k, axis=1) * sm_scale
        
        # -- 2. Online softmax update --
        # Find current block's max score, masking out padded values
        m_curr = tl.max(tl.where(n_mask, s, -float('inf')), axis=0)
        
        # Update global max
        m_new = tl.maximum(m, m_curr)
        
        # Rescale accumulator and sum of exps based on new max
        alpha = tl.exp(m - m_new)
        acc = acc * alpha
        l = l * alpha
        
        # Compute probabilities for the current block
        p = tl.exp(s - m_new)
        p = tl.where(n_mask, p, 0.0)
        
        # Update sum of exps (denominator)
        l += tl.sum(p, axis=0)
        
        # Update global max
        m = m_new
        
        # -- 3. Update output O = P @ V --
        # Load a block of V vectors
        v_d_offsets = tl.arange(0, D_HEAD_V)
        v_ptrs = V_ptr + (n_offsets[:, None] * stride_vn + v_d_offsets[None, :] * stride_vd)
        v = tl.load(v_ptrs, mask=n_mask[:, None] & (v_d_offsets[None, :] < D_HEAD_V))
        
        # Update accumulator: p is (BLOCK_N), v is (BLOCK_N, D_HEAD_V) -> p^T @ V
        acc += tl.sum(p[:, None] * v, axis=0)

    # -- Final normalization and store --
    l = tl.where(l == 0, 1.0, l)
    acc = acc / l

    # Store the final output vector
    o_d_offsets = tl.arange(0, D_HEAD_V)
    o_ptrs = O_ptr + o_d_offsets * stride_od
    tl.store(o_ptrs, acc.to(tl.float16), mask=o_d_offsets < D_HEAD_V)


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
    # Input tensor shapes
    Z, H, M, Dq = Q.shape
    _, _, N, _ = K.shape
    _, _, _, Dv = V.shape
    
    # Shape constraints
    assert M == 1, "This kernel is optimized for decoding (M=1)"
    
    # Output tensor
    O = torch.empty((Z, H, M, Dv), device=Q.device, dtype=Q.dtype)
    
    # Execution grid: one program per head per batch element
    grid = (Z * H,)
    
    # Launch the kernel
    _decoding_attn_kernel[grid](
        Q, K, V, O,
        Q.stride(0), Q.stride(1), Q.stride(2), Q.stride(3),
        K.stride(0), K.stride(1), K.stride(2), K.stride(3),
        V.stride(0), V.stride(1), V.stride(2), V.stride(3),
        O.stride(0), O.stride(1), O.stride(2), O.stride(3),
        Z, H, N,
        D_HEAD_Q=Dq,
        D_HEAD_V=Dv,
    )
    
    return O
"""
        return {"code": kernel_code}