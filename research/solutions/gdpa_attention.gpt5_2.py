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
                stride_qz, stride_qh, stride_qm, stride_qd,
                stride_kz, stride_kh, stride_kn, stride_kd,
                stride_vz, stride_vh, stride_vn, stride_vd,
                stride_gqz, stride_gqh, stride_gqm, stride_gqd,
                stride_gkz, stride_gkh, stride_gkn, stride_gkd,
                stride_oz, stride_oh, stride_om, stride_od,
                Z, H, M, N,
                scale,
                BLOCK_M: tl.constexpr, BLOCK_N: tl.constexpr,
                D_HEAD: tl.constexpr, D_VALUE: tl.constexpr,
            ):
                pid_z = tl.program_id(0)
                pid_h = tl.program_id(1)
                pid_m = tl.program_id(2)

                offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
                offs_dq = tl.arange(0, D_HEAD)
                offs_dv = tl.arange(0, D_VALUE)

                m_mask = offs_m < M

                # Load Q and GQ, apply gating
                q_ptrs = Q_ptr + pid_z * stride_qz + pid_h * stride_qh + offs_m[:, None] * stride_qm + offs_dq[None, :] * stride_qd
                gq_ptrs = GQ_ptr + pid_z * stride_gqz + pid_h * stride_gqh + offs_m[:, None] * stride_gqm + offs_dq[None, :] * stride_gqd
                q = tl.load(q_ptrs, mask=m_mask[:, None], other=0.0).to(tl.float32)
                gq = tl.load(gq_ptrs, mask=m_mask[:, None], other=0.0).to(tl.float32)
                s_q = 1.0 / (1.0 + tl.exp(-gq))
                q = q * s_q

                # Initialize streaming softmax state
                m_i = tl.full([BLOCK_M], -float('inf'), tl.float32)
                l_i = tl.zeros([BLOCK_M], tl.float32)
                acc = tl.zeros([BLOCK_M, D_VALUE], tl.float32)

                offs_n = tl.arange(0, BLOCK_N)
                for start_n in range(0, N, BLOCK_N):
                    n_idx = start_n + offs_n
                    n_mask = n_idx < N

                    # Load K and GK, apply gating
                    k_ptrs = K_ptr + pid_z * stride_kz + pid_h * stride_kh + n_idx[:, None] * stride_kn + offs_dq[None, :] * stride_kd
                    gk_ptrs = GK_ptr + pid_z * stride_gkz + pid_h * stride_gkh + n_idx[:, None] * stride_gkn + offs_dq[None, :] * stride_gkd
                    k = tl.load(k_ptrs, mask=n_mask[:, None], other=0.0).to(tl.float32)
                    gk = tl.load(gk_ptrs, mask=n_mask[:, None], other=0.0).to(tl.float32)
                    s_k = 1.0 / (1.0 + tl.exp(-gk))
                    k = k * s_k

                    # Compute qk = Qg @ Kg^T
                    qk = tl.dot(q, tl.trans(k)) * scale  # [BLOCK_M, BLOCK_N]

                    # Compute numerically stable streaming softmax update
                    m_ij = tl.max(qk, 1)  # max over BLOCK_N
                    m_new = tl.maximum(m_i, m_ij)
                    p = tl.exp(qk - m_new[:, None])
                    alpha = tl.exp(m_i - m_new)
                    l_new = alpha * l_i + tl.sum(p, 1)

                    # Load V block
                    v_ptrs = V_ptr + pid_z * stride_vz + pid_h * stride_vh + n_idx[:, None] * stride_vn + offs_dv[None, :] * stride_vd
                    v = tl.load(v_ptrs, mask=n_mask[:, None], other=0.0).to(tl.float32)

                    # Accumulate output
                    acc = acc * alpha[:, None] + tl.dot(p.to(tl.float32), v)

                    # Update state
                    m_i = m_new
                    l_i = l_new

                # Normalize and store
                out = acc / l_i[:, None]
                o_ptrs = O_ptr + pid_z * stride_oz + pid_h * stride_oh + offs_m[:, None] * stride_om + offs_dv[None, :] * stride_od
                tl.store(o_ptrs, out.to(tl.float16), mask=m_mask[:, None])


            def gdpa_attn(Q: torch.Tensor, K: torch.Tensor, V: torch.Tensor, GQ: torch.Tensor, GK: torch.Tensor) -> torch.Tensor:
                Z, H, M, Dq = Q.shape
                Zk, Hk, N, Dqk = K.shape
                Zv, Hv, Nv, Dv = V.shape
                assert Z == Zk == Zv
                assert H == Hk == Hv
                assert Dq == Dqk
                assert N == Nv
                assert Q.is_cuda and K.is_cuda and V.is_cuda and GQ.is_cuda and GK.is_cuda
                assert Q.dtype == torch.float16 and K.dtype == torch.float16 and V.dtype == torch.float16
                assert GQ.dtype == torch.float16 and GK.dtype == torch.float16

                O = torch.empty((Z, H, M, Dv), device=Q.device, dtype=torch.float16)

                BLOCK_M = 64
                BLOCK_N = 64
                num_warps = 4 if max(BLOCK_M, BLOCK_N) <= 64 else 8
                num_stages = 3

                grid = (Z, H, (M + BLOCK_M - 1) // BLOCK_M)
                scale = 1.0 / math.sqrt(float(Dq))

                _gdpa_fwd_kernel[grid](
                    Q, K, V, GQ, GK, O,
                    Q.stride(0), Q.stride(1), Q.stride(2), Q.stride(3),
                    K.stride(0), K.stride(1), K.stride(2), K.stride(3),
                    V.stride(0), V.stride(1), V.stride(2), V.stride(3),
                    GQ.stride(0), GQ.stride(1), GQ.stride(2), GQ.stride(3),
                    GK.stride(0), GK.stride(1), GK.stride(2), GK.stride(3),
                    O.stride(0), O.stride(1), O.stride(2), O.stride(3),
                    Z, H, M, N,
                    scale,
                    BLOCK_M=BLOCK_M, BLOCK_N=BLOCK_N,
                    D_HEAD=Dq, D_VALUE=Dv,
                    num_warps=num_warps, num_stages=num_stages
                )
                return O
        """)
        return {"code": code}