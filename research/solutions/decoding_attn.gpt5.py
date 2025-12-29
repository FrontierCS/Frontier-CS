import os
import math
import torch
import triton
import triton.language as tl


@triton.autotune(
    configs=[
        triton.Config({'BLOCK_N': 64, 'BLOCK_DV': 64}, num_warps=4, num_stages=3),
        triton.Config({'BLOCK_N': 128, 'BLOCK_DV': 64}, num_warps=4, num_stages=3),
        triton.Config({'BLOCK_N': 256, 'BLOCK_DV': 64}, num_warps=8, num_stages=4),
        triton.Config({'BLOCK_N': 512, 'BLOCK_DV': 64}, num_warps=8, num_stages=4),
        triton.Config({'BLOCK_N': 128, 'BLOCK_DV': 128}, num_warps=8, num_stages=4),
        triton.Config({'BLOCK_N': 256, 'BLOCK_DV': 128}, num_warps=8, num_stages=4),
    ],
    key=['N', 'D_HEAD', 'D_VALUE'],
)
@triton.jit
def _decoding_attn_kernel(
    q_ptr, k_ptr, v_ptr, o_ptr,
    stride_qz, stride_qh, stride_qm, stride_qd,
    stride_kz, stride_kh, stride_kn, stride_kd,
    stride_vz, stride_vh, stride_vn, stride_vd,
    stride_oz, stride_oh, stride_om, stride_od,
    Z, H, M, N, D_HEAD, D_VALUE,
    scale,
    BLOCK_N: tl.constexpr,
    BLOCK_DV: tl.constexpr,
    BLOCK_DH: tl.constexpr = 64,
):
    pid_m = tl.program_id(0)
    pid_v = tl.program_id(1)

    m_idx = pid_m % M
    h_idx = (pid_m // M) % H
    z_idx = pid_m // (M * H)

    dv_start = pid_v * BLOCK_DV
    dv_offsets = dv_start + tl.arange(0, BLOCK_DV)
    dv_mask = dv_offsets < D_VALUE

    # Base offsets for each tensor
    q_base = z_idx * stride_qz + h_idx * stride_qh + m_idx * stride_qm
    k_base = z_idx * stride_kz + h_idx * stride_kh
    v_base = z_idx * stride_vz + h_idx * stride_vh
    o_base = z_idx * stride_oz + h_idx * stride_oh + m_idx * stride_om

    # Initialize running softmax stats
    m_prev = tl.full([1], float('-inf'), tl.float32)
    l_prev = tl.zeros([1], dtype=tl.float32)
    acc = tl.zeros([BLOCK_DV], dtype=tl.float32)

    n_iter = 0
    while n_iter < N:
        n_offsets = n_iter + tl.arange(0, BLOCK_N)
        n_mask = n_offsets < N

        # Compute scores = K[n, :] dot Q[:] across D_HEAD in tiles
        scores = tl.zeros([BLOCK_N], dtype=tl.float32)

        d_iter = 0
        while d_iter < D_HEAD:
            d_offsets = d_iter + tl.arange(0, BLOCK_DH)
            d_mask = d_offsets < D_HEAD

            # Load q tile
            q_ptrs = q_ptr + q_base + d_offsets * stride_qd
            q_tile = tl.load(q_ptrs, mask=d_mask, other=0.0).to(tl.float32)

            # Load K block [BLOCK_N, BLOCK_DH]
            k_ptrs = k_ptr + k_base + n_offsets[:, None] * stride_kn + d_offsets[None, :] * stride_kd
            k_block = tl.load(k_ptrs, mask=n_mask[:, None] & d_mask[None, :], other=0.0).to(tl.float32)

            # Accumulate partial dot product
            scores += tl.sum(k_block * q_tile[None, :], axis=1)

            d_iter += BLOCK_DH

        # Scale
        scores = scores * scale

        # Streaming softmax update
        block_max = tl.max(scores, axis=0)
        m_new = tl.maximum(m_prev, block_max)
        alpha = tl.exp(m_prev - m_new)

        p = tl.exp(scores - m_new)
        p = tl.where(n_mask, p, 0.0)
        l_new = l_prev * alpha + tl.sum(p, axis=0)

        # Scale acc by alpha
        acc = acc * alpha

        # Load V block [BLOCK_N, BLOCK_DV] and accumulate acc += (p^T) * V_block
        v_ptrs = v_ptr + v_base + n_offsets[:, None] * stride_vn + dv_offsets[None, :] * stride_vd
        v_block = tl.load(v_ptrs, mask=n_mask[:, None] & dv_mask[None, :], other=0.0).to(tl.float32)
        # Weighted sum along N dimension
        acc += tl.sum(v_block * p[:, None], axis=0)

        # Update running stats
        m_prev = m_new
        l_prev = l_new

        n_iter += BLOCK_N

    # Normalize acc by l_prev
    out = acc / l_prev
    o_ptrs = o_ptr + o_base + dv_offsets * stride_od
    tl.store(o_ptrs, out.to(tl.float16), mask=dv_mask)


def decoding_attn(Q: torch.Tensor, K: torch.Tensor, V: torch.Tensor) -> torch.Tensor:
    """
    Decoding attention computation.

    Args:
        Q: (Z, H, M, Dq) float16/cuda
        K: (Z, H, N, Dq) float16/cuda
        V: (Z, H, N, Dv) float16/cuda

    Returns:
        (Z, H, M, Dv) float16/cuda
    """
    assert Q.is_cuda and K.is_cuda and V.is_cuda, "Tensors must be on CUDA device"
    assert Q.dtype in (torch.float16, torch.bfloat16) and K.dtype == Q.dtype and V.dtype == Q.dtype, "Tensors must be same half-precision dtype"
    assert Q.shape[0] == K.shape[0] == V.shape[0], "Batch (Z) mismatch"
    assert Q.shape[1] == K.shape[1] == V.shape[1], "Head (H) mismatch"
    assert K.shape[2] == V.shape[2], "Sequence length (N) mismatch"
    assert Q.shape[3] == K.shape[3], "Dq mismatch"

    Z, H, M, Dq = Q.shape
    _, _, N, _ = K.shape
    Dv = V.shape[3]

    # Use float scaling consistent with dtype
    scale = 1.0 / math.sqrt(Dq)

    # Allocate output
    O = torch.empty((Z, H, M, Dv), device=Q.device, dtype=Q.dtype)

    # Extract strides (in elements)
    sqz, sqh, sqm, sqd = Q.stride()
    skz, skh, skn, skd = K.stride()
    svz, svh, svn, svd = V.stride()
    soz, soh, som, sod = O.stride()

    grid = lambda META: (
        Z * H * M,
        triton.cdiv(Dv, META['BLOCK_DV'])
    )

    _decoding_attn_kernel[grid](
        Q, K, V, O,
        sqz, sqh, sqm, sqd,
        skz, skh, skn, skd,
        svz, svh, svn, svd,
        soz, soh, som, sod,
        Z, H, M, N, Dq, Dv,
        scale,
    )

    return O


class Solution:
    def solve(self, spec_path: str = None) -> dict:
        return {"program_path": os.path.abspath(__file__)}