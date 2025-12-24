import textwrap


class Solution:
    def solve(self, spec_path: str = None) -> dict:
        kernel_code = textwrap.dedent(
            r'''
            import math
            import torch
            import triton
            import triton.language as tl


            @triton.autotune(
                configs=[
                    triton.Config({'BLOCK_N': 64, 'BLOCK_DMODEL': 64}, num_warps=4, num_stages=2),
                    triton.Config({'BLOCK_N': 128, 'BLOCK_DMODEL': 64}, num_warps=4, num_stages=2),
                    triton.Config({'BLOCK_N': 256, 'BLOCK_DMODEL': 64}, num_warps=8, num_stages=2),
                ],
                key=['N'],
            )
            @triton.jit
            def _decoding_attn_kernel(
                Q_ptr, K_ptr, V_ptr, Out_ptr,
                stride_qz, stride_qh, stride_qm, stride_qd,
                stride_kz, stride_kh, stride_kn, stride_kd,
                stride_vz, stride_vh, stride_vn, stride_vd,
                stride_oz, stride_oh, stride_om, stride_od,
                Z, H, M, N, Dq, Dv,
                scale,
                BLOCK_N: tl.constexpr,
                BLOCK_DMODEL: tl.constexpr,
            ):
                pid = tl.program_id(0)
                m_id = pid % M
                tmp = pid // M
                h_id = tmp % H
                z_id = tmp // H

                # Pointer to this (z, h, m) query row
                q_ptrs = Q_ptr + z_id * stride_qz + h_id * stride_qh + m_id * stride_qm

                d = tl.arange(0, BLOCK_DMODEL)
                mask_dq = d < Dq
                mask_dv = d < Dv

                # Load query vector (float16, to use tensor cores in tl.dot)
                q = tl.load(q_ptrs + d * stride_qd, mask=mask_dq, other=0.0).to(tl.float16)

                # Base pointers for K and V of this (z, h)
                k_head_ptr = K_ptr + z_id * stride_kz + h_id * stride_kh
                v_head_ptr = V_ptr + z_id * stride_vz + h_id * stride_vh

                # Streaming softmax state
                m_i = tl.full([1], -float('inf'), dtype=tl.float32)
                l_i = tl.zeros([1], dtype=tl.float32)
                acc = tl.zeros([BLOCK_DMODEL], dtype=tl.float32)

                offs_n = tl.arange(0, BLOCK_N)

                start_n = 0
                while start_n < N:
                    n_idx = start_n + offs_n
                    mask_n = n_idx < N

                    # Load K block [BLOCK_N, Dq]
                    k_ptrs = k_head_ptr + n_idx[:, None] * stride_kn + d[None, :] * stride_kd
                    k = tl.load(
                        k_ptrs,
                        mask=mask_n[:, None] & mask_dq[None, :],
                        other=0.0,
                    ).to(tl.float16)

                    # Scaled dot-product between q and each key row -> [BLOCK_N]
                    scores = tl.dot(k, q)
                    scores = scores * scale
                    scores = tl.where(mask_n, scores, -float('inf'))

                    # Online softmax update
                    m_curr = tl.max(scores, axis=0)
                    m_new = tl.maximum(m_i, m_curr)
                    alpha = tl.exp(m_i - m_new)

                    p = tl.exp(scores - m_new)
                    p = tl.where(mask_n, p, 0.0)

                    l_i = l_i * alpha + tl.sum(p, axis=0)

                    # Load V block [BLOCK_N, Dv] and accumulate weighted values
                    v_ptrs = v_head_ptr + n_idx[:, None] * stride_vn + d[None, :] * stride_vd
                    v = tl.load(
                        v_ptrs,
                        mask=mask_n[:, None] & mask_dv[None, :],
                        other=0.0,
                    ).to(tl.float32)

                    acc = acc * alpha + tl.sum(p[:, None] * v, axis=0)

                    m_i = m_new
                    start_n += BLOCK_N

                # Normalize and store output
                out = acc / l_i
                o_ptrs = (
                    Out_ptr
                    + z_id * stride_oz
                    + h_id * stride_oh
                    + m_id * stride_om
                    + d * stride_od
                )
                tl.store(o_ptrs, out.to(tl.float16), mask=mask_dv)


            def decoding_attn(Q: torch.Tensor, K: torch.Tensor, V: torch.Tensor) -> torch.Tensor:
                """
                Decoding attention computation.
                
                Args:
                    Q: Input tensor of shape (Z, H, M, Dq) - query tensor (float16)
                    K: Input tensor of shape (Z, H, N, Dq) - key tensor (float16)
                    V: Input tensor of shape (Z, H, N, Dv) - value tensor (float16)
                
                Returns:
                    Output tensor of shape (Z, H, M, Dv) - attention output (float16)
                """
                assert Q.is_cuda and K.is_cuda and V.is_cuda, "Inputs must be CUDA tensors"
                assert Q.dtype == torch.float16 and K.dtype == torch.float16 and V.dtype == torch.float16, (
                    "Inputs must be float16"
                )

                Z, H, M, Dq = Q.shape
                Zk, Hk, N, Dk = K.shape
                Zv, Hv, Nv, Dv = V.shape

                assert Z == Zk == Zv, "Batch dimension mismatch between Q, K, V"
                assert H == Hk == Hv, "Head dimension mismatch between Q, K, V"
                assert N == Nv, "Sequence length mismatch between K and V"
                assert Dq == Dk, "Key/query dimension mismatch"

                # Fallback to PyTorch implementation for larger hidden sizes
                if Dq > 64 or Dv > 64:
                    q = Q.reshape(Z * H, M, Dq).to(torch.float32)
                    k = K.reshape(Z * H, N, Dq).to(torch.float32)
                    v = V.reshape(Z * H, N, Dv).to(torch.float32)

                    scale = 1.0 / math.sqrt(Dq)
                    scores = torch.matmul(q, k.transpose(-1, -2)) * scale
                    probs = torch.softmax(scores, dim=-1)
                    out = torch.matmul(probs, v)
                    return out.reshape(Z, H, M, Dv).to(torch.float16)

                O = torch.empty((Z, H, M, Dv), device=Q.device, dtype=torch.float16)

                stride_qz, stride_qh, stride_qm, stride_qd = Q.stride()
                stride_kz, stride_kh, stride_kn, stride_kd = K.stride()
                stride_vz, stride_vh, stride_vn, stride_vd = V.stride()
                stride_oz, stride_oh, stride_om, stride_od = O.stride()

                scale = 1.0 / math.sqrt(Dq)

                total_q = Z * H * M
                grid = (total_q,)

                _decoding_attn_kernel[grid](
                    Q, K, V, O,
                    stride_qz, stride_qh, stride_qm, stride_qd,
                    stride_kz, stride_kh, stride_kn, stride_kd,
                    stride_vz, stride_vh, stride_vn, stride_vd,
                    stride_oz, stride_oh, stride_om, stride_od,
                    Z, H, M, N, Dq, Dv,
                    scale,
                )

                return O
            '''
        )
        return {"code": kernel_code}
