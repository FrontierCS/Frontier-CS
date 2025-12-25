import os
import textwrap

class Solution:
    def solve(self, spec_path: str = None) -> dict:
        code = textwrap.dedent(r"""
        import math
        import torch
        import triton
        import triton.language as tl

        @triton.autotune(
            configs=[
                triton.Config({"BM": 16, "BN": 128}, num_warps=4, num_stages=4),
                triton.Config({"BM": 32, "BN": 128}, num_warps=8, num_stages=4),
                triton.Config({"BM": 16, "BN": 64}, num_warps=4, num_stages=5),
                triton.Config({"BM": 8, "BN": 128}, num_warps=4, num_stages=4),
                triton.Config({"BM": 8, "BN": 64}, num_warps=4, num_stages=5),
            ],
            key=["M"],
        )
        @triton.jit
        def _ragged_attn_fwd(
            Q_ptr, K_ptr, V_ptr, O_ptr, RL_ptr,
            stride_qm: tl.constexpr, stride_qd: tl.constexpr,
            stride_kn: tl.constexpr, stride_kd: tl.constexpr,
            stride_vn: tl.constexpr, stride_vd: tl.constexpr,
            stride_om: tl.constexpr, stride_od: tl.constexpr,
            M: tl.constexpr, N: tl.constexpr, D: tl.constexpr, DV: tl.constexpr,
            BM: tl.constexpr, BN: tl.constexpr,
        ):
            pid_m = tl.program_id(0)

            offs_m = pid_m * BM + tl.arange(0, BM)
            m_mask = offs_m < M

            offs_d = tl.arange(0, D)
            offs_dv = tl.arange(0, DV)

            q = tl.load(Q_ptr + offs_m[:, None] * stride_qm + offs_d[None, :] * stride_qd, mask=m_mask[:, None], other=0.0).to(tl.float16)
            scale = tl.full((), 1.0 / math.sqrt(D), tl.float16)
            q = q * scale

            rl = tl.load(RL_ptr + offs_m, mask=m_mask, other=0).to(tl.int32)
            rl = tl.maximum(rl, 0)
            rl = tl.minimum(rl, N)

            m_i = tl.full((BM,), -float("inf"), tl.float32)
            l_i = tl.zeros((BM,), tl.float32)
            acc = tl.zeros((BM, DV), tl.float32)

            for start_n in tl.static_range(0, N, BN):
                offs_n = start_n + tl.arange(0, BN)
                n_mask = offs_n < N

                k = tl.load(K_ptr + offs_n[:, None] * stride_kn + offs_d[None, :] * stride_kd, mask=n_mask[:, None], other=0.0).to(tl.float16)
                kT = tl.trans(k)

                qk = tl.dot(q, kT).to(tl.float32)

                valid = n_mask[None, :] & (offs_n[None, :] < rl[:, None])

                qk_max_in = tl.where(valid, qk, -float("inf"))
                m_ij = tl.max(qk_max_in, axis=1)
                m_new = tl.maximum(m_i, m_ij)

                m_new_safe = tl.where(tl.is_inf(m_new), 0.0, m_new)

                exp_m = tl.exp(m_i - m_new_safe)
                exp_m = tl.where(tl.is_inf(m_i) & tl.is_inf(m_new), 0.0, exp_m)

                p = tl.exp(qk - m_new_safe[:, None])
                p = tl.where(valid, p, 0.0)

                l_new = l_i * exp_m + tl.sum(p, axis=1)

                v = tl.load(V_ptr + offs_n[:, None] * stride_vn + offs_dv[None, :] * stride_vd, mask=n_mask[:, None], other=0.0).to(tl.float16)
                pv = tl.dot(p.to(tl.float16), v).to(tl.float32)

                acc = acc * exp_m[:, None] + pv
                m_i = m_new
                l_i = l_new

            inv_l = 1.0 / l_i
            inv_l = tl.where(l_i > 0.0, inv_l, 0.0)
            out = (acc * inv_l[:, None]).to(tl.float16)

            tl.store(O_ptr + offs_m[:, None] * stride_om + offs_dv[None, :] * stride_od, out, mask=m_mask[:, None])

        def ragged_attn(Q: torch.Tensor, K: torch.Tensor, V: torch.Tensor, row_lens: torch.Tensor) -> torch.Tensor:
            assert Q.is_cuda and K.is_cuda and V.is_cuda and row_lens.is_cuda
            assert Q.dtype == torch.float16 and K.dtype == torch.float16 and V.dtype == torch.float16
            assert Q.dim() == 2 and K.dim() == 2 and V.dim() == 2 and row_lens.dim() == 1
            M, D = Q.shape
            N, Dk = K.shape
            Nv, DV = V.shape
            assert Dk == D and Nv == N and row_lens.shape[0] == M

            if row_lens.dtype != torch.int32:
                row_lens_i32 = row_lens.to(torch.int32)
            else:
                row_lens_i32 = row_lens

            O = torch.empty((M, DV), device=Q.device, dtype=torch.float16)

            grid = (triton.cdiv(M, 16),)
            _ragged_attn_fwd[grid](
                Q, K, V, O, row_lens_i32,
                Q.stride(0), Q.stride(1),
                K.stride(0), K.stride(1),
                V.stride(0), V.stride(1),
                O.stride(0), O.stride(1),
                M=M, N=N, D=D, DV=DV,
            )
            return O
        """).strip()
        return {"code": code}