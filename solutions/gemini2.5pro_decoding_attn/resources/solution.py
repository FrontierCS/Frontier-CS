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
        triton.Config({'BLOCK_N': 64}, num_warps=2, num_stages=2),
        triton.Config({'BLOCK_N': 64}, num_warps=4, num_stages=2),
        triton.Config({'BLOCK_N': 128}, num_warps=2, num_stages=2),
        triton.Config({'BLOCK_N': 128}, num_warps=4, num_stages=2),
        triton.Config({'BLOCK_N': 256}, num_warps=2, num_stages=2),
        triton.Config({'BLOCK_N': 256}, num_warps=4, num_stages=2),
        triton.Config({'BLOCK_N': 256}, num_warps=8, num_stages=1),
        triton.Config({'BLOCK_N': 512}, num_warps=4, num_stages=1),
        triton.Config({'BLOCK_N': 512}, num_warps=8, num_stages=1),
    ],
    key=['N', 'Dq', 'Dv'],
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
    # This kernel computes attention for a single query (M=1) against a sequence of keys/values.
    # Each program instance handles one attention head. The grid is 1D, with size Z * H.
    z_h_idx = tl.program_id(0)
    z_idx = z_h_idx // H
    h_idx = z_h_idx % H

    # Pointers to the start of the data for the current head.
    q_ptr = Q + z_idx * stride_qz + h_idx * stride_qh
    k_ptr = K + z_idx * stride_kz + h_idx * stride_kh
    v_ptr = V + z_idx * stride_vz + h_idx * stride_vh
    o_ptr = O + z_idx * stride_oz + h_idx * stride_oh

    # Load the query vector. It's small and will be reused, so it stays in registers/SRAM.
    offs_d = tl.arange(0, Dq)
    q = tl.load(q_ptr + offs_d * stride_qd).to(tl.float32)
    
    # Initialize accumulators for the online softmax algorithm.
    # All computations are done in float32 for numerical stability.
    acc = tl.zeros([Dv], dtype=tl.float32)
    m_i = -float("inf")
    l_i = 0.0

    sm_scale = 1.0 / (Dq ** 0.5)

    # Loop over the key/value sequence in blocks of size BLOCK_N.
    offs_n = tl.arange(0, BLOCK_N)
    for start_n in range(0, N, BLOCK_N):
        # --- Load a block of K ---
        current_offs_n = start_n + offs_n
        k_ptrs = k_ptr + (current_offs_n[:, None] * stride_kn + offs_d[None, :] * stride_kd)
        mask_n = current_offs_n < N
        k = tl.load(k_ptrs, mask=mask_n[:, None], other=0.0)

        # --- Compute scores S = Q @ K.T ---
        s_mat = tl.dot(q, tl.trans(k))
        s = tl.view(s_mat, [BLOCK_N]) * sm_scale
        s = tl.where(mask_n, s, -float("inf"))

        # --- Online Softmax update ---
        m_i_new = tl.maximum(m_i, tl.max(s, 0))
        p = tl.exp(s - m_i_new)
        l_i_new = l_i * tl.exp(m_i - m_i_new) + tl.sum(p, 0)

        # --- Load a block of V ---
        offs_dv = tl.arange(0, Dv)
        v_ptrs = v_ptr + (current_offs_n[:, None] * stride_vn + offs_dv[None, :] * stride_vd)
        v = tl.load(v_ptrs, mask=mask_n[:, None], other=0.0)

        # --- Update the output accumulator ---
        l_old_scaled = l_i * tl.exp(m_i - m_i_new)
        acc_scale = l_old_scaled / l_i_new
        acc = acc * acc_scale
        
        p_typed = p.to(v.dtype)
        acc_update_mat = tl.dot(p_typed, v)
        acc += tl.view(acc_update_mat, [Dv]) / l_i_new
        
        l_i = l_i_new
        m_i = m_i_new

    # --- Store the final output ---
    o_ptrs = o_ptr + tl.arange(0, Dv) * stride_od
    tl.store(o_ptrs, acc.to(o_ptr.dtype.element_ty))


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
    
    assert M == 1, "This kernel is specialized for M=1 (decoding)."

    O = torch.empty((Z, H, M, Dv), device=Q.device, dtype=Q.dtype)

    # Each program instance computes attention for one head.
    grid = (Z * H,)
    
    _decoding_attn_kernel[grid](
        Q, K, V, O,
        Q.stride(0), Q.stride(1), Q.stride(2), Q.stride(3),
        K.stride(0), K.stride(1), K.stride(2), K.stride(3),
        V.stride(0), V.stride(1), V.stride(2), V.stride(3),
        O.stride(0), O.stride(1), O.stride(2), O.stride(3),
        Z, H, N,
        Dq=Dq, Dv=Dv
    )
    
    return O
"""
        return {"code": kernel_code}
