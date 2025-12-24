import os
import math
import torch
import triton
import triton.language as tl


@triton.jit
def flash_attn_fwd_kernel(
    Q, K, V, sm_scale, Out,
    stride_qz, stride_qh, stride_qm, stride_qd,
    stride_kz, stride_kh, stride_kn, stride_kd,
    stride_vz, stride_vh, stride_vn, stride_vd,
    stride_oz, stride_oh, stride_om, stride_od,
    Z, H,
    N_CTX: tl.constexpr,
    CAUSAL: tl.constexpr,
    BLOCK_M: tl.constexpr,
    BLOCK_N: tl.constexpr,
    D_HEAD: tl.constexpr,
    D_VALUE: tl.constexpr,
):
    pid_m = tl.program_id(0)
    pid_zh = tl.program_id(1)

    z = pid_zh // H
    h = pid_zh % H

    offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
    offs_n_init = tl.arange(0, BLOCK_N)
    offs_d = tl.arange(0, D_HEAD)
    offs_dv = tl.arange(0, D_VALUE)

    q_ptrs = (
        Q
        + z * stride_qz
        + h * stride_qh
        + offs_m[:, None] * stride_qm
        + offs_d[None, :] * stride_qd
    )
    q = tl.load(q_ptrs, mask=offs_m[:, None] < N_CTX, other=0.0).to(tl.float32)

    m_i = tl.full((BLOCK_M,), -float("inf"), tl.float32)
    l_i = tl.zeros((BLOCK_M,), tl.float32)
    acc = tl.zeros((BLOCK_M, D_VALUE), tl.float32)

    for start_n in range(0, N_CTX, BLOCK_N):
        offs_n = start_n + offs_n_init

        k_ptrs = (
            K
            + z * stride_kz
            + h * stride_kh
            + offs_n[:, None] * stride_kn
            + offs_d[None, :] * stride_kd
        )
        v_ptrs = (
            V
            + z * stride_vz
            + h * stride_vh
            + offs_n[:, None] * stride_vn
            + offs_dv[None, :] * stride_vd
        )

        k = tl.load(k_ptrs, mask=offs_n[:, None] < N_CTX, other=0.0).to(tl.float32)
        v = tl.load(v_ptrs, mask=offs_n[:, None] < N_CTX, other=0.0).to(tl.float32)

        qk = tl.dot(q, tl.trans(k)) * sm_scale

        q_idx = offs_m[:, None]
        k_idx = offs_n[None, :]
        mask = (q_idx < N_CTX) & (k_idx < N_CTX)
        if CAUSAL:
            mask = mask & (k_idx <= q_idx)
        qk = tl.where(mask, qk, -float("inf"))

        max_curr = tl.max(qk, axis=1)
        m_new = tl.maximum(m_i, max_curr)
        p = tl.exp(qk - m_new[:, None])
        alpha = tl.exp(m_i - m_new)
        l_i = l_i * alpha + tl.sum(p, axis=1)
        acc = acc * alpha[:, None] + tl.dot(p, v)
        m_i = m_new

    out = acc / l_i[:, None]

    o_ptrs = (
        Out
        + z * stride_oz
        + h * stride_oh
        + offs_m[:, None] * stride_om
        + offs_dv[None, :] * stride_od
    )
    tl.store(o_ptrs, out.to(tl.float16), mask=offs_m[:, None] < N_CTX)


def _flash_attn_ref(Q: torch.Tensor, K: torch.Tensor, V: torch.Tensor, causal: bool = True) -> torch.Tensor:
    Z, H, M, Dq = Q.shape
    _, _, N, _ = K.shape
    _, _, N2, Dv = V.shape
    assert N == N2
    Qf = Q.float()
    Kf = K.float()
    Vf = V.float()
    scale = 1.0 / math.sqrt(Dq)
    scores = torch.matmul(Qf, Kf.transpose(-2, -1)) * scale  # (Z,H,M,N)
    if causal:
        mask = torch.triu(
            torch.ones(M, N, device=scores.device, dtype=torch.bool),
            diagonal=1,
        )
        scores = scores.masked_fill(mask, float("-inf"))
    probs = torch.softmax(scores, dim=-1)
    out = torch.matmul(probs, Vf)
    return out.to(Q.dtype)


def flash_attn(Q: torch.Tensor, K: torch.Tensor, V: torch.Tensor, causal: bool = True) -> torch.Tensor:
    if (
        (not Q.is_cuda)
        or (not K.is_cuda)
        or (not V.is_cuda)
        or Q.dtype != torch.float16
        or K.dtype != torch.float16
        or V.dtype != torch.float16
    ):
        return _flash_attn_ref(Q, K, V, causal=causal)

    Z, H, M, Dq = Q.shape
    Zk, Hk, N, Dk = K.shape
    Zv, Hv, Nv, Dv = V.shape

    assert Z == Zk == Zv
    assert H == Hk == Hv
    assert M == N == Nv
    assert Dq == Dk

    sm_scale = 1.0 / math.sqrt(Dq)

    Out = torch.empty((Z, H, M, Dv), device=Q.device, dtype=Q.dtype)

    BLOCK_M = 64
    BLOCK_N = 64
    num_warps = 4
    num_stages = 2

    grid = (triton.cdiv(M, BLOCK_M), Z * H)

    flash_attn_fwd_kernel[grid](
        Q,
        K,
        V,
        sm_scale,
        Out,
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
        Out.stride(0),
        Out.stride(1),
        Out.stride(2),
        Out.stride(3),
        Z,
        H,
        N_CTX=M,
        CAUSAL=causal,
        BLOCK_M=BLOCK_M,
        BLOCK_N=BLOCK_N,
        D_HEAD=Dq,
        D_VALUE=Dv,
        num_warps=num_warps,
        num_stages=num_stages,
    )

    return Out


class Solution:
    def solve(self, spec_path: str = None) -> dict:
        return {"program_path": os.path.abspath(__file__)}
