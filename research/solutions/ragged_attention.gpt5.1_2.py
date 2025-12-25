import textwrap


class Solution:
    def solve(self, spec_path: str = None) -> dict:
        code = textwrap.dedent(
            """
            import torch
            import triton
            import triton.language as tl


            @triton.jit
            def _ragged_attn_fwd(
                Q, K, V, Out, RowLens,
                sm_scale,
                M, N, D, DV,
                stride_qm, stride_qd,
                stride_kn, stride_kd,
                stride_vn, stride_vd,
                stride_om, stride_od,
                BLOCK_M: tl.constexpr,
                BLOCK_N: tl.constexpr,
                BLOCK_DMODEL: tl.constexpr,
                BLOCK_DV: tl.constexpr,
            ):
                pid_m = tl.program_id(0)

                offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
                offs_d = tl.arange(0, BLOCK_DMODEL)
                offs_dv = tl.arange(0, BLOCK_DV)

                mask_m = offs_m < M
                mask_d = offs_d < D
                mask_dv = offs_dv < DV

                # Load Q block [BLOCK_M, BLOCK_DMODEL]
                q_ptrs = Q + offs_m[:, None] * stride_qm + offs_d[None, :] * stride_qd
                q = tl.load(q_ptrs, mask=mask_m[:, None] & mask_d[None, :], other=0.0)
                q = q.to(tl.float32)

                # Initialize streaming softmax stats
                acc = tl.zeros((BLOCK_M, BLOCK_DV), dtype=tl.float32)
                m_i = tl.full((BLOCK_M,), -float("inf"), dtype=tl.float32)
                l_i = tl.zeros((BLOCK_M,), dtype=tl.float32)

                row_lens = tl.load(RowLens + offs_m, mask=mask_m, other=0)
                row_lens = row_lens.to(tl.int32)

                # Iterate over K/V blocks
                for start_n in range(0, N, BLOCK_N):
                    offs_n = start_n + tl.arange(0, BLOCK_N)
                    mask_n = offs_n < N

                    # Load K block [BLOCK_N, BLOCK_DMODEL]
                    k_ptrs = K + offs_n[:, None] * stride_kn + offs_d[None, :] * stride_kd
                    k = tl.load(k_ptrs, mask=mask_n[:, None] & mask_d[None, :], other=0.0)
                    k = k.to(tl.float32)

                    # QK^T
                    scores = tl.dot(q, tl.trans(k))
                    scores = scores * sm_scale

                    # Ragged masking per row
                    row_lens_broadcast = row_lens[:, None]
                    n_indices = offs_n[None, :]
                    valid = mask_m[:, None] & mask_n[None, :] & (n_indices < row_lens_broadcast)
                    scores = tl.where(valid, scores, float("-inf"))

                    # Streaming softmax update
                    curr_max = tl.max(scores, axis=1)
                    m_new = tl.maximum(m_i, curr_max)

                    scores_minus_m_new = scores - m_new[:, None]
                    exp_scores = tl.exp(scores_minus_m_new)

                    scale_old = tl.exp(m_i - m_new)
                    l_new = l_i * scale_old + tl.sum(exp_scores, axis=1)

                    # Load V block [BLOCK_N, BLOCK_DV]
                    v_ptrs = V + offs_n[:, None] * stride_vn + offs_dv[None, :] * stride_vd
                    v = tl.load(v_ptrs, mask=mask_n[:, None] & mask_dv[None, :], other=0.0)
                    v = v.to(tl.float32)

                    # Update accumulator
                    acc = acc * scale_old[:, None] + tl.dot(exp_scores, v)

                    m_i = m_new
                    l_i = l_new

                # Normalize
                l_i_safe = tl.where(l_i > 0, l_i, 1.0)
                acc = acc / l_i_safe[:, None]

                # Store output
                out = acc.to(tl.float16)
                out_ptrs = Out + offs_m[:, None] * stride_om + offs_dv[None, :] * stride_od
                tl.store(out_ptrs, out, mask=mask_m[:, None] & mask_dv[None, :])


            def ragged_attn(Q: torch.Tensor, K: torch.Tensor, V: torch.Tensor, row_lens: torch.Tensor) -> torch.Tensor:
                """
                Ragged attention computation.

                Args:
                    Q: (M, D) float16 CUDA tensor
                    K: (N, D) float16 CUDA tensor
                    V: (N, Dv) float16 CUDA tensor
                    row_lens: (M,) int32/int64 CUDA tensor

                Returns:
                    (M, Dv) float16 CUDA tensor
                """
                assert Q.is_cuda and K.is_cuda and V.is_cuda, "Q, K, V must be CUDA tensors"
                assert Q.dtype == torch.float16 and K.dtype == torch.float16 and V.dtype == torch.float16, "Q, K, V must be float16"
                assert row_lens.is_cuda, "row_lens must be CUDA tensor"

                M, D = Q.shape
                N, Dk = K.shape
                Nv, Dv = V.shape
                assert Dk == D, "K dimension mismatch"
                assert Nv == N, "V dimension mismatch"

                # Ensure contiguous tensors for predictable strides
                if not Q.is_contiguous():
                    Q = Q.contiguous()
                if not K.is_contiguous():
                    K = K.contiguous()
                if not V.is_contiguous():
                    V = V.contiguous()

                if row_lens.dtype not in (torch.int32, torch.int64) or not row_lens.is_contiguous():
                    row_lens = row_lens.to(torch.int32).contiguous()
                elif row_lens.dtype != torch.int32:
                    row_lens = row_lens.to(torch.int32)

                Out = torch.empty((M, Dv), device=Q.device, dtype=torch.float16)

                # Block sizes tuned for typical transformer dims (e.g., D=Dv=64)
                BLOCK_M = 64
                BLOCK_N = 64

                # Next power of two for head dimensions, capped for register pressure
                def _next_pow2(x: int) -> int:
                    return 1 << (x - 1).bit_length()

                BLOCK_DMODEL = min(128, _next_pow2(int(D)))
                BLOCK_DV = min(128, _next_pow2(int(Dv)))

                sm_scale = 1.0 / (float(D) ** 0.5)

                grid = lambda META: (triton.cdiv(M, META["BLOCK_M"]),)

                _ragged_attn_fwd[grid](
                    Q, K, V, Out, row_lens,
                    sm_scale,
                    M, N, D, Dv,
                    Q.stride(0), Q.stride(1),
                    K.stride(0), K.stride(1),
                    V.stride(0), V.stride(1),
                    Out.stride(0), Out.stride(1),
                    BLOCK_M=BLOCK_M,
                    BLOCK_N=BLOCK_N,
                    BLOCK_DMODEL=BLOCK_DMODEL,
                    BLOCK_DV=BLOCK_DV,
                    num_warps=4,
                    num_stages=2,
                )

                return Out
            """
        )
        return {"code": code}
