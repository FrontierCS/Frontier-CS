import torch
import triton
import triton.language as tl


class Solution:
    def solve(self, spec_path: str = None) -> dict:
        code = r'''
import torch
import triton
import triton.language as tl


@triton.jit
def _ragged_attn_kernel(
    Q_ptr, K_ptr, V_ptr, O_ptr, ROW_LENS_PTR,
    M, N, D, DV,
    stride_qm, stride_qd,
    stride_km, stride_kd,
    stride_vm, stride_vd,
    stride_om, stride_od,
    stride_rm,
    scale,
    BLOCK_M: tl.constexpr, BLOCK_N: tl.constexpr, BLOCK_D: tl.constexpr, BLOCK_DV: tl.constexpr
):
    pid_m = tl.program_id(0)
    offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
    mask_m = offs_m < M

    # Load row lengths once
    rl = tl.load(ROW_LENS_PTR + offs_m * stride_rm, mask=mask_m, other=0)
    rl = rl.to(tl.int32)
    rl = tl.maximum(rl, 0)
    rl = tl.minimum(rl, N)

    NEG_INF = tl.full([1], -1e9, dtype=tl.float32)[0]

    # Iterate over value dimension in chunks; recompute softmax per chunk (OK for DV=64)
    dv_offsets = tl.arange(0, BLOCK_DV)
    for dv0 in range(0, DV, BLOCK_DV):
        curr_dv = dv0 + dv_offsets
        mask_dv = curr_dv < DV

        # Streaming softmax state per row
        m_i = tl.full([BLOCK_M], NEG_INF, dtype=tl.float32)
        l_i = tl.zeros([BLOCK_M], dtype=tl.float32)
        # Output accumulator for this DV block
        o_accum = tl.zeros([BLOCK_M, BLOCK_DV], dtype=tl.float32)

        # Loop over keys in blocks
        n_offsets = tl.arange(0, BLOCK_N)
        for n0 in range(0, N, BLOCK_N):
            cols = n0 + n_offsets
            mask_n = cols < N

            # Compute scores s = Q @ K^T for [BLOCK_M, BLOCK_N]
            s = tl.zeros([BLOCK_M, BLOCK_N], dtype=tl.float32)
            d_offsets = tl.arange(0, BLOCK_D)
            for d0 in range(0, D, BLOCK_D):
                d_idx = d0 + d_offsets
                mask_d = d_idx < D

                # Q [BM, BD]
                q_ptrs = Q_ptr + (offs_m[:, None] * stride_qm + d_idx[None, :] * stride_qd)
                q = tl.load(q_ptrs, mask=(mask_m[:, None] & mask_d[None, :]), other=0.0).to(tl.float32)

                # K [BN, BD]
                k_ptrs = K_ptr + (cols[None, :] * stride_km + d_idx[:, None] * stride_kd)
                k = tl.load(k_ptrs, mask=(mask_n[None, :] & mask_d[:, None]), other=0.0).to(tl.float32)

                s += tl.dot(q, k)

            s = s * scale

            # Apply ragged mask: only attend to first rl[row] keys
            valid = cols[None, :] < rl[:, None]
            active = valid & mask_m[:, None] & mask_n[None, :]
            s = tl.where(active, s, NEG_INF)

            # Streaming softmax update
            m_curr = tl.maximum(m_i, tl.max(s, axis=1))
            p = tl.exp(s - m_curr[:, None])
            l_curr = l_i * tl.exp(m_i - m_curr) + tl.sum(p, axis=1)

            # Load V^T block [DV_block, BN]
            v_ptrs = V_ptr + (cols[None, :] * stride_vm + curr_dv[:, None] * stride_vd)
            v_t = tl.load(v_ptrs, mask=(mask_n[None, :] & mask_dv[:, None]), other=0.0).to(tl.float32)

            # Update output accumulator: o = o * alpha + p @ V
            alpha = tl.exp(m_i - m_curr)
            o_accum = o_accum * alpha[:, None] + tl.dot(p, v_t)

            # Update m and l
            m_i = m_curr
            l_i = l_curr

        # Normalize and store
        inv_l = 1.0 / l_i
        o_out = o_accum * inv_l[:, None]
        o_ptrs = O_ptr + (offs_m[:, None] * stride_om + curr_dv[None, :] * stride_od)
        tl.store(o_ptrs, o_out.to(tl.float16), mask=(mask_m[:, None] & mask_dv[None, :]))


def ragged_attn(Q: torch.Tensor, K: torch.Tensor, V: torch.Tensor, row_lens: torch.Tensor) -> torch.Tensor:
    """
    Ragged attention computation.

    Args:
        Q: (M, D) float16
        K: (N, D) float16
        V: (N, Dv) float16
        row_lens: (M,) int32/int64
    Returns:
        O: (M, Dv) float16
    """
    assert Q.is_cuda and K.is_cuda and V.is_cuda and row_lens.is_cuda, "All tensors must be CUDA tensors"
    assert Q.dtype == torch.float16 and K.dtype == torch.float16 and V.dtype == torch.float16, "Q,K,V must be float16"
    assert Q.shape[1] == K.shape[1], "Q and K must have same D"
    M, D = Q.shape
    N = K.shape[0]
    DV = V.shape[1]

    O = torch.empty((M, DV), device=Q.device, dtype=torch.float16)

    # Choose block sizes
    def next_power_of_2(x):
        return 1 if x == 0 else 1 << (x - 1).bit_length()
    BLOCK_D = min(64, next_power_of_2(D))
    BLOCK_DV = min(64, next_power_of__2(DV))
    BLOCK_M = 64 if M >= 512 else 32
    BLOCK_N = 64

    # Ensure row_lens has appropriate dtype
    if row_lens.dtype not in (torch.int32, torch.int64):
        row_lens = row_lens.to(torch.int32)
    row_lens_contig = row_lens.contiguous()

    grid = (triton.cdiv(M, BLOCK_M),)

    scale = (1.0 / (D ** 0.5))

    _ragged_attn_kernel[grid](
        Q, K, V, O, row_lens_contig,
        M, N, D, DV,
        Q.stride(0), Q.stride(1),
        K.stride(0), K.stride(1),
        V.stride(0), V.stride(1),
        O.stride(0), O.stride(1),
        row_lens_contig.stride(0),
        scale,
        BLOCK_M=BLOCK_M, BLOCK_N=BLOCK_N, BLOCK_D=BLOCK_D, BLOCK_DV=BLOCK_DV,
        num_warps=4, num_stages=2
    )
    return O
'''
        return {"code": code}
