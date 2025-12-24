import math
import torch
import triton
import triton.language as tl

class Solution:
    def solve(self, spec_path: str = None) -> dict:
        return {
            "code": """
import math
import torch
import triton
import triton.language as tl

def ragged_attn(Q: torch.Tensor, K: torch.Tensor, V: torch.Tensor, row_lens: torch.Tensor) -> torch.Tensor:
    M, D = Q.shape
    N, _ = K.shape
    _, Dv = V.shape
    scale = 1.0 / math.sqrt(float(D))
    output = torch.empty((M, Dv), dtype=Q.dtype, device=Q.device)
    if M == 0:
        return output
    row_lens_int = row_lens.to(torch.int32)
    BLOCK_M = 128
    BLOCK_N = 64
    BLOCK_D = 64
    BLOCK_DV = 64
    grid = lambda: ((M + BLOCK_M - 1) // BLOCK_M,)
    @triton.jit
    def kernel(
        Q_ptr, K_ptr, V_ptr, row_lens_ptr, O_ptr,
        stride_qm, stride_qd,
        stride_km, stride_kd,
        stride_vm, stride_vd,
        stride_om, stride_od,
        stride_row,
        M, N, D, Dv,
        scale,
        BLOCK_M: tl.constexpr, BLOCK_N: tl.constexpr, BLOCK_D: tl.constexpr, BLOCK_DV: tl.constexpr
    ):
        pid_m = tl.program_id(0)
        block_start_m = pid_m * BLOCK_M
        offsets_m = block_start_m + tl.arange(0, BLOCK_M)
        mask_m = offsets_m < M
        q_offsets = offsets_m[:, None] * stride_qm + tl.arange(0, BLOCK_D)[None, :] * stride_qd
        q = tl.load(Q_ptr + q_offsets, mask=mask_m[:, None], other=0.0).to(tl.float32)
        row_offsets = offsets_m * stride_row
        row_lens_block = tl.load(row_lens_ptr + row_offsets, mask=mask_m, other=0).to(tl.int32)
        m_curr = tl.full((BLOCK_M,), -1e9, dtype=tl.float32)
        l_curr = tl.zeros((BLOCK_M,), dtype=tl.float32)
        o_curr = tl.zeros((BLOCK_M, BLOCK_DV), dtype=tl.float32)
        arange_n = tl.arange(0, BLOCK_N)
        arange_dv = tl.arange(0, BLOCK_DV)
        arange_d = tl.arange(0, BLOCK_D)
        num_blocks_n = (N + BLOCK_N - 1) // BLOCK_N
        for n in tl.range(0, num_blocks_n):
            block_start_n = n * BLOCK_N
            offsets_n = block_start_n + arange_n
            mask_n = offsets_n < N
            k_offsets = offsets_n[:, None] * stride_km + arange_d[None, :] * stride_kd
            k_mask = mask_n[:, None]
            k = tl.load(K_ptr + k_offsets, mask=k_mask, other=0.0).to(tl.float32)
            raw_scores = tl.sum(q[:, None, :] * k[None, :, :], axis=2) * scale
            num_valid = tl.where(row_lens_block > block_start_n,
                                 tl.minimum(BLOCK_N, row_lens_block - block_start_n),
                                 0)
            invalid = arange_n[None, :] >= num_valid[:, None]
            scores = tl.where(invalid, -1e4, raw_scores)
            m_block = tl.max(scores, axis=1)
            p = tl.exp(scores - m_block[:, None])
            l_temp = tl.sum(p, axis=1)
            has_valid = (num_valid > 0).to(tl.float32)
            l_block = l_temp * has_valid
            v_offsets = offsets_n[:, None] * stride_vm + arange_dv[None, :] * stride_vd
            v_mask = mask_n[:, None]
            v = tl.load(V_ptr + v_offsets, mask=v_mask, other=0.0).to(tl.float32)
            o_block = tl.sum(p[:, :, None] * v[None, :, :], axis=1)
            o_block = o_block * has_valid[:, None]
            m_new = tl.maximum(m_curr, m_block)
            scale_old = tl.exp(m_curr - m_new)
            scale_new = tl.exp(m_block - m_new)
            l_new = scale_old * l_curr + scale_new * l_block
            o_new = scale_old[:, None] * o_curr + scale_new[:, None] * o_block
            m_curr = m_new
            l_curr = l_new
            o_curr = o_new
        row_mask = l_curr > 0
        o_final = tl.where(row_mask[:, None], o_curr / l_curr[:, None], 0.0)
        o_offsets = offsets_m[:, None] * stride_om + arange_dv[None, :] * stride_od
        o_mask = mask_m[:, None]
        tl.store(O_ptr + o_offsets, o_final.to(O_ptr.dtype.element_ty), mask=o_mask)
    kernel[grid()](
        Q, K, V, row_lens_int, output,
        Q.stride(0), Q.stride(1),
        K.stride(0), K.stride(1),
        V.stride(0), V.stride(1),
        output.stride(0), output.stride(1),
        row_lens_int.stride(0),
        M, N, D, Dv,
        scale,
        BLOCK_M=BLOCK_M, BLOCK_N=BLOCK_N, BLOCK_D=BLOCK_D, BLOCK_DV=BLOCK_DV,
        num_stages=4,
        num_warps=8,
    )
    return output
"""
        }
