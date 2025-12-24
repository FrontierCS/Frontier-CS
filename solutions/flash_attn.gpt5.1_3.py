import textwrap


class Solution:
    def solve(self, spec_path: str = None) -> dict:
        code = textwrap.dedent(
            '''\
            import math
            import torch
            import triton
            import triton.language as tl


            @triton.autotune(
                configs=[
                    triton.Config(
                        {'BLOCK_M': 64, 'BLOCK_N': 64, 'BLOCK_DMODEL': 64, 'BLOCK_DV': 64},
                        num_warps=4,
                        num_stages=2,
                    ),
                    triton.Config(
                        {'BLOCK_M': 128, 'BLOCK_N': 64, 'BLOCK_DMODEL': 64, 'BLOCK_DV': 64},
                        num_warps=8,
                        num_stages=2,
                    ),
                    triton.Config(
                        {'BLOCK_M': 64, 'BLOCK_N': 128, 'BLOCK_DMODEL': 64, 'BLOCK_DV': 64},
                        num_warps=8,
                        num_stages=2,
                    ),
                ],
                key=['M', 'N'],
            )
            @triton.jit
            def flash_attn_fwd_kernel(
                Q, K, V, Out,
                stride_qz, stride_qh, stride_qm, stride_qd,
                stride_kz, stride_kh, stride_kn, stride_kd,
                stride_vz, stride_vh, stride_vn, stride_vd,
                stride_oz, stride_oh, stride_om, stride_od,
                Z, H, M, N, D, Dv, sm_scale,
                causal: tl.constexpr,
                BLOCK_M: tl.constexpr, BLOCK_N: tl.constexpr, BLOCK_DMODEL: tl.constexpr, BLOCK_DV: tl.constexpr,
            ):
                pid_bh = tl.program_id(0)
                pid_m = tl.program_id(1)

                z = pid_bh // H
                h = pid_bh % H

                offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
                mask_m = offs_m < M

                q_ptr = Q + z * stride_qz + h * stride_qh
                k_ptr = K + z * stride_kz + h * stride_kh
                v_ptr = V + z * stride_vz + h * stride_vh
                o_ptr = Out + z * stride_oz + h * stride_oh

                m_i = tl.zeros((BLOCK_M,), dtype=tl.float32)
                l_i = tl.zeros((BLOCK_M,), dtype=tl.float32)
                offs_dv = tl.arange(0, BLOCK_DV)
                mask_dv = offs_dv < Dv
                acc = tl.zeros((BLOCK_M, BLOCK_DV), dtype=tl.float32)

                for start_n in range(0, N, BLOCK_N):
                    offs_n = start_n + tl.arange(0, BLOCK_N)
                    mask_n = offs_n < N

                    S = tl.zeros((BLOCK_M, BLOCK_N), dtype=tl.float32)

                    for d0 in range(0, D, BLOCK_DMODEL):
                        offs_d = d0 + tl.arange(0, BLOCK_DMODEL)
                        mask_d = offs_d < D

                        q = tl.load(
                            q_ptr + offs_m[:, None] * stride_qm + offs_d[None, :] * stride_qd,
                            mask=mask_m[:, None] & mask_d[None, :],
                            other=0.0,
                        )
                        k = tl.load(
                            k_ptr + offs_n[:, None] * stride_kn + offs_d[None, :] * stride_kd,
                            mask=mask_n[:, None] & mask_d[None, :],
                            other=0.0,
                        )

                        q = q.to(tl.float32)
                        k = k.to(tl.float32)

                        S += tl.dot(q, tl.trans(k))

                    S = S * sm_scale

                    if causal:
                        q_idx = offs_m[:, None]
                        k_idx = offs_n[None, :]
                        causal_mask = k_idx <= q_idx
                        S = tl.where(causal_mask, S, float('-inf'))

                    S = tl.where(mask_m[:, None] & mask_n[None, :], S, float('-inf'))

                    max_S = tl.max(S, axis=1)
                    m_new = tl.maximum(m_i, max_S)

                    S_shifted = S - m_new[:, None]
                    p = tl.exp(S_shifted)
                    p_sum = tl.sum(p, axis=1)

                    alpha = tl.exp(m_i - m_new)
                    l_new = l_i * alpha + p_sum

                    v = tl.load(
                        v_ptr + offs_n[:, None] * stride_vn + offs_dv[None, :] * stride_vd,
                        mask=mask_n[:, None] & mask_dv[None, :],
                        other=0.0,
                    )
                    v = v.to(tl.float32)

                    pv = tl.dot(p.to(tl.float32), v)

                    sum_prev = acc * l_i[:, None]
                    new_sum = sum_prev * alpha[:, None] + pv
                    acc_new = new_sum / l_new[:, None]
                    acc = tl.where(l_new[:, None] > 0, acc_new, acc)

                    m_i = m_new
                    l_i = l_new

                o = acc.to(tl.float16)
                tl.store(
                    o_ptr + offs_m[:, None] * stride_om + offs_dv[None, :] * stride_od,
                    o,
                    mask=mask_m[:, None] & mask_dv[None, :],
                )


            def flash_attn(Q: torch.Tensor, K: torch.Tensor, V: torch.Tensor, causal: bool = True) -> torch.Tensor:
                """
                Flash attention computation with optional causal masking.
                """
                assert Q.is_cuda and K.is_cuda and V.is_cuda, "All inputs must be CUDA tensors"
                assert Q.dtype == torch.float16 and K.dtype == torch.float16 and V.dtype == torch.float16, "Inputs must be float16"
                assert Q.shape[0] == K.shape[0] == V.shape[0], "Batch dimension mismatch"
                assert Q.shape[1] == K.shape[1] == V.shape[1], "Head dimension mismatch"
                assert Q.shape[3] == K.shape[3], "Q and K last dimension must match"
                assert K.shape[2] == V.shape[2], "K and V sequence length must match"

                Z, H, M, D = Q.shape
                _, _, N, _ = K.shape
                _, _, _, Dv = V.shape

                if D > 128 or Dv > 64:
                    q = Q.float()
                    k = K.float()
                    v = V.float()
                    scale = 1.0 / math.sqrt(D)
                    scores = torch.matmul(q, k.transpose(-1, -2)) * scale
                    if causal:
                        mask = torch.triu(torch.ones((M, N), device=Q.device, dtype=torch.bool), diagonal=1)
                        scores = scores.masked_fill(mask, float("-inf"))
                    attn = torch.softmax(scores, dim=-1)
                    out = torch.matmul(attn, v)
                    return out.to(Q.dtype)

                Out = torch.empty((Z, H, M, Dv), device=Q.device, dtype=Q.dtype)

                grid = lambda META: (Z * H, triton.cdiv(M, META["BLOCK_M"]))

                sm_scale = 1.0 / math.sqrt(D)

                flash_attn_fwd_kernel[grid](
                    Q, K, V, Out,
                    Q.stride(0), Q.stride(1), Q.stride(2), Q.stride(3),
                    K.stride(0), K.stride(1), K.stride(2), K.stride(3),
                    V.stride(0), V.stride(1), V.stride(2), V.stride(3),
                    Out.stride(0), Out.stride(1), Out.stride(2), Out.stride(3),
                    Z, H, M, N, D, Dv, sm_scale,
                    causal=causal,
                )

                return Out
            '''
        )
        return {"code": code}
