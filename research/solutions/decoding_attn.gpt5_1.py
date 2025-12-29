import math
import os
import textwrap

class Solution:
    def solve(self, spec_path: str = None) -> dict:
        code = textwrap.dedent("""
            import math
            import torch
            import triton
            import triton.language as tl

            @triton.autotune(
                configs=[
                    triton.Config({'BLOCK_M': 1,  'BLOCK_N': 128}, num_warps=4, num_stages=3),
                    triton.Config({'BLOCK_M': 1,  'BLOCK_N': 256}, num_warps=8, num_stages=3),
                    triton.Config({'BLOCK_M': 1,  'BLOCK_N': 512}, num_warps=8, num_stages=3),
                    triton.Config({'BLOCK_M': 2,  'BLOCK_N': 128}, num_warps=4, num_stages=3),
                    triton.Config({'BLOCK_M': 2,  'BLOCK_N': 256}, num_warps=8, num_stages=3),
                    triton.Config({'BLOCK_M': 4,  'BLOCK_N': 128}, num_warps=4, num_stages=3),
                    triton.Config({'BLOCK_M': 4,  'BLOCK_N': 256}, num_warps=8, num_stages=3),
                ],
                key=['M', 'N', 'D_HEAD', 'D_VALUE']
            )
            @triton.jit
            def _decoding_attn_kernel(
                Q_ptr, K_ptr, V_ptr, O_ptr,
                Z, H, M, N,
                stride_qz, stride_qh, stride_qm, stride_qd,
                stride_kz, stride_kh, stride_kn, stride_kd,
                stride_vz, stride_vh, stride_vn, stride_vd,
                stride_oz, stride_oh, stride_om, stride_od,
                scale,
                D_HEAD: tl.constexpr, D_VALUE: tl.constexpr,
                BLOCK_M: tl.constexpr, BLOCK_N: tl.constexpr
            ):
                pid_zh = tl.program_id(0)
                pid_m = tl.program_id(1)

                z = pid_zh // H
                h = pid_zh % H

                offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
                mask_m = offs_m < M

                offs_dh = tl.arange(0, D_HEAD)
                offs_dv = tl.arange(0, D_VALUE)

                # Pointers base for this (z,h)
                Q_head_ptr = Q_ptr + z * stride_qz + h * stride_qh
                K_head_ptr = K_ptr + z * stride_kz + h * stride_kh
                V_head_ptr = V_ptr + z * stride_vz + h * stride_vh
                O_head_ptr = O_ptr + z * stride_oz + h * stride_oh

                # Load Q [BM, D_HEAD] to fp32
                q_ptrs = Q_head_ptr + (offs_m[:, None] * stride_qm + offs_dh[None, :] * stride_qd)
                q = tl.load(q_ptrs, mask=mask_m[:, None], other=0.0).to(tl.float32)

                # Initialize streaming softmax variables
                NEG_INF = -1e9
                m_i = tl.full((BLOCK_M,), NEG_INF, dtype=tl.float32)
                l_i = tl.zeros((BLOCK_M,), dtype=tl.float32)
                acc = tl.zeros((BLOCK_M, D_VALUE), dtype=tl.float32)

                start_n = 0
                while start_n < N:
                    offs_n = start_n + tl.arange(0, BLOCK_N)
                    mask_n = offs_n < N

                    # Load K block [BN, D_HEAD] -> [BN, D_HEAD]
                    k_ptrs = K_head_ptr + (offs_n[:, None] * stride_kn + offs_dh[None, :] * stride_kd)
                    k = tl.load(k_ptrs, mask=mask_n[:, None], other=0.0).to(tl.float32)

                    # Compute qk^T -> [BM, BN]
                    qk = tl.dot(q, tl.trans(k)) * scale

                    # Apply mask for out-of-bound keys
                    qk = tl.where(mask_n[None, :], qk, NEG_INF)

                    # Compute max for numerical stability
                    m_curr = tl.max(qk, axis=1)
                    m_new = tl.maximum(m_i, m_curr)

                    # Compute exponentiated probabilities
                    p = tl.exp(qk - m_new[:, None])

                    # Update l_i and m_i
                    alpha = tl.exp(m_i - m_new)
                    l_new = alpha * l_i + tl.sum(p, axis=1)

                    # Load V block [BN, D_VALUE]
                    v_ptrs = V_head_ptr + (offs_n[:, None] * stride_vn + offs_dv[None, :] * stride_vd)
                    v = tl.load(v_ptrs, mask=mask_n[:, None], other=0.0).to(tl.float32)

                    # Update acc
                    acc = acc * alpha[:, None] + tl.dot(p, v)

                    m_i = m_new
                    l_i = l_new

                    start_n += BLOCK_N

                # Normalize result
                out = acc / l_i[:, None]

                # Store output [BM, D_VALUE]
                o_ptrs = O_head_ptr + (offs_m[:, None] * stride_om + offs_dv[None, :] * stride_od)
                tl.store(o_ptrs, out, mask=mask_m[:, None])

            def decoding_attn(Q: torch.Tensor, K: torch.Tensor, V: torch.Tensor) -> torch.Tensor:
                """
                Decoding attention computation.

                Args:
                    Q: (Z, H, M, Dq) float16
                    K: (Z, H, N, Dq) float16
                    V: (Z, H, N, Dv) float16

                Returns:
                    (Z, H, M, Dv) float16
                """
                assert Q.is_cuda and K.is_cuda and V.is_cuda, "Inputs must be CUDA tensors"
                assert Q.dtype in (torch.float16, torch.bfloat16), "Q must be float16 or bfloat16"
                assert K.dtype == Q.dtype and V.dtype == Q.dtype, "All dtypes must match"
                assert Q.shape[0] == K.shape[0] == V.shape[0], "Batch (Z) mismatch"
                assert Q.shape[1] == K.shape[1] == V.shape[1], "Heads (H) mismatch"
                assert K.shape[3] == Q.shape[3], "Dq mismatch"
                assert K.shape[2] == V.shape[2], "Sequence length N mismatch"

                Z, H, M, Dq = Q.shape
                N = K.shape[2]
                Dv = V.shape[3]

                O = torch.empty((Z, H, M, Dv), device=Q.device, dtype=Q.dtype)

                # Strides
                stride_qz, stride_qh, stride_qm, stride_qd = Q.stride()
                stride_kz, stride_kh, stride_kn, stride_kd = K.stride()
                stride_vz, stride_vh, stride_vn, stride_vd = V.stride()
                stride_oz, stride_oh, stride_om, stride_od = O.stride()

                # Scale factor for softmax
                scale = 1.0 / math.sqrt(Dq)

                # Grid
                def grid(meta):
                    BM = meta['BLOCK_M']
                    return (Z * H, (M + BM - 1) // BM)

                _decoding_attn_kernel[grid](
                    Q, K, V, O,
                    Z, H, M, N,
                    stride_qz, stride_qh, stride_qm, stride_qd,
                    stride_kz, stride_kh, stride_kn, stride_kd,
                    stride_vz, stride_vh, stride_vn, stride_vd,
                    stride_oz, stride_oh, stride_om, stride_od,
                    scale,
                    D_HEAD=Dq, D_VALUE=Dv
                )
                return O
        """)
        return {"code": code}