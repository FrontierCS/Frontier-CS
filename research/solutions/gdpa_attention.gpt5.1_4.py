import textwrap


class Solution:
    def solve(self, spec_path: str = None) -> dict:
        code = textwrap.dedent(
            '''
            import torch
            import triton
            import triton.language as tl


            @triton.jit
            def _gdpa_kernel(
                Q_ptr, K_ptr, V_ptr, GQ_ptr, GK_ptr, Out_ptr,
                Z, H, M, N, Dq, Dv,
                stride_qz, stride_qh, stride_qm, stride_qd,
                stride_kz, stride_kh, stride_kn, stride_kd,
                stride_vz, stride_vh, stride_vn, stride_vd,
                stride_gqz, stride_gqh, stride_gqm, stride_gqd,
                stride_gkz, stride_gkh, stride_gkn, stride_gkd,
                stride_oz, stride_oh, stride_om, stride_od,
                scale,
                BLOCK_M: tl.constexpr, BLOCK_N: tl.constexpr,
                BLOCK_DQ: tl.constexpr, BLOCK_DV: tl.constexpr,
            ):
                pid_m = tl.program_id(0)
                pid_b = tl.program_id(1)
                h = pid_b % H
                z = pid_b // H

                # Base pointers for this (z, h)
                Q_head = Q_ptr + z * stride_qz + h * stride_qh
                K_head = K_ptr + z * stride_kz + h * stride_kh
                V_head = V_ptr + z * stride_vz + h * stride_vh
                GQ_head = GQ_ptr + z * stride_gqz + h * stride_gqh
                GK_head = GK_ptr + z * stride_gkz + h * stride_gkh
                O_head = Out_ptr + z * stride_oz + h * stride_oh

                offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
                m_mask = offs_m < M

                offs_dv = tl.arange(0, BLOCK_DV)
                dv_mask = offs_dv < Dv

                # Initialize accumulators for streaming softmax
                NEG_INF = -1.0e9
                m_i = tl.full((BLOCK_M,), NEG_INF, dtype=tl.float32)
                l_i = tl.zeros((BLOCK_M,), dtype=tl.float32)
                acc = tl.zeros((BLOCK_M, BLOCK_DV), dtype=tl.float32)

                # Loop over key blocks
                for start_n in range(0, N, BLOCK_N):
                    offs_n = start_n + tl.arange(0, BLOCK_N)
                    n_mask = offs_n < N

                    # Compute attention logits for this (q_block, k_block)
                    S = tl.zeros((BLOCK_M, BLOCK_N), dtype=tl.float32)

                    # Loop over Dq chunks
                    for start_d in range(0, Dq, BLOCK_DQ):
                        offs_d = start_d + tl.arange(0, BLOCK_DQ)
                        dq_mask = offs_d < Dq

                        # Load and gate Q: [BLOCK_M, BLOCK_DQ]
                        q_ptrs = Q_head + offs_m[:, None] * stride_qm + offs_d[None, :] * stride_qd
                        gq_ptrs = GQ_head + offs_m[:, None] * stride_gqm + offs_d[None, :] * stride_gqd

                        q = tl.load(q_ptrs, mask=m_mask[:, None] & dq_mask[None, :], other=0.0)
                        gq = tl.load(gq_ptrs, mask=m_mask[:, None] & dq_mask[None, :], other=0.0)

                        q = q.to(tl.float32)
                        gq = gq.to(tl.float32)

                        gate_q = 1.0 / (1.0 + tl.exp(-gq))
                        qg = q * gate_q  # [M, Dq_chunk]

                        # Load and gate K as [BLOCK_DQ, BLOCK_N]
                        k_ptrs = K_head + offs_n[None, :] * stride_kn + offs_d[:, None] * stride_kd
                        gk_ptrs = GK_head + offs_n[None, :] * stride_gkn + offs_d[:, None] * stride_gkd

                        k = tl.load(k_ptrs, mask=dq_mask[:, None] & n_mask[None, :], other=0.0)
                        gk = tl.load(gk_ptrs, mask=dq_mask[:, None] & n_mask[None, :], other=0.0)

                        k = k.to(tl.float32)
                        gk = gk.to(tl.float32)

                        gate_k = 1.0 / (1.0 + tl.exp(-gk))
                        kg = k * gate_k  # [Dq_chunk, N]

                        # Accumulate logits
                        S += tl.dot(qg, kg)

                    # Scale and apply key mask
                    S = S * scale
                    S = tl.where(n_mask[None, :], S, NEG_INF)

                    # Compute new row-wise max for numerical stability
                    s_max = tl.max(S, axis=1)
                    m_i_new = tl.maximum(m_i, s_max)
                    alpha = tl.exp(m_i - m_i_new)

                    # Exponentiate logits
                    P = tl.exp(S - m_i_new[:, None])
                    P = tl.where(n_mask[None, :], P, 0.0)

                    # Update normalization factors
                    l_i = l_i * alpha + tl.sum(P, axis=1)
                    m_i = m_i_new

                    # Load V block: [BLOCK_N, BLOCK_DV]
                    v_ptrs = V_head + offs_n[:, None] * stride_vn + offs_dv[None, :] * stride_vd
                    V_block = tl.load(v_ptrs, mask=n_mask[:, None] & dv_mask[None, :], other=0.0)
                    V_block = V_block.to(tl.float32)

                    # Update output accumulator: [BLOCK_M, BLOCK_DV]
                    acc = acc * alpha[:, None] + tl.dot(P, V_block)

                # Normalize and store
                l_i = tl.maximum(l_i, 1e-6)
                out = acc / l_i[:, None]
                out = out.to(tl.float16)

                o_ptrs = O_head + offs_m[:, None] * stride_om + offs_dv[None, :] * stride_od
                tl.store(o_ptrs, out, mask=m_mask[:, None] & dv_mask[None, :])


            def gdpa_attn(Q: torch.Tensor, K: torch.Tensor, V: torch.Tensor, GQ: torch.Tensor, GK: torch.Tensor) -> torch.Tensor:
                """
                GDPA attention computation with gated Q and K tensors.
                """
                if Q.device.type != "cuda":
                    # Fallback to PyTorch implementation on CPU
                    Dq = Q.size(-1)
                    scale = 1.0 / (Dq ** 0.5)
                    Qg = Q * torch.sigmoid(GQ)
                    Kg = K * torch.sigmoid(GK)
                    scores = torch.matmul(Qg, Kg.transpose(-1, -2)) * scale
                    attn = torch.softmax(scores, dim=-1)
                    return torch.matmul(attn, V).to(Q.dtype)

                assert Q.dtype == torch.float16
                assert K.dtype == torch.float16
                assert V.dtype == torch.float16
                assert GQ.dtype == torch.float16
                assert GK.dtype == torch.float16

                Z, H, M, Dq = Q.shape
                Zk, Hk, N, Dq_k = K.shape
                Zv, Hv, N_v, Dv = V.shape

                assert Z == Zk == Zv
                assert H == Hk == Hv
                assert Dq == Dq_k
                assert N == N_v
                assert GQ.shape == Q.shape
                assert GK.shape == K.shape

                scale = 1.0 / float(Dq ** 0.5)

                Out = torch.empty((Z, H, M, Dv), device=Q.device, dtype=torch.float16)

                # Kernel configuration
                BLOCK_M = 64
                BLOCK_N = 64

                def _next_pow2(v: int) -> int:
                    if v <= 1:
                        return 1
                    return 1 << (v - 1).bit_length()

                BLOCK_DQ = min(128, _next_pow2(Dq))
                BLOCK_DV = min(128, _next_pow2(Dv))

                grid = (triton.cdiv(M, BLOCK_M), Z * H)

                _gdpa_kernel[grid](
                    Q, K, V, GQ, GK, Out,
                    Z, H, M, N, Dq, Dv,
                    *Q.stride(),
                    *K.stride(),
                    *V.stride(),
                    *GQ.stride(),
                    *GK.stride(),
                    *Out.stride(),
                    scale,
                    BLOCK_M=BLOCK_M,
                    BLOCK_N=BLOCK_N,
                    BLOCK_DQ=BLOCK_DQ,
                    BLOCK_DV=BLOCK_DV,
                    num_warps=4,
                    num_stages=2,
                )

                return Out
            '''
        )
        return {"code": code}