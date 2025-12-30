import torch
import triton

class Solution:
    def solve(self, spec_path: str = None) -> dict:
        kernel_code = """
import torch
import triton
import triton.language as tl

@triton.autotune(
    configs=[
        # Basic configurations
        triton.Config({'BLOCK_M': 16, 'BLOCK_N': 64, 'BLOCK_D': 64, 'BLOCK_DV': 64}, num_warps=4, num_stages=3),
        triton.Config({'BLOCK_M': 32, 'BLOCK_N': 64, 'BLOCK_D': 64, 'BLOCK_DV': 64}, num_warps=4, num_stages=3),
        triton.Config({'BLOCK_M': 64, 'BLOCK_N': 64, 'BLOCK_D': 64, 'BLOCK_DV': 64}, num_warps=4, num_stages=4),
        
        # Configurations with larger BLOCK_N
        triton.Config({'BLOCK_M': 16, 'BLOCK_N': 128, 'BLOCK_D': 64, 'BLOCK_DV': 64}, num_warps=4, num_stages=2),
        triton.Config({'BLOCK_M': 32, 'BLOCK_N': 128, 'BLOCK_D': 64, 'BLOCK_DV': 64}, num_warps=8, num_stages=3),
        triton.Config({'BLOCK_M': 64, 'BLOCK_N': 128, 'BLOCK_D': 64, 'BLOCK_DV': 64}, num_warps=8, num_stages=3),

        # Configurations with larger BLOCK_M
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 32, 'BLOCK_D': 64, 'BLOCK_DV': 64}, num_warps=4, num_stages=4),
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 64, 'BLOCK_D': 64, 'BLOCK_DV': 64}, num_warps=8, num_stages=3),

        # Configurations with smaller BLOCK_N for better cache usage on small row_lens
        triton.Config({'BLOCK_M': 32, 'BLOCK_N': 32, 'BLOCK_D': 64, 'BLOCK_DV': 64}, num_warps=4, num_stages=5),
        triton.Config({'BLOCK_M': 64, 'BLOCK_N': 32, 'BLOCK_D': 64, 'BLOCK_DV': 64}, num_warps=4, num_stages=5),
    ],
    key=['M', 'N', 'D', 'Dv'],
)
@triton.jit
def _ragged_kernel(
    Q, K, V, O,
    ROW_LENS,
    stride_qm, stride_qd,
    stride_kn, stride_kd,
    stride_vn, stride_vdv,
    stride_om, stride_odv,
    M, N, D, Dv,
    scale,
    BLOCK_M: tl.constexpr, BLOCK_N: tl.constexpr, BLOCK_D: tl.constexpr, BLOCK_DV: tl.constexpr,
):
    """
    Triton kernel for ragged attention.
    Each program instance computes a BLOCK_M block of rows of the output O.
    """
    # 1. Program and offset setup
    pid_m = tl.program_id(axis=0)
    
    offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
    offs_d = tl.arange(0, BLOCK_D)
    offs_dv = tl.arange(0, BLOCK_DV)

    # 2. Pointer setup for Q
    q_ptrs = Q + offs_m[:, None] * stride_qm + offs_d[None, :] * stride_qd
    
    # 3. Initialize streaming softmax statistics
    m_i = tl.full([BLOCK_M], -float('inf'), dtype=tl.float32)
    l_i = tl.zeros([BLOCK_M], dtype=tl.float32)
    acc = tl.zeros([BLOCK_M, BLOCK_DV], dtype=tl.float32)

    # 4. Load row-specific lengths and query block
    m_mask = offs_m < M
    row_lens_ptrs = ROW_LENS + offs_m
    block_row_lens = tl.load(row_lens_ptrs, mask=m_mask, other=0)

    # Load Q block once, it's used for all key blocks
    q = tl.load(q_ptrs, mask=m_mask[:, None])

    # 5. Loop over key/value blocks
    for start_n in range(0, N, BLOCK_N):
        offs_n = start_n + tl.arange(0, BLOCK_N)
        
        # Pointers to K and V blocks
        k_ptrs = K + offs_n[:, None] * stride_kn + offs_d[None, :] * stride_kd
        v_ptrs = V + offs_n[:, None] * stride_vn + offs_dv[None, :] * stride_vdv
        
        # Load K and V blocks with boundary checks
        n_mask = offs_n < N
        k = tl.load(k_ptrs, mask=n_mask[:, None], other=0.0)
        v = tl.load(v_ptrs, mask=n_mask[:, None], other=0.0)
        
        # Compute attention scores (Q @ K.T)
        s = tl.dot(q, tl.trans(k)) * scale
        
        # Apply the ragged mask
        ragged_mask = (offs_n[None, :] < block_row_lens[:, None])
        s = tl.where(ragged_mask, s, -float('inf'))

        # --- Streaming softmax update ---
        # 6. Find new max score for the block
        m_block = tl.max(s, axis=1)
        m_new = tl.maximum(m_i, m_block)
        
        # 7. Numerically stable update of accumulator and normalizer
        # Correct for m_new = -inf to avoid nan from exp(-inf - (-inf))
        is_m_new_inf = m_new == -float('inf')
        safe_m_new = tl.where(is_m_new_inf, 0.0, m_new)
        
        alpha = tl.exp(m_i - safe_m_new)
        p = tl.exp(s - safe_m_new[:, None])
        
        # Rescale and update accumulator
        acc = acc * alpha[:, None]
        p_casted = p.to(V.dtype)
        acc += tl.dot(p_casted, v)
        
        # Update normalizer
        l_i = l_i * alpha + tl.sum(p, axis=1)
        
        # Update max
        m_i = m_new

    # 8. Final normalization and store
    l_i_inv = 1.0 / l_i
    # Handle cases where all scores were -inf (l_i=0) to avoid 1/0 -> inf
    l_i_inv = tl.where(l_i > 0, l_i_inv, 0.0)
    acc = acc * l_i_inv[:, None]
    
    # Pointers to output block
    o_ptrs = O + offs_m[:, None] * stride_om + offs_dv[None, :] * stride_odv
    tl.store(o_ptrs, acc.to(tl.float16), mask=m_mask[:, None])

def ragged_attn(Q: torch.Tensor, K: torch.Tensor, V: torch.Tensor, row_lens: torch.Tensor) -> torch.Tensor:
    """
    Ragged attention computation.
    
    Args:
        Q: Query tensor of shape (M, D) - query features (float16)
        K: Key tensor of shape (N, D) - key features (float16)
        V: Value tensor of shape (N, Dv) - value features (float16)
        row_lens: Row lengths tensor of shape (M,) - number of valid K/V rows per Q row (int32 or int64)
    
    Returns:
        Output tensor of shape (M, Dv) - attention output (float16)
    """
    M, D = Q.shape
    N, D_k = K.shape
    N_v, Dv = V.shape
    
    # Input validation
    assert D == D_k, f"Q and K must have the same feature dimension D, but got {D} and {D_k}"
    assert N == N_v, f"K and V must have the same sequence length N, but got {N} and {N_v}"
    assert row_lens.shape == (M,), f"row_lens must have shape (M,), but got {row_lens.shape}"
    assert Q.device.type == 'cuda' and K.device.type == 'cuda' and V.device.type == 'cuda', "Inputs must be CUDA tensors"
    
    # This kernel is autotuned for D=Dv=64
    if D != 64 or Dv != 64:
        print(f"Warning: This kernel is optimized for D=64, Dv=64, but got D={D}, Dv={Dv}. Performance may be suboptimal.")

    # Output tensor
    O = torch.empty((M, Dv), device=Q.device, dtype=torch.float16)
    
    # Attention scale
    scale = D ** -0.5
    
    # Kernel grid
    grid = lambda META: (triton.cdiv(M, META['BLOCK_M']),)
    
    # Launch the Triton kernel
    _ragged_kernel[grid](
        Q, K, V, O,
        row_lens,
        Q.stride(0), Q.stride(1),
        K.stride(0), K.stride(1),
        V.stride(0), V.stride(1),
        O.stride(0), O.stride(1),
        M, N, D, Dv,
        scale,
    )
    
    return O

"""
        return {"code": kernel_code}