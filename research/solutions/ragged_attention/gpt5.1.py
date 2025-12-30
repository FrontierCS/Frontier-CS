import math

KERNEL_CODE = """
import math
import torch
import triton
import triton.language as tl

@triton.jit
def _ragged_attn_fwd(
    Q, K, V, ROW_LENS, O,
    M,
    stride_qm, stride_qd,
    stride_kn, stride_kd,
    stride_vn, stride_vd,
    stride_om, stride_od,
    SCALE,
    BLOCK_M: tl.constexpr,
    BLOCK_N: tl.constexpr,
    N_CTX: tl.constexpr,
    HEAD_DIM: tl.constexpr,
    DVALUE: tl.constexpr,
):
    pid_m = tl.program_id(0)
    offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
    mask_m = offs_m < M

    offs_d = tl.arange(0, HEAD_DIM)
    q_ptrs = Q + offs_m[:, None] * stride_qm + offs_d[None, :] * stride_qd
    q = tl.load(q_ptrs, mask=mask_m[:, None], other=0.0)
    q = q.to(tl.float32)

    row_lens = tl.load(ROW_LENS + offs_m, mask=mask_m, other=0)
    row_lens = row_lens.to(tl.int32)

    m_i = tl.full([BLOCK_M], -float('inf'), tl.float32)
    l_i = tl.zeros([BLOCK_M], tl.float32)
    acc = tl.zeros([BLOCK_M, DVALUE], tl.float32)

    offs_v = tl.arange(0, DVALUE)

    for start_n in range(0, N_CTX, BLOCK_N):
        offs_n = start_n + tl.arange(0, BLOCK_N)
        mask_n = offs_n < N_CTX

        k_ptrs = K + offs_n[None, :] * stride_kn + offs_d[:, None] * stride_kd
        k = tl.load(k_ptrs, mask=mask_n[None, :], other=0.0)
        k = k.to(tl.float32)

        scores = tl.dot(q, k) * SCALE

        len_broadcast = row_lens[:, None]
        mask_len = offs_n[None, :] < len_broadcast
        mask_scores = mask_m[:, None] & mask_len & mask_n[None, :]
        scores = tl.where(mask_scores, scores, -float('inf'))

        current_max = tl.max(scores, axis=1)
        m_i_new = tl.maximum(m_i, current_max)
        alpha = tl.exp(m_i - m_i_new)

        scores_shifted = scores - m_i_new[:, None]
        exp_scores = tl.exp(scores_shifted)
        l_i_new = l_i * alpha + tl.sum(exp_scores, axis=1)

        v_ptrs = V + offs_n[:, None] * stride_vn + offs_v[None, :] * stride_vd
        v = tl.load(v_ptrs, mask=mask_n[:, None], other=0.0)
        v = v.to(tl.float32)

        contrib = tl.dot(exp_scores.to(tl.float32), v)

        acc = acc * alpha[:, None] + contrib
        m_i = m_i_new
        l_i = l_i_new

    o = acc / l_i[:, None]
    o = o.to(tl.float16)
    o_ptrs = O + offs_m[:, None] * stride_om + offs_v[None, :] * stride_od
    tl.store(o_ptrs, o, mask=mask_m[:, None])

def ragged_attn(Q: torch.Tensor, K: torch.Tensor, V: torch.Tensor, row_lens: torch.Tensor) -> torch.Tensor:
    assert Q.is_cuda and K.is_cuda and V.is_cuda and row_lens.is_cuda
    assert Q.dtype == torch.float16 and K.dtype == torch.float16 and V.dtype == torch.float16
    M, D = Q.shape
    N, Dk = K.shape
    assert D == Dk
    Nv, Dv = V.shape
    assert Nv == N
    assert row_lens.shape[0] == M

    row_lens_i32 = row_lens.to(torch.int32)
    row_lens_i32 = row_lens_i32.contiguous()

    O = torch.empty((M, Dv), device=Q.device, dtype=torch.float16)

    BLOCK_M = 64
    BLOCK_N = 64

    scale = 1.0 / math.sqrt(D)

    grid = lambda META: (triton.cdiv(M, META["BLOCK_M"]),)

    _ragged_attn_fwd[grid](
        Q, K, V, row_lens_i32, O,
        M,
        Q.stride(0), Q.stride(1),
        K.stride(0), K.stride(1),
        V.stride(0), V.stride(1),
        O.stride(0), O.stride(1),
        scale,
        BLOCK_M=BLOCK_M,
        BLOCK_N=BLOCK_N,
        N_CTX=N,
        HEAD_DIM=D,
        DVALUE=Dv,
        num_warps=4,
        num_stages=2,
    )

    return O
"""

exec(KERNEL_CODE, globals())

class Solution:
    def solve(self, spec_path: str = None) -> dict:
        return {"code": KERNEL_CODE}