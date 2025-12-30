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
                Q_ptr, K_ptr, V_ptr, O_ptr,
                stride_qz, stride_qh, stride_qm, stride_qd,
                stride_kz, stride_kh, stride_kn, stride_kd,
                stride_vz, stride_vh, stride_vn, stride_vd,
                stride_oz, stride_oh, stride_om, stride_od,
                Z, H, M, N, D, DV,
                sm_scale,
                causal: tl.constexpr,
                BLOCK_M: tl.constexpr,
                BLOCK_N: tl.constexpr,
                BLOCK_DMODEL: tl.constexpr,
                BLOCK_DV: tl.constexpr,
            ):
                pid_m = tl.program_id(axis=0)
                pid_zh = tl.program_id(axis=1)

                z = pid_zh // H
                h = pid_zh % H

                offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
                offs_n = tl.arange(0, BLOCK_N)
                offs_d = tl.arange(0, BLOCK_DMODEL)
                offs_dv = tl.arange(0, BLOCK_DV)

                m_mask = offs_m < M
                d_mask = offs_d < D
                dv_mask = offs_dv < DV

                # Load Q block [BLOCK_M, D]
                q_ptrs = Q_ptr + z * stride_qz + h * stride_qh + offs_m[:, None] * stride_qm + offs_d[None, :] * stride_qd
                q = tl.load(q_ptrs, mask=m_mask[:, None] & d_mask[None, :], other=0.0)
                q = q.to(tl.float32)

                # Initialize streaming softmax state
                m_i = tl.full([BLOCK_M], -1e9, tl.float32)  # running max
                l_i = tl.zeros([BLOCK_M], tl.float32)       # running sum of exp
                acc = tl.zeros([BLOCK_M, BLOCK_DV], tl.float32)

                # Iterate over K/V blocks
                for start_n in range(0, N, BLOCK_N):
                    offs_n = start_n + tl.arange(0, BLOCK_N)
                    n_mask = offs_n < N

                    # Load K block [BLOCK_N, D]
                    k_ptrs = K_ptr + z * stride_kz + h * stride_kh + offs_n[:, None] * stride_kn + offs_d[None, :] * stride_kd
                    k = tl.load(k_ptrs, mask=n_mask[:, None] & d_mask[None, :], other=0.0).to(tl.float32)

                    # Compute scores = Q @ K^T
                    scores = tl.dot(q, tl.trans(k)) * sm_scale

                    # Apply causal mask
                    if causal:
                        causal_mask = offs_n[None, :] <= offs_m[:, None]
                        scores = tl.where(causal_mask, scores, -1e9)

                    # Apply padding masks for m/n
                    scores = tl.where(m_mask[:, None] & n_mask[None, :], scores, -1e9)

                    # Numerically stable streaming softmax update
                    m_ij = tl.max(scores, axis=1)
                    m_new = tl.maximum(m_i, m_ij)
                    alpha = tl.exp(m_i - m_new)
                    p = tl.exp(scores - m_new[:, None])
                    l_new = l_i * alpha + tl.sum(p, axis=1)

                    # Load V block [BLOCK_N, DV]
                    v_ptrs = V_ptr + z * stride_vz + h * stride_vh + offs_n[:, None] * stride_vn + offs_dv[None, :] * stride_vd
                    v = tl.load(v_ptrs, mask=n_mask[:, None] & dv_mask[None, :], other=0.0).to(tl.float32)

                    # Update accumulator
                    acc = acc * alpha[:, None] + tl.dot(p, v)

                    # Update running stats
                    m_i = m_new
                    l_i = l_new

                # Normalize and store output
                o = acc / l_i[:, None]
                o_ptrs = O_ptr + z * stride_oz + h * stride_oh + offs_m[:, None] * stride_om + offs_dv[None, :] * stride_od
                tl.store(o_ptrs, o.to(tl.float16), mask=m_mask[:, None] & dv_mask[None, :])

            def _torch_flash_attn_reference(Q, K, V, causal=True):
                # Q: [Z, H, M, D], K: [Z, H, N, D], V: [Z, H, N, DV]
                Z, H, M, D = Q.shape
                N = K.shape[2]
                DV = V.shape[-1]
                sm_scale = 1.0 / math.sqrt(D)
                # Use float32 compute for stability
                q = Q.float()
                k = K.float()
                v = V.float()
                scores = torch.matmul(q, k.transpose(-1, -2)) * sm_scale  # [Z,H,M,N]
                if causal:
                    # Create causal mask [M, N]
                    mask = torch.arange(N, device=Q.device)[None, :] <= torch.arange(M, device=Q.device)[:, None]
                    scores = scores.masked_fill(~mask, float('-inf'))
                probs = torch.softmax(scores, dim=-1)
                out = torch.matmul(probs, v)
                return out.to(Q.dtype)

            def flash_attn(Q: torch.Tensor, K: torch.Tensor, V: torch.Tensor, causal: bool = True) -> torch.Tensor:
                """
                Flash attention computation with optional causal masking.

                Args:
                    Q: (Z, H, M, Dq) float16 CUDA
                    K: (Z, H, N, Dq) float16 CUDA
                    V: (Z, H, N, Dv) float16 CUDA
                    causal: bool
                Returns:
                    (Z, H, M, Dv) float16 CUDA
                """
                assert Q.dim() == 4 and K.dim() == 4 and V.dim() == 4, "Q,K,V must be 4D"
                assert Q.shape[0] == K.shape[0] == V.shape[0], "Batch (Z) mismatch"
                assert Q.shape[1] == K.shape[1] == V.shape[1], "Heads (H) mismatch"
                assert K.shape[2] == V.shape[2], "Seq length N mismatch between K and V"
                assert Q.shape[2] > 0 and K.shape[2] > 0, "Empty sequences not supported"
                assert Q.dtype == torch.float16 and K.dtype == torch.float16 and V.dtype == torch.float16, "Inputs must be float16"
                assert Q.is_cuda and K.is_cuda and V.is_cuda, "Inputs must be CUDA tensors"
                device = Q.device

                Z, H, M, D = Q.shape
                N = K.shape[2]
                DV = V.shape[3]

                # Fallback conditions: very large D or DV not supported by kernel tile size
                BLOCK_M = 64
                BLOCK_N = 64
                BLOCK_DMODEL = 64  # supports D <= 64
                BLOCK_DV = 128     # supports DV <= 128

                if D > BLOCK_DMODEL or DV > BLOCK_DV:
                    return _torch_flash_attn_reference(Q, K, V, causal=causal)

                sm_scale = 1.0 / math.sqrt(D)

                O = torch.empty((Z, H, M, DV), dtype=torch.float16, device=device)

                grid = (triton.cdiv(M, BLOCK_M), Z * H)

                _flash_attn_fwd_kernel[grid](
                    Q, K, V, O,
                    Q.stride(0), Q.stride(1), Q.stride(2), Q.stride(3),
                    K.stride(0), K.stride(1), K.stride(2), K.stride(3),
                    V.stride(0), V.stride(1), V.stride(2), V.stride(3),
                    O.stride(0), O.stride(1), O.stride(2), O.stride(3),
                    Z, H, M, N, D, DV,
                    sm_scale,
                    causal=causal,
                    BLOCK_M=BLOCK_M,
                    BLOCK_N=BLOCK_N,
                    BLOCK_DMODEL=BLOCK_DMODEL,
                    BLOCK_DV=BLOCK_DV,
                    num_warps=4,
                    num_stages=2,
                )
                return O
        """)
        return {"code": code}