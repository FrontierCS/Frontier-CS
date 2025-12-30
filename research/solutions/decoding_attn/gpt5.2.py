import os
import math
import inspect
import sys
import torch
import triton
import triton.language as tl

_LOG2E = 1.4426950408889634


@triton.autotune(
    configs=[
        triton.Config({"BLOCK_N": 64}, num_warps=4, num_stages=3),
        triton.Config({"BLOCK_N": 128}, num_warps=4, num_stages=4),
        triton.Config({"BLOCK_N": 256}, num_warps=8, num_stages=4),
    ],
    key=["N"],
    warmup=2,
    rep=3,
)
@triton.jit
def _decoding_attn_kernel(
    Q_ptr,
    K_ptr,
    V_ptr,
    O_ptr,
    stride_qz: tl.constexpr,
    stride_qh: tl.constexpr,
    stride_qm: tl.constexpr,
    stride_qd: tl.constexpr,
    stride_kz: tl.constexpr,
    stride_kh: tl.constexpr,
    stride_kn: tl.constexpr,
    stride_kd: tl.constexpr,
    stride_vz: tl.constexpr,
    stride_vh: tl.constexpr,
    stride_vn: tl.constexpr,
    stride_vd: tl.constexpr,
    stride_oz: tl.constexpr,
    stride_oh: tl.constexpr,
    stride_om: tl.constexpr,
    stride_od: tl.constexpr,
    Z: tl.constexpr,
    H: tl.constexpr,
    M: tl.constexpr,
    N: tl.constexpr,
    DQ: tl.constexpr,
    DV: tl.constexpr,
    SCALE: tl.constexpr,
    BLOCK_N: tl.constexpr,
):
    pid = tl.program_id(0)

    m = pid % M
    pid = pid // M
    h = pid % H
    z = pid // H

    offs_dq = tl.arange(0, DQ)
    q_ptrs = Q_ptr + z * stride_qz + h * stride_qh + m * stride_qm + offs_dq * stride_qd
    q = tl.load(q_ptrs, mask=offs_dq < DQ, other=0.0).to(tl.float16)
    q = q[None, :]

    offs_dv = tl.arange(0, DV)
    acc = tl.zeros([DV], dtype=tl.float32)
    m_i = tl.full([1], -float("inf"), tl.float32)
    l_i = tl.zeros([1], dtype=tl.float32)

    base_k = K_ptr + z * stride_kz + h * stride_kh
    base_v = V_ptr + z * stride_vz + h * stride_vh

    for start_n in tl.static_range(0, N, BLOCK_N):
        offs_n = start_n + tl.arange(0, BLOCK_N)
        mask_n = offs_n < N

        k_ptrs = base_k + offs_n[:, None] * stride_kn + offs_dq[None, :] * stride_kd
        k = tl.load(k_ptrs, mask=mask_n[:, None] & (offs_dq[None, :] < DQ), other=0.0).to(tl.float16)
        scores = tl.dot(q, tl.trans(k), out_dtype=tl.float32)[0, :]
        scores = scores * SCALE
        scores = tl.where(mask_n, scores, -float("inf"))

        m_ij = tl.max(scores, axis=0)
        m_new = tl.maximum(m_i, m_ij)

        p = tl.math.exp2((scores - m_new) * _LOG2E)
        p = tl.where(mask_n, p, 0.0)

        alpha = tl.math.exp2((m_i - m_new) * _LOG2E)
        l_new = l_i * alpha + tl.sum(p, axis=0)

        v_ptrs = base_v + offs_n[:, None] * stride_vn + offs_dv[None, :] * stride_vd
        v = tl.load(v_ptrs, mask=mask_n[:, None] & (offs_dv[None, :] < DV), other=0.0).to(tl.float16)

        wsum = tl.dot(p.to(tl.float16)[None, :], v, out_dtype=tl.float32)[0, :]
        acc = acc * alpha + wsum

        m_i = m_new
        l_i = l_new

    out = acc / l_i
    o_ptrs = O_ptr + z * stride_oz + h * stride_oh + m * stride_om + offs_dv * stride_od
    tl.store(o_ptrs, out.to(tl.float16), mask=offs_dv < DV)


def decoding_attn(Q: torch.Tensor, K: torch.Tensor, V: torch.Tensor) -> torch.Tensor:
    if not (isinstance(Q, torch.Tensor) and isinstance(K, torch.Tensor) and isinstance(V, torch.Tensor)):
        raise TypeError("Q, K, V must be torch.Tensor")
    if Q.device != K.device or Q.device != V.device:
        raise ValueError("Q, K, V must be on the same device")
    if Q.dtype != torch.float16 or K.dtype != torch.float16 or V.dtype != torch.float16:
        # Fallback
        Z, H, M, DQ = Q.shape
        _, _, N, _ = K.shape
        scale = 1.0 / math.sqrt(DQ)
        scores = torch.matmul(Q, K.transpose(-2, -1)) * scale
        p = torch.softmax(scores.float(), dim=-1).to(torch.float16)
        return torch.matmul(p, V)

    if Q.ndim != 4 or K.ndim != 4 or V.ndim != 4:
        raise ValueError("Q, K, V must be 4D tensors (Z, H, M/N, D)")

    Z, H, M, DQ = Q.shape
    Zk, Hk, N, DQk = K.shape
    Zv, Hv, Nv, DV = V.shape
    if Zk != Z or Zv != Z or Hk != H or Hv != H or Nv != N or DQk != DQ:
        raise ValueError("Mismatched shapes among Q, K, V")

    if not Q.is_cuda:
        scale = 1.0 / math.sqrt(DQ)
        scores = torch.matmul(Q, K.transpose(-2, -1)) * scale
        p = torch.softmax(scores.float(), dim=-1).to(torch.float16)
        return torch.matmul(p, V)

    out = torch.empty((Z, H, M, DV), device=Q.device, dtype=torch.float16)

    SCALE = 1.0 / math.sqrt(DQ)
    grid = (Z * H * M,)

    _decoding_attn_kernel[grid](
        Q,
        K,
        V,
        out,
        stride_qz=Q.stride(0),
        stride_qh=Q.stride(1),
        stride_qm=Q.stride(2),
        stride_qd=Q.stride(3),
        stride_kz=K.stride(0),
        stride_kh=K.stride(1),
        stride_kn=K.stride(2),
        stride_kd=K.stride(3),
        stride_vz=V.stride(0),
        stride_vh=V.stride(1),
        stride_vn=V.stride(2),
        stride_vd=V.stride(3),
        stride_oz=out.stride(0),
        stride_oh=out.stride(1),
        stride_om=out.stride(2),
        stride_od=out.stride(3),
        Z=Z,
        H=H,
        M=M,
        N=N,
        DQ=DQ,
        DV=DV,
        SCALE=SCALE,
    )
    return out


class Solution:
    def solve(self, spec_path: str = None) -> dict:
        path = globals().get("__file__", None)
        if path and os.path.exists(path):
            return {"program_path": path}
        try:
            src = inspect.getsource(sys.modules[__name__])
            return {"code": src}
        except Exception:
            return {"code": ""}