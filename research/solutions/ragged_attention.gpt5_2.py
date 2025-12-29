import math
import os
import textwrap


class Solution:
    def solve(self, spec_path: str = None) -> dict:
        code = textwrap.dedent(
            """
            import math
            import torch
            import triton
            import triton.language as tl


            @triton.jit
            def _ragged_attn_fwd(
                Q, K, V, O, ROW_LENS,
                M, N, D, DV,
                stride_qm, stride_qd,
                stride_km, stride_kd,
                stride_vm, stride_vd,
                stride_om, stride_od,
                scale,
                BLOCK_M: tl.constexpr,
                BLOCK_N: tl.constexpr,
                BLOCK_D: tl.constexpr,
                BLOCK_DV: tl.constexpr,
            ):
                pid_m = tl.program_id(0)
                offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
                offs_d = tl.arange(0, BLOCK_D)
                offs_dv = tl.arange(0, BLOCK_DV)

                m_mask = offs_m < M
                d_mask = offs_d < D
                dv_mask = offs_dv < DV

                # Load Q block
                q_ptrs = Q + offs_m[:, None] * stride_qm + offs_d[None, :] * stride_qd
                q = tl.load(q_ptrs, mask=m_mask[:, None] & d_mask[None, :], other=0.).to(tl.float32)

                # Load row lengths
                rl_ptrs = ROW_LENS + offs_m
                row_lens = tl.load(rl_ptrs, mask=m_mask, other=0).to(tl.int32)
                max_len = tl.max(row_lens, axis=0)
                # Limit max to N
                n_eff = tl.minimum(max_len, N)

                # Streaming softmax state
                m_i = tl.full((BLOCK_M,), -float("inf"), dtype=tl.float32)
                l_i = tl.zeros((BLOCK_M,), dtype=tl.float32)
                acc = tl.zeros((BLOCK_M, BLOCK_DV), dtype=tl.float32)

                n_start = 0
                while n_start < n_eff:
                    offs_n = n_start + tl.arange(0, BLOCK_N)
                    n_mask = offs_n < N

                    # Load K block
                    k_ptrs = K + offs_n[:, None] * stride_km + offs_d[None, :] * stride_kd
                    k = tl.load(k_ptrs, mask=n_mask[:, None] & d_mask[None, :], other=0.).to(tl.float32)

                    # Compute scores
                    # s: [BLOCK_M, BLOCK_N]
                    s = tl.dot(q, tl.trans(k)) * scale

                    # Apply ragged masking per row: only attend to first row_lens[i]
                    # valid mask for scores: (offs_n < row_lens[i]) & m_mask
                    valid_n = offs_n[None, :] < row_lens[:, None]
                    s_mask = valid_n & m_mask[:, None] & n_mask[None, :]
                    s = tl.where(s_mask, s, -float("inf"))

                    # Update streaming softmax
                    block_max = tl.max(s, axis=1)
                    m_new = tl.maximum(m_i, block_max)
                    alpha = tl.exp(m_i - m_new)
                    p = tl.exp(s - m_new[:, None])
                    # ensure masked elements contribute zero
                    p = tl.where(s_mask, p, 0.0)

                    l_i = l_i * alpha + tl.sum(p, axis=1)

                    # Load V block
                    v_ptrs = V + offs_n[:, None] * stride_vm + offs_dv[None, :] * stride_vd
                    v = tl.load(v_ptrs, mask=n_mask[:, None] & dv_mask[None, :], other=0.).to(tl.float32)

                    acc = acc * alpha[:, None] + tl.dot(p, v)

                    m_i = m_new
                    n_start += BLOCK_N

                # Normalize and store
                out = acc / l_i[:, None]
                o_ptrs = O + offs_m[:, None] * stride_om + offs_dv[None, :] * stride_od
                tl.store(o_ptrs, out.to(tl.float16), mask=m_mask[:, None] & dv_mask[None, :])


            def ragged_attn(Q: torch.Tensor, K: torch.Tensor, V: torch.Tensor, row_lens: torch.Tensor) -> torch.Tensor:
                """
                Ragged attention computation.

                Args:
                    Q: Query tensor of shape (M, D) - query features (float16)
                    K: Key tensor of shape (N, D) - key features (float16)
                    V: Value tensor of shape (N, Dv) - value features (float16)
                    row_lens: Row lengths tensor of shape (M,) - number of valid K/V rows per Q row (int32 or int64)

                Returns:
                    Output tensor of shape (M, Dv) - attention output (float16)
                """
                assert Q.is_cuda and K.is_cuda and V.is_cuda, "All tensors must be CUDA tensors"
                assert Q.dtype in (torch.float16, torch.bfloat16) and K.dtype in (torch.float16, torch.bfloat16) and V.dtype in (torch.float16, torch.bfloat16), "Q, K, V must be float16/bfloat16"
                assert Q.shape[1] == K.shape[1], "Q and K must have the same feature dimension D"
                assert K.shape[0] == V.shape[0], "K and V must have same number of rows N"
                assert row_lens.shape[0] == Q.shape[0], "row_lens must have length M"
                M, D = Q.shape
                N = K.shape[0]
                DV = V.shape[1]

                # Ensure contiguity
                Qc = Q.contiguous()
                Kc = K.contiguous()
                Vc = V.contiguous()
                if row_lens.dtype != torch.int32:
                    row_lens_c = row_lens.to(torch.int32).contiguous()
                else:
                    row_lens_c = row_lens.contiguous()

                O = torch.empty((M, DV), device=Q.device, dtype=torch.float16)

                # Choose block sizes optimized for D=64, DV=64 (as per spec)
                BLOCK_M = 64
                BLOCK_N = 64
                BLOCK_D = 64
                BLOCK_DV = 64

                # Safety: handle cases where D or DV < block (masking handles >)
                scale = 1.0 / math.sqrt(float(D))

                grid = (triton.cdiv(M, BLOCK_M),)

                _ragged_attn_fwd[grid](
                    Qc, Kc, Vc, O, row_lens_c,
                    M, N, D, DV,
                    Qc.stride(0), Qc.stride(1),
                    Kc.stride(0), Kc.stride(1),
                    Vc.stride(0), Vc.stride(1),
                    O.stride(0), O.stride(1),
                    scale,
                    BLOCK_M=BLOCK_M,
                    BLOCK_N=BLOCK_N,
                    BLOCK_D=BLOCK_D,
                    BLOCK_DV=BLOCK_DV,
                    num_warps=4,
                    num_stages=3,
                )

                return O
            """
        )
        return {"code": code}