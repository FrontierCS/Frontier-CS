import math
import textwrap

class Solution:
    def solve(self, spec_path: str = None) -> dict:
        code = textwrap.dedent("""
            import math
            import torch
            import triton
            import triton.language as tl

            def _next_power_of_2(x: int) -> int:
                if x <= 1:
                    return 1
                return 1 << (x - 1).bit_length()

            @triton.jit
            def gdpa_fwd(
                Q_ptr, K_ptr, V_ptr, GQ_ptr, GK_ptr, O_ptr,
                Z, H, M, N, DQ, DV,
                stride_qz, stride_qh, stride_qm, stride_qd,
                stride_kz, stride_kh, stride_kn, stride_kd,
                stride_vz, stride_vh, stride_vn, stride_vd,
                stride_gqz, stride_gqh, stride_gqm, stride_gqd,
                stride_gkz, stride_gkh, stride_gkn, stride_gkd,
                stride_oz, stride_oh, stride_om, stride_od,
                sm_scale,
                BLOCK_M: tl.constexpr, BLOCK_N: tl.constexpr,
                HEAD_DIM: tl.constexpr, HEAD_DV: tl.constexpr
            ):
                pid_z = tl.program_id(0)
                pid_h = tl.program_id(1)
                pid_m = tl.program_id(2)

                offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
                offs_d = tl.arange(0, HEAD_DIM)
                offs_dv = tl.arange(0, HEAD_DV)

                # Base pointers per (z,h)
                q_base = Q_ptr + pid_z * stride_qz + pid_h * stride_qh
                k_base = K_ptr + pid_z * stride_kz + pid_h * stride_kh
                v_base = V_ptr + pid_z * stride_vz + pid_h * stride_vh
                gq_base = GQ_ptr + pid_z * stride_gqz + pid_h * stride_gqh
                gk_base = GK_ptr + pid_z * stride_gkz + pid_h * stride_gkh
                o_base = O_ptr + pid_z * stride_oz + pid_h * stride_oh

                # Load Q and GQ, apply gating: Qg = Q * sigmoid(GQ)
                q_ptrs = q_base + (offs_m[:, None] * stride_qm + offs_d[None, :] * stride_qd)
                gq_ptrs = gq_base + (offs_m[:, None] * stride_gqm + offs_d[None, :] * stride_gqd)
                q_mask = (offs_m[:, None] < M) & (offs_d[None, :] < DQ)
                q = tl.load(q_ptrs, mask=q_mask, other=0.0).to(tl.float32)
                gq = tl.load(gq_ptrs, mask=q_mask, other=0.0).to(tl.float32)
                gate_q = 1.0 / (1.0 + tl.exp(-gq))
                q = q * gate_q

                # Streaming softmax vars
                neg_inf = float("-inf")
                m_i = tl.full([BLOCK_M], neg_inf, dtype=tl.float32)
                l_i = tl.zeros([BLOCK_M], dtype=tl.float32)
                acc = tl.zeros([BLOCK_M, HEAD_DV], dtype=tl.float32)

                # Iterate over key/value blocks
                for start_n in range(0, N, BLOCK_N):
                    offs_n = start_n + tl.arange(0, BLOCK_N)

                    k_ptrs = k_base + (offs_n[:, None] * stride_kn + offs_d[None, :] * stride_kd)
                    gk_ptrs = gk_base + (offs_n[:, None] * stride_gkn + offs_d[None, :] * stride_gkd)
                    k_mask = (offs_n[:, None] < N) & (offs_d[None, :] < DQ)
                    k = tl.load(k_ptrs, mask=k_mask, other=0.0).to(tl.float32)
                    gk = tl.load(gk_ptrs, mask=k_mask, other=0.0).to(tl.float32)
                    gate_k = 1.0 / (1.0 + tl.exp(-gk))
                    k = k * gate_k

                    # Compute QK^T
                    qk = tl.dot(q, tl.trans(k)) * sm_scale

                    # Mask invalid rows/cols
                    row_mask = offs_m < M
                    col_mask = offs_n < N
                    qk = tl.where(col_mask[None, :], qk, neg_inf)
                    qk = tl.where(row_mask[:, None], qk, neg_inf)

                    # Numerically stable softmax update
                    m_ij = tl.max(qk, axis=1)
                    m_new = tl.maximum(m_i, m_ij)
                    alpha = tl.exp(m_i - m_new)
                    p = tl.exp(qk - m_new[:, None])
                    s_ij = tl.sum(p, axis=1)

                    # Load V
                    v_ptrs = v_base + (offs_n[:, None] * stride_vn + offs_dv[None, :] * stride_vd)
                    v_mask = (offs_n[:, None] < N) & (offs_dv[None, :] < DV)
                    v = tl.load(v_ptrs, mask=v_mask, other=0.0).to(tl.float32)

                    # Update acc and l_i
                    acc = acc * alpha[:, None] + tl.dot(p, v)
                    l_i = l_i * alpha + s_ij
                    m_i = m_new

                # Normalize
                o = acc / l_i[:, None]

                # Store
                o_ptrs = o_base + (offs_m[:, None] * stride_om + offs_dv[None, :] * stride_od)
                o_mask = (offs_m[:, None] < M) & (offs_dv[None, :] < DV)
                tl.store(o_ptrs, o.to(tl.float16), mask=o_mask)

            def gdpa_attn(Q: torch.Tensor, K: torch.Tensor, V: torch.Tensor, GQ: torch.Tensor, GK: torch.Tensor) -> torch.Tensor:
                assert Q.is_cuda and K.is_cuda and V.is_cuda and GQ.is_cuda and GK.is_cuda, "All tensors must be CUDA"
                assert Q.dtype == torch.float16 and K.dtype == torch.float16 and V.dtype == torch.float16
                assert GQ.dtype == torch.float16 and GK.dtype == torch.float16
                assert Q.dim() == 4 and K.dim() == 4 and V.dim() == 4 and GQ.dim() == 4 and GK.dim() == 4
                Zq, Hq, M, DQ = Q.shape
                Zk, Hk, Nk, DQk = K.shape
                Zv, Hv, Nv, DV = V.shape
                Zgq, Hgq, Mgq, DQgq = GQ.shape
                Zgk, Hgk, Ngk, DQgk = GK.shape

                assert Zq == Zk == Zv == Zgq == Zgk, "Batch size mismatch"
                assert Hq == Hk == Hv == Hgq == Hgk, "Head size mismatch"
                assert M == Nk == Nv == Mgq == Ngk, "Seq length mismatch"
                assert DQ == DQk == DQgq == DQgk, "Q/K feature dim mismatch"

                Z, H = Zq, Hq
                N = Nk

                # Heuristics for tile sizes
                # Use power-of-two head dims for better performance with masking
                HEAD_DIM = min(128, _next_power_of_2(int(DQ)))
                HEAD_DV = min(128, _next_power_of__2(int(DV)))
                # Block sizes tuned for L4; moderate sizes for good occupancy
                if M >= 1024:
                    BLOCK_M = 64
                    BLOCK_N = 128
                else:
                    BLOCK_M = 64
                    BLOCK_N = 64

                O = torch.empty((Z, H, M, DV), device=Q.device, dtype=torch.float16)

                sm_scale = 1.0 / math.sqrt(float(DQ))

                grid = (Z, H, triton.cdiv(M, BLOCK_M))

                gdpa_fwd[grid](
                    Q, K, V, GQ, GK, O,
                    Z, H, M, N, DQ, DV,
                    Q.stride(0), Q.stride(1), Q.stride(2), Q.stride(3),
                    K.stride(0), K.stride(1), K.stride(2), K.stride(3),
                    V.stride(0), V.stride(1), V.stride(2), V.stride(3),
                    GQ.stride(0), GQ.stride(1), GQ.stride(2), GQ.stride(3),
                    GK.stride(0), GK.stride(1), GK.stride(2), GK.stride(3),
                    O.stride(0), O.stride(1), O.stride(2), O.stride(3),
                    sm_scale,
                    BLOCK_M=BLOCK_M, BLOCK_N=BLOCK_N,
                    HEAD_DIM=HEAD_DIM, HEAD_DV=HEAD_DV,
                    num_warps=4, num_stages=2
                )
                return O
        """)
        return {"code": code}