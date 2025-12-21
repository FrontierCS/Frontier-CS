class Solution:
    def solve(self, spec_path: str = None) -> dict:
        code = """
import torch
import triton
import triton.language as tl
import math

@triton.jit
def kernel(
    Q, K, V, row_lens, O,
    stride_q_row, stride_q_col,
    stride_k_row, stride_k_col,
    stride_v_row, stride_v_col,
    stride_row_lens,
    stride_o_row, stride_o_col,
    M, D, Dv, scale,
    BLOCK_N: tl.constexpr
):
    pid = tl.program_id(0)
    if pid >= M:
        return
    i = pid
    L = tl.load(row_lens + i * stride_row_lens, dtype=tl.int32)
    # Load q
    q_offsets = tl.arange(0, D)
    q_ptrs = Q + i * stride_q_row + q_offsets * stride_q_col
    q = tl.load(q_ptrs, mask=q_offsets < D).to(tl.float32)
    # Initialize streaming softmax
    m = -1e9 * tl.ones([], dtype=tl.float32)
    l = tl.zeros([], dtype=tl.float32)
    o = tl.zeros([Dv], dtype=tl.float32)
    # Loop over key blocks
    off = 0
    while off < L:
        j_offsets = tl.arange(0, BLOCK_N)
        mask_j = (off + j_offsets) < L
        # Load k_block
        j_bytes = j_offsets * stride_k_row
        d_bytes = tl.arange(0, D) * stride_k_col
        k_ptrs = K + off * stride_k_row + j_bytes[:, None] + d_bytes[None, :]
        mask_k = mask_j[:, None] & (tl.arange(0, D)[None, :] < D)
        k_block = tl.load(k_ptrs, mask=mask_k, other=0.0).to(tl.float32)
        # Compute scores
        scores = tl.dot(q[None, :], k_block) * scale
        s = scores[0]
        s = tl.where(mask_j, s, -1e4 * tl.ones_like(s))
        # Load v_block
        j_bytes_v = j_offsets * stride_v_row
        dv_bytes = tl.arange(0, Dv) * stride_v_col
        v_ptrs = V + off * stride_v_row + j_bytes_v[:, None] + dv_bytes[None, :]
        mask_v = mask_j[:, None] & (tl.arange(0, Dv)[None, :] < Dv)
        v_block = tl.load(v_ptrs, mask=mask_v, other=0.0).to(tl.float32)
        # Streaming softmax update
        m_loc = tl.max(s, 0)
        m_new = tl.maximum(m, m_loc)
        exp_old = tl.exp(m - m_new)
        exp_s = tl.exp(s - m_new)
        l_new = l * exp_old + tl.sum(exp_s)
        # New contribution
        contrib_new = tl.dot(exp_s[:, None], v_block)[0] / l_new
        # Old contribution scale
        old_scale = (l * exp_old) / l_new
        # Update o
        o = o * old_scale + contrib_new
        # Update stats
        m = m_new
        l = l_new
        # Advance
        off += BLOCK_N
    # Store o
    o_offsets = tl.arange(0, Dv)
    o_ptrs = O + i * stride_o_row + o_offsets * stride_o_col
    tl.store(o_ptrs, o.to(tl.float16), mask=o_offsets < Dv)

def ragged_attn(Q: torch.Tensor, K: torch.Tensor, V: torch.Tensor, row_lens: torch.Tensor) -> torch.Tensor:
    M, D = Q.shape
    N, _ = K.shape
    _, Dv = V.shape
    scale = 1 / math.sqrt(D)
    O = torch.empty((M, Dv), dtype=Q.dtype, device=Q.device)
    row_lens = row_lens.to(torch.int32)
    element_size = torch.tensor(0, dtype=Q.dtype).element_size()
    int_size = 4
    stride_q_row = Q.stride(0) * element_size
    stride_q_col = Q.stride(1) * element_size
    stride_k_row = K.stride(0) * element_size
    stride_k_col = K.stride(1) * element_size
    stride_v_row = V.stride(0) * element_size
    stride_v_col = V.stride(1) * element_size
    stride_row_lens = row_lens.stride(0) * int_size
    stride_o_row = O.stride(0) * element_size
    stride_o_col = O.stride(1) * element_size
    BLOCK_N = 128
    grid = (M,)
    kernel[grid](
        Q, K, V, row_lens, O,
        stride_q_row, stride_q_col,
        stride_k_row, stride_k_col,
        stride_v_row, stride_v_col,
        stride_row_lens,
        stride_o_row, stride_o_col,
        M, D, Dv, scale,
        BLOCK_N=BLOCK_N
    )
    return O
"""
        return {"code": code}
