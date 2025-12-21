import torch

class Solution:
    def solve(self, spec_path: str = None) -> dict:
        # Note: The evaluation environment executes the code returned in the "code" key.
        # All necessary imports and functions must be self-contained in this string.
        
        kernel_code = """
import torch
import triton
import triton.language as tl

@triton.autotune(
    configs=[
        triton.Config({'BLOCK_SIZE_N': 32}, num_stages=4, num_warps=2),
        triton.Config({'BLOCK_SIZE_N': 64}, num_stages=4, num_warps=4),
        triton.Config({'BLOCK_SIZE_N': 128}, num_stages=4, num_warps=4),
        triton.Config({'BLOCK_SIZE_N': 256}, num_stages=2, num_warps=8),
        triton.Config({'BLOCK_SIZE_N': 512}, num_stages=1, num_warps=8),
    ],
    key=['N', 'Dq', 'Dv'],
)
@triton.jit
def _decoding_attn_kernel(
    Q_ptr, K_ptr, V_ptr, O_ptr,
    stride_qz, stride_qh, stride_qm, stride_qd,
    stride_kz, stride_kh, stride_kn, stride_kd,
    stride_vz, stride_vh, stride_vn, stride_vd,
    stride_oz, stride_oh, stride_om, stride_od,
    Z, H, N, M, Dq, Dv,
    BLOCK_SIZE_N: tl.constexpr,
    BLOCK_D: tl.constexpr,
    BLOCK_DV: tl.constexpr,
):
    \"\"\"
    Triton kernel for decoding attention.
    Each program instance computes the attention output for one head.
    The grid is (Z, H).
    \"\"\"
    # Program IDs for batch and head dimensions
    pid_z = tl.program_id(0)
    pid_h = tl.program_id(1)

    # Pointers to the current head's data
    q_base_ptr = Q_ptr + pid_z * stride_qz + pid_h * stride_qh
    k_base_ptr = K_ptr + pid_z * stride_kz + pid_h * stride_kh
    v_base_ptr = V_ptr + pid_z * stride_vz + pid_h * stride_vh
    o_base_ptr = O_ptr + pid_z * stride_oz + pid_h * stride_oh

    # Load query vector once, it's used for all key/value blocks.
    offs_d = tl.arange(0, BLOCK_D)
    q = tl.load(q_base_ptr + offs_d * stride_qd, mask=offs_d < Dq, other=0.0).to(tl.float32)

    # Initialize accumulators and online softmax statistics
    acc = tl.zeros([BLOCK_DV], dtype=tl.float32)
    m_i = -float('inf')
    l_i = 0.0
    
    # Attention scaling factor
    sm_scale = Dq**-0.5
    
    # Loop over the sequence length N in blocks
    offs_n = tl.arange(0, BLOCK_SIZE_N)
    for start_n in range(0, N, BLOCK_SIZE_N):
        current_offs_n = start_n + offs_n
        
        # --- Load K block ---
        k_offs = current_offs_n[:, None] * stride_kn + offs_d[None, :] * stride_kd
        k_mask = (current_offs_n[:, None] < N)
        k = tl.load(k_base_ptr + k_offs, mask=k_mask, other=0.0)
        
        # --- Compute scores S = Q @ K.T ---
        s_ij = tl.sum(q[None, :] * k.to(tl.float32), axis=1) * sm_scale
        # Mask out-of-bound scores
        s_ij = tl.where(current_offs_n < N, s_ij, -float('inf'))

        # --- Online softmax update ---
        m_ij = tl.max(s_ij, axis=0) # Block-wise max
        m_new = tl.maximum(m_i, m_ij) # Update overall max
        
        # Rescale previous accumulator and sum of probabilities
        alpha = tl.exp(m_i - m_new)
        acc = acc * alpha
        l_i = l_i * alpha

        # Compute new probabilities and update sum
        p_ij = tl.exp(s_ij - m_new)
        l_i += tl.sum(p_ij, axis=0)
        
        # --- Load V block ---
        offs_dv = tl.arange(0, BLOCK_DV)
        v_offs = current_offs_n[:, None] * stride_vn + offs_dv[None, :] * stride_vd
        v_mask = (current_offs_n[:, None] < N)
        v = tl.load(v_base_ptr + v_offs, mask=v_mask, other=0.0)
        
        # --- Update accumulator ---
        # p_ij is (BLOCK_SIZE_N,), v is (BLOCK_SIZE_N, Dv). dot -> (Dv,)
        # Use fp16 for V and P for dot product to leverage tensor cores
        acc += tl.dot(p_ij.to(v.dtype), v)
        
        m_i = m_new

    # Final normalization
    o = acc / l_i
    
    # --- Store output ---
    offs_dv = tl.arange(0, BLOCK_DV)
    tl.store(o_base_ptr + offs_dv * stride_od, o.to(O_ptr.dtype.element_ty), mask=offs_dv < Dv)

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

    assert M == 1, "This kernel is specialized for M=1 decoding attention."
    
    O = torch.empty((Z, H, M, Dv), dtype=Q.dtype, device=Q.device)

    # Grid dimensions are (Z, H), one program per attention head.
    grid = (Z, H)

    # Launch the Triton kernel.
    _decoding_attn_kernel[grid](
        Q, K, V, O,
        Q.stride(0), Q.stride(1), Q.stride(2), Q.stride(3),
        K.stride(0), K.stride(1), K.stride(2), K.stride(3),
        V.stride(0), V.stride(1), V.stride(2), V.stride(3),
        O.stride(0), O.stride(1), O.stride(2), O.stride(3),
        Z, H, N, M, Dq, Dv,
        BLOCK_D=Dq,
        BLOCK_DV=Dv,
    )
    
    return O

"""
        return {"code": kernel_code}
