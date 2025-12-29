import math
import torch
import triton
import triton.language as tl


@triton.jit
def _ragged_attn_kernel(
    Q, K, V, O, ROW_LENS,
    M, D, DV,
    stride_qm, stride_qd,
    stride_kn, stride_kd,
    stride_vn, stride_vd,
    stride_om, stride_od,
    SCALE: tl.constexpr,
    N_CTX: tl.constexpr,
    BLOCK_M: tl.constexpr, BLOCK_N: tl.constexpr,
    BLOCK_DMODEL: tl.constexpr, BLOCK_DV: tl.constexpr
):
    pid_m = tl.program_id(0)
    offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
    mask_m = offs_m < M

    offs_d = tl.arange(0, BLOCK_DMODEL)
    offs_n = tl.arange(0, BLOCK_N)
    offs_v = tl.arange(0, BLOCK_DV)

    # Load Q block once
    q_ptrs = Q + offs_m[:, None] * stride_qm + offs_d[None, :] * stride_qd
    q = tl.load(q_ptrs, mask=mask_m[:, None] & (offs_d[None, :] < D), other=0.0).to(tl.float32)

    # Load row lengths
    rl = tl.load(ROW_LENS + offs_m, mask=mask_m, other=0).to(tl.int32)
    rl = tl.maximum(rl, 0)
    rl = tl.minimum(rl, N_CTX)

    # Streaming softmax state
    m_i = tl.full((BLOCK_M,), -float('inf'), dtype=tl.float32)
    l_i = tl.zeros((BLOCK_M,), dtype=tl.float32)
    acc = tl.zeros((BLOCK_M, BLOCK_DV), dtype=tl.float32)

    dv_mask = offs_v < DV

    for start_n in range(0, N_CTX, BLOCK_N):
        n_idx = start_n + offs_n
        n_mask = n_idx < N_CTX

        # Load K tile
        k_ptrs = K + n_idx[:, None] * stride_kn + offs_d[None, :] * stride_kd
        k = tl.load(k_ptrs, mask=(n_mask[:, None]) & (offs_d[None, :] < D), other=0.0).to(tl.float32)

        # Compute scores = Q*K^T
        scores = tl.dot(q, tl.trans(k)) * SCALE

        # Apply ragged mask: j < row_lens[i]
        allowed = n_idx[None, :] < rl[:, None]
        valid = mask_m[:, None] & (allowed & n_mask[None, :])
        scores = tl.where(valid, scores, -float('inf'))

        # Update max
        m_curr = tl.max(scores, axis=1)
        m_new = tl.maximum(m_i, m_curr)
        mnew_is_neg_inf = m_new == -float('inf')

        # Compute exp(scores - m_new)
        scores_delta = scores - m_new[:, None]
        scores_delta = tl.where(mnew_is_neg_inf[:, None], -float('inf'), scores_delta)
        w = tl.exp(scores_delta)

        # Compute alpha = exp(m_i - m_new), safe when both -inf
        alpha_delta = m_i - m_new
        alpha_delta = tl.where(mnew_is_neg_inf, 0.0, alpha_delta)
        alpha = tl.exp(alpha_delta)

        # Update l
        l_new = l_i * alpha + tl.sum(w, axis=1)

        # Load V tile and update acc
        v_ptrs = V + n_idx[:, None] * stride_vn + offs_v[None, :] * stride_vd
        v = tl.load(v_ptrs, mask=(n_mask[:, None]) & (dv_mask[None, :]), other=0.0).to(tl.float32)

        acc = acc * alpha[:, None] + tl.dot(w, v)

        m_i = m_new
        l_i = l_new

    out = acc / l_i[:, None]
    o_ptrs = O + offs_m[:, None] * stride_om + offs_v[None, :] * stride_od
    tl.store(o_ptrs, out.to(tl.float16), mask=mask_m[:, None] & dv_mask[None, :])


