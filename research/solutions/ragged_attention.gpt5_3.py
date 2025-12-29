import math
import torch
import triton
import triton.language as tl


@triton.jit
def _ragged_attn_kernel(
    Q, K, V, O, ROW_LENS,
    M, N, D, DV,
    stride_qm, stride_qd,
    stride_km, stride_kd,
    stride_vm, stride_vd,
    stride_om, stride_od,
    scale,
    BLOCK_M: tl.constexpr,
    BLOCK_N: tl.constexpr,
    BLOCK_D: tl.constexpr,
    BLOCK_DV: tl.constexpr,
):
    pid_m = tl.program_id(0)
    off_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
    off_m_mask = off_m < M

    # Load row lengths
    rl = tl.load(ROW_LENS + off_m, mask=off_m_mask, other=0).to(tl.int32)
    max_len = tl.max(rl, axis=0)
    num_k_iters = (max_len + BLOCK_N - 1) // BLOCK_N

    # DV offsets
    off_dv = tl.arange(0, BLOCK_DV)
    dv_mask = off_dv < DV

    # Initialize accumulators for streaming softmax
    # m_i, l_i per row
    # Use a very negative number instead of -inf to avoid NaNs in some operations
    NEG_INF = -1.0e9
    m_i = tl.full([BLOCK_M], NEG_INF, dtype=tl.float32)
    l_i = tl.zeros([BLOCK_M], dtype=tl.float32)
    acc = tl.zeros([BLOCK_M, BLOCK_DV], dtype=tl.float32)

    # Precompute Q blocks per D tiles to reduce repeated loads inside N loop if D <= BLOCK_D
    # But we support D > BLOCK_D by looping over D inside N loop.
    # Here, we won't pre-load Q because if D > BLOCK_D we still need loop per N iteration.

    # Main loop over N blocks
    n_iter = 0
    while n_iter < num_k_iters:
        off_n = n_iter * BLOCK_N + tl.arange(0, BLOCK_N)
        n_mask = off_n < N

        # Compute S = Q @ K^T for this (BM x BN) block, possibly looping over D
        S = tl.zeros([BLOCK_M, BLOCK_N], dtype=tl.float32)

        d_iter = 0
        while d_iter < D:
            off_d = d_iter + tl.arange(0, BLOCK_D)
            d_mask = off_d < D

            # Load Q chunk [BM, Dchunk]
            q_ptrs = Q + off_m[:, None] * stride_qm + off_d[None, :] * stride_qd
            q_chunk = tl.load(q_ptrs, mask=off_m_mask[:, None] & d_mask[None, :], other=0.0).to(tl.float32)

            # Load K^T chunk [Dchunk, BN]
            k_ptrs = K + off_n[None, :] * stride_km + off_d[:, None] * stride_kd
            k_chunk = tl.load(k_ptrs, mask=d_mask[:, None] & n_mask[None, :], other=0.0).to(tl.float32)

            S += tl.dot(q_chunk, k_chunk)
            d_iter += BLOCK_D

        # Apply scaling
        S = S * scale

        # Build mask for valid attention positions per row (ragged)
        # valid if off_n < rl[off_m]
        valid_mask = (off_n[None, :] < rl[:, None]) & off_m_mask[:, None] & n_mask[None, :]

        # Mask invalid positions with very negative number
        S_masked = tl.where(valid_mask, S, NEG_INF)

        # Compute local max per row
        local_max = tl.max(S_masked, axis=1)
        # Safe version to avoid issues when there are no valid entries: replace -inf-like with 0 for exponent
        local_max_safe = tl.where(local_max == NEG_INF, 0.0, local_max)

        # Compute exp(S - local_max) but zero out invalid positions explicitly
        P_local = tl.exp(S_masked - local_max_safe[:, None])
        P_local = tl.where(valid_mask, P_local, 0.0)

        # Compute streaming softmax update
        m_new = tl.maximum(m_i, local_max)
        # alpha = exp(m_i - m_new) if m_i is not -inf sentinel
        alpha = tl.exp(m_i - m_new)
        alpha = tl.where(m_i == NEG_INF, 0.0, alpha)
        # beta = exp(local_max - m_new) if local_max is not -inf sentinel
        beta = tl.exp(local_max - m_new)
        beta = tl.where(local_max == NEG_INF, 0.0, beta)

        # l_new = l_i * alpha + sum(P_local) * beta
        l_part = tl.sum(P_local, axis=1)
        l_new = l_i * alpha + l_part * beta
        inv_l_new = tl.where(l_new > 0, 1.0 / l_new, 0.0)

        # Load V block [BN, DV] and compute contribution
        v_ptrs = V + off_n[:, None] * stride_vm + off_dv[None, :] * stride_vd
        v_block = tl.load(v_ptrs, mask=n_mask[:, None] & dv_mask[None, :], other=0.0).to(tl.float32)

        contrib = tl.dot(P_local, v_block)  # [BM, DV]
        # acc = acc * (l_i * alpha / l_new) + contrib * (beta / l_new)
        scale_old = (l_i * alpha) * inv_l_new
        scale_new = beta * inv_l_new
        acc = acc * scale_old[:, None] + contrib * scale_new[:, None]

        # Update streaming state
        m_i = m_new
        l_i = l_new

        n_iter += BLOCK_N

    # Store result
    o_ptrs = O + off_m[:, None] * stride_om + off_dv[None, :] * stride_od
    tl.store(o_ptrs, acc.to(tl.float16), mask=off_m_mask[:, None] & dv_mask[None, :])


