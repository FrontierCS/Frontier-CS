import textwrap

class Solution:
    def solve(self, spec_path: str = None) -> dict:
        code = textwrap.dedent("""
        import torch
        import triton
        import triton.language as tl
        import math

        @triton.jit
        def kernel(
            Q, stride_qm, stride_qd,
            K, stride_km, stride_kd,
            V, stride_vm, stride_vd,
            O, stride_om, stride_od,
            row_lens, stride_rm,
            M: tl.constexpr, N: tl.constexpr, Dv: tl.constexpr, D: tl.constexpr,
            scale: tl.float32,
            BM: tl.constexpr, BN: tl.constexpr
        ):
            pid = tl.program_id(0)
            qbase = pid * BM
            # load row_lens_block
            offsets_r = qbase + tl.arange(0, BM)
            mask_r = offsets_r < M
            row_lens_block = tl.load(row_lens + offsets_r * stride_rm, mask=mask_r, other=0)
            # load Q_block
            offsets_qm = qbase + tl.arange(0, BM)
            offsets_qd = tl.arange(0, D)
            mask_q = offsets_qm[:, None] < M & offsets_qd[None, :] < D
            offs_q = offsets_qm[:, None] * stride_qm + offsets_qd[None, :] * stride_qd
            Q_block = tl.load(Q + offs_q, mask=mask_q, other=0.0, eviction_policy='evict_last').to(tl.float32)
            # init acc
            acc_m = tl.full([BM], -1e9, dtype=tl.float32)
            acc_l = tl.zeros([BM], dtype=tl.float32)
            acc_o = tl.zeros([BM, Dv], dtype=tl.float32)
            large_neg = -10000.0
            # loop over k blocks
            for start_n in range(0, N, BN):
                # load K_block
                offsets_km = start_n + tl.arange(0, BN)
                offsets_kd = tl.arange(0, D)
                mask_k = offsets_km[:, None] < N & offsets_kd[None, :] < D
                offs_k = offsets_km[:, None] * stride_km + offsets_kd[None, :] * stride_kd
                K_block = tl.load(K + offs_k, mask=mask_k, other=0.0, eviction_policy='evict_last').to(tl.float32)
                # load V_block
                offsets_vm = start_n + tl.arange(0, BN)
                offsets_vd = tl.arange(0, Dv)
                mask_v = offsets_vm[:, None] < N & offsets_vd[None, :] < Dv
                offs_v = offsets_vm[:, None] * stride_vm + offsets_vd[None, :] * stride_vd
                V_block = tl.load(V + offs_v, mask=mask_v, other=0.0, eviction_policy='evict_last').to(tl.float32)
                # compute raw_scores
                raw_scores = tl.dot(Q_block, K_block.T) * scale
                # compute mask
                end_j = tl.maximum(tl.zeros([BM], dtype=tl.int32), row_lens_block.to(tl.int32) - start_n)
                j_ar = tl.arange(0, BN, dtype=tl.int32)
                mask = j_ar[None, :] < end_j[:, None]
                # apply mask
                raw_scores = tl.where(mask, raw_scores, large_neg)
                # local softmax
                m_i = tl.max(raw_scores, axis=1)
                p = tl.exp(raw_scores - m_i[:, None])
                l_i = tl.sum(p, axis=1)
                o_contrib = tl.dot(p, V_block)
                # correct for fully masked
                valid_block = row_lens_block.to(tl.int32) > start_n
                m_i = tl.where(valid_block, m_i, -1e9)
                l_i = tl.where(valid_block, l_i, 0.0)
                o_contrib = tl.where(valid_block[:, None], o_contrib, 0.0)
                # update acc
                m_new = tl.maximum(acc_m, m_i)
                exp_scale = tl.exp(acc_m - m_new)
                acc_o = exp_scale[:, None] * acc_o + tl.exp(m_i[:, None] - m_new[:, None]) * o_contrib
                acc_l = exp_scale * acc_l + tl.exp(m_i - m_new) * l_i
                acc_m = m_new
            # finalize and store
            acc_l_safe = tl.where(acc_l > 0, acc_l, 1.0)
            final_o = acc_o / acc_l_safe[:, None]
            offsets_om = qbase + tl.arange(0, BM)
            offsets_od = tl.arange(0, Dv)
            mask_o = offsets_om[:, None] < M & offsets_od[None, :] < Dv
            offs_o = offsets_om[:, None] * stride_om + offsets_od[None, :] * stride_od
            tl.store(O + offs_o, final_o.to(tl.float16), mask=mask_o)

        def ragged_attn(Q: torch.Tensor, K: torch.Tensor, V: torch.Tensor, row_lens: torch.Tensor) -> torch.Tensor:
            M, D = Q.shape
            N, _ = K.shape
            _, Dv = V.shape
            scale = 1.0 / math.sqrt(D)
            output = torch.empty((M, Dv), dtype=Q.dtype, device=Q.device)
            row_lens_ = row_lens.to(torch.int32).contiguous()
            BM = 64
            BN = 64
            def grid(meta):
                return (triton.cdiv(M, meta["BM"]),)
            kernel[grid](
                Q, stride_qm=Q.stride(0), stride_qd=Q.stride(1),
                K, stride_km=K.stride(0), stride_kd=K.stride(1),
                V, stride_vm=V.stride(0), stride_vd=V.stride(1),
                O=output, stride_om=output.stride(0), stride_od=output.stride(1),
                row_lens=row_lens_, stride_rm=row_lens_.stride(0),
                M=M, N=N, Dv=Dv, D=D,
                scale=scale,
                BM=BM, BN=BN,
                num_stages=2, num_warps=4
            )
            return output
        """)
        return {"code": code}