def ragged_attn(Q: torch.Tensor, K: torch.Tensor, V: torch.Tensor, row_lens: torch.Tensor) -> torch.Tensor:
    assert Q.is_cuda and K.is_cuda and V.is_cuda, "Inputs must be CUDA tensors"
    assert Q.dtype == torch.float16 and K.dtype == torch.float16 and V.dtype == torch.float16, "Q, K, V must be float16"
    assert Q.dim() == 2 and K.dim() == 2 and V.dim() == 2, "Q, K, V must be 2D"
    assert Q.shape[1] == K.shape[1], "Q and K must have same D"
    assert K.shape[0] == V.shape[0], "K and V must have same N"
    assert row_lens.dim() == 1 and row_lens.shape[0] == Q.shape[0], "row_lens must be (M,)"

    M, D = Q.shape
    N = K.shape[0]
    DV = V.shape[1]

    # Ensure types
    if row_lens.dtype != torch.int32:
        row_lens = row_lens.to(torch.int32)

    # Output
    O = torch.empty((M, DV), device=Q.device, dtype=torch.float16)

    # Strides (in elements)
    stride_qm, stride_qd = Q.stride()
    stride_kn, stride_kd = K.stride()
    stride_vn, stride_vd = V.stride()
    stride_om, stride_od = O.stride()

    # Tiling parameters
    BLOCK_M = 64
    BLOCK_N = 64
    BLOCK_DMODEL = 64
    BLOCK_DV = 64

    # Compute scale
    SCALE = 1.0 / math.sqrt(D)

    # Grid
    grid = (triton.cdiv(M, BLOCK_M),)

    # Launch kernel
    _ragged_attn_kernel[grid](
        Q, K, V, O, row_lens,
        M, D, DV,
        stride_qm, stride_qd,
        stride_kn, stride_kd,
        stride_vn, stride_vd,
        stride_om, stride_od,
        SCALE,
        N,  # N_CTX as constexpr
        BLOCK_M=BLOCK_M, BLOCK_N=BLOCK_N,
        BLOCK_DMODEL=BLOCK_DMODEL, BLOCK_DV=BLOCK_DV,
        num_warps=4, num_stages=3
    )

    return O


