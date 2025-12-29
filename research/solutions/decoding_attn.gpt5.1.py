import math
import sys
import inspect
import torch
import triton
import triton.language as tl


@triton.autotune(
    configs=[
        triton.Config({'BLOCK_N': 64}, num_warps=4, num_stages=2),
        triton.Config({'BLOCK_N': 128}, num_warps=4, num_stages=2),
        triton.Config({'BLOCK_N': 256}, num_warps=8, num_stages=2),
    ],
    key=['N_CTX'],
)
@triton.jit
def decoding_attn_kernel(
    Q_ptr, K_ptr, V_ptr, Out_ptr,
    stride_qz, stride_qh, stride_qm, stride_qd,
    stride_kz, stride_kh, stride_kn, stride_kd,
    stride_vz, stride_vh, stride_vn, stride_vd,
    stride_oz, stride_oh, stride_om, stride_od,
    Z, H, M,
    sm_scale,
    N_CTX: tl.constexpr, D_HEAD: tl.constexpr, D_VAL: tl.constexpr,
    BLOCK_N: tl.constexpr,
):
    pid = tl.program_id(0)

    m_idx = pid % M
    tmp = pid // M
    h_idx = tmp % H
    z_idx = tmp // H

    offs_dq = tl.arange(0, D_HEAD)
    offs_dv = tl.arange(0, D_VAL)

    q_ptrs = Q_ptr + (
        z_idx * stride_qz +
        h_idx * stride_qh +
        m_idx * stride_qm +
        offs_dq * stride_qd
    )
    q = tl.load(q_ptrs).to(tl.float32)

    k_base = K_ptr + z_idx * stride_kz + h_idx * stride_kh
    v_base = V_ptr + z_idx * stride_vz + h_idx * stride_vh
    o_ptrs = Out_ptr + (
        z_idx * stride_oz +
        h_idx * stride_oh +
        m_idx * stride_om +
        offs_dv * stride_od
    )

    m_i = -float('inf')
    l_i = 0.0
    acc = tl.zeros([D_VAL], dtype=tl.float32)

    for start_n in range(0, N_CTX, BLOCK_N):
        offs_n = start_n + tl.arange(0, BLOCK_N)
        mask_n = offs_n < N_CTX

        k_ptrs = k_base + (
            offs_n[:, None] * stride_kn +
            offs_dq[None, :] * stride_kd
        )
        v_ptrs = v_base + (
            offs_n[:, None] * stride_vn +
            offs_dv[None, :] * stride_vd
        )

        k = tl.load(k_ptrs, mask=mask_n[:, None], other=0.0).to(tl.float32)
        v = tl.load(v_ptrs, mask=mask_n[:, None], other=0.0).to(tl.float32)

        scores = tl.sum(k * q[None, :], axis=1)
        scores = scores * sm_scale
        scores = tl.where(mask_n, scores, -float('inf'))

        block_max = tl.max(scores, axis=0)
        m_new = tl.maximum(m_i, block_max)
        alpha = tl.exp(m_i - m_new)
        exp_scores = tl.exp(scores - m_new)

        l_new = alpha * l_i + tl.sum(exp_scores, axis=0)
        acc = acc * alpha + tl.sum(exp_scores[:, None] * v, axis=0)

        m_i = m_new
        l_i = l_new

    out = acc / l_i
    tl.store(o_ptrs, out.to(tl.float16))


def _baseline_decoding_attn(Q: torch.Tensor, K: torch.Tensor, V: torch.Tensor) -> torch.Tensor:
    Z, H, M, Dq = Q.shape
    N = K.shape[2]
    Dv = V.shape[3]
    scale = 1.0 / math.sqrt(Dq)

    q = Q.to(torch.float32) * scale
    k = K.to(torch.float32)
    v = V.to(torch.float32)

    attn_scores = torch.matmul(q, k.transpose(-2, -1))
    attn_probs = torch.softmax(attn_scores, dim=-1)
    out = torch.matmul(attn_probs, v)
    return out.to(torch.float16)


def decoding_attn(Q: torch.Tensor, K: torch.Tensor, V: torch.Tensor) -> torch.Tensor:
    Z, H, M, Dq = Q.shape
    Zk, Hk, N, Dqk = K.shape
    Zv, Hv, Nv, Dv = V.shape

    assert Z == Zk == Zv
    assert H == Hk == Hv
    assert N == Nv
    assert Dq == Dqk

    if (not Q.is_cuda) or (not K.is_cuda) or (not V.is_cuda):
        return _baseline_decoding_attn(Q, K, V)

    if Q.dtype is not torch.float16 or K.dtype is not torch.float16 or V.dtype is not torch.float16:
        return _baseline_decoding_attn(Q, K, V)

    O = torch.empty((Z, H, M, Dv), device=Q.device, dtype=torch.float16)

    stride_qz, stride_qh, stride_qm, stride_qd = Q.stride()
    stride_kz, stride_kh, stride_kn, stride_kd = K.stride()
    stride_vz, stride_vh, stride_vn, stride_vd = V.stride()
    stride_oz, stride_oh, stride_om, stride_od = O.stride()

    Z_int = int(Z)
    H_int = int(H)
    M_int = int(M)
    N_int = int(N)
    Dq_int = int(Dq)
    Dv_int = int(Dv)

    sm_scale = 1.0 / math.sqrt(Dq_int)

    grid = (Z_int * H_int * M_int,)

    decoding_attn_kernel[grid](
        Q, K, V, O,
        stride_qz, stride_qh, stride_qm, stride_qd,
        stride_kz, stride_kh, stride_kn, stride_kd,
        stride_vz, stride_vh, stride_vn, stride_vd,
        stride_oz, stride_oh, stride_om, stride_od,
        Z_int, H_int, M_int,
        sm_scale,
        N_CTX=N_int, D_HEAD=Dq_int, D_VAL=Dv_int,
    )

    return O


class Solution:
    def solve(self, spec_path: str = None) -> dict:
        module = sys.modules[__name__]
        if hasattr(module, '__file__'):
            with open(module.__file__, 'r') as f:
                code = f.read()
        else:
            code = inspect.getsource(module)
        return {"code": code}