import torch
import triton
import triton.language as tl


@triton.jit
def _ragged_attn_fwd(
    Q, K, V, ROW_LENS, O,
    M, D, DV,
    stride_qm, stride_qd,
    stride_km, stride_kd,
    stride_vm, stride_vd,
    stride_om, stride_od,
    stride_rl,
    sm_scale,
    N_CTX: tl.constexpr,
    BLOCK_M: tl.constexpr,
    BLOCK_N: tl.constexpr,
    BLOCK_D: tl.constexpr,
    BLOCK_DV: tl.constexpr,
):
    pid_m = tl.program_id(0)
    offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
    mask_m = offs_m < M

    # Load row lengths for ragged masking
    row_lens = tl.load(
        ROW_LENS + offs_m * stride_rl,
        mask=mask_m,
        other=0,
    )
    row_lens = row_lens.to(tl.int32)

    # Offsets for feature dimensions
    offs_d = tl.arange(0, BLOCK_D)
    mask_d = offs_d < D

    offs_dv = tl.arange(0, BLOCK_DV)
    mask_dv = offs_dv < DV

    # Load queries [BM, D]
    q = tl.load(
        Q + offs_m[:, None] * stride_qm + offs_d[None, :] * stride_qd,
        mask=mask_m[:, None] & mask_d[None, :],
        other=0.0,
    )
    q = q.to(tl.float32)

    # Streaming softmax state
    m_i = tl.full((BLOCK_M,), -float("inf"), dtype=tl.float32)
    l_i = tl.zeros((BLOCK_M,), dtype=tl.float32)
    acc = tl.zeros((BLOCK_M, BLOCK_DV), dtype=tl.float32)

    for start_n in range(0, N_CTX, BLOCK_N):
        offs_n = start_n + tl.arange(0, BLOCK_N)
        mask_n = offs_n < N_CTX

        # Load keys [BN, D]
        k = tl.load(
            K + offs_n[:, None] * stride_km + offs_d[None, :] * stride_kd,
            mask=mask_n[:, None] & mask_d[None, :],
            other=0.0,
        )
        k = k.to(tl.float32)

        # Load values [BN, DV]
        v = tl.load(
            V + offs_n[:, None] * stride_vm + offs_dv[None, :] * stride_vd,
            mask=mask_n[:, None] & mask_dv[None, :],
            other=0.0,
        )
        v = v.to(tl.float32)

        # Attention scores [BM, BN]
        scores = tl.dot(q, tl.trans(k)) * sm_scale

        # Ragged + bounds mask: j < row_lens[i], and within N, and valid row
        valid_k = offs_n[None, :] < row_lens[:, None]
        mask_scores = valid_k & mask_n[None, :] & mask_m[:, None]
        scores = tl.where(mask_scores, scores, -float("inf"))

        # Streaming softmax update
        row_max = tl.max(scores, axis=1)
        m_i_new = tl.maximum(m_i, row_max)

        scores_shifted = scores - m_i_new[:, None]
        p = tl.exp(scores_shifted)
        l_i_new = tl.sum(p, axis=1)

        alpha = tl.exp(m_i - m_i_new)
        l_i = l_i * alpha + l_i_new

        acc = acc * alpha[:, None] + tl.dot(p, v)

        m_i = m_i_new

    out = acc / l_i[:, None]
    out = out.to(tl.float16)

    tl.store(
        O + offs_m[:, None] * stride_om + offs_dv[None, :] * stride_od,
        out,
        mask=mask_m[:, None] & mask_dv[None, :],
    )


def ragged_attn(Q: torch.Tensor, K: torch.Tensor, V: torch.Tensor, row_lens: torch.Tensor) -> torch.Tensor:
    assert Q.is_cuda and K.is_cuda and V.is_cuda, "Q, K, V must be CUDA tensors"
    assert Q.dtype == torch.float16 and K.dtype == torch.float16 and V.dtype == torch.float16, "Q, K, V must be float16"
    assert Q.shape[1] == K.shape[1], "Q and K must have same feature dimension"
    assert K.shape[0] == V.shape[0], "K and V must have same number of rows"
    assert row_lens.shape[0] == Q.shape[0], "row_lens length must match number of query rows"

    M, D = Q.shape
    N = K.shape[0]
    DV = V.shape[1]

    Q_ = Q.contiguous()
    K_ = K.contiguous()
    V_ = V.contiguous()

    # Ensure row_lens is on device and int32
    row_lens_ = row_lens.to(device=Q.device)
    if row_lens_.dtype != torch.int32:
        row_lens_ = row_lens_.to(torch.int32)
    row_lens_ = row_lens_.contiguous()

    O = torch.empty((M, DV), device=Q.device, dtype=torch.float16)

    BLOCK_M = 64
    BLOCK_N = 64
    BLOCK_D = 64
    BLOCK_DV = 64

    assert D <= BLOCK_D and DV <= BLOCK_DV, "D and DV must be <= 64 for this kernel"

    sm_scale = 1.0 / (D ** 0.5)

    grid = lambda META: (triton.cdiv(M, META["BLOCK_M"]),)

    _ragged_attn_fwd[grid](
        Q_, K_, V_, row_lens_, O,
        M, D, DV,
        Q_.stride(0), Q_.stride(1),
        K_.stride(0), K_.stride(1),
        V_.stride(0), V_.stride(1),
        O.stride(0), O.stride(1),
        row_lens_.stride(0),
        sm_scale,
        N_CTX=N,
        BLOCK_M=BLOCK_M,
        BLOCK_N=BLOCK_N,
        BLOCK_D=BLOCK_D,
        BLOCK_DV=BLOCK_DV,
        num_warps=4,
        num_stages=2,
    )

    return O


class Solution:
    def solve(self, spec_path: str = None) -> dict:
        import os
        import sys
        import inspect

        try:
            path = os.path.abspath(__file__)
            with open(path, "r") as f:
                code = f.read()
        except Exception:
            module = sys.modules[__name__]
            code = inspect.getsource(module)
        return {"code": code}