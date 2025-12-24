import os
import math
import torch

try:
    import triton
    import triton.language as tl
    _TRITON_AVAILABLE = True
except Exception:
    triton = None
    tl = None
    _TRITON_AVAILABLE = False


_LOG2E = 1.4426950408889634


if _TRITON_AVAILABLE:
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
        N_CTX: tl.constexpr,
        SM_SCALE_LOG2: tl.constexpr,
        DQ: tl.constexpr,
        DV: tl.constexpr,
        BLOCK_M: tl.constexpr,
        BLOCK_N: tl.constexpr,
    ):
        pid_zh = tl.program_id(0)
        pid_m = tl.program_id(1)

        z = pid_zh // H
        h = pid_zh - z * H

        offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
        mask_m = offs_m < M

        offs_dq = tl.arange(0, DQ)
        offs_dv = tl.arange(0, DV)

        q_base = Q_ptr + z * stride_qz + h * stride_qh
        k_base = K_ptr + z * stride_kz + h * stride_kh
        v_base = V_ptr + z * stride_vz + h * stride_vh
        o_base = O_ptr + z * stride_oz + h * stride_oh

        q_ptrs = q_base + offs_m[:, None] * stride_qm + offs_dq[None, :] * stride_qd
        q = tl.load(q_ptrs, mask=mask_m[:, None], other=0.0).to(tl.float16)

        m_i = tl.full((BLOCK_M,), -float("inf"), tl.float32)
        l_i = tl.zeros((BLOCK_M,), tl.float32)
        acc = tl.zeros((BLOCK_M, DV), tl.float32)

        # Online softmax over N
        for start_n in tl.static_range(0, N_CTX, BLOCK_N):
            offs_n = start_n + tl.arange(0, BLOCK_N)
            mask_n = offs_n < N_CTX

            k_ptrs = k_base + offs_dq[:, None] * stride_kd + offs_n[None, :] * stride_kn
            k = tl.load(k_ptrs, mask=mask_n[None, :], other=0.0).to(tl.float16)

            qk = tl.dot(q, k).to(tl.float32) * SM_SCALE_LOG2
            qk = tl.where(mask_n[None, :], qk, -float("inf"))

            m_ij = tl.maximum(m_i, tl.max(qk, axis=1))
            alpha = tl.exp2(m_i - m_ij)
            l_i = l_i * alpha

            p = tl.exp2(qk - m_ij[:, None])
            p = tl.where(mask_n[None, :], p, 0.0)
            l_i = l_i + tl.sum(p, axis=1)

            acc = acc * alpha[:, None]

            v_ptrs = v_base + offs_n[:, None] * stride_vn + offs_dv[None, :] * stride_vd
            v = tl.load(v_ptrs, mask=mask_n[:, None], other=0.0).to(tl.float16)

            acc = acc + tl.dot(p.to(tl.float16), v).to(tl.float32)

            m_i = m_ij

        out = acc / l_i[:, None]
        o_ptrs = o_base + offs_m[:, None] * stride_om + offs_dv[None, :] * stride_od
        tl.store(o_ptrs, out.to(tl.float16), mask=mask_m[:, None])


def decoding_attn(Q: torch.Tensor, K: torch.Tensor, V: torch.Tensor) -> torch.Tensor:
    if not _TRITON_AVAILABLE or (not Q.is_cuda) or (not K.is_cuda) or (not V.is_cuda):
        d = Q.shape[-1]
        scores = torch.matmul(Q.to(torch.float32), K.transpose(-2, -1).to(torch.float32)) * (1.0 / math.sqrt(d))
        p = torch.softmax(scores, dim=-1).to(torch.float32)
        out = torch.matmul(p, V.to(torch.float32)).to(torch.float16)
        return out

    assert Q.dtype == torch.float16 and K.dtype == torch.float16 and V.dtype == torch.float16
    assert Q.ndim == 4 and K.ndim == 4 and V.ndim == 4
    Z, H, M, DQ = Q.shape
    Zk, Hk, N, DQk = K.shape
    Zv, Hv, Nv, DV = V.shape
    assert Zk == Z and Zv == Z and Hk == H and Hv == H and DQk == DQ and Nv == N

    O = torch.empty((Z, H, M, DV), device=Q.device, dtype=torch.float16)

    # Choose a fixed high-perf config for decoding (M is typically 1)
    if N >= 4096:
        BLOCK_N = 512
        num_warps = 8
        num_stages = 4
    else:
        BLOCK_N = 256
        num_warps = 4
        num_stages = 4

    BLOCK_M = 1

    scale_log2 = (1.0 / math.sqrt(DQ)) * _LOG2E

    grid = (Z * H, triton.cdiv(M, BLOCK_M))

    _decoding_attn_kernel[grid](
        Q, K, V, O,
        Q.stride(0), Q.stride(1), Q.stride(2), Q.stride(3),
        K.stride(0), K.stride(1), K.stride(2), K.stride(3),
        V.stride(0), V.stride(1), V.stride(2), V.stride(3),
        O.stride(0), O.stride(1), O.stride(2), O.stride(3),
        Z=Z, H=H, M=M, N_CTX=N,
        SM_SCALE_LOG2=scale_log2,
        DQ=DQ, DV=DV,
        BLOCK_M=BLOCK_M, BLOCK_N=BLOCK_N,
        num_warps=num_warps,
        num_stages=num_stages,
    )
    return O


class Solution:
    def solve(self, spec_path: str = None) -> dict:
        return {"program_path": os.path.abspath(__file__)}
