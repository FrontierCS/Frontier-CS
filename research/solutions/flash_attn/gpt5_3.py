import torch
import triton
import triton.language as tl


class Solution:
    def solve(self, spec_path: str = None) -> dict:
        code = r'''
import torch
import triton
import triton.language as tl
from typing import Optional

@triton.autotune(
    configs=[
        triton.Config({'BLOCK_M': 64, 'BLOCK_N': 64}, num_warps=4, num_stages=2),
        triton.Config({'BLOCK_M': 64, 'BLOCK_N': 128}, num_warps=4, num_stages=2),
        triton.Config({'BLOCK_M': 64, 'BLOCK_N': 128}, num_warps=8, num_stages=2),
        triton.Config({'BLOCK_M': 64, 'BLOCK_N': 128}, num_warps=8, num_stages=3),
        triton.Config({'BLOCK_M': 32, 'BLOCK_N': 128}, num_warps=4, num_stages=2),
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 64}, num_warps=8, num_stages=2),
    ],
    key=['M', 'N', 'D_HEAD', 'D_VALUE', 'HAS_CAUSAL'],
)
@triton.jit
def _flash_attn_fwd(
    Q_ptr, K_ptr, V_ptr, O_ptr,
    B, M, N,
    stride_qb, stride_qm, stride_qd,
    stride_kb, stride_kn, stride_kd,
    stride_vb, stride_vn, stride_vd,
    stride_ob, stride_om, stride_od,
    SM_SCALE: tl.constexpr,
    HAS_CAUSAL: tl.constexpr,
    D_HEAD: tl.constexpr,
    D_VALUE: tl.constexpr,
    BLOCK_M: tl.constexpr, BLOCK_N: tl.constexpr,
):
    pid_m = tl.program_id(0)
    pid_b = tl.program_id(1)

    off_m = pid_m * BLOCK_M
    offs_m = off_m + tl.arange(0, BLOCK_M)
    offs_d = tl.arange(0, D_HEAD)
    offs_dv = tl.arange(0, D_VALUE)

    # Load Q block [BM, D_HEAD]
    q_ptrs = Q_ptr + pid_b * stride_qb + (offs_m[:, None] * stride_qm) + (offs_d[None, :] * stride_qd)
    q = tl.load(q_ptrs, mask=(offs_m[:, None] < M), other=0.0).to(tl.float32)

    m_i = tl.full((BLOCK_M,), float('-inf'), dtype=tl.float32)
    l_i = tl.zeros((BLOCK_M,), dtype=tl.float32)
    acc = tl.zeros((BLOCK_M, D_VALUE), dtype=tl.float32)

    # Iterate over K/V blocks
    for start_n in range(0, N, BLOCK_N):
        offs_n = start_n + tl.arange(0, BLOCK_N)

        k_ptrs = K_ptr + pid_b * stride_kb + (offs_n[:, None] * stride_kn) + (offs_d[None, :] * stride_kd)
        v_ptrs = V_ptr + pid_b * stride_vb + (offs_n[:, None] * stride_vn) + (offs_dv[None, :] * stride_vd)

        k = tl.load(k_ptrs, mask=(offs_n[:, None] < N), other=0.0).to(tl.float32)  # [BN, D_HEAD]
        v = tl.load(v_ptrs, mask=(offs_n[:, None] < N) & (offs_dv[None, :] < D_VALUE), other=0.0)  # [BN, D_VALUE]
        v = v.to(tl.float32)

        # Compute qk = q @ k^T -> [BM, BN]
        qk = tl.dot(q, tl.trans(k))  # float32

        # Scale
        qk = qk * SM_SCALE

        # Masks
        mask_m = offs_m[:, None] < M
        mask_n = offs_n[None, :] < N
        valid = mask_m & mask_n

        if HAS_CAUSAL:
            # Only allow keys <= queries
            causal_mask = (offs_m[:, None] >= offs_n[None, :])
            valid = valid & causal_mask

        # Apply mask: invalid positions to -inf
        qk = tl.where(valid, qk, float('-inf'))

        # Compute new max for streaming softmax
        row_max = tl.max(qk, axis=1)
        m_i_new = tl.maximum(m_i, row_max)

        # Compute exp and sums
        qk_shifted = qk - m_i_new[:, None]
        p = tl.exp(qk_shifted)

        # Zero out p in invalid positions (since exp(-inf) could be nan in some cases)
        p = tl.where(valid, p, 0.0)

        l_i_new = l_i * tl.exp(m_i - m_i_new) + tl.sum(p, axis=1)

        # Update accumulator
        acc = acc * (tl.exp(m_i - m_i_new))[:, None] + tl.dot(p, v)

        # Update running values
        m_i = m_i_new
        l_i = l_i_new

    # Normalize and store
    o = acc / l_i[:, None]
    o = o.to(tl.float16)
    o_ptrs = O_ptr + pid_b * stride_ob + (offs_m[:, None] * stride_om) + (offs_dv[None, :] * stride_od)
    tl.store(o_ptrs, o, mask=(offs_m[:, None] < M) & (offs_dv[None, :] < D_VALUE))


def flash_attn(Q: torch.Tensor, K: torch.Tensor, V: torch.Tensor, causal: bool = True) -> torch.Tensor:
    """
    Flash attention computation with optional causal masking.
    Args:
        Q: (Z, H, M, Dq) float16, CUDA
        K: (Z, H, N, Dq) float16, CUDA
        V: (Z, H, N, Dv) float16, CUDA
        causal: apply causal mask
    Returns:
        (Z, H, M, Dv) float16
    """
    assert Q.is_cuda and K.is_cuda and V.is_cuda, "Inputs must be on CUDA"
    assert Q.dtype == torch.float16 and K.dtype == torch.float16 and V.dtype == torch.float16, "Inputs must be float16"
    Z, H, M, Dq = Q.shape
    Zk, Hk, Nk, Dqk = K.shape
    Zv, Hv, Nv, Dv = V.shape
    assert Z == Zk == Zv and H == Hk == Hv, "Batch/heads mismatch"
    assert Dq == Dqk and Nk == Nv, "K/V dims mismatch"
    N = Nk
    assert M == N, "Flash attention assumes M == N in this benchmark"

    # Make tensors contiguous for predictable strides
    Qc = Q.contiguous()
    Kc = K.contiguous()
    Vc = V.contiguous()

    B = Z * H

    # Merge Z and H dimensions
    Qv = Qc.view(B, M, Dq)
    Kv = Kc.view(B, N, Dq)
    Vv = Vc.view(B, N, Dv)

    # Allocate output
    Ov = torch.empty((B, M, Dv), device=Q.device, dtype=torch.float16)

    # Compute strides (in elements)
    stride_qb, stride_qm, stride_qd = Qv.stride()
    stride_kb, stride_kn, stride_kd = Kv.stride()
    stride_vb, stride_vn, stride_vd = Vv.stride()
    stride_ob, stride_om, stride_od = Ov.stride()

    # Softmax scale
    sm_scale = 1.0 / (Dq ** 0.5)

    # Launch kernel
    grid = (triton.cdiv(M, 64), B)  # BLOCK_M default 64; autotune will adjust BLOCK_N
    _flash_attn_fwd[grid](
        Qv, Kv, Vv, Ov,
        B, M, N,
        stride_qb, stride_qm, stride_qd,
        stride_kb, stride_kn, stride_kd,
        stride_vb, stride_vn, stride_vd,
        stride_ob, stride_om, stride_od,
        sm_scale,
        causal,
        D_HEAD=Dq,
        D_VALUE=Dv,
    )
    # Reshape back to (Z, H, M, Dv)
    O = Ov.view(Z, H, M, Dv)
    return O
'''
        return {"code": code}