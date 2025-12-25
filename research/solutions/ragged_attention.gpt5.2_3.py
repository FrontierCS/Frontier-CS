import os
import textwrap

class Solution:
    def solve(self, spec_path: str = None) -> dict:
        code = textwrap.dedent(
            r"""
            import math
            import torch
            import triton
            import triton.language as tl

            @triton.autotune(
                configs=[
                    triton.Config({"BM": 16, "BN": 128}, num_warps=4, num_stages=2),
                    triton.Config({"BM": 32, "BN": 128}, num_warps=8, num_stages=2),
                    triton.Config({"BM": 8, "BN": 128}, num_warps=4, num_stages=2),
                ],
                key=["M"],
            )
            @triton.jit
            def _ragged_attn_fwd(
                Q_ptr, K_ptr, V_ptr, O_ptr, RL_ptr,
                M: tl.constexpr, N: tl.constexpr, D: tl.constexpr, DV: tl.constexpr,
                stride_qm: tl.constexpr, stride_qd: tl.constexpr,
                stride_kn: tl.constexpr, stride_kd: tl.constexpr,
                stride_vn: tl.constexpr, stride_vd: tl.constexpr,
                stride_om: tl.constexpr, stride_od: tl.constexpr,
                scale: tl.constexpr,
                BM: tl.constexpr, BN: tl.constexpr,
            ):
                pid = tl.program_id(0)

                offs_m = pid * BM + tl.arange(0, BM)
                row_mask = offs_m < M

                row_lens = tl.load(RL_ptr + offs_m, mask=row_mask, other=0).to(tl.int32)

                offs_d = tl.arange(0, D)
                q_ptrs = Q_ptr + offs_m[:, None] * stride_qm + offs_d[None, :] * stride_qd
                q = tl.load(q_ptrs, mask=row_mask[:, None], other=0.0).to(tl.float16)

                m_i = tl.full((BM,), -float("inf"), tl.float32)
                l_i = tl.zeros((BM,), tl.float32)
                acc = tl.zeros((BM, DV), tl.float32)

                offs_dk = tl.arange(0, D)
                offs_dv = tl.arange(0, DV)

                # N is constexpr; unroll blocks
                for start_n in tl.static_range(0, N, BN):
                    offs_n = start_n + tl.arange(0, BN)
                    n_mask = offs_n < N

                    # K as (D, BN)
                    k_ptrs = K_ptr + offs_n[None, :] * stride_kn + offs_dk[:, None] * stride_kd
                    k = tl.load(k_ptrs, mask=n_mask[None, :], other=0.0).to(tl.float16)

                    scores = tl.dot(q, k).to(tl.float32) * scale

                    valid = row_mask[:, None] & n_mask[None, :] & (offs_n[None, :] < row_lens[:, None])
                    scores = tl.where(valid, scores, -float("inf"))

                    block_max = tl.max(scores, axis=1)
                    m_new = tl.maximum(m_i, block_max)

                    m_new_is_neginf = m_new == -float("inf")
                    alpha = tl.where(m_new_is_neginf, 0.0, tl.exp(m_i - m_new))

                    p = tl.where(m_new_is_neginf[:, None], 0.0, tl.exp(scores - m_new[:, None])).to(tl.float16)

                    # V as (BN, DV)
                    v_ptrs = V_ptr + offs_n[:, None] * stride_vn + offs_dv[None, :] * stride_vd
                    v = tl.load(v_ptrs, mask=n_mask[:, None], other=0.0).to(tl.float16)

                    acc = acc * alpha[:, None] + tl.dot(p, v).to(tl.float32)
                    l_i = l_i * alpha + tl.sum(p.to(tl.float32), axis=1)
                    m_i = m_new

                out = tl.where(l_i[:, None] > 0.0, acc / l_i[:, None], 0.0).to(tl.float16)

                o_ptrs = O_ptr + offs_m[:, None] * stride_om + offs_dv[None, :] * stride_od
                tl.store(o_ptrs, out, mask=row_mask[:, None])


            def ragged_attn(Q: torch.Tensor, K: torch.Tensor, V: torch.Tensor, row_lens: torch.Tensor) -> torch.Tensor:
                assert Q.is_cuda and K.is_cuda and V.is_cuda and row_lens.is_cuda
                assert Q.dtype == torch.float16 and K.dtype == torch.float16 and V.dtype == torch.float16
                assert Q.ndim == 2 and K.ndim == 2 and V.ndim == 2 and row_lens.ndim == 1
                M, D = Q.shape
                N, Dk = K.shape
                Nv, DV = V.shape
                assert Dk == D
                assert Nv == N
                assert row_lens.shape[0] == M

                if row_lens.dtype not in (torch.int32, torch.int64):
                    row_lens = row_lens.to(torch.int32)
                if row_lens.dtype == torch.int64:
                    row_lens_i32 = row_lens.to(torch.int32)
                else:
                    row_lens_i32 = row_lens

                O = torch.empty((M, DV), device=Q.device, dtype=torch.float16)

                scale = 1.0 / math.sqrt(D)

                grid = (triton.cdiv(M, 16),)
                _ragged_attn_fwd[grid](
                    Q, K, V, O, row_lens_i32,
                    M=M, N=N, D=D, DV=DV,
                    stride_qm=Q.stride(0), stride_qd=Q.stride(1),
                    stride_kn=K.stride(0), stride_kd=K.stride(1),
                    stride_vn=V.stride(0), stride_vd=V.stride(1),
                    stride_om=O.stride(0), stride_od=O.stride(1),
                    scale=scale,
                )
                return O
            """
        ).strip() + "\n"
        return {"code": code}