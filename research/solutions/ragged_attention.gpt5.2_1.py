import math
import textwrap
import torch
import triton
import triton.language as tl


@triton.jit
def _ragged_attn_fwd_kernel(
    Q_ptr,
    K_ptr,
    V_ptr,
    O_ptr,
    ROW_LENS_ptr,
    M,
    stride_qm: tl.constexpr,
    stride_qd: tl.constexpr,
    stride_kn: tl.constexpr,
    stride_kd: tl.constexpr,
    stride_vn: tl.constexpr,
    stride_vd: tl.constexpr,
    stride_om: tl.constexpr,
    stride_od: tl.constexpr,
    SCALE: tl.constexpr,
    N: tl.constexpr,
    D: tl.constexpr,
    DV: tl.constexpr,
    BLOCK_M: tl.constexpr,
    BLOCK_N: tl.constexpr,
):
    pid_m = tl.program_id(0)

    offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
    mask_m = offs_m < M

    row_lens = tl.load(ROW_LENS_ptr + offs_m, mask=mask_m, other=0).to(tl.int32)

    offs_d = tl.arange(0, D)
    q = tl.load(
        Q_ptr + offs_m[:, None] * stride_qm + offs_d[None, :] * stride_qd,
        mask=mask_m[:, None],
        other=0.0,
    ).to(tl.float16)

    m_i = tl.full((BLOCK_M,), float("-inf"), tl.float32)
    l_i = tl.zeros((BLOCK_M,), tl.float32)
    offs_dv = tl.arange(0, DV)
    acc = tl.zeros((BLOCK_M, DV), tl.float32)

    for start_n in tl.static_range(0, N, BLOCK_N):
        offs_n = start_n + tl.arange(0, BLOCK_N)
        mask_n = offs_n < N

        k = tl.load(
            K_ptr + offs_n[:, None] * stride_kn + offs_d[None, :] * stride_kd,
            mask=mask_n[:, None],
            other=0.0,
        ).to(tl.float16)

        v = tl.load(
            V_ptr + offs_n[:, None] * stride_vn + offs_dv[None, :] * stride_vd,
            mask=mask_n[:, None],
            other=0.0,
        ).to(tl.float16)

        scores = tl.dot(q, tl.trans(k)).to(tl.float32) * SCALE

        mask_ragged = offs_n[None, :] < row_lens[:, None]
        valid = mask_m[:, None] & mask_n[None, :] & mask_ragged
        scores = tl.where(valid, scores, float("-inf"))

        m_ij = tl.max(scores, axis=1)
        m_new = tl.maximum(m_i, m_ij)

        m_new_is_neginf = m_new == float("-inf")
        scores_shift = scores - m_new[:, None]
        scores_shift = tl.where(m_new_is_neginf[:, None], float("-inf"), scores_shift)

        p = tl.exp(scores_shift)
        l_new = l_i * tl.where(m_new_is_neginf, 0.0, tl.exp(m_i - m_new)) + tl.sum(p, axis=1)

        p16 = p.to(tl.float16)
        acc = acc * tl.where(m_new_is_neginf, 0.0, tl.exp(m_i - m_new))[:, None] + tl.dot(p16, v, out_dtype=tl.float32)

        m_i = m_new
        l_i = l_new

    out = tl.where(l_i[:, None] > 0.0, acc / l_i[:, None], 0.0).to(tl.float16)
    tl.store(
        O_ptr + offs_m[:, None] * stride_om + offs_dv[None, :] * stride_od,
        out,
        mask=mask_m[:, None],
    )


def ragged_attn(Q: torch.Tensor, K: torch.Tensor, V: torch.Tensor, row_lens: torch.Tensor) -> torch.Tensor:
    assert Q.is_cuda and K.is_cuda and V.is_cuda and row_lens.is_cuda
    assert Q.dtype == torch.float16 and K.dtype == torch.float16 and V.dtype == torch.float16
    assert Q.ndim == 2 and K.ndim == 2 and V.ndim == 2 and row_lens.ndim == 1
    M, D = Q.shape
    N, Dk = K.shape
    Nv, DV = V.shape
    assert D == Dk
    assert N == Nv
    assert row_lens.shape[0] == M

    if row_lens.dtype != torch.int32:
        row_lens_i32 = row_lens.to(torch.int32)
    else:
        row_lens_i32 = row_lens

    O = torch.empty((M, DV), device=Q.device, dtype=torch.float16)

    BLOCK_M = 64
    BLOCK_N = 64
    scale = 1.0 / math.sqrt(D)

    grid = (triton.cdiv(M, BLOCK_M),)

    _ragged_attn_fwd_kernel[grid](
        Q,
        K,
        V,
        O,
        row_lens_i32,
        M,
        stride_qm=Q.stride(0),
        stride_qd=Q.stride(1),
        stride_kn=K.stride(0),
        stride_kd=K.stride(1),
        stride_vn=V.stride(0),
        stride_vd=V.stride(1),
        stride_om=O.stride(0),
        stride_od=O.stride(1),
        SCALE=scale,
        N=N,
        D=D,
        DV=DV,
        BLOCK_M=BLOCK_M,
        BLOCK_N=BLOCK_N,
        num_warps=4,
        num_stages=3,
    )
    return O


