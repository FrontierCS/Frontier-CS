import torch
import triton
import triton.language as tl

# The Triton kernel and flash_attn function must be defined before the Solution class
# so they can be packaged as a string.

_flash_attn_code_str = """
import torch
import triton
import triton.language as tl

@triton.autotune(
    configs=[
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 64}, num_stages=3, num_warps=4),
        triton.Config({'BLOCK_M': 256, 'BLOCK_N': 64}, num_stages=3, num_warps=8),
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 128}, num_stages=3, num_warps=8),
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 64}, num_stages=4, num_warps=4),
        triton.Config({'BLOCK_M': 64, 'BLOCK_N': 64}, num_stages=4, num_warps=4),
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 32}, num_stages=5, num_warps=4),
        triton.Config({'BLOCK_M': 64, 'BLOCK_N': 128}, num_stages=3, num_warps=4),
        triton.Config({'BLOCK_M': 256, 'BLOCK_N': 128}, num_stages=3, num_warps=8),
    ],
    key=['causal', 'M', 'N', 'Dq'],
)
@triton.jit
def _flash_attn_kernel(
    Q, K, V, O,
    s_q_z, s_q_h, s_q_m, s_q_d,
    s_k_z, s_k_h, s_k_n, s_k_d,
    s_v_z, s_v_h, s_v_n, s_v_d,
    s_o_z, s_o_h, s_o_m, s_o_d,
    Z, H, M, N, Dq,
    sm_scale,
    causal: tl.constexpr,
    BLOCK_M: tl.constexpr,
    BLOCK_N: tl.constexpr,
    BLOCK_D: tl.constexpr,
):
    # Grid and program IDs
    start_m = tl.program_id(0)
    batch_head_id = tl.program_id(1)
    
    # Decompose batch_head_id into z and h
    z_id = batch_head_id // H
    h_id = batch_head_id % H

    # Pointers to Q and O tiles
    q_offset_m = start_m * BLOCK_M + tl.arange(0, BLOCK_M)
    q_offset_d = tl.arange(0, BLOCK_D)
    q_ptrs = Q + z_id * s_q_z + h_id * s_q_h + (q_offset_m[:, None] * s_q_m + q_offset_d[None, :] * s_q_d)
    
    o_offset_m = q_offset_m
    o_offset_d = q_offset_d
    o_ptrs = O + z_id * s_o_z + h_id * s_o_h + (o_offset_m[:, None] * s_o_m + o_offset_d[None, :] * s_o_d)

    # Initialize streaming softmax statistics
    m_i = tl.full([BLOCK_M], -float('inf'), dtype=tl.float32)
    l_i = tl.zeros([BLOCK_M], dtype=tl.float32)
    acc = tl.zeros([BLOCK_M, BLOCK_D], dtype=tl.float32)

    # Load Q tile
    q_mask = q_offset_m[:, None] < M
    q = tl.load(q_ptrs, mask=q_mask, other=0.0)
    q = (q * sm_scale).to(tl.float16)

    # Base pointers for K and V
    k_base_ptr = K + z_id * s_k_z + h_id * s_k_h
    v_base_ptr = V + z_id * s_v_z + h_id * s_v_h
    
    k_offset_d = tl.arange(0, BLOCK_D)
    v_offset_d = tl.arange(0, BLOCK_D)

    # Loop over K, V blocks
    # For causal attention, we only iterate up to the current query block
    end_n = N if not causal else (start_m + 1) * BLOCK_M
    end_n = tl.minimum(end_n, N)

    for start_n in range(0, end_n, BLOCK_N):
        # -- Load K tile --
        k_offset_n = start_n + tl.arange(0, BLOCK_N)
        k_ptrs = k_base_ptr + (k_offset_d[:, None] * s_k_d + k_offset_n[None, :] * s_k_n)
        k_mask = k_offset_n[None, :] < N
        k = tl.load(k_ptrs, mask=k_mask, other=0.0)

        # -- Compute S = Q @ K.T --
        s = tl.dot(q, k)

        # -- Apply causal mask --
        if causal:
            m_range = start_m * BLOCK_M + tl.arange(0, BLOCK_M)
            n_range = start_n + tl.arange(0, BLOCK_N)
            causal_mask = m_range[:, None] >= n_range[None, :]
            s = tl.where(causal_mask, s, -float('inf'))

        # -- Streaming softmax update --
        m_ij = tl.max(s, 1)
        m_new = tl.maximum(m_i, m_ij)
        
        alpha = tl.exp(m_i - m_new)
        beta = tl.exp(s - m_new[:, None])
        
        l_new = alpha * l_i + tl.sum(beta, 1)
        
        acc = acc * alpha[:, None]
        
        m_i = m_new
        l_i = l_new
        
        # -- Load V tile and update accumulator --
        v_offset_n = start_n + tl.arange(0, BLOCK_N)
        v_ptrs = v_base_ptr + (v_offset_n[:, None] * s_v_n + v_offset_d[None, :] * s_v_d)
        v_mask = v_offset_n[:, None] < N
        v = tl.load(v_ptrs, mask=v_mask, other=0.0)
        
        beta = beta.to(tl.float16)
        acc += tl.dot(beta, v)

    # -- Final normalization and store --
    l_i_safe = tl.where(l_i == 0, 1.0, l_i)
    acc = acc / l_i_safe[:, None]

    o_mask = o_offset_m[:, None] < M
    tl.store(o_ptrs, acc.to(tl.float16), mask=o_mask)


def flash_attn(Q: torch.Tensor, K: torch.Tensor, V: torch.Tensor, causal: bool = True) -> torch.Tensor:
    Z, H, M, Dq = Q.shape
    _, _, N, Dv = V.shape
    
    assert Dq == K.shape[3] and Dq == Dv, f"Feature dimensions must match, got Dq={Dq}, Dk={K.shape[3]}, Dv={Dv}"
    assert Dq in {16, 32, 64, 128}, "Feature dimension must be one of {16, 32, 64, 128}"
    
    O = torch.empty_like(Q)

    sm_scale = 1.0 / (Dq ** 0.5)

    grid = lambda meta: (triton.cdiv(M, meta['BLOCK_M']), Z * H)

    _flash_attn_kernel[grid](
        Q, K, V, O,
        Q.stride(0), Q.stride(1), Q.stride(2), Q.stride(3),
        K.stride(0), K.stride(1), K.stride(2), K.stride(3),
        V.stride(0), V.stride(1), V.stride(2), V.stride(3),
        O.stride(0), O.stride(1), O.stride(2), O.stride(3),
        Z, H, M, N, Dq,
        sm_scale,
        causal=causal,
        BLOCK_D=Dq
    )
    
    return O
"""

class Solution:
    def solve(self, spec_path: str = None) -> dict:
        """
        Returns a dict with either:
        - {"code": "python_code_string"}
        - {"program_path": "path/to/kernel.py"}
        """
        return {"code": _flash_attn_code_str}