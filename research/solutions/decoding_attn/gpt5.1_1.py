import os
import sys
import inspect
import math
import torch
import triton
import triton.language as tl


@triton.autotune(
    configs=[
        triton.Config({'BLOCK_N': 64}, num_warps=2, num_stages=2),
        triton.Config({'BLOCK_N': 128}, num_warps=4, num_stages=2),
        triton.Config({'BLOCK_N': 256}, num_warps=4, num_stages=2),
        triton.Config({'BLOCK_N': 512}, num_warps=8, num_stages=2),
    ],
    key=['N'],
)
@triton.jit
def _decoding_attn_kernel(
    Q, K, V, Out,
    stride_q_m, stride_q_d,
    stride_k_b, stride_k_n, stride_k_d,
    stride_v_b, stride_v_n, stride_v_d,
    stride_o_m, stride_o_d,
    B, M, N,
    scale,
    BLOCK_N: tl.constexpr,
    D_HEAD: tl.constexpr,
    DV_HEAD: tl.constexpr,
):
    pid = tl.program_id(0)
    bm = pid
    head_idx = bm // M

    offs_d = tl.arange(0, D_HEAD)
    offs_v = tl.arange(0, DV_HEAD)

    q_ptrs = Q + bm * stride_q_m + offs_d * stride_q_d
    q = tl.load(q_ptrs).to(tl.float32)

    acc = tl.zeros((DV_HEAD,), dtype=tl.float32)
    m_prev = -float("inf")
    l_prev = 0.0

    offs_n = tl.arange(0, BLOCK_N)
    start_n = 0

    while start_n < N:
        n_idx = start_n + offs_n
        mask_n = n_idx < N

        k_ptrs = (
            K
            + head_idx * stride_k_b
            + n_idx[:, None] * stride_k_n
            + offs_d[None, :] * stride_k_d
        )
        v_ptrs = (
            V
            + head_idx * stride_v_b
            + n_idx[:, None] * stride_v_n
            + offs_v[None, :] * stride_v_d
        )

        k = tl.load(k_ptrs, mask=mask_n[:, None], other=0.0).to(tl.float32)
        v = tl.load(v_ptrs, mask=mask_n[:, None], other=0.0).to(tl.float32)

        qk = tl.sum(k * q[None, :], axis=1) * scale
        neg_inf = -float("inf")
        qk = tl.where(mask_n, qk, neg_inf)

        max_s = tl.max(qk, axis=0)
        m_curr = tl.maximum(m_prev, max_s)
        exp_m_prev = tl.exp(m_prev - m_curr)

        p = tl.exp(qk - m_curr)
        p = tl.where(mask_n, p, 0.0)

        l_curr = l_prev * exp_m_prev + tl.sum(p, axis=0)
        block_acc = tl.sum(v * p[:, None], axis=0)

        acc = acc * exp_m_prev + block_acc
        m_prev = m_curr
        l_prev = l_curr

        start_n += BLOCK_N

    out = acc / l_prev
    out = out.to(tl.float16)

    o_ptrs = Out + bm * stride_o_m + offs_v * stride_o_d
    tl.store(o_ptrs, out)


def decoding_attn(Q: torch.Tensor, K: torch.Tensor, V: torch.Tensor) -> torch.Tensor:
    if Q.device.type != "cuda" or not torch.cuda.is_available():
        # CPU / non-CUDA fallback
        Z, H, M, Dq = Q.shape
        Zk, Hk, N, Dk = K.shape
        Zv, Hv, Nv, Dv = V.shape
        assert Z == Zk == Zv
        assert H == Hk == Hv
        assert N == Nv
        assert Dq == Dk
        scale = 1.0 / math.sqrt(Dq)
        q = Q.float()
        k = K.float()
        v = V.float()
        scores = torch.matmul(q, k.transpose(-2, -1)) * scale
        weights = torch.softmax(scores, dim=-1, dtype=torch.float32)
        out = torch.matmul(weights, v)
        return out.to(Q.dtype)

    assert Q.dtype == torch.float16 and K.dtype == torch.float16 and V.dtype == torch.float16

    Z, H, M, Dq = Q.shape
    Zk, Hk, N, Dk = K.shape
    Zv, Hv, Nv, Dv = V.shape

    assert Z == Zk == Zv
    assert H == Hk == Hv
    assert N == Nv
    assert Dq == Dk

    B = Z * H

    q = Q.contiguous().view(B * M, Dq)
    k = K.contiguous().view(B, N, Dq)
    v = V.contiguous().view(B, N, Dv)

    out = torch.empty((B * M, Dv), device=Q.device, dtype=Q.dtype)

    scale = 1.0 / math.sqrt(Dq)

    grid = (q.shape[0],)

    _decoding_attn_kernel[grid](
        q, k, v, out,
        q.stride(0), q.stride(1),
        k.stride(0), k.stride(1), k.stride(2),
        v.stride(0), v.stride(1), v.stride(2),
        out.stride(0), out.stride(1),
        B, M, N,
        scale,
        D_HEAD=Dq,
        DV_HEAD=Dv,
    )

    out = out.view(Z, H, M, Dv)
    return out


class Solution:
    def solve(self, spec_path: str = None) -> dict:
        try:
            path = __file__
            with open(path, "r") as f:
                code = f.read()
            return {"code": code}
        except Exception:
            code = inspect.getsource(sys.modules[__name__])
            return {"code": code}