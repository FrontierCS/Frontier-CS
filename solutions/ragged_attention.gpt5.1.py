import torch
import triton
import triton.language as tl
import math

CODE = """
import torch
import triton
import triton.language as tl
import math

@triton.jit
def _ragged_attn_kernel(
    Q_ptr, K_ptr, V_ptr, ROW_LENS_PTR, O_ptr,
    M, N, D, DV,
    stride_qm, stride_qd,
    stride_km, stride_kd,
    stride_vm, stride_vd,
    stride_om, stride_od,
    scale,
    BLOCK_M: tl.constexpr, BLOCK_N: tl.constexpr,
    BLOCK_D: tl.constexpr, BLOCK_DV: tl.constexpr,
):
    pid_m = tl.program_id(0)
    offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
    mask_m = offs_m < M

    # Load row lengths
    row_lens = tl.load(ROW_LENS_PTR + offs_m, mask=mask_m, other=0)
    row_lens = row_lens.to(tl.int32)

    offs_d = tl.arange(0, BLOCK_D)
    d_mask = offs_d < D

    # Load Q block [BM, D]
    q = tl.load(
        Q_ptr + offs_m[:, None] * stride_qm + offs_d[None, :] * stride_qd,
        mask=mask_m[:, None] & d_mask[None, :],
        other=0.0,
    )
    q = q.to(tl.float32)

    neg_inf = float("-inf")
    m_i = tl.full((BLOCK_M,), neg_inf, tl.float32)
    l_i = tl.zeros((BLOCK_M,), tl.float32)

    offs_dv = tl.arange(0, BLOCK_DV)
    dv_mask = offs_dv < DV
    acc = tl.zeros((BLOCK_M, BLOCK_DV), tl.float32)

    # Loop over K/V blocks along sequence length
    for start_n in range(0, N, BLOCK_N):
        offs_n = start_n + tl.arange(0, BLOCK_N)
        kv_mask = offs_n < N

        # Load K block [BN, D]
        k = tl.load(
            K_ptr + offs_n[:, None] * stride_km + offs_d[None, :] * stride_kd,
            mask=kv_mask[:, None] & d_mask[None, :],
            other=0.0,
        )
        k = k.to(tl.float32)

        # Scores = Q @ K^T -> [BM, BN]
        scores = tl.dot(q, tl.trans(k)) * scale

        # Ragged and bounds masking
        valid_len = offs_n[None, :] < row_lens[:, None]
        valid = valid_len & kv_mask[None, :] & mask_m[:, None]
        scores = tl.where(valid, scores, neg_inf)

        # Streaming softmax update
        current_max = tl.max(scores, axis=1)
        new_m = tl.maximum(m_i, current_max)

        scores_diff = scores - new_m[:, None]
        p = tl.exp(scores_diff)
        sum_p = tl.sum(p, axis=1)

        alpha = tl.exp(m_i - new_m)
        l_i = l_i * alpha + sum_p

        # Load V block [BN, DV]
        v = tl.load(
            V_ptr + offs_n[:, None] * stride_vm + offs_dv[None, :] * stride_vd,
            mask=kv_mask[:, None] & dv_mask[None, :],
            other=0.0,
        )
        v = v.to(tl.float32)

        # Update output accumulator
        pv = tl.dot(p, v)  # [BM, DV]
        acc = acc * alpha[:, None] + pv

        m_i = new_m

    # Normalize and write output
    inv_l = 1.0 / l_i
    inv_l = tl.where(l_i > 0.0, inv_l, 0.0)

    out = acc * inv_l[:, None]
    out = out.to(tl.float16)

    tl.store(
        O_ptr + offs_m[:, None] * stride_om + offs_dv[None, :] * stride_od,
        out,
        mask=mask_m[:, None] & dv_mask[None, :],
    )


def ragged_attn(Q: torch.Tensor, K: torch.Tensor, V: torch.Tensor, row_lens: torch.Tensor) -> torch.Tensor:
    assert Q.is_cuda and K.is_cuda and V.is_cuda, "Q, K, V must be CUDA tensors"
    assert Q.dtype == torch.float16 and K.dtype == torch.float16 and V.dtype == torch.float16, "Q, K, V must be float16"

    M, D = Q.shape
    N, Dk = K.shape
    assert Dk == D, "K must have same feature dimension as Q"

    Nv, DV = V.shape
    assert Nv == N, "V must have same number of rows as K"

    if row_lens.device != Q.device:
        row_lens = row_lens.to(Q.device)
    if row_lens.dtype != torch.int32:
        row_lens = row_lens.to(torch.int32)

    O = torch.empty((M, DV), device=Q.device, dtype=torch.float16)

    BLOCK_M = 64
    BLOCK_N = 128
    BLOCK_D = 64
    BLOCK_DV = 64

    grid = (triton.cdiv(M, BLOCK_M),)

    scale = 1.0 / math.sqrt(float(D))

    _ragged_attn_kernel[grid](
        Q, K, V, row_lens, O,
        M, N, D, DV,
        Q.stride(0), Q.stride(1),
        K.stride(0), K.stride(1),
        V.stride(0), V.stride(1),
        O.stride(0), O.stride(1),
        scale,
        BLOCK_M=BLOCK_M,
        BLOCK_N=BLOCK_N,
        BLOCK_D=BLOCK_D,
        BLOCK_DV=BLOCK_DV,
        num_warps=4,
        num_stages=2,
    )

    return O
"""

exec(CODE, globals())


class Solution:
    def solve(self, spec_path: str = None) -> dict:
        return {"code": CODE}
