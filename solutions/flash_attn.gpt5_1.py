import math
import os

class Solution:
    def solve(self, spec_path: str = None) -> dict:
        code = r'''
import math
import torch
import triton
import triton.language as tl

@triton.jit
def _flash_attn_fwd_kernel(
    Q_ptr, K_ptr, V_ptr, O_ptr,
    stride_q_zh, stride_q_m, stride_q_d,
    stride_k_zh, stride_k_n, stride_k_d,
    stride_v_zh, stride_v_n, stride_v_d,
    stride_o_zh, stride_o_m, stride_o_d,
    ZH, M, N, D, DV,
    sm_scale: tl.constexpr,
    CAUSAL: tl.constexpr,
    BLOCK_M: tl.constexpr, BLOCK_N: tl.constexpr, BLOCK_DMODEL: tl.constexpr, BLOCK_DV: tl.constexpr,
):
    pid_m = tl.program_id(0)
    pid_b = tl.program_id(1)

    offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
    offs_n = tl.arange(0, BLOCK_N)
    offs_d = tl.arange(0, BLOCK_DMODEL)
    offs_dv = tl.arange(0, BLOCK_DV)

    # Load Q: [BM, D]
    q_ptrs = Q_ptr + pid_b * stride_q_zh + offs_m[:, None] * stride_q_m + offs_d[None, :] * stride_q_d
    q_mask_m = offs_m < M
    q_mask_d = offs_d < D
    q = tl.load(q_ptrs, mask=q_mask_m[:, None] & q_mask_d[None, :], other=0.0).to(tl.float16)

    # Initialize streaming softmax state
    m_i = tl.full((BLOCK_M,), -float("inf"), dtype=tl.float32)
    l_i = tl.zeros((BLOCK_M,), dtype=tl.float32)
    acc = tl.zeros((BLOCK_M, BLOCK_DV), dtype=tl.float32)

    # Loop over K/V tiles
    n_start = 0
    while n_start < N:
        offs_nc = n_start + offs_n

        # Load K: [BN, D]
        k_ptrs = K_ptr + pid_b * stride_k_zh + offs_nc[:, None] * stride_k_n + offs_d[None, :] * stride_k_d
        k_mask_n = offs_nc < N
        k_mask_d = offs_d < D
        k = tl.load(k_ptrs, mask=k_mask_n[:, None] & k_mask_d[None, :], other=0.0).to(tl.float16)

        # Compute scores = Q @ K^T
        # q:[BM,D], k:[BN,D] -> qk:[BM,BN]
        qk = tl.dot(q, tl.trans(k)).to(tl.float32)
        qk = qk * sm_scale

        if CAUSAL:
            # Apply causal mask: keys with index > query index are masked
            offs_m_global = offs_m[:, None]
            offs_n_global = offs_nc[None, :]
            causal_mask = offs_n_global > offs_m_global
            qk = tl.where(causal_mask, tl.full_like(qk, -float("inf")), qk)

        # Compute new m_i and l_i using log-sum-exp trick
        m_ij = tl.max(qk, axis=1)
        m_new = tl.maximum(m_i, m_ij)
        # p = exp(qk - m_new)
        p = tl.exp(qk - m_new[:, None])
        # l_new = l_i * exp(m_i - m_new) + sum(p)
        alpha = tl.exp(m_i - m_new)
        l_new = l_i * alpha + tl.sum(p, axis=1)

        # Load V and update accumulator
        v_ptrs = V_ptr + pid_b * stride_v_zh + offs_nc[:, None] * stride_v_n + offs_dv[None, :] * stride_v_d
        v_mask_dv = offs_dv < DV
        v = tl.load(v_ptrs, mask=k_mask_n[:, None] & v_mask_dv[None, :], other=0.0).to(tl.float16)

        # update = p @ V
        update = tl.dot(p.to(tl.float16), v).to(tl.float32)

        # acc = acc * (l_i * alpha / l_new) + update / l_new
        inv_l_new = 1.0 / l_new
        acc = acc * (l_i * alpha * inv_l_new)[:, None] + update * inv_l_new[:, None]

        # Update running stats
        m_i = m_new
        l_i = l_new

        n_start += BLOCK_N

    # Write back O
    o_ptrs = O_ptr + pid_b * stride_o_zh + offs_m[:, None] * stride_o_m + offs_dv[None, :] * stride_o_d
    o_mask = (offs_m[:, None] < M) & (offs_dv[None, :] < DV)
    tl.store(o_ptrs, acc.to(tl.float16), mask=o_mask)


def _pick_configs(M, N, Dq, Dv):
    # Heuristic configs
    BLOCK_M = 128 if M >= 128 else 64
    BLOCK_N = 64
    # BLOCK for model dims (Dq, Dv)
    if Dq <= 64:
        BLOCK_DMODEL = 64
    elif Dq <= 128:
        BLOCK_DMODEL = 128
    else:
        # Cap at 128, masked loads handle the rest
        BLOCK_DMODEL = 128
    if Dv <= 64:
        BLOCK_DV = 64
    elif Dv <= 128:
        BLOCK_DV = 128
    else:
        BLOCK_DV = 128

    num_warps = 4 if (BLOCK_M == 64 or (Dq <= 64 and Dv <= 64)) else 8
    num_stages = 3
    return BLOCK_M, BLOCK_N, BLOCK_DMODEL, BLOCK_DV, num_warps, num_stages


def flash_attn(Q: torch.Tensor, K: torch.Tensor, V: torch.Tensor, causal: bool = True) -> torch.Tensor:
    """
    Flash attention computation with optional causal masking.

    Args:
        Q: (Z, H, M, Dq) float16, CUDA
        K: (Z, H, N, Dq) float16, CUDA
        V: (Z, H, N, Dv) float16, CUDA
        causal: bool

    Returns:
        O: (Z, H, M, Dv) float16
    """
    assert Q.is_cuda and K.is_cuda and V.is_cuda, "Inputs must be CUDA tensors"
    assert Q.dtype == torch.float16 and K.dtype == torch.float16 and V.dtype == torch.float16, "Inputs must be float16"
    assert Q.dim() == 4 and K.dim() == 4 and V.dim() == 4, "Q, K, V must be 4D tensors"
    Z, H, M, Dq = Q.shape
    Zk, Hk, N, Dk = K.shape
    Zv, Hv, Nv, Dv = V.shape
    assert Z == Zk == Zv and H == Hk == Hv, "Batch/head dims must match"
    assert Dq == Dk, "Q/K feature dims must match"
    assert N == Nv, "K/V sequence dims must match"
    assert N == M, "Flash attn requires N == M"

    # Ensure contiguous layout for predictable strides
    Qc = Q.contiguous()
    Kc = K.contiguous()
    Vc = V.contiguous()

    O = torch.empty((Z, H, M, Dv), device=Q.device, dtype=torch.float16)

    ZH = Z * H
    # Combine Z and H into a single dimension via stride_h
    stride_q_zh = Qc.stride(1)
    stride_q_m = Qc.stride(2)
    stride_q_d = Qc.stride(3)
    stride_k_zh = Kc.stride(1)
    stride_k_n = Kc.stride(2)
    stride_k_d = Kc.stride(3)
    stride_v_zh = Vc.stride(1)
    stride_v_n = Vc.stride(2)
    stride_v_d = Vc.stride(3)
    stride_o_zh = O.stride(1)
    stride_o_m = O.stride(2)
    stride_o_d = O.stride(3)

    BLOCK_M, BLOCK_N, BLOCK_DMODEL, BLOCK_DV, num_warps, num_stages = _pick_configs(M, N, Dq, Dv)

    grid = (triton.cdiv(M, BLOCK_M), ZH)
    sm_scale = 1.0 / math.sqrt(Dq)

    _flash_attn_fwd_kernel[grid](
        Qc, Kc, Vc, O,
        stride_q_zh, stride_q_m, stride_q_d,
        stride_k_zh, stride_k_n, stride_k_d,
        stride_v_zh, stride_v_n, stride_v_d,
        stride_o_zh, stride_o_m, stride_o_d,
        ZH, M, N, Dq, Dv,
        sm_scale,
        CAUSAL=causal,
        BLOCK_M=BLOCK_M, BLOCK_N=BLOCK_N, BLOCK_DMODEL=BLOCK_DMODEL, BLOCK_DV=BLOCK_DV,
        num_warps=num_warps, num_stages=num_stages
    )
    return O
'''
        return {"code": code}
