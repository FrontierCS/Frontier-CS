import math
import os
import torch
import triton
import triton.language as tl


@triton.autotune(
    configs=[
        triton.Config(dict(BM=1, BN=64), num_stages=2, num_warps=4),
        triton.Config(dict(BM=1, BN=128), num_stages=2, num_warps=4),
        triton.Config(dict(BM=1, BN=256), num_stages=2, num_warps=8),
        triton.Config(dict(BM=2, BN=128), num_stages=2, num_warps=4),
        triton.Config(dict(BM=2, BN=256), num_stages=2, num_warps=8),
        triton.Config(dict(BM=4, BN=128), num_stages=2, num_warps=8),
        triton.Config(dict(BM=4, BN=256), num_stages=2, num_warps=8),
    ],
    key=["N", "D_HEAD_Q", "D_HEAD_V"],
)
@triton.jit
def _decoding_attn_kernel(
    Q_ptr, K_ptr, V_ptr, O_ptr,
    Z, H, M, N,
    sQz, sQh, sQm, sQd,
    sKz, sKh, sKn, sKd,
    sVz, sVh, sVn, sVd,
    sOz, sOh, sOm, sOd,
    sm_scale,
    D_HEAD_Q: tl.constexpr, D_HEAD_V: tl.constexpr,
    BM: tl.constexpr, BN: tl.constexpr,
):
    pid_m = tl.program_id(0)
    pid_h = tl.program_id(1)
    pid_z = tl.program_id(2)

    # Offsets
    offs_m = pid_m * BM + tl.arange(0, BM)
    mask_m = offs_m < M

    offs_dq = tl.arange(0, D_HEAD_Q)
    offs_dv = tl.arange(0, D_HEAD_V)

    # Base pointers for this (z, h)
    Q_base = Q_ptr + pid_z * sQz + pid_h * sQh
    K_base = K_ptr + pid_z * sKz + pid_h * sKh
    V_base = V_ptr + pid_z * sVz + pid_h * sVh
    O_base = O_ptr + pid_z * sOz + pid_h * sOh

    # Load Q [BM, D_HEAD_Q]
    q_ptrs = Q_base + offs_m[:, None] * sQm + offs_dq[None, :] * sQd
    q = tl.load(q_ptrs, mask=mask_m[:, None], other=0.0).to(tl.float32)

    # Initialize online softmax state
    m_i = tl.full((BM,), -float("inf"), tl.float32)
    l_i = tl.zeros((BM,), tl.float32)
    o_acc = tl.zeros((BM, D_HEAD_V), tl.float32)

    # Iterate over K/V blocks along N
    offs_bn = tl.arange(0, BN)
    n_blocks = tl.cdiv(N, BN)
    for nb in range(0, n_blocks):
        offs_n = nb * BN + offs_bn
        kv_mask = offs_n < N

        # Load K [BN, D_HEAD_Q]
        k_ptrs = K_base + offs_n[:, None] * sKn + offs_dq[None, :] * sKd
        k = tl.load(k_ptrs, mask=kv_mask[:, None], other=0.0).to(tl.float32)

        # Compute QK^T [BM, BN]
        qk = tl.dot(q, tl.trans(k))
        qk = qk * sm_scale
        qk = tl.where(kv_mask[None, :], qk, -float("inf"))

        # Online softmax update
        m_ij = tl.max(qk, 1)
        m_new = tl.maximum(m_i, m_ij)
        p = tl.exp(qk - m_new[:, None])
        l_ij = tl.sum(p, 1)
        l_new = tl.exp(m_i - m_new) * l_i + l_ij

        # Load V [BN, D_HEAD_V]
        v_ptrs = V_base + offs_n[:, None] * sVn + offs_dv[None, :] * sVd
        v = tl.load(v_ptrs, mask=kv_mask[:, None], other=0.0).to(tl.float32)

        # Compute contribution to O
        pv = tl.dot(p.to(tl.float32), v)  # [BM, D_HEAD_V]
        alpha = tl.exp(m_i - m_new) * (l_i / l_new)
        o_acc = o_acc * alpha[:, None] + pv / l_new[:, None]

        # Update state
        m_i = m_new
        l_i = l_new

    # Store result
    o_ptrs = O_base + offs_m[:, None] * sOm + offs_dv[None, :] * sOd
    tl.store(o_ptrs, o_acc.to(tl.float16), mask=mask_m[:, None])