class Solution:
    def solve(self, spec_path: str = None) -> dict:
        code = '''
import math
import torch
import triton
import triton.language as tl


@triton.jit
def _ragged_attn_kernel(
    Q, K, V, O, ROW_LENS,
    M, D, DV,
    stride_qm, stride_qd,
    stride_kn, stride_kd,
    stride_vn, stride_vd,
    stride_om, stride_od,
    SCALE: tl.constexpr,
    N_CTX: tl.constexpr,
    BLOCK_M: tl.constexpr, BLOCK_N: tl.constexpr,
    BLOCK_DMODEL: tl.constexpr, BLOCK_DV: tl.constexpr
):
    pid_m = tl.program_id(0)
    offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
    mask_m = offs_m < M

    offs_d = tl.arange(0, BLOCK_DMODEL)
    offs_n = tl.arange(0, BLOCK_N)
    offs_v = tl.arange(0, BLOCK_DV)

    # Load Q block once
    q_ptrs = Q + offs_m[:, None] * stride_qm + offs_d[None, :] * stride_qd
    q = tl.load(q_ptrs, mask=mask_m[:, None] & (offs_d[None, :] < D), other=0.0).to(tl.float32)

    # Load row lengths
    rl = tl.load(ROW_LENS + offs_m, mask=mask_m, other=0).to(tl.int32)
    rl = tl.maximum(rl, 0)
    rl = tl.minimum(rl, N_CTX)

    # Streaming softmax state
    m_i = tl.full((BLOCK_M,), -float('inf'), dtype=tl.float32)
    l_i = tl.zeros((BLOCK_M,), dtype=tl.float32)
    acc = tl.zeros((BLOCK_M, BLOCK_DV), dtype=tl.float32)

    dv_mask = offs_v < DV

    for start_n in range(0, N_CTX, BLOCK_N):
        n_idx = start_n + offs_n
        n_mask = n_idx < N_CTX

        # Load K tile
        k_ptrs = K + n_idx[:, None] * stride_kn + offs_d[None, :] * stride_kd
        k = tl.load(k_ptrs, mask=(n_mask[:, None]) & (offs_d[None, :] < D), other=0.0).to(tl.float32)

        # Compute scores = Q*K^T
        scores = tl.dot(q, tl.trans(k)) * SCALE

        # Apply ragged mask: j < row_lens[i]
        allowed = n_idx[None, :] < rl[:, None]
        valid = mask_m[:, None] & (allowed & n_mask[None, :])
        scores = tl.where(valid, scores, -float('inf'))

        # Update max
        m_curr = tl.max(scores, axis=1)
        m_new = tl.maximum(m_i, m_curr)
        mnew_is_neg_inf = m_new == -float('inf')

        # Compute exp(scores - m_new)
        scores_delta = scores - m_new[:, None]
        scores_delta = tl.where(mnew_is_neg_inf[:, None], -float('inf'), scores_delta)
        w = tl.exp(scores_delta)

        # Compute alpha = exp(m_i - m_new), safe when both -inf
        alpha_delta = m_i - m_new
        alpha_delta = tl.where(mnew_is_neg_inf, 0.0, alpha_delta)
        alpha = tl.exp(alpha_delta)

        # Update l
        l_new = l_i * alpha + tl.sum(w, axis=1)

        # Load V tile and update acc
        v_ptrs = V + n_idx[:, None] * stride_vn + offs_v[None, :] * stride_vd
        v = tl.load(v_ptrs, mask=(n_mask[:, None]) & (dv_mask[None, :]), other=0.0).to(tl.float32)

        acc = acc * alpha[:, None] + tl.dot(w, v)

        m_i = m_new
        l_i = l_new

    out = acc / l_i[:, None]
    o_ptrs = O + offs_m[:, None] * stride_om + offs_v[None, :] * stride_od
    tl.store(o_ptrs, out.to(tl.float16), mask=mask_m[:, None] & dv_mask[None, :])


def ragged_attn(Q: torch.Tensor, K: torch.Tensor, V: torch.Tensor, row_lens: torch.Tensor) -> torch.Tensor:
    assert Q.is_cuda and K.is_cuda and V.is_cuda, "Inputs must be CUDA tensors"
    assert Q.dtype == torch.float16 and K.dtype == torch.float16 and V.dtype == torch.float16, "Q, K, V must be float16"
    assert Q.dim() == 2 and K.dim() == 2 and V.dim() == 2, "Q, K, V must be 2D"
    assert Q.shape[1] == K.shape[1], "Q and K must have same D"
    assert K.shape[0] == V.shape[0], "K and V must have same N"
    assert row_lens.dim() == 1 and row_lens.shape[0] == Q.shape[0], "row_lens must be (M,)"

    M, D = Q.shape
    N = K.shape[0]
    DV = V.shape[1]

    # Ensure types
    if row_lens.dtype != torch.int32:
        row_lens = row_lens.to(torch.int32)

    # Output
    O = torch.empty((M, DV), device=Q.device, dtype=torch.float16)

    # Strides (in elements)
    stride_qm, stride_qd = Q.stride()
    stride_kn, stride_kd = K.stride()
    stride_vn, stride_vd = V.stride()
    stride_om, stride_od = O.stride()

    # Tiling parameters
    BLOCK_M = 64
    BLOCK_N = 64
    BLOCK_DMODEL = 64
    BLOCK_DV = 64

    # Compute scale
    SCALE = 1.0 / math.sqrt(D)

    # Grid
    grid = (triton.cdiv(M, BLOCK_M),)

    _ragged_attn_kernel[grid](
        Q, K, V, O, row_lens,
        M, D, DV,
        stride_qm, stride_qd,
        stride_kn, stride_kd,
        stride_vn, stride_vd,
        stride_om, stride_od,
        SCALE,
        N,  # N_CTX as constexpr
        BLOCK_M=BLOCK_M, BLOCK_N=BLOCK_N,
        BLOCK_DMODEL=BLOCK_DMODEL, BLOCK_DV=BLOCK_DV,
        num_warps=4, num_stages=3
    )

    return O
'''
        return {"code": code}