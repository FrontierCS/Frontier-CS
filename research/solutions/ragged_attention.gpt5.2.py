import textwrap


class Solution:
    def solve(self, spec_path: str = None) -> dict:
        code = textwrap.dedent(
            r"""
            import math
            import torch
            import triton
            import triton.language as tl


            @triton.jit
            def _ragged_attn_kernel(
                Q_ptr, K_ptr, V_ptr, O_ptr, ROW_ptr,
                stride_qm: tl.constexpr, stride_qd: tl.constexpr,
                stride_kn: tl.constexpr, stride_kd: tl.constexpr,
                stride_vn: tl.constexpr, stride_vd: tl.constexpr,
                stride_om: tl.constexpr, stride_od: tl.constexpr,
                M: tl.constexpr, N: tl.constexpr, D: tl.constexpr, DV: tl.constexpr,
                SCALE: tl.constexpr,
                BM: tl.constexpr, BN: tl.constexpr,
            ):
                pid_m = tl.program_id(0)
                offs_m = pid_m * BM + tl.arange(0, BM)
                mask_m = offs_m < M

                # row lengths
                row_len = tl.load(ROW_ptr + offs_m, mask=mask_m, other=0).to(tl.int32)
                row_len = tl.minimum(row_len, N)

                # Q block (BM, D)
                offs_d = tl.arange(0, D)
                q = tl.load(
                    Q_ptr + offs_m[:, None] * stride_qm + offs_d[None, :] * stride_qd,
                    mask=mask_m[:, None],
                    other=0.0,
                ).to(tl.float16)

                # init streaming softmax stats
                neg_inf = -float("inf")
                m_i = tl.where(row_len > 0, neg_inf, 0.0).to(tl.float32)  # (BM,)
                l_i = tl.zeros((BM,), dtype=tl.float32)
                acc = tl.zeros((BM, DV), dtype=tl.float32)

                offs_dv = tl.arange(0, DV)

                # loop over K/V blocks
                for start_n in tl.static_range(0, N, BN):
                    offs_n = start_n + tl.arange(0, BN)  # (BN,)
                    n_in_bounds = offs_n < N

                    # K^T block (D, BN) for tl.dot: (BM,D) x (D,BN) => (BM,BN)
                    kT = tl.load(
                        K_ptr + offs_n[None, :] * stride_kn + offs_d[:, None] * stride_kd,
                        mask=n_in_bounds[None, :],
                        other=0.0,
                    ).to(tl.float16)

                    scores = tl.dot(q, kT).to(tl.float32) * SCALE  # (BM, BN)

                    # ragged mask: valid if key index < row_len for each row
                    valid = (offs_n[None, :] < row_len[:, None]) & n_in_bounds[None, :]
                    scores = tl.where(valid, scores, neg_inf)

                    m_ij = tl.max(scores, axis=1)  # (BM,)
                    m_new = tl.maximum(m_i, m_ij)  # (BM,)
                    alpha = tl.exp(m_i - m_new)  # (BM,)

                    p = tl.exp(scores - m_new[:, None])  # (BM, BN) float32
                    l_new = l_i * alpha + tl.sum(p, axis=1)  # (BM,)

                    # V block (BN, DV)
                    v = tl.load(
                        V_ptr + offs_n[:, None] * stride_vn + offs_dv[None, :] * stride_vd,
                        mask=n_in_bounds[:, None],
                        other=0.0,
                    ).to(tl.float16)

                    p16 = p.to(tl.float16)
                    acc_block = tl.dot(p16, v).to(tl.float32)  # (BM, DV)

                    acc = acc * alpha[:, None] + acc_block
                    m_i = m_new
                    l_i = l_new

                l_safe = tl.where(l_i > 0.0, l_i, 1.0)
                out = acc / l_safe[:, None]
                out = tl.where((l_i[:, None] > 0.0) & mask_m[:, None], out, 0.0)

                tl.store(
                    O_ptr + offs_m[:, None] * stride_om + offs_dv[None, :] * stride_od,
                    out.to(tl.float16),
                    mask=mask_m[:, None],
                )


            def ragged_attn(Q: torch.Tensor, K: torch.Tensor, V: torch.Tensor, row_lens: torch.Tensor) -> torch.Tensor:
                assert Q.is_cuda and K.is_cuda and V.is_cuda and row_lens.is_cuda
                assert Q.dtype == torch.float16 and K.dtype == torch.float16 and V.dtype == torch.float16
                assert Q.ndim == 2 and K.ndim == 2 and V.ndim == 2
                assert row_lens.ndim == 1
                M, D = Q.shape
                N, Dk = K.shape
                Nv, DV = V.shape
                assert Dk == D
                assert Nv == N
                assert row_lens.shape[0] == M
                assert D == 64 and DV == 64, "Optimized kernel expects D=64 and DV=64"

                O = torch.empty((M, DV), device=Q.device, dtype=torch.float16)

                BM = 2
                BN = 128
                grid = (triton.cdiv(M, BM),)

                scale = 1.0 / math.sqrt(D)

                _ragged_attn_kernel[grid](
                    Q, K, V, O, row_lens,
                    stride_qm=Q.stride(0), stride_qd=Q.stride(1),
                    stride_kn=K.stride(0), stride_kd=K.stride(1),
                    stride_vn=V.stride(0), stride_vd=V.stride(1),
                    stride_om=O.stride(0), stride_od=O.stride(1),
                    M=M, N=N, D=D, DV=DV,
                    SCALE=scale,
                    BM=BM, BN=BN,
                    num_warps=4,
                    num_stages=3,
                )
                return O
            """
        ).strip()
        return {"code": code}