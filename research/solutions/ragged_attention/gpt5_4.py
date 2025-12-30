import math
import torch
import triton
import triton.language as tl


@triton.autotune(
    configs=[
        triton.Config(
            {
                "BLOCK_M": 64,
                "BLOCK_N": 128,
                "BLOCK_D": 64,
                "BLOCK_DV": 64,
            },
            num_warps=4,
            num_stages=2,
        ),
        triton.Config(
            {
                "BLOCK_M": 128,
                "BLOCK_N": 128,
                "BLOCK_D": 64,
                "BLOCK_DV": 64,
            },
            num_warps=8,
            num_stages=2,
        ),
        triton.Config(
            {
                "BLOCK_M": 64,
                "BLOCK_N": 64,
                "BLOCK_D": 64,
                "BLOCK_DV": 64,
            },
            num_warps=4,
            num_stages=2,
        ),
    ],
    key=["M", "N", "D", "DV"],
)
@triton.jit
def _ragged_attn_fwd(
    Q, K, V, O, ROW_LENS,
    M: tl.constexpr, N: tl.constexpr, D: tl.constexpr, DV: tl.constexpr,
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
    offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
    offs_d = tl.arange(0, BLOCK_D)
    offs_dv = tl.arange(0, BLOCK_DV)

    mask_m = offs_m < M
    mask_d = offs_d < D
    mask_dv = offs_dv < DV

    # Load Q block: [BM, D]
    q_ptrs = Q + offs_m[:, None] * stride_qm + offs_d[None, :] * stride_qd
    q = tl.load(q_ptrs, mask=mask_m[:, None] & mask_d[None, :], other=0.0).to(tl.float16)

    # Load row lengths: [BM]
    rl = tl.load(ROW_LENS + offs_m, mask=mask_m, other=0).to(tl.int32)

    # Initialize streaming softmax stats
    m_i = tl.full((BLOCK_M,), -float("inf"), tl.float32)
    l_i = tl.zeros((BLOCK_M,), tl.float32)
    acc = tl.zeros((BLOCK_M, BLOCK_DV), tl.float32)

    # Iterate over K/V blocks
    for start_n in range(0, N, BLOCK_N):
        offs_n = start_n + tl.arange(0, BLOCK_N)
        mask_n = offs_n < N

        # Load K block: [BN, D]
        k_ptrs = K + offs_n[:, None] * stride_km + offs_d[None, :] * stride_kd
        k = tl.load(k_ptrs, mask=mask_n[:, None] & mask_d[None, :], other=0.0).to(tl.float16)

        # Compute scores: [BM, BN]
        qk = tl.dot(q, tl.trans(k)).to(tl.float32) * scale

        # Apply ragged mask
        offs_n_i32 = offs_n.to(tl.int32)[None, :]  # [1, BN]
        allowed = (offs_n_i32 < rl[:, None]) & mask_m[:, None] & mask_n[None, :]
        scores = tl.where(allowed, qk, -float("inf"))

        # Compute softmax with streaming
        m_curr = tl.max(scores, axis=1)
        m_new = tl.maximum(m_i, m_curr)
        # exp(scores - m_new)
        scores_shifted = scores - m_new[:, None]
        p = tl.exp(scores_shifted)
        l_curr = tl.sum(p, axis=1)

        alpha = tl.exp(m_i - m_new)
        l_new = l_i * alpha + l_curr

        # Load V block: [BN, DV]
        v_ptrs = V + offs_n[:, None] * stride_vm + offs_dv[None, :] * stride_vd
        v = tl.load(v_ptrs, mask=mask_n[:, None] & mask_dv[None, :], other=0.0).to(tl.float16)

        # Update acc
        # Convert p to f16 for dot; accumulation is f32
        acc = acc * alpha[:, None] + tl.dot(p.to(tl.float16), v)

        # Update running stats
        m_i = m_new
        l_i = l_new

    # Normalize acc by l_i
    # Guard against division by zero (shouldn't happen if rl > 0)
    denom = tl.where(l_i > 0, l_i, 1.0)
    o = acc / denom[:, None]
    # Store O
    o_ptrs = O + offs_m[:, None] * stride_om + offs_dv[None, :] * stride_od
    tl.store(o_ptrs, o.to(tl.float16), mask=mask_m[:, None] & mask_dv[None, :])


def ragged_attn(Q: torch.Tensor, K: torch.Tensor, V: torch.Tensor, row_lens: torch.Tensor) -> torch.Tensor:
    assert Q.is_cuda and K.is_cuda and V.is_cuda and row_lens.is_cuda
    assert Q.dtype == torch.float16 and K.dtype == torch.float16 and V.dtype == torch.float16
    assert Q.dim() == 2 and K.dim() == 2 and V.dim() == 2 and row_lens.dim() == 1
    M, D = Q.shape
    N, Dk = K.shape
    Nv, DV = V.shape
    assert D == Dk and N == Nv, "Incompatible shapes"
    # Ensure row_lens is int32
    if row_lens.dtype != torch.int32:
        row_lens_32 = row_lens.to(torch.int32)
    else:
        row_lens_32 = row_lens
    O = torch.empty((M, DV), device=Q.device, dtype=torch.float16)

    scale = 1.0 / math.sqrt(D)

    grid = (triton.cdiv(M, 64),)

    _ragged_attn_fwd[grid](
        Q, K, V, O, row_lens_32,
        M, N, D, DV,
        Q.stride(0), Q.stride(1),
        K.stride(0), K.stride(1),
        V.stride(0), V.stride(1),
        O.stride(0), O.stride(1),
        scale,
    )
    return O


class Solution:
    def solve(self, spec_path: str = None) -> dict:
        code = r'''
import math
import torch
import triton
import triton.language as tl


@triton.autotune(
    configs=[
        triton.Config(
            {
                "BLOCK_M": 64,
                "BLOCK_N": 128,
                "BLOCK_D": 64,
                "BLOCK_DV": 64,
            },
            num_warps=4,
            num_stages=2,
        ),
        triton.Config(
            {
                "BLOCK_M": 128,
                "BLOCK_N": 128,
                "BLOCK_D": 64,
                "BLOCK_DV": 64,
            },
            num_warps=8,
            num_stages=2,
        ),
        triton.Config(
            {
                "BLOCK_M": 64,
                "BLOCK_N": 64,
                "BLOCK_D": 64,
                "BLOCK_DV": 64,
            },
            num_warps=4,
            num_stages=2,
        ),
    ],
    key=["M", "N", "D", "DV"],
)
@triton.jit
def _ragged_attn_fwd(
    Q, K, V, O, ROW_LENS,
    M: tl.constexpr, N: tl.constexpr, D: tl.constexpr, DV: tl.constexpr,
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
    offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
    offs_d = tl.arange(0, BLOCK_D)
    offs_dv = tl.arange(0, BLOCK_DV)

    mask_m = offs_m < M
    mask_d = offs_d < D
    mask_dv = offs_dv < DV

    # Load Q block: [BM, D]
    q_ptrs = Q + offs_m[:, None] * stride_qm + offs_d[None, :] * stride_qd
    q = tl.load(q_ptrs, mask=mask_m[:, None] & mask_d[None, :], other=0.0).to(tl.float16)

    # Load row lengths: [BM]
    rl = tl.load(ROW_LENS + offs_m, mask=mask_m, other=0).to(tl.int32)

    # Initialize streaming softmax stats
    m_i = tl.full((BLOCK_M,), -float("inf"), tl.float32)
    l_i = tl.zeros((BLOCK_M,), tl.float32)
    acc = tl.zeros((BLOCK_M, BLOCK_DV), tl.float32)

    # Iterate over K/V blocks
    for start_n in range(0, N, BLOCK_N):
        offs_n = start_n + tl.arange(0, BLOCK_N)
        mask_n = offs_n < N

        # Load K block: [BN, D]
        k_ptrs = K + offs_n[:, None] * stride_km + offs_d[None, :] * stride_kd
        k = tl.load(k_ptrs, mask=mask_n[:, None] & mask_d[None, :], other=0.0).to(tl.float16)

        # Compute scores: [BM, BN]
        qk = tl.dot(q, tl.trans(k)).to(tl.float32) * scale

        # Apply ragged mask
        offs_n_i32 = offs_n.to(tl.int32)[None, :]  # [1, BN]
        allowed = (offs_n_i32 < rl[:, None]) & mask_m[:, None] & mask_n[None, :]
        scores = tl.where(allowed, qk, -float("inf"))

        # Compute softmax with streaming
        m_curr = tl.max(scores, axis=1)
        m_new = tl.maximum(m_i, m_curr)
        scores_shifted = scores - m_new[:, None]
        p = tl.exp(scores_shifted)
        l_curr = tl.sum(p, axis=1)

        alpha = tl.exp(m_i - m_new)
        l_new = l_i * alpha + l_curr

        # Load V block: [BN, DV]
        v_ptrs = V + offs_n[:, None] * stride_vm + offs_dv[None, :] * stride_vd
        v = tl.load(v_ptrs, mask=mask_n[:, None] & mask_dv[None, :], other=0.0).to(tl.float16)

        # Update acc
        acc = acc * alpha[:, None] + tl.dot(p.to(tl.float16), v)

        # Update running stats
        m_i = m_new
        l_i = l_new

    # Normalize acc by l_i
    denom = tl.where(l_i > 0, l_i, 1.0)
    o = acc / denom[:, None]
    # Store O
    o_ptrs = O + offs_m[:, None] * stride_om + offs_dv[None, :] * stride_od
    tl.store(o_ptrs, o.to(tl.float16), mask=mask_m[:, None] & mask_dv[None, :])


def ragged_attn(Q: torch.Tensor, K: torch.Tensor, V: torch.Tensor, row_lens: torch.Tensor) -> torch.Tensor:
    assert Q.is_cuda and K.is_cuda and V.is_cuda and row_lens.is_cuda
    assert Q.dtype == torch.float16 and K.dtype == torch.float16 and V.dtype == torch.float16
    assert Q.dim() == 2 and K.dim() == 2 and V.dim() == 2 and row_lens.dim() == 1
    M, D = Q.shape
    N, Dk = K.shape
    Nv, DV = V.shape
    assert D == Dk and N == Nv, "Incompatible shapes"
    # Ensure row_lens is int32
    if row_lens.dtype != torch.int32:
        row_lens_32 = row_lens.to(torch.int32)
    else:
        row_lens_32 = row_lens
    O = torch.empty((M, DV), device=Q.device, dtype=torch.float16)

    scale = 1.0 / math.sqrt(D)

    grid = (triton.cdiv(M, 64),)

    _ragged_attn_fwd[grid](
        Q, K, V, O, row_lens_32,
        M, N, D, DV,
        Q.stride(0), Q.stride(1),
        K.stride(0), K.stride(1),
        V.stride(0), V.stride(1),
        O.stride(0), O.stride(1),
        scale,
    )
    return O
'''
        return {"code": code}