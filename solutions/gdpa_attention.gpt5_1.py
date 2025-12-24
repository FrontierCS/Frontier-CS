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
            def _gdpa_fwd_kernel(
                Q_ptr, K_ptr, V_ptr, GQ_ptr, GK_ptr, O_ptr,
                Z, H, M,
                stride_qz, stride_qh, stride_qm, stride_qd,
                stride_kz, stride_kh, stride_kn, stride_kd,
                stride_vz, stride_vh, stride_vn, stride_vd,
                stride_gqz, stride_gqh, stride_gqm, stride_gqd,
                stride_gkz, stride_gkh, stride_gkn, stride_gkd,
                stride_oz, stride_oh, stride_om, stride_od,
                sm_scale: tl.constexpr,
                N_CTX: tl.constexpr,
                D_HEAD: tl.constexpr,
                D_VALUE: tl.constexpr,
                BLOCK_M: tl.constexpr,
                BLOCK_N: tl.constexpr,
            ):
                pid = tl.program_id(axis=0)
                num_m = tl.cdiv(M, BLOCK_M)
                total_hz = Z * H
                hz_id = pid // num_m
                m_block_id = pid % num_m
                z_id = hz_id // H
                h_id = hz_id % H

                m_offs = m_block_id * BLOCK_M + tl.arange(0, BLOCK_M)
                n_offs_base = tl.arange(0, BLOCK_N)
                d_offs = tl.arange(0, D_HEAD)
                dv_offs = tl.arange(0, D_VALUE)

                # Pointers for Q and GQ
                q_ptrs = Q_ptr + z_id * stride_qz + h_id * stride_qh + m_offs[:, None] * stride_qm + d_offs[None, :] * stride_qd
                gq_ptrs = GQ_ptr + z_id * stride_gqz + h_id * stride_gqh + m_offs[:, None] * stride_gqm + d_offs[None, :] * stride_gqd

                # Load Q and GQ, apply gating
                q = tl.load(q_ptrs, mask=(m_offs[:, None] < M), other=0.0)
                gq = tl.load(gq_ptrs, mask=(m_offs[:, None] < M), other=0.0)
                gq_f32 = gq.to(tl.float32)
                gate_q = 1.0 / (1.0 + tl.exp(-gq_f32))
                qg = q * gate_q.to(q.dtype)

                # Initialize streaming softmax state
                m_i = tl.full([BLOCK_M], -float("inf"), dtype=tl.float32)
                l_i = tl.zeros([BLOCK_M], dtype=tl.float32)
                acc = tl.zeros([BLOCK_M, D_VALUE], dtype=tl.float32)

                # Loop over K/V blocks
                for n_start in range(0, N_CTX, BLOCK_N):
                    n_offs = n_start + n_offs_base

                    # Load K and GK, apply gating
                    k_ptrs = K_ptr + z_id * stride_kz + h_id * stride_kh + n_offs[:, None] * stride_kn + d_offs[None, :] * stride_kd
                    gk_ptrs = GK_ptr + z_id * stride_gkz + h_id * stride_gkh + n_offs[:, None] * stride_gkn + d_offs[None, :] * stride_gkd
                    k = tl.load(k_ptrs, mask=(n_offs[:, None] < N_CTX), other=0.0)
                    gk = tl.load(gk_ptrs, mask=(n_offs[:, None] < N_CTX), other=0.0)
                    gk_f32 = gk.to(tl.float32)
                    gate_k = 1.0 / (1.0 + tl.exp(-gk_f32))
                    kg = k * gate_k.to(k.dtype)

                    # Compute attention scores
                    scores = tl.dot(qg, tl.trans(kg))
                    scores = scores.to(tl.float32) * sm_scale

                    # Apply masks for out-of-bounds rows/cols
                    valid_m = m_offs < M
                    valid_n = n_offs < N_CTX
                    scores = tl.where(valid_m[:, None] & valid_n[None, :], scores, -1e9)

                    # Compute streaming softmax update
                    row_max = tl.max(scores, axis=1)
                    m_new = tl.maximum(m_i, row_max)
                    alpha = tl.exp(m_i - m_new)

                    p = tl.exp(scores - m_new[:, None])
                    p = tl.where(valid_m[:, None] & valid_n[None, :], p, 0.0)

                    l_new = l_i * alpha + tl.sum(p, axis=1)

                    # Load V block
                    v_ptrs = V_ptr + z_id * stride_vz + h_id * stride_vh + n_offs[:, None] * stride_vn + dv_offs[None, :] * stride_vd
                    v = tl.load(v_ptrs, mask=(n_offs[:, None] < N_CTX), other=0.0)

                    # Accumulate numerator
                    update = tl.dot(p.to(tl.float16), v)  # float32 accumulation
                    acc = acc * alpha[:, None] + update

                    # Update m and l
                    m_i = m_new
                    l_i = l_new

                # Normalize
                l_safe = tl.where(m_offs < M, l_i, 1.0)
                out = acc / l_safe[:, None]

                # Store results
                o_ptrs = O_ptr + z_id * stride_oz + h_id * stride_oh + m_offs[:, None] * stride_om + dv_offs[None, :] * stride_od
                tl.store(o_ptrs, out.to(tl.float16), mask=(m_offs[:, None] < M))

            def gdpa_attn(Q: torch.Tensor, K: torch.Tensor, V: torch.Tensor, GQ: torch.Tensor, GK: torch.Tensor) -> torch.Tensor:
                assert Q.is_cuda and K.is_cuda and V.is_cuda and GQ.is_cuda and GK.is_cuda, "All tensors must be CUDA tensors"
                assert Q.dtype == torch.float16 and K.dtype == torch.float16 and V.dtype == torch.float16, "Q, K, V must be float16"
                assert GQ.dtype == torch.float16 and GK.dtype == torch.float16, "GQ, GK must be float16"
                assert Q.ndim == 4 and K.ndim == 4 and V.ndim == 4 and GQ.ndim == 4 and GK.ndim == 4, "Input tensors must be 4D"
                Z, H, M, Dq = Q.shape
                Zk, Hk, N, Dk = K.shape
                Zv, Hv, Nv, Dv = V.shape
                assert Z == Zk == Zv and H == Hk == Hv and Dq == Dk and M == N == Nv, "Shape mismatch"
                assert GQ.shape == Q.shape and GK.shape == K.shape, "Gate shapes must match Q and K"

                # Output
                O = torch.empty((Z, H, M, Dv), device=Q.device, dtype=torch.float16)

                # Strides (in elements)
                stride_qz, stride_qh, stride_qm, stride_qd = Q.stride()
                stride_kz, stride_kh, stride_kn, stride_kd = K.stride()
                stride_vz, stride_vh, stride_vn, stride_vd = V.stride()
                stride_gqz, stride_gqh, stride_gqm, stride_gqd = GQ.stride()
                stride_gkz, stride_gkh, stride_gkn, stride_gkd = GK.stride()
                stride_oz, stride_oh, stride_om, stride_od = O.stride()

                # Block sizes
                # Choose tiles tuned for head_dim=64, value_dim up to 128
                BLOCK_M = 128 if M >= 128 else 64
                BLOCK_N = 64

                # Grid
                grid = ( (Z * H) * triton.cdiv(M, BLOCK_M), )

                sm_scale = 1.0 / math.sqrt(Dq)

                num_warps = 8 if BLOCK_M >= 128 else 4
                num_stages = 2

                _gdpa_fwd_kernel[grid](
                    Q, K, V, GQ, GK, O,
                    Z, H, M,
                    stride_qz, stride_qh, stride_qm, stride_qd,
                    stride_kz, stride_kh, stride_kn, stride_kd,
                    stride_vz, stride_vh, stride_vn, stride_vd,
                    stride_gqz, stride_gqh, stride_gqm, stride_gqd,
                    stride_gkz, stride_gkh, stride_gkn, stride_gkd,
                    stride_oz, stride_oh, stride_om, stride_od,
                    sm_scale,
                    N_CTX=N,
                    D_HEAD=Dq,
                    D_VALUE=Dv,
                    BLOCK_M=BLOCK_M,
                    BLOCK_N=BLOCK_N,
                    num_warps=num_warps,
                    num_stages=num_stages,
                )
                return O
        """)
        return {"code": code}