def ragged_attn(Q: torch.Tensor, K: torch.Tensor, V: torch.Tensor, row_lens: torch.Tensor) -> torch.Tensor:
    assert Q.is_cuda and K.is_cuda and V.is_cuda and row_lens.is_cuda
    assert Q.dtype in (torch.float16, torch.bfloat16) and K.dtype in (torch.float16, torch.bfloat16) and V.dtype in (torch.float16, torch.bfloat16)
    M, D = Q.shape
    N, Dk = K.shape
    Nv, DV = V.shape
    assert D == Dk and N == Nv
    # Make contiguous
    Qc = Q.contiguous()
    Kc = K.contiguous()
    Vc = V.contiguous()
    rl = row_lens.to(dtype=torch.int32).contiguous()

    # Output
    O = torch.empty((M, DV), device=Q.device, dtype=torch.float16)

    # Strides
    stride_qm, stride_qd = Qc.stride()
    stride_km, stride_kd = Kc.stride()
    stride_vm, stride_vd = Vc.stride()
    stride_om, stride_od = O.stride()

    # Tiling params (optimized for given problem sizes)
    BLOCK_M = 64
    BLOCK_N = 64
    BLOCK_D = 64
    BLOCK_DV = 64

    # Handle DV tail if needed
    if DV < BLOCK_DV:
        BLOCK_DV = 1 << (DV - 1).bit_length() if DV > 0 else 1
        BLOCK_DV = min(64, BLOCK_DV)

    # Scale
    scale = 1.0 / math.sqrt(D)

    grid = (triton.cdiv(M, BLOCK_M),)

    _ragged_attn_kernel[grid](
        Qc, Kc, Vc, O, rl,
        M, N, D, DV,
        stride_qm, stride_qd,
        stride_km, stride_kd,
        stride_vm, stride_vd,
        stride_om, stride_od,
        scale,
        BLOCK_M=BLOCK_M,
        BLOCK_N=BLOCK_N,
        BLOCK_D=BLOCK_D,
        BLOCK_DV=BLOCK_DV,
        num_warps=4,
        num_stages=2,
    )

    return O


