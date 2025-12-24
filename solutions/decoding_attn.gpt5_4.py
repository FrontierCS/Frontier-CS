import os
import textwrap

class Solution:
    def solve(self, spec_path: str = None) -> dict:
        code = textwrap.dedent("""
            import torch
            import triton
            import triton.language as tl

            @triton.autotune(
                configs=[
                    triton.Config({'BLOCK_K': 64,  'BLOCK_DQ': 64,  'BLOCK_DV': 64},  num_warps=4, num_stages=3),
                    triton.Config({'BLOCK_K': 128, 'BLOCK_DQ': 64,  'BLOCK_DV': 64},  num_warps=4, num_stages=3),
                    triton.Config({'BLOCK_K': 256, 'BLOCK_DQ': 64,  'BLOCK_DV': 64},  num_warps=8, num_stages=4),
                    triton.Config({'BLOCK_K': 128, 'BLOCK_DQ': 64,  'BLOCK_DV': 128}, num_warps=8, num_stages=4),
                    triton.Config({'BLOCK_K': 256, 'BLOCK_DQ': 64,  'BLOCK_DV': 128}, num_warps=8, num_stages=4),
                    triton.Config({'BLOCK_K': 64,  'BLOCK_DQ': 128, 'BLOCK_DV': 64},  num_warps=4, num_stages=3),
                    triton.Config({'BLOCK_K': 128, 'BLOCK_DQ': 128, 'BLOCK_DV': 64},  num_warps=4, num_stages=3),
                    triton.Config({'BLOCK_K': 256, 'BLOCK_DQ': 128, 'BLOCK_DV': 64},  num_warps=8, num_stages=4),
                ],
                key=['N', 'Dq', 'Dv'],
            )
            @triton.jit
            def _decoding_attn_kernel(
                Q_ptr, K_ptr, V_ptr, O_ptr,
                stride_qz, stride_qh, stride_qm, stride_qd,
                stride_kz, stride_kh, stride_kn, stride_kd,
                stride_vz, stride_vh, stride_vn, stride_vd,
                stride_oz, stride_oh, stride_om, stride_od,
                Z, H, M, N, Dq, Dv,
                sm_scale: tl.constexpr,
                BLOCK_K: tl.constexpr, BLOCK_DQ: tl.constexpr, BLOCK_DV: tl.constexpr
            ):
                pid = tl.program_id(axis=0)
                m_id = pid % M
                tmp = pid // M
                h_id = tmp % H
                z_id = tmp // H

                # Load query vector q of size Dq
                offs_dq = tl.arange(0, BLOCK_DQ)
                q_base = Q_ptr + z_id * stride_qz + h_id * stride_qh + m_id * stride_qm
                q = tl.load(q_base + offs_dq * stride_qd, mask=offs_dq < Dq, other=0.0)
                q = q.to(tl.float32)

                # Loop over value dimension in tiles so we can support any Dv
                dv_start = 0
                while dv_start < Dv:
                    offs_dv = dv_start + tl.arange(0, BLOCK_DV)
                    dv_mask = offs_dv < Dv

                    out_acc = tl.zeros([BLOCK_DV], dtype=tl.float32)
                    m_i = tl.full([1], -float('inf'), dtype=tl.float32)
                    l_i = tl.zeros([1], dtype=tl.float32)

                    n_start = 0
                    while n_start < N:
                        offs_n = n_start + tl.arange(0, BLOCK_K)
                        n_mask = offs_n < N

                        # Load K tile [BLOCK_K, BLOCK_DQ]
                        k_ptrs = (
                            K_ptr
                            + z_id * stride_kz
                            + h_id * stride_kh
                            + offs_n[:, None] * stride_kn
                            + offs_dq[None, :] * stride_kd
                        )
                        k = tl.load(k_ptrs, mask=n_mask[:, None] & (offs_dq[None, :] < Dq), other=0.0)
                        k = k.to(tl.float32)

                        # Compute scores = K @ q
                        scores = tl.sum(k * q[None, :], axis=1)
                        scores = scores * sm_scale
                        # Mask out-of-bounds
                        scores = tl.where(n_mask, scores, -float('inf'))

                        # Online softmax update
                        block_max = tl.max(scores, axis=0)
                        m_prev = m_i
                        m_i = tl.maximum(m_i, block_max)
                        alpha = tl.exp(m_prev - m_i)

                        p = tl.exp(scores - m_i)
                        # p zeros for masked positions already handled by -inf
                        sum_p = tl.sum(p, axis=0)
                        l_i = l_i * alpha + sum_p

                        # Load V tile [BLOCK_K, BLOCK_DV]
                        v_ptrs = (
                            V_ptr
                            + z_id * stride_vz
                            + h_id * stride_vh
                            + offs_n[:, None] * stride_vn
                            + offs_dv[None, :] * stride_vd
                        )
                        v = tl.load(v_ptrs, mask=n_mask[:, None] & dv_mask[None, :], other=0.0)
                        v = v.to(tl.float32)

                        contrib = tl.sum(v * p[:, None], axis=0)
                        out_acc = out_acc * alpha + contrib

                        n_start += BLOCK_K

                    # Normalize and store
                    out = out_acc / l_i
                    o_ptrs = (
                        O_ptr
                        + z_id * stride_oz
                        + h_id * stride_oh
                        + m_id * stride_om
                        + offs_dv * stride_od
                    )
                    tl.store(o_ptrs, out.to(tl.float16), mask=dv_mask)

                    dv_start += BLOCK_DV

            def decoding_attn(Q: torch.Tensor, K: torch.Tensor, V: torch.Tensor) -> torch.Tensor:
                assert Q.is_cuda and K.is_cuda and V.is_cuda, "Tensors must be on CUDA device"
                assert Q.dtype in (torch.float16, torch.bfloat16), "Q must be float16/bfloat16"
                assert K.dtype == Q.dtype and V.dtype == Q.dtype, "K and V must have same dtype as Q"
                assert Q.shape[0] == K.shape[0] == V.shape[0], "Z must match"
                assert Q.shape[1] == K.shape[1] == V.shape[1], "H must match"
                assert Q.shape[3] == K.shape[3], "Dq must match between Q and K"
                Z, H, M, Dq = Q.shape
                _, _, N, _ = K.shape
                _, _, _, Dv = V.shape

                # Allocate output
                O = torch.empty((Z, H, M, Dv), device=Q.device, dtype=torch.float16)

                # Strides (in elements)
                stride_qz, stride_qh, stride_qm, stride_qd = Q.stride()
                stride_kz, stride_kh, stride_kn, stride_kd = K.stride()
                stride_vz, stride_vh, stride_vn, stride_vd = V.stride()
                stride_oz, stride_oh, stride_om, stride_od = O.stride()

                # scale
                sm_scale = 1.0 / (Dq ** 0.5)

                grid = (Z * H * M,)

                _decoding_attn_kernel[grid](
                    Q, K, V, O,
                    stride_qz, stride_qh, stride_qm, stride_qd,
                    stride_kz, stride_kh, stride_kn, stride_kd,
                    stride_vz, stride_vh, stride_vn, stride_vd,
                    stride_oz, stride_oh, stride_om, stride_od,
                    Z, H, M, N, Dq, Dv,
                    sm_scale,
                )
                return O
        """)
        return {"code": code}
