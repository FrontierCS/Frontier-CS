import math
import torch
import triton
import triton.language as tl


@triton.jit
def _ragged_attn_fwd_kernel(
    Q_ptr, K_ptr, V_ptr, ROW_LENS_ptr, O_ptr,
    M, N,
    stride_qm, stride_qd,
    stride_kn, stride_kd,
    stride_vn, stride_vd,
    stride_om, stride_od,
    scale,
    BLOCK_M: tl.constexpr,
    BLOCK_N: tl.constexpr,
    D: tl.constexpr,
    DV: tl.constexpr,
):
    pid_m = tl.program_id(axis=0)

    offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
    m_mask = offs_m < M

    offs_d = tl.arange(0, D)
    offs_dv = tl.arange(0, DV)

    # Load row lengths for each row in the block
    row_len = tl.load(ROW_LENS_ptr + offs_m, mask=m_mask, other=0).to(tl.int32)

    # Load Q block: [BM, D]
    q_ptrs = Q_ptr + offs_m[:, None] * stride_qm + offs_d[None, :] * stride_qd
    q = tl.load(q_ptrs, mask=m_mask[:, None], other=0.0).to(tl.float32)

    # Initialize streaming softmax stats and accumulator
    m_i = tl.full([BLOCK_M], -float('inf'), tl.float32)
    l_i = tl.zeros([BLOCK_M], tl.float32)
    acc = tl.zeros([BLOCK_M, DV], tl.float32)

    start_n = 0
    while start_n < N:
        offs_n = start_n + tl.arange(0, BLOCK_N)
        n_mask = offs_n < N

        # Load K block: [BN, D]
        k_ptrs = K_ptr + offs_n[:, None] * stride_kn + offs_d[None, :] * stride_kd
        k = tl.load(k_ptrs, mask=n_mask[:, None], other=0.0).to(tl.float32)

        # Compute scores: [BM, BN] = Q @ K^T
        scores = tl.dot(q, tl.trans(k)) * scale

        # Ragged + bounds mask
        valid = m_mask[:, None] & n_mask[None, :] & (offs_n[None, :] < row_len[:, None])
        scores = tl.where(valid, scores, -float('inf'))

        # Compute per-row max for current block
        s_max = tl.max(scores, axis=1)
        m_i_new = tl.maximum(m_i, s_max)

        # Compute exponentials in a stable way
        scores_shifted = scores - m_i_new[:, None]
        # Mask rows with no valid entries in this block to avoid NaNs
        has_any = s_max != -float('inf')
        scores_shifted = tl.where(has_any[:, None], scores_shifted, -float('inf'))
        p = tl.exp(scores_shifted)
        p = tl.where(valid, p, 0.0)

        # Update normalization terms
        old_l_i = l_i
        exp_m_delta = tl.where(m_i_new == m_i, 1.0, tl.exp(m_i - m_i_new))
        p_sum = tl.sum(p, axis=1)
        l_new = old_l_i * exp_m_delta + p_sum

        # Load V block: [BN, DV]
        v_ptrs = V_ptr + offs_n[:, None] * stride_vn + offs_dv[None, :] * stride_vd
        v = tl.load(v_ptrs, mask=n_mask[:, None], other=0.0).to(tl.float32)

        # Compute P @ V for the block
        pv = tl.dot(p, v)  # [BM, DV]

        # Update accumulator
        l_new_safe = tl.where(l_new == 0, 1.0, l_new)
        acc = acc * ((old_l_i * exp_m_delta) / l_new_safe)[:, None] + pv / l_new_safe[:, None]

        # Commit updates
        l_i = tl.where(l_new == 0, old_l_i, l_new)
        m_i = tl.where(has_any | (old_l_i > 0), m_i_new, m_i)

        start_n += BLOCK_N

    # Store output
    o_ptrs = O_ptr + offs_m[:, None] * stride_om + offs_dv[None, :] * stride_od
    tl.store(o_ptrs, acc.to(tl.float16), mask=m_mask[:, None])


