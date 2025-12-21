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
            def _flash_attn_fwd(
                Q, K, V, Out,
                stride_qz, stride_qm, stride_qk,
                stride_kz, stride_kn, stride_kk,
                stride_vz, stride_vn, stride_vv,
                stride_oz, stride_om, stride_ov,
                ZH, sm_scale,
                N_CTX: tl.constexpr,
                BLOCK_M: tl.constexpr, BLOCK_N: tl.constexpr,
                HEAD_DIM: tl.constexpr, VALUE_DIM: tl.constexpr,
                CAUSAL: tl.constexpr,
            ):
                pid_z = tl.program_id(0)
                pid_m = tl.program_id(1)

                offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
                offs_dq = tl.arange(0, HEAD_DIM)
                offs_dv = tl.arange(0, VALUE_DIM)

                m_mask = offs_m < N_CTX

                q_ptrs = Q + pid_z * stride_qz + offs_m[:, None] * stride_qm + offs_dq[None, :] * stride_qk
                q = tl.load(q_ptrs, mask=m_mask[:, None], other=0.0).to(tl.float32)
                q = q * sm_scale

                # initialize softmax statistics
                m_i = tl.where(m_mask, -float("inf"), 0.0)
                l_i = tl.where(m_mask, 0.0, 1.0)
                acc = tl.zeros((BLOCK_M, VALUE_DIM), dtype=tl.float32)

                for start_n in range(0, N_CTX, BLOCK_N):
                    offs_n = start_n + tl.arange(0, BLOCK_N)
                    n_mask = offs_n < N_CTX

                    k_ptrs = K + pid_z * stride_kz + offs_n[:, None] * stride_kn + offs_dq[None, :] * stride_kk
                    v_ptrs = V + pid_z * stride_vz + offs_n[:, None] * stride_vn + offs_dv[None, :] * stride_vv

                    k = tl.load(k_ptrs, mask=n_mask[:, None], other=0.0).to(tl.float32)
                    v = tl.load(v_ptrs, mask=n_mask[:, None], other=0.0).to(tl.float32)

                    # compute attention scores
                    qk = tl.dot(q, tl.trans(k))

                    if CAUSAL:
                        q_idx = offs_m[:, None]
                        k_idx = offs_n[None, :]
                        causal_mask = k_idx <= q_idx
                        qk = tl.where(causal_mask, qk, float("-inf"))

                    # mask out-of-bounds positions
                    qk = tl.where(n_mask[None, :], qk, float("-inf"))
                    qk = tl.where(m_mask[:, None], qk, float("-inf"))

                    # softmax update
                    m_ij = tl.max(qk, axis=1)
                    m_new = tl.maximum(m_i, m_ij)
                    exp_logits = tl.exp(qk - m_new[:, None])
                    alpha = tl.exp(m_i - m_new)
                    l_i = l_i * alpha + tl.sum(exp_logits, axis=1)
                    acc = acc * alpha[:, None] + tl.dot(exp_logits, v)
                    m_i = m_new

                # write back
                out = acc / l_i[:, None]
                out = out.to(tl.float16)

                o_ptrs = Out + pid_z * stride_oz + offs_m[:, None] * stride_om + offs_dv[None, :] * stride_ov
                tl.store(o_ptrs, out, mask=m_mask[:, None])


            def flash_attn(Q: torch.Tensor, K: torch.Tensor, V: torch.Tensor, causal: bool = True) -> torch.Tensor:
                # Q: (Z, H, M, Dq), K: (Z, H, N, Dq), V: (Z, H, N, Dv)
                if not (Q.is_cuda and K.is_cuda and V.is_cuda):
                    raise ValueError("Q, K, V must be CUDA tensors")
                if not (Q.dtype == torch.float16 and K.dtype == torch.float16 and V.dtype == torch.float16):
                    raise TypeError("Q, K, V must be float16 tensors")

                Z, H, M, Dq = Q.shape
                Zk, Hk, N, Dk = K.shape
                Zv, Hv, Nv, Dv = V.shape

                if not (Z == Zk == Zv):
                    raise ValueError("Batch dimensions of Q, K, V must match")
                if not (H == Hk == Hv):
                    raise ValueError("Head dimensions of Q, K, V must match")
                if not (M == N == Nv):
                    raise ValueError("Sequence lengths of Q, K, V must match for flash attention")
                if Dq != Dk:
                    raise ValueError("Q and K must have the same head dimension")

                ZH = Z * H
                N_CTX = M

                Q_ = Q.contiguous().view(ZH, M, Dq)
                K_ = K.contiguous().view(ZH, N, Dq)
                V_ = V.contiguous().view(ZH, N, Dv)

                Out = torch.empty((ZH, M, Dv), device=Q.device, dtype=torch.float16)

                sm_scale = 1.0 / math.sqrt(Dq)

                BLOCK_M = 64
                BLOCK_N = 64

                grid = (ZH, triton.cdiv(N_CTX, BLOCK_M))

                _flash_attn_fwd[grid](
                    Q_, K_, V_, Out,
                    Q_.stride(0), Q_.stride(1), Q_.stride(2),
                    K_.stride(0), K_.stride(1), K_.stride(2),
                    V_.stride(0), V_.stride(1), V_.stride(2),
                    Out.stride(0), Out.stride(1), Out.stride(2),
                    ZH,
                    sm_scale,
                    N_CTX=N_CTX,
                    BLOCK_M=BLOCK_M,
                    BLOCK_N=BLOCK_N,
                    HEAD_DIM=Dq,
                    VALUE_DIM=Dv,
                    CAUSAL=causal,
                    num_warps=4,
                    num_stages=2,
                )

                return Out.view(Z, H, M, Dv)
            '''
        )
        return {"code": code}
