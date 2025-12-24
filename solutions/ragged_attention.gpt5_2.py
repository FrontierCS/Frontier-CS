import math
import torch
import triton
import triton.language as tl


@triton.jit
def _ragged_attn_kernel(
    Q_ptr, K_ptr, V_ptr, O_ptr, ROW_LENS_ptr,
    M, N, D, DV, SCALE,
    stride_qm, stride_qd,
    stride_kn, stride_kd,
    stride_vn, stride_vd,
    stride_om, stride_od,
    BLOCK_M: tl.constexpr,
    BLOCK_N: tl.constexpr,
    BLOCK_D: tl.constexpr,
    BLOCK_DV: tl.constexpr,
):
    pid_m = tl.program_id(0)
    offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
    offs_d = tl.arange(0, BLOCK_D)
    offs_dv = tl.arange(0, BLOCK_DV)

    row_mask = offs_m < M

    # Load Q [BM, D]
    q_ptrs = Q_ptr + offs_m[:, None] * stride_qm + offs_d[None, :] * stride_qd
    q = tl.load(q_ptrs, mask=row_mask[:, None] & (offs_d[None, :] < D), other=0.0).to(tl.float32)

    # Load row lengths
    rlen = tl.load(ROW_LENS_ptr + offs_m, mask=row_mask, other=0).to(tl.int32)

    # Streaming softmax variables
    NEG_LARGE = -1e9
    m_i = tl.full([BLOCK_M], NEG_LARGE, dtype=tl.float32)
    l_i = tl.zeros([BLOCK_M], dtype=tl.float32)
    acc = tl.zeros([BLOCK_M, BLOCK_DV], dtype=tl.float32)

    # Loop over K/V columns
    for start_n in range(0, tl.multiple_of(N, BLOCK_N), BLOCK_N):
        offs_n = start_n + tl.arange(0, BLOCK_N)
        n_mask = offs_n < N

        # Load K [BN, D]
        k_ptrs = K_ptr + offs_n[:, None] * stride_kn + offs_d[None, :] * stride_kd
        k = tl.load(k_ptrs, mask=n_mask[:, None] & (offs_d[None, :] < D), other=0.0).to(tl.float32)

        # Compute scores [BM, BN] = Q @ K^T
        scores = tl.dot(q, tl.trans(k)) * SCALE

        # Ragged masking: valid if offs_n < row_len for each row
        rag_mask = (offs_n[None, :] < rlen[:, None]) & row_mask[:, None] & n_mask[None, :]

        scores = tl.where(rag_mask, scores, tl.full_like(scores, -float('inf')))

        # Update streaming softmax
        row_max = tl.max(scores, axis=1)
        m_new = tl.maximum(m_i, row_max)
        p = tl.exp(scores - m_new[:, None])
        l_new = tl.exp(m_i - m_new) * l_i + tl.sum(p, axis=1)

        # Load V [BN, DV]
        v_ptrs = V_ptr + offs_n[:, None] * stride_vn + offs_dv[None, :] * stride_vd
        v = tl.load(v_ptrs, mask=n_mask[:, None] & (offs_dv[None, :] < DV), other=0.0).to(tl.float32)

        # Update accumulator
        alpha = tl.exp(m_i - m_new)
        acc = acc * alpha[:, None] + tl.dot(p, v)

        m_i = m_new
        l_i = l_new

    # Normalize and store
    denom = tl.where(row_mask, l_i, 1.0)
    out = acc / denom[:, None]
    o_ptrs = O_ptr + offs_m[:, None] * stride_om + offs_dv[None, :] * stride_od
    tl.store(o_ptrs, out.to(tl.float16), mask=row_mask[:, None] & (offs_dv[None, :] < DV))


def ragged_attn(Q: torch.Tensor, K: torch.Tensor, V: torch.Tensor, row_lens: torch.Tensor) -> torch.Tensor:
    assert Q.is_cuda and K.is_cuda and V.is_cuda, "All tensors must be CUDA tensors"
    assert Q.dtype == torch.float16 and K.dtype == torch.float16 and V.dtype == torch.float16, "Q, K, V must be float16"
    assert row_lens.is_cuda, "row_lens must be CUDA tensor"
    assert row_lens.dtype in (torch.int32, torch.int64)

    M, D = Q.shape
    N, Dk = K.shape
    Nv, Dv = V.shape
    assert D == Dk, "Q and K must have same feature dimension"
    assert N == Nv, "K and V must have same number of rows"

    # Ensure row_lens int32
    if row_lens.dtype != torch.int32:
        row_lens = row_lens.to(torch.int32)

    O = torch.empty((M, Dv), device=Q.device, dtype=torch.float16)

    # Tiling parameters
    BLOCK_M = 64
    BLOCK_N = 128
    BLOCK_D = 64
    BLOCK_DV = min(64, Dv)

    # Assumptions for performance (D and Dv not exceeding block sizes)
    # If D or Dv exceed block sizes, kernel still runs but will truncate; to be robust, we bound them
    assert D <= BLOCK_D and Dv <= BLOCK_DV, "Kernel expects D and Dv <= 64 for optimized path"

    grid = (triton.cdiv(M, BLOCK_M),)

    SCALE = 1.0 / math.sqrt(float(D))

    _ragged_attn_kernel[grid](
        Q, K, V, O, row_lens,
        M, N, D, Dv, SCALE,
        Q.stride(0), Q.stride(1),
        K.stride(0), K.stride(1),
        V.stride(0), V.stride(1),
        O.stride(0), O.stride(1),
        BLOCK_M=BLOCK_M, BLOCK_N=BLOCK_N, BLOCK_D=BLOCK_D, BLOCK_DV=BLOCK_DV,
        num_warps=4, num_stages=2,
    )
    return O