def ragged_attn(Q: torch.Tensor, K: torch.Tensor, V: torch.Tensor, row_lens: torch.Tensor) -> torch.Tensor:
    assert Q.is_cuda and K.is_cuda and V.is_cuda and row_lens.is_cuda, "All tensors must be CUDA tensors"
    assert Q.dtype == torch.float16 and K.dtype == torch.float16 and V.dtype == torch.float16, "Q, K, V must be float16"
    assert Q.shape[1] == K.shape[1], "Q and K must have same feature dimension"
    assert K.shape[0] == V.shape[0], "K and V must have same number of rows"
    assert row_lens.dim() == 1 and row_lens.shape[0] == Q.shape[0], "row_lens must match number of query rows"

    M, D = Q.shape
    N = K.shape[0]
    DV = V.shape[1]

    # Convert to int32 for Triton
    if row_lens.dtype != torch.int32:
        row_lens_i32 = row_lens.to(torch.int32)
    else:
        row_lens_i32 = row_lens

    O = torch.empty((M, DV), dtype=torch.float16, device=Q.device)

    # Heuristic block sizes
    if D <= 64:
        BLOCK_M = 64
        BLOCK_N = 128
        num_warps = 4
    else:
        BLOCK_M = 32
        BLOCK_N = 128
        num_warps = 8

    scale = 1.0 / math.sqrt(D)

    grid = (triton.cdiv(M, BLOCK_M),)

    _ragged_attn_fwd_kernel[grid](
        Q, K, V, row_lens_i32, O,
        M, N,
        Q.stride(0), Q.stride(1),
        K.stride(0), K.stride(1),
        V.stride(0), V.stride(1),
        O.stride(0), O.stride(1),
        scale,
        BLOCK_M=BLOCK_M, BLOCK_N=BLOCK_N,
        D=D, DV=DV,
        num_warps=num_warps, num_stages=2,
    )
    return O


