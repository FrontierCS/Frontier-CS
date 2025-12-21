import os
import textwrap

class Solution:
    def solve(self, spec_path: str = None) -> dict:
        code = textwrap.dedent("""
            import torch
            import triton
            import triton.language as tl

            @triton.jit
            def _flash_attn_fwd_kernel(
                Q_ptr, K_ptr, V_ptr, O_ptr,
                Z, H, M, N, D, Dv,
                stride_qz, stride_qh, stride_qm, stride_qd,
                stride_kz, stride_kh, stride_kn, stride_kd,
                stride_vz, stride_vh, stride_vn, stride_vd,
                stride_oz, stride_oh, stride_om, stride_od,
                sm_scale: tl.float32,
                causal: tl.constexpr,
                BLOCK_M: tl.constexpr,
                BLOCK_N: tl.constexpr,
                BLOCK_DMODEL: tl.constexpr,
                BLOCK_DVALUE: tl.constexpr,
            ):
                pid_m = tl.program_id(0)
                pid_bh = tl.program_id(1)

                h = pid_bh % H
                z = pid_bh // H

                offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
                offs_n = tl.arange(0, BLOCK_N)
                offs_d = tl.arange(0, BLOCK_DMODEL)
                offs_dv = tl.arange(0, BLOCK_DVALUE)

                row_mask = offs_m < M

                # Base pointers
                Q_ptr_zh = Q_ptr + z * stride_qz + h * stride_qh
                K_ptr_zh = K_ptr + z * stride_kz + h * stride_kh
                V_ptr_zh = V_ptr + z * stride_vz + h * stride_vh
                O_ptr_zh = O_ptr + z * stride_oz + h * stride_oh

                # Load Q block [BM, D]
                q_ptrs = Q_ptr_zh + (offs_m[:, None] * stride_qm + offs_d[None, :] * stride_qd)
                q = tl.load(q_ptrs, mask=(row_mask[:, None] & (offs_d[None, :] < D)), other=0.0).to(tl.float32)

                # Initialize streaming softmax state
                m_i = tl.full((BLOCK_M,), -float('inf'), tl.float32)
                l_i = tl.zeros((BLOCK_M,), tl.float32)
                acc = tl.zeros((BLOCK_M, BLOCK_DVALUE), tl.float32)

                # Iterate over K/V blocks
                n_start = 0
                while n_start < N:
                    cols = n_start + offs_n
                    col_mask = cols < N

                    # Load K block [BN, D]
                    k_ptrs = K_ptr_zh + (cols[:, None] * stride_kn + offs_d[None, :] * stride_kd)
                    k = tl.load(k_ptrs, mask=(col_mask[:, None] & (offs_d[None, :] < D)), other=0.0).to(tl.float32)

                    # Compute QK^T
                    qk = tl.dot(q, tl.trans(k)) * sm_scale

                    # Valid mask for attention
                    valid = (row_mask[:, None] & col_mask[None, :])
                    if causal:
                        valid = valid & (offs_m[:, None] >= cols[None, :])

                    # Apply mask with -inf to invalid positions
                    qk = tl.where(valid, qk, -float('inf'))

                    # Row-wise max
                    row_max = tl.max(qk, axis=1)

                    # Update running max
                    m_i_new = tl.maximum(m_i, row_max)

                    # Shifted scores and safe mask to avoid NaNs
                    qk_shifted = qk - m_i_new[:, None]
                    qk_shifted = tl.where(valid, qk_shifted, -float('inf'))

                    # Exponentiate
                    p = tl.exp(qk_shifted)

                    # Load V block [BN, Dv]
                    v_ptrs = V_ptr_zh + (cols[:, None] * stride_vn + offs_dv[None, :] * stride_vd)
                    v = tl.load(v_ptrs, mask=(col_mask[:, None] & (offs_dv[None, :] < Dv)), other=0.0).to(tl.float32)

                    # Compute P @ V -> [BM, Dv]
                    pv = tl.dot(p, v)

                    # Update l_i
                    # alpha = exp(m_i - m_i_new), but handle m_i == m_i_new to avoid NaNs when both -inf
                    same = m_i_new == m_i
                    alpha = tl.exp(m_i - m_i_new)
                    alpha = tl.where(same, 1.0, alpha)
                    p_sum = tl.sum(p, axis=1)
                    l_i_new = l_i * alpha + p_sum

                    # Normalize and update acc
                    inv_l = tl.where(l_i_new > 0, 1.0 / l_i_new, 0.0)
                    acc = acc * ((l_i * alpha) * inv_l)[:, None] + pv * inv_l[:, None]

                    # Update running stats
                    l_i = l_i_new
                    m_i = m_i_new

                    n_start += BLOCK_N

                # Store output [BM, Dv]
                o = acc
                o = o.to(tl.float16)
                o_ptrs = O_ptr_zh + (offs_m[:, None] * stride_om + offs_dv[None, :] * stride_od)
                tl.store(o_ptrs, o, mask=(row_mask[:, None] & (offs_dv[None, :] < Dv)))


            def _next_power_of_two(x: int) -> int:
                if x <= 1:
                    return 1
                return 1 << ((x - 1).bit_length())

            def flash_attn(Q: torch.Tensor, K: torch.Tensor, V: torch.Tensor, causal: bool = True) -> torch.Tensor:
                assert Q.is_cuda and K.is_cuda and V.is_cuda, "Inputs must be on CUDA"
                assert Q.dtype == torch.float16 and K.dtype == torch.float16 and V.dtype == torch.float16, "Inputs must be float16"
                assert Q.dim() == 4 and K.dim() == 4 and V.dim() == 4, "Expected 4D tensors (Z,H,Len,Dim)"
                Z, H, M, D = Q.shape
                Zk, Hk, N, Dk = K.shape
                Zv, Hv, Nv, Dv = V.shape
                assert Z == Zk == Zv and H == Hk == Hv and D == Dk and N == Nv, "Shape mismatch"
                # Allocate output
                O = torch.empty((Z, H, M, Dv), device=Q.device, dtype=torch.float16)

                # Strides (assume row-major but get actual strides)
                stride_qz, stride_qh, stride_qm, stride_qd = Q.stride()
                stride_kz, stride_kh, stride_kn, stride_kd = K.stride()
                stride_vz, stride_vh, stride_vn, stride_vd = V.stride()
                stride_oz, stride_oh, stride_om, stride_od = O.stride()

                # Tiling parameters
                # Choose BLOCK_M to be large; BLOCK_N moderate; D-model/value to next power-of-two for efficient dot
                BLOCK_M = 128 if M >= 128 else (64 if M >= 64 else 32)
                BLOCK_N = 64 if N >= 64 else (32 if N >= 32 else 16)
                BLOCK_DMODEL = min(128, _next_power_of_two(int(D)))
                BLOCK_DVALUE = min(128, _next_power_of_two(int(Dv)))

                num_warps = 4 if BLOCK_M <= 128 else 8
                num_stages = 3

                grid = (triton.cdiv(M, BLOCK_M), Z * H)

                sm_scale = (1.0 / (D ** 0.5))

                _flash_attn_fwd_kernel[grid](
                    Q, K, V, O,
                    Z, H, M, N, D, Dv,
                    stride_qz, stride_qh, stride_qm, stride_qd,
                    stride_kz, stride_kh, stride_kn, stride_kd,
                    stride_vz, stride_vh, stride_vn, stride_vd,
                    stride_oz, stride_oh, stride_om, stride_od,
                    sm_scale,
                    causal,
                    BLOCK_M=BLOCK_M,
                    BLOCK_N=BLOCK_N,
                    BLOCK_DMODEL=BLOCK_DMODEL,
                    BLOCK_DVALUE=BLOCK_DVALUE,
                    num_warps=num_warps,
                    num_stages=num_stages,
                )

                return O
        """)
        return {"code": code}