def decoding_attn(Q: torch.Tensor, K: torch.Tensor, V: torch.Tensor) -> torch.Tensor:
    """
    Decoding attention computation.

    Args:
        Q: Tensor (Z, H, M, Dq) float16/cuda
        K: Tensor (Z, H, N, Dq) float16/cuda
        V: Tensor (Z, H, N, Dv) float16/cuda

    Returns:
        Tensor (Z, H, M, Dv) float16
    """
    assert Q.is_cuda and K.is_cuda and V.is_cuda, "Inputs must be CUDA tensors"
    assert Q.dtype == torch.float16 and K.dtype == torch.float16 and V.dtype == torch.float16, "Inputs must be float16"
    assert Q.shape[0] == K.shape[0] == V.shape[0], "Batch dimension mismatch"
    assert Q.shape[1] == K.shape[1] == V.shape[1], "Head dimension mismatch"
    assert Q.shape[3] == K.shape[3], "Q/K head dim mismatch"
    assert K.shape[2] == V.shape[2], "K/V sequence length mismatch"

    Z, H, M, Dq = Q.shape
    _, _, N, Dk = K.shape
    _, _, _, Dv = V.shape

    assert Dq == Dk

    sm_scale = 1.0 / math.sqrt(Dq)

    O = torch.empty((Z, H, M, Dv), device=Q.device, dtype=torch.float16)

    # Ensure strides are in elements (PyTorch default)
    sQz, sQh, sQm, sQd = Q.stride()
    sKz, sKh, sKn, sKd = K.stride()
    sVz, sVh, sVn, sVd = V.stride()
    sOz, sOh, sOm, sOd = O.stride()

    # Launch kernel
    def grid(meta):
        BM = meta["BM"]
        return (triton.cdiv(M, BM), H, Z)

    _decoding_attn_kernel[grid](
        Q, K, V, O,
        Z, H, M, N,
        sQz, sQh, sQm, sQd,
        sKz, sKh, sKn, sKd,
        sVz, sVh, sVn, sVd,
        sOz, sOh, sOm, sOd,
        sm_scale,
        D_HEAD_Q=Dq, D_HEAD_V=Dv,
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
        triton.Config(dict(BM=1, BN=64), num_stages=2, num_warps=4),
        triton.Config(dict(BM=1, BN=128), num_stages=2, num_warps=4),
        triton.Config(dict(BM=1, BN=256), num_stages=2, num_warps=8),
        triton.Config(dict(BM=2, BN=128), num_stages=2, num_warps=4),
        triton.Config(dict(BM=2, BN=256), num_stages=2, num_warps=8),
        triton.Config(dict(BM=4, BN=128), num_stages=2, num_warps=8),
        triton.Config(dict(BM=4, BN=256), num_stages=2, num_warps=8),
    ],
    key=["N", "D_HEAD_Q", "D_HEAD_V"],
)
@triton.jit
def _decoding_attn_kernel(
    Q_ptr, K_ptr, V_ptr, O_ptr,
    Z, H, M, N,
    sQz, sQh, sQm, sQd,
    sKz, sKh, sKn, sKd,
    sVz, sVh, sVn, sVd,
    sOz, sOh, sOm, sOd,
    sm_scale,
    D_HEAD_Q: tl.constexpr, D_HEAD_V: tl.constexpr,
    BM: tl.constexpr, BN: tl.constexpr,
):
    pid_m = tl.program_id(0)
    pid_h = tl.program_id(1)
    pid_z = tl.program_id(2)

    offs_m = pid_m * BM + tl.arange(0, BM)
    mask_m = offs_m < M

    offs_dq = tl.arange(0, D_HEAD_Q)
    offs_dv = tl.arange(0, D_HEAD_V)

    Q_base = Q_ptr + pid_z * sQz + pid_h * sQh
    K_base = K_ptr + pid_z * sKz + pid_h * sKh
    V_base = V_ptr + pid_z * sVz + pid_h * sVh
    O_base = O_ptr + pid_z * sOz + pid_h * sOh

    q_ptrs = Q_base + offs_m[:, None] * sQm + offs_dq[None, :] * sQd
    q = tl.load(q_ptrs, mask=mask_m[:, None], other=0.0).to(tl.float32)

    m_i = tl.full((BM,), -float("inf"), tl.float32)
    l_i = tl.zeros((BM,), tl.float32)
    o_acc = tl.zeros((BM, D_HEAD_V), tl.float32)

    offs_bn = tl.arange(0, BN)
    n_blocks = tl.cdiv(N, BN)
    for nb in range(0, n_blocks):
        offs_n = nb * BN + offs_bn
        kv_mask = offs_n < N

        k_ptrs = K_base + offs_n[:, None] * sKn + offs_dq[None, :] * sKd
        k = tl.load(k_ptrs, mask=kv_mask[:, None], other=0.0).to(tl.float32)

        qk = tl.dot(q, tl.trans(k))
        qk = qk * sm_scale
        qk = tl.where(kv_mask[None, :], qk, -float("inf"))

        m_ij = tl.max(qk, 1)
        m_new = tl.maximum(m_i, m_ij)
        p = tl.exp(qk - m_new[:, None])
        l_ij = tl.sum(p, 1)
        l_new = tl.exp(m_i - m_new) * l_i + l_ij

        v_ptrs = V_base + offs_n[:, None] * sVn + offs_dv[None, :] * sVd
        v = tl.load(v_ptrs, mask=kv_mask[:, None], other=0.0).to(tl.float32)

        pv = tl.dot(p.to(tl.float32), v)
        alpha = tl.exp(m_i - m_new) * (l_i / l_new)
        o_acc = o_acc * alpha[:, None] + pv / l_new[:, None]

        m_i = m_new
        l_i = l_new

    o_ptrs = O_base + offs_m[:, None] * sOm + offs_dv[None, :] * sOd
    tl.store(o_ptrs, o_acc.to(tl.float16), mask=mask_m[:, None])


