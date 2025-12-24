import math
import torch
import triton
import triton.language as tl


@triton.autotune(
    configs=[
        triton.Config({'BLOCK_M': 1, 'BLOCK_N': 64, 'BLOCK_DQ': 64, 'BLOCK_DV': 64}, num_warps=2, num_stages=4),
        triton.Config({'BLOCK_M': 1, 'BLOCK_N': 128, 'BLOCK_DQ': 64, 'BLOCK_DV': 64}, num_warps=4, num_stages=4),
        triton.Config({'BLOCK_M': 1, 'BLOCK_N': 256, 'BLOCK_DQ': 64, 'BLOCK_DV': 64}, num_warps=4, num_stages=4),
        triton.Config({'BLOCK_M': 1, 'BLOCK_N': 512, 'BLOCK_DQ': 64, 'BLOCK_DV': 64}, num_warps=8, num_stages=3),
        triton.Config({'BLOCK_M': 1, 'BLOCK_N': 128, 'BLOCK_DQ': 128, 'BLOCK_DV': 64}, num_warps=4, num_stages=4),
        triton.Config({'BLOCK_M': 1, 'BLOCK_N': 256, 'BLOCK_DQ': 128, 'BLOCK_DV': 64}, num_warps=8, num_stages=3),
    ],
    key=['N_CTX'],
)
@triton.jit
def _decoding_attn_kernel(
    Q_ptr, K_ptr, V_ptr, O_ptr,
    Z, H, M, N,
    DQ, DV,
    stride_qz, stride_qh, stride_qm, stride_qd,
    stride_kz, stride_kh, stride_kn, stride_kd,
    stride_vz, stride_vh, stride_vn, stride_vd,
    stride_oz, stride_oh, stride_om, stride_od,
    scale,
    BLOCK_M: tl.constexpr, BLOCK_N: tl.constexpr, BLOCK_DQ: tl.constexpr, BLOCK_DV: tl.constexpr
):
    pid_m = tl.program_id(0)
    pid_h = tl.program_id(1)
    pid_z = tl.program_id(2)

    off_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
    m_mask = off_m < M

    dq_idx = tl.arange(0, BLOCK_DQ)
    dv_idx = tl.arange(0, BLOCK_DV)

    # Load Q block [BM, DQ]
    q_ptrs = Q_ptr + pid_z * stride_qz + pid_h * stride_qh + off_m[:, None] * stride_qm + dq_idx[None, :] * stride_qd
    q_mask = m_mask[:, None] & (dq_idx[None, :] < DQ)
    q = tl.load(q_ptrs, mask=q_mask, other=0.0).to(tl.float32)

    # Initialize online softmax
    m_i = tl.full((BLOCK_M,), -float('inf'), dtype=tl.float32)
    l_i = tl.zeros((BLOCK_M,), dtype=tl.float32)
    acc = tl.zeros((BLOCK_M, BLOCK_DV), dtype=tl.float32)

    n_block_start = 0
    while n_block_start < N:
        off_n = n_block_start + tl.arange(0, BLOCK_N)
        n_mask = off_n < N

        # Load K [BN, DQ]
        k_ptrs = K_ptr + pid_z * stride_kz + pid_h * stride_kh + off_n[:, None] * stride_kn + dq_idx[None, :] * stride_kd
        k_mask = n_mask[:, None] & (dq_idx[None, :] < DQ)
        k = tl.load(k_ptrs, mask=k_mask, other=0.0).to(tl.float32)

        # Compute attention scores [BM, BN]
        qk = tl.dot(q, tl.trans(k)) * scale  # [BM, BN]

        # Compute online softmax update
        current_max = tl.max(qk, axis=1)
        m_new = tl.maximum(m_i, current_max)
        alpha = tl.exp(m_i - m_new)

        p = tl.exp(qk - m_new[:, None])
        l_new = tl.sum(p, axis=1) + l_i * alpha

        # Load V [BN, DV]
        v_ptrs = V_ptr + pid_z * stride_vz + pid_h * stride_vh + off_n[:, None] * stride_vn + dv_idx[None, :] * stride_vd
        v_mask = n_mask[:, None] & (dv_idx[None, :] < DV)
        v = tl.load(v_ptrs, mask=v_mask, other=0.0).to(tl.float32)

        # Update accumulator
        acc = acc * alpha[:, None] + tl.dot(p.to(tl.float32), v)

        # Update m_i, l_i
        m_i = m_new
        l_i = l_new

        n_block_start += BLOCK_N

    # Normalize
    out = acc / l_i[:, None]
    # Store output [BM, DV]
    o_ptrs = O_ptr + pid_z * stride_oz + pid_h * stride_oh + off_m[:, None] * stride_om + dv_idx[None, :] * stride_od
    o_mask = m_mask[:, None] & (dv_idx[None, :] < DV)
    tl.store(o_ptrs, out.to(tl.float16), mask=o_mask)