class Solution:
    def solve(self, spec_path: str = None) -> dict:
        code = textwrap.dedent(
            r"""
            import math
            import torch
            import triton
            import triton.language as tl

            @triton.jit
            def _ragged_attn_fwd_kernel(
                Q_ptr,
                K_ptr,
                V_ptr,
                O_ptr,
                ROW_LENS_ptr,
                M,
                stride_qm: tl.constexpr,
                stride_qd: tl.constexpr,
                stride_kn: tl.constexpr,
                stride_kd: tl.constexpr,
                stride_vn: tl.constexpr,
                stride_vd: tl.constexpr,
                stride_om: tl.constexpr,
                stride_od: tl.constexpr,
                SCALE: tl.constexpr,
                N: tl.constexpr,
                D: tl.constexpr,
                DV: tl.constexpr,
                BLOCK_M: tl.constexpr,
                BLOCK_N: tl.constexpr,
            ):
                pid_m = tl.program_id(0)

                offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
                mask_m = offs_m < M

                row_lens = tl.load(ROW_LENS_ptr + offs_m, mask=mask_m, other=0).to(tl.int32)

                offs_d = tl.arange(0, D)
                q = tl.load(
                    Q_ptr + offs_m[:, None] * stride_qm + offs_d[None, :] * stride_qd,
                    mask=mask_m[:, None],
                    other=0.0,
                ).to(tl.float16)

                m_i = tl.full((BLOCK_M,), float("-inf"), tl.float32)
                l_i = tl.zeros((BLOCK_M,), tl.float32)
                offs_dv = tl.arange(0, DV)
                acc = tl.zeros((BLOCK_M, DV), tl.float32)

                for start_n in tl.static_range(0, N, BLOCK_N):
                    offs_n = start_n + tl.arange(0, BLOCK_N)
                    mask_n = offs_n < N

                    k = tl.load(
                        K_ptr + offs_n[:, None] * stride_kn + offs_d[None, :] * stride_kd,
                        mask=mask_n[:, None],
                        other=0.0,
                    ).to(tl.float16)

                    v = tl.load(
                        V_ptr + offs_n[:, None] * stride_vn + offs_dv[None, :] * stride_vd,
                        mask=mask_n[:, None],
                        other=0.0,
                    ).to(tl.float16)

                    scores = tl.dot(q, tl.trans(k)).to(tl.float32) * SCALE

                    mask_ragged = offs_n[None, :] < row_lens[:, None]
                    valid = mask_m[:, None] & mask_n[None, :] & mask_ragged
                    scores = tl.where(valid, scores, float("-inf"))

                    m_ij = tl.max(scores, axis=1)
                    m_new = tl.maximum(m_i, m_ij)

                    m_new_is_neginf = m_new == float("-inf")
                    scores_shift = scores - m_new[:, None]
                    scores_shift = tl.where(m_new_is_neginf[:, None], float("-inf"), scores_shift)

                    p = tl.exp(scores_shift)
                    l_new = l_i * tl.where(m_new_is_neginf, 0.0, tl.exp(m_i - m_new)) + tl.sum(p, axis=1)

                    p16 = p.to(tl.float16)
                    acc = acc * tl.where(m_new_is_neginf, 0.0, tl.exp(m_i - m_new))[:, None] + tl.dot(p16, v, out_dtype=tl.float32)

                    m_i = m_new
                    l_i = l_new

                out = tl.where(l_i[:, None] > 0.0, acc / l_i[:, None], 0.0).to(tl.float16)
                tl.store(
                    O_ptr + offs_m[:, None] * stride_om + offs_dv[None, :] * stride_od,
                    out,
                    mask=mask_m[:, None],
                )

            def ragged_attn(Q: torch.Tensor, K: torch.Tensor, V: torch.Tensor, row_lens: torch.Tensor) -> torch.Tensor:
                assert Q.is_cuda and K.is_cuda and V.is_cuda and row_lens.is_cuda
                assert Q.dtype == torch.float16 and K.dtype == torch.float16 and V.dtype == torch.float16
                assert Q.ndim == 2 and K.ndim == 2 and V.ndim == 2 and row_lens.ndim == 1
                M, D = Q.shape
                N, Dk = K.shape
                Nv, DV = V.shape
                assert D == Dk
                assert N == Nv
                assert row_lens.shape[0] == M

                if row_lens.dtype != torch.int32:
                    row_lens_i32 = row_lens.to(torch.int32)
                else:
                    row_lens_i32 = row_lens

                O = torch.empty((M, DV), device=Q.device, dtype=torch.float16)

                BLOCK_M = 64
                BLOCK_N = 64
                scale = 1.0 / math.sqrt(D)

                grid = (triton.cdiv(M, BLOCK_M),)

                _ragged_attn_fwd_kernel[grid](
                    Q,
                    K,
                    V,
                    O,
                    row_lens_i32,
                    M,
                    stride_qm=Q.stride(0),
                    stride_qd=Q.stride(1),
                    stride_kn=K.stride(0),
                    stride_kd=K.stride(1),
                    stride_vn=V.stride(0),
                    stride_vd=V.stride(1),
                    stride_om=O.stride(0),
                    stride_od=O.stride(1),
                    SCALE=scale,
                    N=N,
                    D=D,
                    DV=DV,
                    BLOCK_M=BLOCK_M,
                    BLOCK_N=BLOCK_N,
                    num_warps=4,
                    num_stages=3,
                )
                return O
            """
        ).lstrip()
        return {"code": code}