def decoding_attn(Q: torch.Tensor, K: torch.Tensor, V: torch.Tensor) -> torch.Tensor:
    assert Q.is_cuda and K.is_cuda and V.is_cuda, "Inputs must be CUDA tensors"
    assert Q.dtype == torch.float16 and K.dtype == torch.float16 and V.dtype == torch.float16, "Inputs must be float16"
    assert Q.shape[0] == K.shape[0] == V.shape[0], "Batch dimension mismatch"
    assert Q.shape[1] == K.shape[1] == V.shape[1], "Head dimension mismatch"
    assert Q.shape[3] == K.shape[3], "Q/K head dim mismatch"
    assert K.shape[2] == V.shape[2], "K/V sequence length mismatch"

    Z, H, M, Dq = Q.shape
    _, _, N, Dk = K.shape
    _, _, _, Dv = V.shape
    assert Dq == Dk

    sm_scale = 1.0 / math.sqrt(Dq)

    O = torch.empty((Z, H, M, Dv), device=Q.device, dtype=torch.float16)

    sQz, sQh, sQm, sQd = Q.stride()
    sKz, sKh, sKn, sKd = K.stride()
    sVz, sVh, sVn, sVd = V.stride()
    sOz, sOh, sOm, sOd = O.stride()

    def grid(meta):
        BM = meta["BM"]
        return (triton.cdiv(M, BM), H, Z)

    _decoding_attn_kernel[grid](
        Q, K, V, O,
        Z, H, M, N,
        sQz, sQh, sQm, sQd,
        sKz, sKh, sKn, sKd,
        sVz, sVh, sVn, sVd,
        sOz, sOh, sOm, sOd,
        sm_scale,
        D_HEAD_Q=Dq, D_HEAD_V=Dv,
    )
    return O
'''
        return {"code": code}