def decoding_attn(Q: torch.Tensor, K: torch.Tensor, V: torch.Tensor) -> torch.Tensor:
    """
    Decoding attention computation.

    Args:
        Q: (Z, H, M, Dq) float16
        K: (Z, H, N, Dq) float16
        V: (Z, H, N, Dv) float16

    Returns:
        (Z, H, M, Dv) float16
    """
    assert Q.dtype in (torch.float16, torch.bfloat16)
    assert K.dtype == Q.dtype and V.dtype == Q.dtype
    assert Q.is_cuda and K.is_cuda and V.is_cuda, "Tensors must be on CUDA"

    Z, H, M, DQ = Q.shape
    Zk, Hk, N, DQk = K.shape
    Zv, Hv, Nv, DV = V.shape
    assert Z == Zk == Zv and H == Hk == Hv and DQ == DQk and N == Nv

    O = torch.empty((Z, H, M, DV), device=Q.device, dtype=Q.dtype)

    # Extract strides (in elements)
    stride_qz, stride_qh, stride_qm, stride_qd = Q.stride()
    stride_kz, stride_kh, stride_kn, stride_kd = K.stride()
    stride_vz, stride_vh, stride_vn, stride_vd = V.stride()
    stride_oz, stride_oh, stride_om, stride_od = O.stride()

    scale = 1.0 / math.sqrt(DQ)

    grid = (M, H, Z)
    _decoding_attn_kernel[grid](
        Q, K, V, O,
        Z, H, M, N,
        DQ, DV,
        stride_qz, stride_qh, stride_qm, stride_qd,
        stride_kz, stride_kh, stride_kn, stride_kd,
        stride_vz, stride_vh, stride_vn, stride_vd,
        stride_oz, stride_oh, stride_om, stride_od,
        scale,
        N_CTX=N
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
        triton.Config({'BLOCK_M': 1, 'BLOCK_N': 64, 'BLOCK_DQ': 64, 'BLOCK_DV': 64}, num_warps=2, num_stages=4),
        triton.Config({'BLOCK_M': 1, 'BLOCK_N': 128, 'BLOCK_DQ': 64, 'BLOCK_DV': 64}, num_warps=4, num_stages=4),
        triton.Config({'BLOCK_M': 1, 'BLOCK_N': 256, 'BLOCK_DQ': 64, 'BLOCK_DV': 64}, num_warps=4, num_stages=4),
        triton.Config({'BLOCK_M': 1, 'BLOCK_N': 512, 'BLOCK_DQ': 64, 'BLOCK_DV': 64}, num_warps=8, num_stages=3),
        triton.Config({'BLOCK_M': 1, 'BLOCK_N': 128, 'BLOCK_DQ': 128, 'BLOCK_DV': 64}, num_warps=4, num_stages=4),
        triton.Config({'BLOCK_M': 1, 'BLOCK_N': 256, 'BLOCK_DQ': 128, 'BLOCK_DV': 64}, num_warps=8, num_stages=3),
    ],
    key=['N_CTX'],
)
@triton.jit
def _decoding_attn_kernel(
    Q_ptr, K_ptr, V_ptr, O_ptr,
    Z, H, M, N,
    DQ, DV,
    stride_qz, stride_qh, stride_qm, stride_qd,
    stride_kz, stride_kh, stride_kn, stride_kd,
    stride_vz, stride_vh, stride_vn, stride_vd,
    stride_oz, stride_oh, stride_om, stride_od,
    scale,
    BLOCK_M: tl.constexpr, BLOCK_N: tl.constexpr, BLOCK_DQ: tl.constexpr, BLOCK_DV: tl.constexpr
):
    pid_m = tl.program_id(0)
    pid_h = tl.program_id(1)
    pid_z = tl.program_id(2)

    off_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
    m_mask = off_m < M

    dq_idx = tl.arange(0, BLOCK_DQ)
    dv_idx = tl.arange(0, BLOCK_DV)

    # Load Q block [BM, DQ]
    q_ptrs = Q_ptr + pid_z * stride_qz + pid_h * stride_qh + off_m[:, None] * stride_qm + dq_idx[None, :] * stride_qd
    q_mask = m_mask[:, None] & (dq_idx[None, :] < DQ)
    q = tl.load(q_ptrs, mask=q_mask, other=0.0).to(tl.float32)

    # Initialize online softmax
    m_i = tl.full((BLOCK_M,), -float('inf'), dtype=tl.float32)
    l_i = tl.zeros((BLOCK_M,), dtype=tl.float32)
    acc = tl.zeros((BLOCK_M, BLOCK_DV), dtype=tl.float32)

    n_block_start = 0
    while n_block_start < N:
        off_n = n_block_start + tl.arange(0, BLOCK_N)
        n_mask = off_n < N

        # Load K [BN, DQ]
        k_ptrs = K_ptr + pid_z * stride_kz + pid_h * stride_kh + off_n[:, None] * stride_kn + dq_idx[None, :] * stride_kd
        k_mask = n_mask[:, None] & (dq_idx[None, :] < DQ)
        k = tl.load(k_ptrs, mask=k_mask, other=0.0).to(tl.float32)

        # Compute attention scores [BM, BN]
        qk = tl.dot(q, tl.trans(k)) * scale  # [BM, BN]

        # Compute online softmax update
        current_max = tl.max(qk, axis=1)
        m_new = tl.maximum(m_i, current_max)
        alpha = tl.exp(m_i - m_new)

        p = tl.exp(qk - m_new[:, None])
        l_new = tl.sum(p, axis=1) + l_i * alpha

        # Load V [BN, DV]
        v_ptrs = V_ptr + pid_z * stride_vz + pid_h * stride_vh + off_n[:, None] * stride_vn + dv_idx[None, :] * stride_vd
        v_mask = n_mask[:, None] & (dv_idx[None, :] < DV)
        v = tl.load(v_ptrs, mask=v_mask, other=0.0).to(tl.float32)

        # Update accumulator
        acc = acc * alpha[:, None] + tl.dot(p.to(tl.float32), v)

        # Update m_i, l_i
        m_i = m_new
        l_i = l_new

        n_block_start += BLOCK_N

    # Normalize
    out = acc / l_i[:, None]
    # Store output [BM, DV]
    o_ptrs = O_ptr + pid_z * stride_oz + pid_h * stride_oh + off_m[:, None] * stride_om + dv_idx[None, :] * stride_od
    o_mask = m_mask[:, None] & (dv_idx[None, :] < DV)
    tl.store(o_ptrs, out.to(tl.float16), mask=o_mask)


