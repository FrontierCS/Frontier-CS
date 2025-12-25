import math
import os
import torch
import triton
import triton.language as tl


@triton.autotune(
    configs=[
        triton.Config({"BLOCK_N": 64}, num_warps=4, num_stages=2),
        triton.Config({"BLOCK_N": 128}, num_warps=4, num_stages=2),
        triton.Config({"BLOCK_N": 256}, num_warps=4, num_stages=2),
        triton.Config({"BLOCK_N": 128}, num_warps=8, num_stages=2),
    ],
    key=["N_CTX"],
)
@triton.jit
def _decoding_attn_kernel(
    Q_ptr,
    K_ptr,
    V_ptr,
    Out_ptr,
    Z,
    H,
    M,
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
    scale,
    N_CTX: tl.constexpr,
    HEAD_DIM: tl.constexpr,
    VALUE_DIM: tl.constexpr,
    BLOCK_N: tl.constexpr,
):
    pid = tl.program_id(axis=0)

    m_idx = pid % M
    tmp = pid // M
    h_idx = tmp % H
    z_idx = tmp // H

    offs_d = tl.arange(0, HEAD_DIM)
    offs_v = tl.arange(0, VALUE_DIM)

    q_ptr = Q_ptr + z_idx * stride_qz + h_idx * stride_qh + m_idx * stride_qm
    q = tl.load(q_ptr + offs_d * stride_qd, mask=offs_d < HEAD_DIM, other=0.0)
    q = q.to(tl.float32)

    k_base = K_ptr + z_idx * stride_kz + h_idx * stride_kh
    v_base = V_ptr + z_idx * stride_vz + h_idx * stride_vh

    NEG_INF = -1e9
    m_i = tl.full([1], NEG_INF, dtype=tl.float32)
    l_i = tl.zeros([1], dtype=tl.float32)
    acc = tl.zeros([VALUE_DIM], dtype=tl.float32)

    for start_n in range(0, N_CTX, BLOCK_N):
        offs_n = start_n + tl.arange(0, BLOCK_N)
        mask_n = offs_n < N_CTX

        k_ptrs = k_base + offs_n[:, None] * stride_kn + offs_d[None, :] * stride_kd
        k = tl.load(
            k_ptrs,
            mask=mask_n[:, None] & (offs_d[None, :] < HEAD_DIM),
            other=0.0,
        )
        k = k.to(tl.float32)

        q_broadcast = q[None, :]
        scores = tl.sum(k * q_broadcast, axis=1)
        scores = scores * scale
        scores = tl.where(mask_n, scores, NEG_INF)

        m_curr = tl.max(scores, axis=0)
        m_i_new = tl.maximum(m_i, m_curr)
        exp_m_i_diff = tl.exp(m_i - m_i_new)

        scores_shifted = scores - m_i_new
        p = tl.exp(scores_shifted) * mask_n

        l_i_new = l_i * exp_m_i_diff + tl.sum(p, axis=0)

        v_ptrs = v_base + offs_n[:, None] * stride_vn + offs_v[None, :] * stride_vd
        v = tl.load(
            v_ptrs,
            mask=mask_n[:, None] & (offs_v[None, :] < VALUE_DIM),
            other=0.0,
        )
        v = v.to(tl.float32)

        acc = acc * exp_m_i_diff + tl.sum(p[:, None] * v, axis=0)

        m_i = m_i_new
        l_i = l_i_new

    out = acc / l_i
    out = out.to(tl.float16)

    out_ptr = Out_ptr + z_idx * stride_oz + h_idx * stride_oh + m_idx * stride_om
    tl.store(out_ptr + offs_v * stride_od, out, mask=offs_v < VALUE_DIM)


def _decoding_attn_torch(Q: torch.Tensor, K: torch.Tensor, V: torch.Tensor) -> torch.Tensor:
    Z, H, M, Dq = Q.shape
    _, _, N, _ = K.shape
    _, _, _, Dv = V.shape
    scale = 1.0 / math.sqrt(Dq)
    attn_scores = torch.matmul(Q.to(torch.float32), K.transpose(-1, -2).to(torch.float32)) * scale
    attn_probs = torch.softmax(attn_scores, dim=-1)
    out = torch.matmul(attn_probs, V.to(torch.float32))
    return out.to(torch.float16)


def decoding_attn(Q: torch.Tensor, K: torch.Tensor, V: torch.Tensor) -> torch.Tensor:
    if (
        (not Q.is_cuda)
        or (not K.is_cuda)
        or (not V.is_cuda)
        or Q.dtype not in (torch.float16, torch.bfloat16)
        or K.dtype not in (torch.float16, torch.bfloat16)
        or V.dtype not in (torch.float16, torch.bfloat16)
    ):
        return _decoding_attn_torch(Q, K, V)

    assert Q.ndim == 4 and K.ndim == 4 and V.ndim == 4, "Q, K, V must be 4D tensors"
    Z, H, M, D_HEAD = Q.shape
    Zk, Hk, N_CTX, Dk = K.shape
    Zv, Hv, Nv, D_VALUE = V.shape
    assert Z == Zk == Zv
    assert H == Hk == Hv
    assert N_CTX == Nv
    assert D_HEAD == Dk

    scale = float(1.0 / math.sqrt(D_HEAD))

    Out = torch.empty((Z, H, M, D_VALUE), device=Q.device, dtype=torch.float16)

    stride_qz, stride_qh, stride_qm, stride_qd = Q.stride()
    stride_kz, stride_kh, stride_kn, stride_kd = K.stride()
    stride_vz, stride_vh, stride_vn, stride_vd = V.stride()
    stride_oz, stride_oh, stride_om, stride_od = Out.stride()

    grid = (Z * H * M,)

    _decoding_attn_kernel[grid](
        Q,
        K,
        V,
        Out,
        Z,
        H,
        M,
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
        scale,
        N_CTX=N_CTX,
        HEAD_DIM=D_HEAD,
        VALUE_DIM=D_VALUE,
    )

    return Out


class Solution:
    def solve(self, spec_path: str = None) -> dict:
        return {"program_path": os.path.abspath(__file__)}
