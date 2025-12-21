import os
import math
import torch
import triton
import triton.language as tl


@triton.autotune(
    configs=[
        triton.Config({"BLOCK_N": 64}, num_warps=4, num_stages=2),
        triton.Config({"BLOCK_N": 128}, num_warps=4, num_stages=2),
        triton.Config({"BLOCK_N": 256}, num_warps=8, num_stages=2),
        triton.Config({"BLOCK_N": 512}, num_warps=8, num_stages=2),
    ],
    key=["N_CTX", "D_HEAD", "DV_HEAD"],
)
@triton.jit
def decoding_attn_kernel(
    Q_ptr, K_ptr, V_ptr, O_ptr,
    Z, H, M, N_CTX,
    stride_qz, stride_qh, stride_qm, stride_qd,
    stride_kz, stride_kh, stride_kn, stride_kd,
    stride_vz, stride_vh, stride_vn, stride_vd,
    stride_oz, stride_oh, stride_om, stride_od,
    sm_scale,
    D_HEAD: tl.constexpr,
    DV_HEAD: tl.constexpr,
    BLOCK_N: tl.constexpr,
):
    pid = tl.program_id(axis=0)

    HM = H * M
    z = pid // HM
    rem = pid % HM
    h = rem // M
    m_idx = rem % M

    # Offsets for D dimensions
    offs_dq = tl.arange(0, D_HEAD)
    offs_dv = tl.arange(0, DV_HEAD)

    # Base pointers
    q_base = Q_ptr + z * stride_qz + h * stride_qh + m_idx * stride_qm
    k_base = K_ptr + z * stride_kz + h * stride_kh
    v_base = V_ptr + z * stride_vz + h * stride_vh
    o_base = O_ptr + z * stride_oz + h * stride_oh + m_idx * stride_om

    # Load Q once
    q = tl.load(q_base + offs_dq * stride_qd, mask=offs_dq < D_HEAD, other=0.0).to(tl.float32)

    # Initialize online softmax stats
    m_i = tl.full([1], -float("inf"), dtype=tl.float32)
    l_i = tl.zeros([1], dtype=tl.float32)
    acc = tl.zeros([DV_HEAD], dtype=tl.float32)

    # Iterate over K/V blocks
    for start_n in range(0, N_CTX, BLOCK_N):
        offs_n = start_n + tl.arange(0, BLOCK_N)
        n_mask = offs_n < N_CTX

        k_ptrs = k_base + offs_n[:, None] * stride_kn + offs_dq[None, :] * stride_kd
        v_ptrs = v_base + offs_n[:, None] * stride_vn + offs_dv[None, :] * stride_vd

        k = tl.load(k_ptrs, mask=n_mask[:, None], other=0.0).to(tl.float32)

        qk = tl.sum(k * q[None, :], axis=1)
        qk = qk * sm_scale
        qk = tl.where(n_mask, qk, -float("inf"))

        m_curr = tl.max(qk, axis=0)
        m_new = tl.maximum(m_i, m_curr)

        p = tl.exp(qk - m_new)
        alpha = tl.exp(m_i - m_new)

        l_new = l_i * alpha + tl.sum(p, axis=0)

        v = tl.load(v_ptrs, mask=n_mask[:, None], other=0.0).to(tl.float32)
        pv = tl.sum(p[:, None] * v, axis=0)

        acc = acc * alpha + pv

        m_i = m_new
        l_i = l_new

    out = acc / l_i
    tl.store(o_base + offs_dv * stride_od, out.to(tl.float16), mask=offs_dv < DV_HEAD)


def decoding_attn(Q: torch.Tensor, K: torch.Tensor, V: torch.Tensor) -> torch.Tensor:
    assert Q.is_cuda and K.is_cuda and V.is_cuda, "Tensors must be on CUDA device"
    assert Q.dtype in (torch.float16, torch.bfloat16) and K.dtype == Q.dtype and V.dtype == Q.dtype, "Q, K, V must have same dtype (fp16/bf16)"
    assert Q.dim() == 4 and K.dim() == 4 and V.dim() == 4, "Q, K, V must be 4D"
    Zq, Hq, M, Dq = Q.shape
    Zk, Hk, N, Dk = K.shape
    Zv, Hv, Nv, Dv = V.shape
    assert Zq == Zk == Zv, "Batch (Z) mismatch"
    assert Hq == Hk == Hv, "Head (H) mismatch"
    assert Dq == Dk, "Q/K feature dim mismatch"
    assert N == Nv, "K/V sequence length mismatch"
    Z = Zq
    H = Hq

    O = torch.empty((Z, H, M, Dv), device=Q.device, dtype=Q.dtype)

    # Compute scales and strides
    sm_scale = 1.0 / math.sqrt(Dq)

    grid = (Z * H * M,)

    decoding_attn_kernel[grid](
        Q, K, V, O,
        Z, H, M, N,
        Q.stride(0), Q.stride(1), Q.stride(2), Q.stride(3),
        K.stride(0), K.stride(1), K.stride(2), K.stride(3),
        V.stride(0), V.stride(1), V.stride(2), V.stride(3),
        O.stride(0), O.stride(1), O.stride(2), O.stride(3),
        sm_scale,
        D_HEAD=Dq, DV_HEAD=Dv, N_CTX=N,
    )
    return O


class Solution:
    def solve(self, spec_path: str = None) -> dict:
        return {"program_path": os.path.abspath(__file__)}