def decoding_attn(Q: torch.Tensor, K: torch.Tensor, V: torch.Tensor) -> torch.Tensor:
    """
    Decoding attention computation.

    Args:
        Q: (Z, H, M, Dq) float16
        K: (Z, H, N, Dq) float16
        V: (Z, H, N, Dv) float16

    Returns:
        (Z, H, M, Dv) float16
    """
    assert Q.dtype in (torch.float16, torch.bfloat16)
    assert K.dtype == Q.dtype and V.dtype == Q.dtype
    assert Q.is_cuda and K.is_cuda and V.is_cuda, "Tensors must be on CUDA"

    Z, H, M, DQ = Q.shape
    Zk, Hk, N, DQk = K.shape
    Zv, Hv, Nv, DV = V.shape
    assert Z == Zk == Zv and H == Hk == Hv and DQ == DQk and N == Nv

    O = torch.empty((Z, H, M, DV), device=Q.device, dtype=Q.dtype)

    # Extract strides (in elements)
    stride_qz, stride_qh, stride_qm, stride_qd = Q.stride()
    stride_kz, stride_kh, stride_kn, stride_kd = K.stride()
    stride_vz, stride_vh, stride_vn, stride_vd = V.stride()
    stride_oz, stride_oh, stride_om, stride_od = O.stride()

    scale = 1.0 / math.sqrt(DQ)

    grid = (M, H, Z)
    _decoding_attn_kernel[grid](
        Q, K, V, O,
        Z, H, M, N,
        DQ, DV,
        stride_qz, stride_qh, stride_qm, stride_qd,
        stride_kz, stride_kh, stride_kn, stride_kd,
        stride_vz, stride_vh, stride_vn, stride_vd,
        stride_oz, stride_oh, stride_om, stride_od,
        scale,
        N_CTX=N
    )
    return O
'''
        return {"code": code}