class Solution:
    def solve(self, spec_path: str = None) -> dict:
        code = r'''
import math
import torch
import triton
import triton.language as tl


@triton.jit
def _ragged_attn_fwd_kernel(
    Q_ptr, K_ptr, V_ptr, ROW_LENS_ptr, O_ptr,
    M, N,
    stride_qm, stride_qd,
    stride_kn, stride_kd,
    stride_vn, stride_vd,
    stride_om, stride_od,
    scale,
    BLOCK_M: tl.constexpr,
    BLOCK_N: tl.constexpr,
    D: tl.constexpr,
    DV: tl.constexpr,
):
    pid_m = tl.program_id(axis=0)

    offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
    m_mask = offs_m < M

    offs_d = tl.arange(0, D)
    offs_dv = tl.arange(0, DV)

    # Load row lengths for each row in the block
    row_len = tl.load(ROW_LENS_ptr + offs_m, mask=m_mask, other=0).to(tl.int32)

    # Load Q block: [BM, D]
    q_ptrs = Q_ptr + offs_m[:, None] * stride_qm + offs_d[None, :] * stride_qd
    q = tl.load(q_ptrs, mask=m_mask[:, None], other=0.0).to(tl.float32)

    # Initialize streaming softmax stats and accumulator
    m_i = tl.full([BLOCK_M], -float('inf'), tl.float32)
    l_i = tl.zeros([BLOCK_M], tl.float32)
    acc = tl.zeros([BLOCK_M, DV], tl.float32)

    start_n = 0
    while start_n < N:
        offs_n = start_n + tl.arange(0, BLOCK_N)
        n_mask = offs_n < N

        # Load K block: [BN, D]
        k_ptrs = K_ptr + offs_n[:, None] * stride_kn + offs_d[None, :] * stride_kd
        k = tl.load(k_ptrs, mask=n_mask[:, None], other=0.0).to(tl.float32)

        # Compute scores: [BM, BN] = Q @ K^T
        scores = tl.dot(q, tl.trans(k)) * scale

        # Ragged + bounds mask
        valid = m_mask[:, None] & n_mask[None, :] & (offs_n[None, :] < row_len[:, None])
        scores = tl.where(valid, scores, -float('inf'))

        # Compute per-row max for current block
        s_max = tl.max(scores, axis=1)
        m_i_new = tl.maximum(m_i, s_max)

        # Compute exponentials in a stable way
        scores_shifted = scores - m_i_new[:, None]
        # Mask rows with no valid entries in this block to avoid NaNs
        has_any = s_max != -float('inf')
        scores_shifted = tl.where(has_any[:, None], scores_shifted, -float('inf'))
        p = tl.exp(scores_shifted)
        p = tl.where(valid, p, 0.0)

        # Update normalization terms
        old_l_i = l_i
        exp_m_delta = tl.where(m_i_new == m_i, 1.0, tl.exp(m_i - m_i_new))
        p_sum = tl.sum(p, axis=1)
        l_new = old_l_i * exp_m_delta + p_sum

        # Load V block: [BN, DV]
        v_ptrs = V_ptr + offs_n[:, None] * stride_vn + offs_dv[None, :] * stride_vd
        v = tl.load(v_ptrs, mask=n_mask[:, None], other=0.0).to(tl.float32)

        # Compute P @ V for the block
        pv = tl.dot(p, v)  # [BM, DV]

        # Update accumulator
        l_new_safe = tl.where(l_new == 0, 1.0, l_new)
        acc = acc * ((old_l_i * exp_m_delta) / l_new_safe)[:, None] + pv / l_new_safe[:, None]

        # Commit updates
        l_i = tl.where(l_new == 0, old_l_i, l_new)
        m_i = tl.where(has_any | (old_l_i > 0), m_i_new, m_i)

        start_n += BLOCK_N

    # Store output
    o_ptrs = O_ptr + offs_m[:, None] * stride_om + offs_dv[None, :] * stride_od
    tl.store(o_ptrs, acc.to(tl.float16), mask=m_mask[:, None])


def ragged_attn(Q: torch.Tensor, K: torch.Tensor, V: torch.Tensor, row_lens: torch.Tensor) -> torch.Tensor:
    assert Q.is_cuda and K.is_cuda and V.is_cuda and row_lens.is_cuda, "All tensors must be CUDA tensors"
    assert Q.dtype == torch.float16 and K.dtype == torch.float16 and V.dtype == torch.float16, "Q, K, V must be float16"
    assert Q.shape[1] == K.shape[1], "Q and K must have same feature dimension"
    assert K.shape[0] == V.shape[0], "K and V must have same number of rows"
    assert row_lens.dim() == 1 and row_lens.shape[0] == Q.shape[0], "row_lens must match number of query rows"

    M, D = Q.shape
    N = K.shape[0]
    DV = V.shape[1]

    # Convert to int32 for Triton
    if row_lens.dtype != torch.int32:
        row_lens_i32 = row_lens.to(torch.int32)
    else:
        row_lens_i32 = row_lens

    O = torch.empty((M, DV), dtype=torch.float16, device=Q.device)

    # Heuristic block sizes
    if D <= 64:
        BLOCK_M = 64
        BLOCK_N = 128
        num_warps = 4
    else:
        BLOCK_M = 32
        BLOCK_N = 128
        num_warps = 8

    scale = 1.0 / math.sqrt(D)

    grid = (triton.cdiv(M, BLOCK_M),)

    _ragged_attn_fwd_kernel[grid](
        Q, K, V, row_lens_i32, O,
        M, N,
        Q.stride(0), Q.stride(1),
        K.stride(0), K.stride(1),
        V.stride(0), V.stride(1),
        O.stride(0), O.stride(1),
        scale,
        BLOCK_M=BLOCK_M, BLOCK_N=BLOCK_N,
        D=D, DV=DV,
        num_warps=num_warps, num_stages=2,
    )
    return O
'''
        return {"code": code}
