import math
import textwrap

class Solution:
    def solve(self, spec_path: str = None) -> dict:
        code = textwrap.dedent("""
            import math
            import torch
            import triton
            import triton.language as tl

            @triton.jit
            def _ragged_attn_fwd(
                Q, K, V, O, ROW_LENS,
                M, N,
                stride_qm, stride_qd,
                stride_kn, stride_kd,
                stride_vn, stride_vd,
                stride_om, stride_od,
                scale,
                BLOCK_M: tl.constexpr, BLOCK_N: tl.constexpr,
                D_HEAD: tl.constexpr, DV_HEAD: tl.constexpr,
            ):
                pid_m = tl.program_id(0)
                offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
                mask_m = offs_m < M

                # Load Q block
                offs_d = tl.arange(0, D_HEAD)
                q_ptrs = Q + offs_m[:, None] * stride_qm + offs_d[None, :] * stride_qd
                q = tl.load(q_ptrs, mask=mask_m[:, None], other=0.0)  # [BM, D], fp16

                # Prepare accumulators
                acc = tl.zeros((BLOCK_M, DV_HEAD), dtype=tl.float32)
                m_i = tl.full((BLOCK_M,), -float("inf"), dtype=tl.float32)
                l_i = tl.zeros((BLOCK_M,), dtype=tl.float32)

                # Load row lengths for this tile
                lens = tl.load(ROW_LENS + offs_m, mask=mask_m, other=0).to(tl.int32)

                # Iterate over keys/values in blocks
                n_start = 0
                offs_dv = tl.arange(0, DV_HEAD)
                while n_start < N:
                    offs_n = n_start + tl.arange(0, BLOCK_N)
                    mask_n = offs_n < N

                    # Load K block
                    k_ptrs = K + offs_n[:, None] * stride_kn + offs_d[None, :] * stride_kd
                    k = tl.load(k_ptrs, mask=mask_n[:, None], other=0.0)  # [BN, D], fp16

                    # Compute scores = Q @ K^T
                    scores = tl.dot(q, tl.trans(k))  # [BM, BN], float32
                    scores = scores * scale

                    # Ragged mask: only allow keys j < lens[i]
                    # allowed shape: [BM, BN]
                    allowed = (offs_n[None, :] < lens[:, None]) & mask_m[:, None] & mask_n[None, :]
                    scores = tl.where(allowed, scores, -float("inf"))

                    # Streaming softmax update
                    m_ij = tl.max(scores, axis=1)
                    m_new = tl.maximum(m_i, m_ij)
                    p = tl.exp(scores - m_new[:, None])
                    alpha = tl.exp(m_i - m_new)
                    l_i = l_i * alpha + tl.sum(p, axis=1)
                    acc = acc * alpha[:, None]

                    # Multiply probabilities by V block and accumulate
                    v_ptrs = V + offs_n[:, None] * stride_vn + offs_dv[None, :] * stride_vd
                    v = tl.load(v_ptrs, mask=mask_n[:, None], other=0.0)  # [BN, DV], fp16
                    pv = tl.dot(p, v)  # [BM, DV], float32
                    acc += pv

                    m_i = m_new
                    n_start += BLOCK_N

                # Normalize
                eps = 1e-6
                l_i_safe = l_i + eps
                out = acc / l_i_safe[:, None]

                # Store output
                o_ptrs = O + offs_m[:, None] * stride_om + offs_dv[None, :] * stride_od
                tl.store(o_ptrs, out.to(tl.float16), mask=mask_m[:, None])

            def ragged_attn(Q: torch.Tensor, K: torch.Tensor, V: torch.Tensor, row_lens: torch.Tensor) -> torch.Tensor:
                """
                Ragged attention computation.

                Args:
                    Q: (M, D) float16 CUDA
                    K: (N, D) float16 CUDA
                    V: (N, Dv) float16 CUDA
                    row_lens: (M,) int32/int64 CUDA or CPU
                Returns:
                    O: (M, Dv) float16 CUDA
                """
                assert Q.is_cuda and K.is_cuda and V.is_cuda, "Q, K, V must be CUDA tensors"
                assert Q.dtype == torch.float16 and K.dtype == torch.float16 and V.dtype == torch.float16, "Q, K, V must be float16"
                M, D = Q.shape
                N, Dk = K.shape
                assert Dk == D, "K dim must match Q"
                Nv, Dv = V.shape
                assert Nv == N, "V rows must match K"
                if row_lens.device != Q.device:
                    row_lens = row_lens.to(Q.device)
                row_lens = row_lens.to(torch.int32).contiguous()

                O = torch.empty((M, Dv), device=Q.device, dtype=torch.float16)

                # Strides
                stride_qm, stride_qd = Q.stride()
                stride_kn, stride_kd = K.stride()
                stride_vn, stride_vd = V.stride()
                stride_om, stride_od = O.stride()

                # Kernel launch parameters
                BLOCK_M = 64
                BLOCK_N = 128
                num_warps = 4
                num_stages = 2

                scale = 1.0 / math.sqrt(max(1, D))

                grid = (triton.cdiv(M, BLOCK_M),)
                _ragged_attn_fwd[grid](
                    Q, K, V, O, row_lens,
                    M, N,
                    stride_qm, stride_qd,
                    stride_kn, stride_kd,
                    stride_vn, stride_vd,
                    stride_om, stride_od,
                    scale,
                    BLOCK_M=BLOCK_M, BLOCK_N=BLOCK_N,
                    D_HEAD=D, DV_HEAD=Dv,
                    num_warps=num_warps, num_stages=num_stages
                )
                return O
        """)
        return {"code": code}
