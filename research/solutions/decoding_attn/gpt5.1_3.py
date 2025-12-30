import math
import sys
import inspect

import torch
import triton
import triton.language as tl


@triton.autotune(
    configs=[
        triton.Config({"BLOCK_N": 64}, num_warps=2, num_stages=2),
        triton.Config({"BLOCK_N": 128}, num_warps=4, num_stages=2),
        triton.Config({"BLOCK_N": 256}, num_warps=4, num_stages=3),
        triton.Config({"BLOCK_N": 512}, num_warps=8, num_stages=3),
    ],
    key=["N"],
)
@triton.jit
def _decoding_attn_kernel(
    Q_ptr,
    K_ptr,
    V_ptr,
    Out_ptr,
    stride_qz,
    stride_qh,
    stride_qm,
    stride_qd,
    stride_kz,
    stride_kh,
    stride_kn,
    stride_kd,
    stride_vz,
    stride_vh,
    stride_vn,
    stride_vd,
    stride_oz,
    stride_oh,
    stride_om,
    stride_od,
    Z,
    H,
    M,
    N,
    sm_scale,
    D_HEAD: tl.constexpr,
    D_VAL: tl.constexpr,
    BLOCK_N: tl.constexpr,
):
    pid = tl.program_id(0)
    m_idx = pid % M
    tmp = pid // M
    h_idx = tmp % H
    z_idx = tmp // H

    offs_dq = tl.arange(0, D_HEAD)
    q_row_ptr = Q_ptr + z_idx * stride_qz + h_idx * stride_qh + m_idx * stride_qm
    q = tl.load(q_row_ptr + offs_dq).to(tl.float32)

    o_row_ptr = Out_ptr + z_idx * stride_oz + h_idx * stride_oh + m_idx * stride_om
    offs_dv = tl.arange(0, D_VAL)

    k_base = K_ptr + z_idx * stride_kz + h_idx * stride_kh
    v_base = V_ptr + z_idx * stride_vz + h_idx * stride_vh

    m_i = -float("inf")
    l_i = 0.0
    acc = tl.zeros((D_VAL,), dtype=tl.float32)

    n = 0
    while n < N:
        offs_n = n + tl.arange(0, BLOCK_N)
        mask_n = offs_n < N

        k_ptrs = k_base + offs_n[:, None] * stride_kn + offs_dq[None, :] * stride_kd
        k = tl.load(k_ptrs, mask=mask_n[:, None], other=0.0).to(tl.float32)

        scores = tl.dot(k, q) * sm_scale
        scores = tl.where(mask_n, scores, -float("inf"))

        max_block = tl.max(scores, axis=0)
        m_new = tl.maximum(m_i, max_block)
        exp_prev_scale = tl.exp(m_i - m_new)
        exp_scores = tl.exp(scores - m_new)
        l_new = l_i * exp_prev_scale + tl.sum(exp_scores, axis=0)

        v_ptrs = v_base + offs_n[:, None] * stride_vn + offs_dv[None, :] * stride_vd
        v = tl.load(v_ptrs, mask=mask_n[:, None], other=0.0).to(tl.float32)

        acc = acc * exp_prev_scale + tl.sum(v * exp_scores[:, None], axis=0)

        m_i = m_new
        l_i = l_new
        n += BLOCK_N

    out = acc / l_i
    tl.store(o_row_ptr + offs_dv, out.to(tl.float16))


def decoding_attn(Q: torch.Tensor, K: torch.Tensor, V: torch.Tensor) -> torch.Tensor:
    if not (Q.is_cuda and K.is_cuda and V.is_cuda):
        raise ValueError("Q, K, V must be CUDA tensors")
    if Q.dtype != torch.float16 or K.dtype != torch.float16 or V.dtype != torch.float16:
        raise ValueError("Q, K, V must be float16 tensors")

    if Q.dim() != 4 or K.dim() != 4 or V.dim() != 4:
        raise ValueError("Q, K, V must be 4D tensors")

    Z, H, M, D_HEAD = Q.shape
    Zk, Hk, N, D_HEAD_k = K.shape
    Zv, Hv, N_v, D_VAL = V.shape

    if Zk != Z or Zv != Z or Hk != H or Hv != H:
        raise ValueError("Batch and head dimensions of Q, K, V must match")
    if N != N_v:
        raise ValueError("Sequence length dimension of K and V must match")
    if D_HEAD_k != D_HEAD:
        raise ValueError("Head dimensions of Q and K must match")

    sm_scale = 1.0 / math.sqrt(D_HEAD)
    out = torch.empty((Z, H, M, D_VAL), device=Q.device, dtype=torch.float16)

    grid = (Z * H * M,)

    _decoding_attn_kernel[grid](
        Q,
        K,
        V,
        out,
        Q.stride(0),
        Q.stride(1),
        Q.stride(2),
        Q.stride(3),
        K.stride(0),
        K.stride(1),
        K.stride(2),
        K.stride(3),
        V.stride(0),
        V.stride(1),
        V.stride(2),
        V.stride(3),
        out.stride(0),
        out.stride(1),
        out.stride(2),
        out.stride(3),
        Z,
        H,
        M,
        N,
        sm_scale,
        D_HEAD=D_HEAD,
        D_VAL=D_VAL,
    )

    return out


class Solution:
    def solve(self, spec_path: str = None) -> dict:
        module = sys.modules[__name__]
        code = inspect.getsource(module)
        return {"code": code}