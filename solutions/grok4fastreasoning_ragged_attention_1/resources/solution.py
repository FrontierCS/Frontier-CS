import torch
import triton
import triton.language as tl
import math

@triton.jit
def _ragged_attn_kernel(
    Q, K, V, row_lens, O,
    scale, D, Dv, M,
    BLOCK_DV: tl.constexpr,
    BLOCK_K: tl.constexpr
):
    i = tl.program_id(0)
    if i >= M:
        return

    l_i = tl.load(row_lens + i)

    local_idx = tl.arange(0, BLOCK_DV)

    # Load Q_i
    q_base = Q + i * D
    q_ptrs = q_base + local_idx
    q_mask = local_idx < D
    q = tl.load(q_ptrs, mask=q_mask, other=0.0).to(tl.float32)

    # Initialize streaming softmax
    m = -float('inf')
    l = 0.0
    o_local = 0.0

    j = 0
    N = K.shape[0]  # Assuming K.shape accessible, but pass N if needed; here assume

    # Full blocks
    while j + BLOCK_K <= l_i:
        for jj in range(0, BLOCK_K):
            j_this = j + jj
            # Load K row
            k_base = K + j_this * D
            k_ptrs = k_base + local_idx
            k = tl.load(k_ptrs, mask=local_idx < D, other=0.0).to(tl.float32)
            partial = q * k
            score = tl.sum(partial) * scale

            # Load V row
            v_base = V + j_this * Dv
            v_ptrs = v_base + local_idx
            v = tl.load(v_ptrs, mask=local_idx < Dv, other=0.0).to(tl.float32)

            # Streaming update
            m_new = tl.maximum(m, score)
            exp_old = tl.exp(m - m_new)
            exp_score = tl.exp(score - m_new)
            l_new = l * exp_old + exp_score
            o_local = o_local * exp_old + exp_score * v
            m = m_new
            l = l_new
        j += BLOCK_K

    # Remaining
    if j < l_i:
        bk = l_i - j
        for jj in range(0, bk):
            j_this = j + jj
            # Load K row
            k_base = K + j_this * D
            k_ptrs = k_base + local_idx
            k = tl.load(k_ptrs, mask=local_idx < D, other=0.0).to(tl.float32)
            partial = q * k
            score = tl.sum(partial) * scale

            # Load V row
            v_base = V + j_this * Dv
            v_ptrs = v_base + local_idx
            v = tl.load(v_ptrs, mask=local_idx < Dv, other=0.0).to(tl.float32)

            # Streaming update
            m_new = tl.maximum(m, score)
            exp_old = tl.exp(m - m_new)
            exp_score = tl.exp(score - m_new)
            l_new = l * exp_old + exp_score
            o_local = o_local * exp_old + exp_score * v
            m = m_new
            l = l_new

    # Finalize
    o_final = tl.where(l == 0.0, 0.0, o_local / l)
    # Store
    o_base = O + i * Dv
    o_ptrs = o_base + local_idx
    tl.store(o_ptrs, o_final.to(tl.float16), mask=local_idx < Dv)

def ragged_attn(Q: torch.Tensor, K: torch.Tensor, V: torch.Tensor, row_lens: torch.Tensor) -> torch.Tensor:
    assert Q.is_cuda and K.is_cuda and V.is_cuda and row_lens.is_cuda
    M, D = Q.shape
    N, _ = K.shape
    _, Dv = V.shape
    scale = 1 / math.sqrt(D)
    O = torch.empty((M, Dv), dtype=torch.float16, device=Q.device)

    BLOCK_DV = 64
    BLOCK_K = 64

    grid = (M,)
    _ragged_attn_kernel[grid](
        Q, K, V, row_lens, O,
        scale, D, Dv, M,
        BLOCK_DV=BLOCK_DV,
        BLOCK_K=BLOCK_K
    )
    return O

class Solution:
    def solve(self, spec_path: str = None) -> dict:
        return {"code": "Implemented in the module above; use ragged_attn directly."}
