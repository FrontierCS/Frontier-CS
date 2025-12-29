import textwrap

class Solution:
    def solve(self, spec_path: str = None) -> dict:
        code = textwrap.dedent(
            r"""
            import math
            import torch
            import triton
            import triton.language as tl


            @triton.jit
            def _flash_attn_fwd(
                Q_ptr, K_ptr, V_ptr, O_ptr,
                stride_qz, stride_qh, stride_qm, stride_qd,
                stride_kz, stride_kh, stride_kn, stride_kd,
                stride_vz, stride_vh, stride_vn, stride_vd,
                stride_oz, stride_oh, stride_om, stride_od,
                H: tl.constexpr,
                sm_scale,
                M_CTX: tl.constexpr,
                N_CTX: tl.constexpr,
                D_HEAD: tl.constexpr,
                D_V: tl.constexpr,
                CAUSAL: tl.constexpr,
                BLOCK_M: tl.constexpr,
                BLOCK_N: tl.constexpr,
            ):
                pid_m = tl.program_id(0)
                pid_bh = tl.program_id(1)

                z = pid_bh // H
                h = pid_bh - z * H

                Q_ptr = Q_ptr + z * stride_qz + h * stride_qh
                K_ptr = K_ptr + z * stride_kz + h * stride_kh
                V_ptr = V_ptr + z * stride_vz + h * stride_vh
                O_ptr = O_ptr + z * stride_oz + h * stride_oh

                offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
                row_mask = offs_m < M_CTX

                offs_d = tl.arange(0, D_HEAD)
                tl.multiple_of(offs_d, 8)

                sm_scale_f16 = tl.full((), sm_scale, tl.float16)

                q = tl.load(
                    Q_ptr + offs_m[:, None] * stride_qm + offs_d[None, :] * stride_qd,
                    mask=row_mask[:, None],
                    other=0.0,
                ).to(tl.float16)
                q = (q * sm_scale_f16).to(tl.float16)

                m_i = tl.where(row_mask, -float("inf"), 0.0).to(tl.float32)
                l_i = tl.where(row_mask, 0.0, 1.0).to(tl.float32)

                offs_dv = tl.arange(0, D_V)
                tl.multiple_of(offs_dv, 8)

                acc = tl.zeros((BLOCK_M, D_V), dtype=tl.float32)

                for start_n in tl.static_range(0, N_CTX, BLOCK_N):
                    offs_n = start_n + tl.arange(0, BLOCK_N)
                    col_mask = offs_n < N_CTX

                    k = tl.load(
                        K_ptr + offs_n[None, :] * stride_kn + offs_d[:, None] * stride_kd,
                        mask=col_mask[None, :],
                        other=0.0,
                    ).to(tl.float16)

                    qk = tl.dot(q, k)  # fp32 accumulator

                    if CAUSAL:
                        causal_mask = offs_n[None, :] <= offs_m[:, None]
                    else:
                        causal_mask = True

                    mask = row_mask[:, None] & col_mask[None, :] & causal_mask
                    qk = tl.where(mask, qk, -float("inf"))

                    m_ij = tl.max(qk, axis=1)
                    m_new = tl.maximum(m_i, m_ij)

                    exp_m = tl.exp(m_i - m_new)
                    p = tl.exp(qk - m_new[:, None])

                    l_new = l_i * exp_m + tl.sum(p, axis=1)

                    v = tl.load(
                        V_ptr + offs_n[:, None] * stride_vn + offs_dv[None, :] * stride_vd,
                        mask=col_mask[:, None],
                        other=0.0,
                    ).to(tl.float16)

                    p16 = p.to(tl.float16)
                    acc = acc * exp_m[:, None] + tl.dot(p16, v)

                    m_i = m_new
                    l_i = l_new

                out = acc / l_i[:, None]
                out = out.to(tl.float16)

                tl.store(
                    O_ptr + offs_m[:, None] * stride_om + offs_dv[None, :] * stride_od,
                    out,
                    mask=row_mask[:, None],
                )


            def flash_attn(Q: torch.Tensor, K: torch.Tensor, V: torch.Tensor, causal: bool = True) -> torch.Tensor:
                assert Q.is_cuda and K.is_cuda and V.is_cuda
                assert Q.dtype == torch.float16 and K.dtype == torch.float16 and V.dtype == torch.float16
                assert Q.ndim == 4 and K.ndim == 4 and V.ndim == 4
                Z, H, M, D = Q.shape
                Zk, Hk, N, Dk = K.shape
                Zv, Hv, Nv, Dv = V.shape
                assert Zk == Z and Zv == Z and Hk == H and Hv == H and Dk == D and Nv == N

                sm_scale = 1.0 / math.sqrt(D)

                O = torch.empty((Z, H, M, Dv), device=Q.device, dtype=torch.float16)

                if causal:
                    if M >= 2048:
                        BLOCK_M, BLOCK_N = 128, 64
                        num_warps, num_stages = 8, 4
                    else:
                        BLOCK_M, BLOCK_N = 128, 64
                        num_warps, num_stages = 4, 4
                else:
                    if M >= 2048:
                        BLOCK_M, BLOCK_N = 128, 128
                        num_warps, num_stages = 8, 4
                    else:
                        BLOCK_M, BLOCK_N = 128, 128
                        num_warps, num_stages = 4, 4

                grid = (triton.cdiv(M, BLOCK_M), Z * H)

                _flash_attn_fwd[grid](
                    Q, K, V, O,
                    Q.stride(0), Q.stride(1), Q.stride(2), Q.stride(3),
                    K.stride(0), K.stride(1), K.stride(2), K.stride(3),
                    V.stride(0), V.stride(1), V.stride(2), V.stride(3),
                    O.stride(0), O.stride(1), O.stride(2), O.stride(3),
                    H=H,
                    sm_scale=sm_scale,
                    M_CTX=M,
                    N_CTX=N,
                    D_HEAD=D,
                    D_V=Dv,
                    CAUSAL=causal,
                    BLOCK_M=BLOCK_M,
                    BLOCK_N=BLOCK_N,
                    num_warps=num_warps,
                    num_stages=num_stages,
                )
                return O
            """
        ).strip()
        return {"code": code}