class Solution:
    def solve(self, spec_path: str = None) -> dict:
        code = """
import math
import torch
import triton
import triton.language as tl


@triton.jit
def _ragged_attn_kernel(
    Q, K, V, O, ROW_LENS,
    M, N, D, DV,
    stride_qm, stride_qd,
    stride_km, stride_kd,
    stride_vm, stride_vd,
    stride_om, stride_od,
    scale,
    BLOCK_M: tl.constexpr,
    BLOCK_N: tl.constexpr,
    BLOCK_D: tl.constexpr,
    BLOCK_DV: tl.constexpr,
):
    pid_m = tl.program_id(0)
    off_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
    off_m_mask = off_m < M

    # Load row lengths
    rl = tl.load(ROW_LENS + off_m, mask=off_m_mask, other=0).to(tl.int32)
    max_len = tl.max(rl, axis=0)
    num_k_iters = (max_len + BLOCK_N - 1) // BLOCK_N

    # DV offsets
    off_dv = tl.arange(0, BLOCK_DV)
    dv_mask = off_dv < DV

    # Initialize accumulators for streaming softmax
    NEG_INF = -1.0e9
    m_i = tl.full([BLOCK_M], NEG_INF, dtype=tl.float32)
    l_i = tl.zeros([BLOCK_M], dtype=tl.float32)
    acc = tl.zeros([BLOCK_M, BLOCK_DV], dtype=tl.float32)

    n_iter = 0
    while n_iter < num_k_iters:
        off_n = n_iter * BLOCK_N + tl.arange(0, BLOCK_N)
        n_mask = off_n < N

        # Compute S = Q @ K^T for this (BM x BN) block, possibly looping over D
        S = tl.zeros([BLOCK_M, BLOCK_N], dtype=tl.float32)
        d_iter = 0
        while d_iter < D:
            off_d = d_iter + tl.arange(0, BLOCK_D)
            d_mask = off_d < D

            # Load Q chunk [BM, Dchunk]
            q_ptrs = Q + off_m[:, None] * stride_qm + off_d[None, :] * stride_qd
            q_chunk = tl.load(q_ptrs, mask=off_m_mask[:, None] & d_mask[None, :], other=0.0).to(tl.float32)

            # Load K^T chunk [Dchunk, BN]
            k_ptrs = K + off_n[None, :] * stride_km + off_d[:, None] * stride_kd
            k_chunk = tl.load(k_ptrs, mask=d_mask[:, None] & n_mask[None, :], other=0.0).to(tl.float32)

            S += tl.dot(q_chunk, k_chunk)
            d_iter += BLOCK_D

        # Apply scaling
        S = S * scale

        # Valid mask per row
        valid_mask = (off_n[None, :] < rl[:, None]) & off_m_mask[:, None] & n_mask[None, :]

        # Mask invalid scores
        S_masked = tl.where(valid_mask, S, NEG_INF)

        # Local max per row
        local_max = tl.max(S_masked, axis=1)
        local_max_safe = tl.where(local_max == NEG_INF, 0.0, local_max)

        # P_local = exp(S - local_max) with invalid positions set to 0
        P_local = tl.exp(S_masked - local_max_safe[:, None])
        P_local = tl.where(valid_mask, P_local, 0.0)

        # Streaming softmax update
        m_new = tl.maximum(m_i, local_max)
        alpha = tl.exp(m_i - m_new)
        alpha = tl.where(m_i == NEG_INF, 0.0, alpha)
        beta = tl.exp(local_max - m_new)
        beta = tl.where(local_max == NEG_INF, 0.0, beta)

        l_part = tl.sum(P_local, axis=1)
        l_new = l_i * alpha + l_part * beta
        inv_l_new = tl.where(l_new > 0, 1.0 / l_new, 0.0)

        # Load V and compute contribution
        v_ptrs = V + off_n[:, None] * stride_vm + off_dv[None, :] * stride_vd
        v_block = tl.load(v_ptrs, mask=n_mask[:, None] & dv_mask[None, :], other=0.0).to(tl.float32)

        contrib = tl.dot(P_local, v_block)
        scale_old = (l_i * alpha) * inv_l_new
        scale_new = beta * inv_l_new
        acc = acc * scale_old[:, None] + contrib * scale_new[:, None]

        m_i = m_new
        l_i = l_new

        n_iter += BLOCK_N

    # Store result
    o_ptrs = O + off_m[:, None] * stride_om + off_dv[None, :] * stride_od
    tl.store(o_ptrs, acc.to(tl.float16), mask=off_m_mask[:, None] & dv_mask[None, :])


def ragged_attn(Q: torch.Tensor, K: torch.Tensor, V: torch.Tensor, row_lens: torch.Tensor) -> torch.Tensor:
    assert Q.is_cuda and K.is_cuda and V.is_cuda and row_lens.is_cuda
    assert Q.dtype in (torch.float16, torch.bfloat16) and K.dtype in (torch.float16, torch.bfloat16) and V.dtype in (torch.float16, torch.bfloat16)
    M, D = Q.shape
    N, Dk = K.shape
    Nv, DV = V.shape
    assert D == Dk and N == Nv

    Qc = Q.contiguous()
    Kc = K.contiguous()
    Vc = V.contiguous()
    rl = row_lens.to(dtype=torch.int32).contiguous()

    O = torch.empty((M, DV), device=Q.device, dtype=torch.float16)

    stride_qm, stride_qd = Qc.stride()
    stride_km, stride_kd = Kc.stride()
    stride_vm, stride_vd = Vc.stride()
    stride_om, stride_od = O.stride()

    BLOCK_M = 64
    BLOCK_N = 64
    BLOCK_D = 64
    BLOCK_DV = 64
    if DV < BLOCK_DV:
        BLOCK_DV = 1 << (DV - 1).bit_length() if DV > 0 else 1
        BLOCK_DV = min(64, BLOCK_DV)

    scale = 1.0 / math.sqrt(D)

    grid = (triton.cdiv(M, BLOCK_M),)

    _ragged_attn_kernel[grid](
        Qc, Kc, Vc, O, rl,
        M, N, D, DV,
        stride_qm, stride_qd,
        stride_km, stride_kd,
        stride_vm, stride_vd,
        stride_om, stride_od,
        scale,
        BLOCK_M=BLOCK_M,
        BLOCK_N=BLOCK_N,
        BLOCK_D=BLOCK_D,
        BLOCK_DV=BLOCK_DV,
        num_warps=4,
        num_stages=2,
    )

    return O
"""
        return {"code": code}