import textwrap


class Solution:
    def solve(self, spec_path: str = None) -> dict:
        code = textwrap.dedent(
            '''
            import math
            import torch
            import triton
            import triton.language as tl


            @triton.jit
            def _gdpa_fwd_kernel(
                Q_ptr, K_ptr, V_ptr, GQ_ptr, GK_ptr, O_ptr,
                B, M, N, D_HEAD, D_VALUE,
                stride_qb, stride_qm, stride_qd,
                stride_kb, stride_kn, stride_kd,
                stride_vb, stride_vn, stride_vd,
                stride_gqb, stride_gqm, stride_gqd,
                stride_gkb, stride_gkn, stride_gkd,
                stride_ob, stride_om, stride_od,
                BLOCK_M: tl.constexpr, BLOCK_N: tl.constexpr,
                BLOCK_D_HEAD: tl.constexpr, BLOCK_D_VALUE: tl.constexpr,
            ):
                bh = tl.program_id(0)
                m_block = tl.program_id(1)

                offs_m = m_block * BLOCK_M + tl.arange(0, BLOCK_M)
                offs_dh = tl.arange(0, BLOCK_D_HEAD)
                offs_dv = tl.arange(0, BLOCK_D_VALUE)

                m_mask = offs_m < M
                dh_mask = offs_dh < D_HEAD
                dv_mask = offs_dv < D_VALUE

                # Load Q and GQ block and apply gating once per query block
                q_ptrs = Q_ptr + bh * stride_qb + offs_m[:, None] * stride_qm + offs_dh[None, :] * stride_qd
                gq_ptrs = GQ_ptr + bh * stride_gqb + offs_m[:, None] * stride_gqm + offs_dh[None, :] * stride_gqd

                q = tl.load(q_ptrs, mask=m_mask[:, None] & dh_mask[None, :], other=0.0)
                gq = tl.load(gq_ptrs, mask=m_mask[:, None] & dh_mask[None, :], other=0.0)

                q = q.to(tl.float32)
                gq = gq.to(tl.float32)
                qg = q * tl.sigmoid(gq)  # [BLOCK_M, BLOCK_D_HEAD]

                # Scaling factor 1 / sqrt(D_HEAD)
                scale = 1.0 / tl.sqrt(tl.float32(D_HEAD))

                # Streaming softmax state
                m_i = tl.full((BLOCK_M,), -float("inf"), dtype=tl.float32)
                l_i = tl.zeros((BLOCK_M,), dtype=tl.float32)
                acc = tl.zeros((BLOCK_M, BLOCK_D_VALUE), dtype=tl.float32)

                n_start = 0
                NEG_INF = -1.0e9

                while n_start < N:
                    offs_n = n_start + tl.arange(0, BLOCK_N)
                    n_mask = offs_n < N

                    k_ptrs = K_ptr + bh * stride_kb + offs_n[:, None] * stride_kn + offs_dh[None, :] * stride_kd
                    gk_ptrs = GK_ptr + bh * stride_gkb + offs_n[:, None] * stride_gkn + offs_dh[None, :] * stride_gkd
                    v_ptrs = V_ptr + bh * stride_vb + offs_n[:, None] * stride_vn + offs_dv[None, :] * stride_vd

                    k = tl.load(k_ptrs, mask=n_mask[:, None] & dh_mask[None, :], other=0.0)
                    gk = tl.load(gk_ptrs, mask=n_mask[:, None] & dh_mask[None, :], other=0.0)
                    v = tl.load(v_ptrs, mask=n_mask[:, None] & dv_mask[None, :], other=0.0)

                    k = k.to(tl.float32)
                    gk = gk.to(tl.float32)
                    v = v.to(tl.float32)

                    kg = k * tl.sigmoid(gk)  # [BLOCK_N, BLOCK_D_HEAD]

                    # Attention logits for current key block
                    qk = tl.dot(qg, tl.trans(kg)) * scale  # [BLOCK_M, BLOCK_N]

                    # Mask out-of-range keys so they don't contribute
                    qk = tl.where(n_mask[None, :], qk, NEG_INF)

                    # Numerically stable streaming softmax update
                    m_ij = tl.max(qk, axis=1)
                    m_new = tl.maximum(m_i, m_ij)

                    p = tl.exp(qk - m_new[:, None])
                    l_ij = tl.sum(p, axis=1)

                    l_new = l_i * tl.exp(m_i - m_new) + l_ij

                    # Previous accumulator contribution
                    acc_scale = tl.where(l_new > 0, l_i * tl.exp(m_i - m_new) / l_new, 0.0)
                    acc = acc * acc_scale[:, None]

                    # Current block contribution
                    pv = tl.dot(p, v)  # [BLOCK_M, BLOCK_D_VALUE]
                    acc += pv * (1.0 / l_new)[:, None]

                    m_i = m_new
                    l_i = l_new

                    n_start += BLOCK_N

                # Store output
                o_ptrs = O_ptr + bh * stride_ob + offs_m[:, None] * stride_om + offs_dv[None, :] * stride_od
                tl.store(o_ptrs, acc.to(tl.float16), mask=m_mask[:, None] & dv_mask[None, :])


            def _gdpa_attn_baseline(Q: torch.Tensor,
                                    K: torch.Tensor,
                                    V: torch.Tensor,
                                    GQ: torch.Tensor,
                                    GK: torch.Tensor) -> torch.Tensor:
                Z, H, M, Dq = Q.shape
                Zk, Hk, N, Dqk = K.shape
                Zv, Hv, Nv, Dv = V.shape
                assert Z == Zk == Zv
                assert H == Hk == Hv
                assert M == N == Nv
                assert Dq == Dqk

                Qg = Q * torch.sigmoid(GQ)
                Kg = K * torch.sigmoid(GK)
                scale = 1.0 / math.sqrt(Dq)
                attn_logits = torch.matmul(Qg, Kg.transpose(-2, -1)) * scale
                attn = torch.softmax(attn_logits, dim=-1)
                out = torch.matmul(attn, V)
                return out


            def gdpa_attn(Q: torch.Tensor,
                          K: torch.Tensor,
                          V: torch.Tensor,
                          GQ: torch.Tensor,
                          GK: torch.Tensor) -> torch.Tensor:
                """
                GDPA attention computation with gated Q and K tensors.
                
                Args:
                    Q: (Z, H, M, Dq) float16 CUDA
                    K: (Z, H, N, Dq) float16 CUDA
                    V: (Z, H, N, Dv) float16 CUDA
                    GQ: (Z, H, M, Dq) float16 CUDA
                    GK: (Z, H, N, Dq) float16 CUDA
                
                Returns:
                    (Z, H, M, Dv) float16 CUDA
                """
                assert Q.dim() == 4 and K.dim() == 4 and V.dim() == 4
                assert GQ.shape == Q.shape
                assert GK.shape == K.shape

                Z, H, M, Dq = Q.shape
                Zk, Hk, N, Dqk = K.shape
                Zv, Hv, Nv, Dv = V.shape

                assert Z == Zk == Zv
                assert H == Hk == Hv
                assert M == N == Nv
                assert Dq == Dqk

                use_triton = (
                    Q.is_cuda and K.is_cuda and V.is_cuda and
                    GQ.is_cuda and GK.is_cuda and
                    Q.dtype == torch.float16 and
                    K.dtype == torch.float16 and
                    V.dtype == torch.float16 and
                    GQ.dtype == torch.float16 and
                    GK.dtype == torch.float16 and
                    Dq <= 64 and
                    Dv <= 64
                )

                if not use_triton:
                    return _gdpa_attn_baseline(Q, K, V, GQ, GK)

                device = Q.device
                B = Z * H

                Qh = Q.contiguous().view(B, M, Dq)
                Kh = K.contiguous().view(B, N, Dq)
                Vh = V.contiguous().view(B, N, Dv)
                GQh = GQ.contiguous().view(B, M, Dq)
                GKh = GK.contiguous().view(B, N, Dq)

                Oh = torch.empty((B, M, Dv), device=device, dtype=torch.float16)

                BLOCK_M = 64
                BLOCK_N = 64
                BLOCK_D_HEAD = 64
                BLOCK_D_VALUE = 64

                grid = (B, triton.cdiv(M, BLOCK_M))

                _gdpa_fwd_kernel[grid](
                    Qh, Kh, Vh, GQh, GKh, Oh,
                    B, M, N, Dq, Dv,
                    Qh.stride(0), Qh.stride(1), Qh.stride(2),
                    Kh.stride(0), Kh.stride(1), Kh.stride(2),
                    Vh.stride(0), Vh.stride(1), Vh.stride(2),
                    GQh.stride(0), GQh.stride(1), GQh.stride(2),
                    GKh.stride(0), GKh.stride(1), GKh.stride(2),
                    Oh.stride(0), Oh.stride(1), Oh.stride(2),
                    BLOCK_M=BLOCK_M,
                    BLOCK_N=BLOCK_N,
                    BLOCK_D_HEAD=BLOCK_D_HEAD,
                    BLOCK_D_VALUE=BLOCK_D_VALUE,
                    num_warps=4,
                    num_stages=2,
                )

                out = Oh.view(Z, H, M, Dv)
                return out
            '''
        )
        return {"code": code}
