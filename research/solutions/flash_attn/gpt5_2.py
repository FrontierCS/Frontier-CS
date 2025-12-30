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

        @triton.jit
        def _flash_attn_fwd_kernel(
            Q_ptr, K_ptr, V_ptr, Out_ptr,
            stride_qz, stride_qh, stride_qm, stride_qd,
            stride_kz, stride_kh, stride_kn, stride_kd,
            stride_vz, stride_vh, stride_vn, stride_vd,
            stride_oz, stride_oh, stride_om, stride_od,
            Z, H, M, N,
            Dq, Dv,
            sm_scale,
            BLOCK_M: tl.constexpr, BLOCK_N: tl.constexpr,
            D_HEAD: tl.constexpr, D_VALUE: tl.constexpr,
            CAUSAL: tl.constexpr
        ):
            pid_m = tl.program_id(axis=0)
            pid_zh = tl.program_id(axis=1)

            z = pid_zh // H
            h = pid_zh % H

            offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
            mask_m = offs_m < M

            offs_dq = tl.arange(0, D_HEAD)
            mask_dq = offs_dq < Dq

            offs_dv = tl.arange(0, D_VALUE)
            mask_dv = offs_dv < Dv

            q_ptrs = Q_ptr + z * stride_qz + h * stride_qh + offs_m[:, None] * stride_qm + offs_dq[None, :] * stride_qd
            q = tl.load(q_ptrs, mask=mask_m[:, None] & mask_dq[None, :], other=0.0).to(tl.float32)

            m_i = tl.full((BLOCK_M,), -float('inf'), dtype=tl.float32)
            l_i = tl.zeros((BLOCK_M,), dtype=tl.float32)
            o = tl.zeros((BLOCK_M, D_VALUE), dtype=tl.float32)

            k_base_ptr = K_ptr + z * stride_kz + h * stride_kh
            v_base_ptr = V_ptr + z * stride_vz + h * stride_vh

            for start_n in range(0, N, BLOCK_N):
                offs_n = start_n + tl.arange(0, BLOCK_N)
                mask_n = offs_n < N

                k_ptrs = k_base_ptr + offs_n[:, None] * stride_kn + offs_dq[None, :] * stride_kd
                k = tl.load(k_ptrs, mask=mask_n[:, None] & mask_dq[None, :], other=0.0).to(tl.float32)

                s = tl.dot(q, tl.trans(k)) * sm_scale

                # Validity mask for rows and columns
                valid = mask_m[:, None] & mask_n[None, :]

                if CAUSAL:
                    # Causal mask: col <= row
                    valid = valid & (offs_n[None, :] <= offs_m[:, None])

                # Apply masks: invalid positions get -inf
                s = tl.where(valid, s, -float('inf'))

                m_ij = tl.max(s, axis=1)
                m_new = tl.maximum(m_i, m_ij)

                p = tl.exp(s - m_new[:, None])
                alpha = tl.exp(m_i - m_new)

                l_i = l_i * alpha + tl.sum(p, axis=1)
                o = o * alpha[:, None]

                v_ptrs = v_base_ptr + offs_n[:, None] * stride_vn + offs_dv[None, :] * stride_vd
                v = tl.load(v_ptrs, mask=mask_n[:, None] & mask_dv[None, :], other=0.0).to(tl.float32)

                o += tl.dot(p, v)
                m_i = m_new

            o = o / l_i[:, None]

            out_ptrs = Out_ptr + z * stride_oz + h * stride_oh + offs_m[:, None] * stride_om + offs_dv[None, :] * stride_od
            tl.store(out_ptrs, o.to(tl.float16), mask=mask_m[:, None] & mask_dv[None, :])

        def _next_power_of_2(x: int) -> int:
            if x <= 0:
                return 1
            return 1 << (x - 1).bit_length()

        def _pick_config(M, N, Dq, Dv):
            # Heuristic configuration
            # Larger BM for longer sequences, BN fixed at 64 for good balance
            BLOCK_M = 128 if M >= 512 else 64
            BLOCK_N = 64
            # Warp selection
            if Dq <= 64 and Dv <= 64:
                num_warps = 4
                num_stages = 2
            else:
                num_warps = 8
                num_stages = 2
            return BLOCK_M, BLOCK_N, num_warps, num_stages

        def _torch_flash_attn(Q, K, V, causal=True):
            # Fallback for environments without Triton or unsupported shapes
            dtype = Q.dtype
            Z, H, M, Dq = Q.shape
            N = K.shape[2]
            scale = 1.0 / math.sqrt(Dq)
            q = Q.float()
            k = K.float()
            v = V.float()
            attn_scores = torch.matmul(q, k.transpose(-2, -1)) * scale
            if causal:
                idx_i = torch.arange(M, device=Q.device).view(1, 1, M, 1)
                idx_j = torch.arange(N, device=Q.device).view(1, 1, 1, N)
                mask = idx_j <= idx_i
                attn_scores = attn_scores.masked_fill(~mask, float('-inf'))
            attn_probs = torch.softmax(attn_scores, dim=-1)
            out = torch.matmul(attn_probs, v)
            return out.to(dtype)

        def flash_attn(Q: torch.Tensor, K: torch.Tensor, V: torch.Tensor, causal: bool = True) -> torch.Tensor:
            if not (Q.is_cuda and K.is_cuda and V.is_cuda):
                return _torch_flash_attn(Q, K, V, causal)
            assert Q.dtype == torch.float16 and K.dtype == torch.float16 and V.dtype == torch.float16, "Inputs must be float16"
            assert Q.is_contiguous() and K.is_contiguous() and V.is_contiguous(), "Inputs must be contiguous"
            Z, H, M, Dq = Q.shape
            Zk, Hk, N, Dk = K.shape
            Zv, Hv, Nv, Dv = V.shape
            assert Z == Zk == Zv and H == Hk == Hv and Dq == Dk and N == Nv, "Shape mismatch"
            # Allocate output
            Out = torch.empty((Z, H, M, Dv), device=Q.device, dtype=torch.float16)

            BLOCK_M, BLOCK_N, num_warps, num_stages = _pick_config(M, N, Dq, Dv)
            # Choose compile-time dimensions for head/value dims; pad to next power of 2 for vectorization
            # But still load/store with masks to handle real dims
            D_HEAD = _next_power_of_2(Dq) if Dq <= 128 else Dq
            D_VALUE = _next_power_of_2(Dv) if Dv <= 128 else Dv

            # Limit to reasonable max to avoid register pressure
            if D_HEAD > 128 or D_VALUE > 128:
                # Fallback if too large to ensure stability
                return _torch_flash_attn(Q, K, V, causal)

            grid = (triton.cdiv(M, BLOCK_M), Z * H)
            sm_scale = 1.0 / math.sqrt(Dq)

            _flash_attn_fwd_kernel[grid](
                Q, K, V, Out,
                Q.stride(0), Q.stride(1), Q.stride(2), Q.stride(3),
                K.stride(0), K.stride(1), K.stride(2), K.stride(3),
                V.stride(0), V.stride(1), V.stride(2), V.stride(3),
                Out.stride(0), Out.stride(1), Out.stride(2), Out.stride(3),
                Z, H, M, N,
                Dq, Dv,
                sm_scale,
                BLOCK_M=BLOCK_M, BLOCK_N=BLOCK_N,
                D_HEAD=D_HEAD, D_VALUE=D_VALUE,
                CAUSAL=causal,
                num_warps=num_warps,
                num_stages=num_stages
            )
            return Out
        """)
        return {"code": code}