class Solution:
    def solve(self, spec_path: str = None) -> dict:
        code = r"""
import math
import torch
import triton
import triton.language as tl


@triton.jit
def _ragged_attn_kernel(
    Q_ptr, K_ptr, V_ptr, O_ptr, ROW_LENS_ptr,
    M, N, D, DV, SCALE,
    stride_qm, stride_qd,
    stride_kn, stride_kd,
    stride_vn, stride_vd,
    stride_om, stride_od,
    BLOCK_M: tl.constexpr,
    BLOCK_N: tl.constexpr,
    BLOCK_D: tl.constexpr,
    BLOCK_DV: tl.constexpr,
):
    pid_m = tl.program_id(0)
    offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
    offs_d = tl.arange(0, BLOCK_D)
    offs_dv = tl.arange(0, BLOCK_DV)

    row_mask = offs_m < M

    # Load Q [BM, D]
    q_ptrs = Q_ptr + offs_m[:, None] * stride_qm + offs_d[None, :] * stride_qd
    q = tl.load(q_ptrs, mask=row_mask[:, None] & (offs_d[None, :] < D), other=0.0).to(tl.float32)

    # Load row lengths
    rlen = tl.load(ROW_LENS_ptr + offs_m, mask=row_mask, other=0).to(tl.int32)

    # Streaming softmax variables
    NEG_LARGE = -1e9
    m_i = tl.full([BLOCK_M], NEG_LARGE, dtype=tl.float32)
    l_i = tl.zeros([BLOCK_M], dtype=tl.float32)
    acc = tl.zeros([BLOCK_M, BLOCK_DV], dtype=tl.float32)

    # Loop over K/V columns
    for start_n in range(0, tl.multiple_of(N, BLOCK_N), BLOCK_N):
        offs_n = start_n + tl.arange(0, BLOCK_N)
        n_mask = offs_n < N

        # Load K [BN, D]
        k_ptrs = K_ptr + offs_n[:, None] * stride_kn + offs_d[None, :] * stride_kd
        k = tl.load(k_ptrs, mask=n_mask[:, None] & (offs_d[None, :] < D), other=0.0).to(tl.float32)

        # Compute scores [BM, BN] = Q @ K^T
        scores = tl.dot(q, tl.trans(k)) * SCALE

        # Ragged masking: valid if offs_n < row_len for each row
        rag_mask = (offs_n[None, :] < rlen[:, None]) & row_mask[:, None] & n_mask[None, :]

        scores = tl.where(rag_mask, scores, tl.full_like(scores, -float('inf')))

        # Update streaming softmax
        row_max = tl.max(scores, axis=1)
        m_new = tl.maximum(m_i, row_max)
        p = tl.exp(scores - m_new[:, None])
        l_new = tl.exp(m_i - m_new) * l_i + tl.sum(p, axis=1)

        # Load V [BN, DV]
        v_ptrs = V_ptr + offs_n[:, None] * stride_vn + offs_dv[None, :] * stride_vd
        v = tl.load(v_ptrs, mask=n_mask[:, None] & (offs_dv[None, :] < DV), other=0.0).to(tl.float32)

        # Update accumulator
        alpha = tl.exp(m_i - m_new)
        acc = acc * alpha[:, None] + tl.dot(p, v)

        m_i = m_new
        l_i = l_new

    # Normalize and store
    denom = tl.where(row_mask, l_i, 1.0)
    out = acc / denom[:, None]
    o_ptrs = O_ptr + offs_m[:, None] * stride_om + offs_dv[None, :] * stride_od
    tl.store(o_ptrs, out.to(tl.float16), mask=row_mask[:, None] & (offs_dv[None, :] < DV))


def ragged_attn(Q: torch.Tensor, K: torch.Tensor, V: torch.Tensor, row_lens: torch.Tensor) -> torch.Tensor:
    assert Q.is_cuda and K.is_cuda and V.is_cuda, "All tensors must be CUDA tensors"
    assert Q.dtype == torch.float16 and K.dtype == torch.float16 and V.dtype == torch.float16, "Q, K, V must be float16"
    assert row_lens.is_cuda, "row_lens must be CUDA tensor"
    assert row_lens.dtype in (torch.int32, torch.int64)

    M, D = Q.shape
    N, Dk = K.shape
    Nv, Dv = V.shape
    assert D == Dk, "Q and K must have same feature dimension"
    assert N == Nv, "K and V must have same number of rows"

    # Ensure row_lens int32
    if row_lens.dtype != torch.int32:
        row_lens = row_lens.to(torch.int32)

    O = torch.empty((M, Dv), device=Q.device, dtype=torch.float16)

    # Tiling parameters
    BLOCK_M = 64
    BLOCK_N = 128
    BLOCK_D = 64
    BLOCK_DV = min(64, Dv)

    assert D <= BLOCK_D and Dv <= BLOCK_DV, "Kernel expects D and Dv <= 64 for optimized path"

    grid = (triton.cdiv(M, BLOCK_M),)

    SCALE = 1.0 / math.sqrt(float(D))

    _ragged_attn_kernel[grid](
        Q, K, V, O, row_lens,
        M, N, D, Dv, SCALE,
        Q.stride(0), Q.stride(1),
        K.stride(0), K.stride(1),
        V.stride(0), V.stride(1),
        O.stride(0), O.stride(1),
        BLOCK_M=BLOCK_M, BLOCK_N=BLOCK_N, BLOCK_D=BLOCK_D, BLOCK_DV=BLOCK_DV,
        num_warps=4, num_stages=2,
    )
    return O
"""
        return {"code": code}
