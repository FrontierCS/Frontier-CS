import math
import inspect
import torch
import triton
import triton.language as tl


@triton.jit
def flash_attn_fwd(
    Q, K, V, Out,
    stride_qz, stride_qh, stride_qm, stride_qk,
    stride_kz, stride_kh, stride_kn, stride_kk,
    stride_vz, stride_vh, stride_vn, stride_vk,
    stride_oz, stride_oh, stride_om, stride_ok,
    Z, H, N_CTX, D_HEAD_QK, D_HEAD_V,
    sm_scale,
    causal: tl.constexpr,
    BLOCK_M: tl.constexpr,
    BLOCK_N: tl.constexpr,
    BLOCK_DMODEL_QK: tl.constexpr,
    BLOCK_DMODEL_V: tl.constexpr,
):
    pid_m = tl.program_id(0)
    pid_z_h = tl.program_id(1)

    z = pid_z_h // H
    h = pid_z_h % H

    offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
    offs_m = offs_m.to(tl.int32)

    offs_dq = tl.arange(0, BLOCK_DMODEL_QK)
    offs_dv = tl.arange(0, BLOCK_DMODEL_V)

    mask_m = offs_m < N_CTX
    mask_dq = offs_dq < D_HEAD_QK
    mask_dv = offs_dv < D_HEAD_V

    q_ptrs = Q + (
        z * stride_qz
        + h * stride_qh
        + offs_m[:, None] * stride_qm
        + offs_dq[None, :] * stride_qk
    )
    q = tl.load(q_ptrs, mask=mask_m[:, None] & mask_dq[None, :], other=0.0).to(tl.float32)

    m_i = tl.full((BLOCK_M,), -float("inf"), dtype=tl.float32)
    l_i = tl.zeros((BLOCK_M,), dtype=tl.float32)
    acc = tl.zeros((BLOCK_M, BLOCK_DMODEL_V), dtype=tl.float32)

    offs_n_init = tl.arange(0, BLOCK_N)

    for start_n in range(0, N_CTX, BLOCK_N):
        offs_n = start_n + offs_n_init
        offs_n = offs_n.to(tl.int32)
        mask_n = offs_n < N_CTX

        k_ptrs = K + (
            z * stride_kz
            + h * stride_kh
            + offs_n[:, None] * stride_kn
            + offs_dq[None, :] * stride_kk
        )
        k = tl.load(k_ptrs, mask=mask_n[:, None] & mask_dq[None, :], other=0.0).to(tl.float32)

        v_ptrs = V + (
            z * stride_vz
            + h * stride_vh
            + offs_n[:, None] * stride_vn
            + offs_dv[None, :] * stride_vk
        )
        v = tl.load(v_ptrs, mask=mask_n[:, None] & mask_dv[None, :], other=0.0).to(tl.float32)

        qk = tl.dot(q, tl.trans(k)) * sm_scale

        if causal:
            causal_mask = offs_m[:, None] >= offs_n[None, :]
            qk = tl.where(causal_mask, qk, -float("inf"))

        m_curr = tl.max(qk, axis=1)
        m_i_new = tl.maximum(m_i, m_curr)

        qk_shifted = qk - m_i_new[:, None]
        p = tl.exp(qk_shifted)

        l_prev_scaled = l_i * tl.exp(m_i - m_i_new)
        l_i_new = l_prev_scaled + tl.sum(p, axis=1)

        acc_scale = tl.where(l_i_new > 0, l_prev_scaled / l_i_new, tl.zeros_like(l_prev_scaled))
        acc_scale = acc_scale[:, None]

        pv = tl.dot(p, v)
        acc = acc * acc_scale + pv / l_i_new[:, None]

        m_i = m_i_new
        l_i = l_i_new

    o_ptrs = Out + (
        z * stride_oz
        + h * stride_oh
        + offs_m[:, None] * stride_om
        + offs_dv[None, :] * stride_ok
    )
    out = acc.to(tl.float16)
    tl.store(o_ptrs, out, mask=mask_m[:, None] & mask_dv[None, :])


def flash_attn(Q: torch.Tensor, K: torch.Tensor, V: torch.Tensor, causal: bool = True) -> torch.Tensor:
    Z, H, M, Dq = Q.shape
    Zk, Hk, N, Dk = K.shape
    Zv, Hv, Nv, Dv = V.shape

    assert Q.is_cuda and K.is_cuda and V.is_cuda, "Tensors must be on CUDA"
    assert Q.dtype == torch.float16 and K.dtype == torch.float16 and V.dtype == torch.float16, "Inputs must be float16"
    assert Z == Zk == Zv, "Batch dimension mismatch"
    assert H == Hk == Hv, "Head dimension mismatch"
    assert Dq == Dk, "Q and K feature dims must match"
    assert N == Nv, "Key and Value sequence length mismatch"
    assert M == N, "Flash attention assumes M == N"

    if Dq > 128 or Dv > 128:
        raise NotImplementedError("Head dimensions > 128 are not supported in this implementation")

    BLOCK_M = 64
    BLOCK_N = 64

    if Dq <= 64:
        BLOCK_DMODEL_QK = 64
    else:
        BLOCK_DMODEL_QK = 128

    if Dv <= 64:
        BLOCK_DMODEL_V = 64
    else:
        BLOCK_DMODEL_V = 128

    Out = torch.empty((Z, H, M, Dv), device=Q.device, dtype=torch.float16)

    grid = (triton.cdiv(M, BLOCK_M), Z * H)

    sm_scale = 1.0 / math.sqrt(Dq)

    flash_attn_fwd[grid](
        Q, K, V, Out,
        Q.stride(0), Q.stride(1), Q.stride(2), Q.stride(3),
        K.stride(0), K.stride(1), K.stride(2), K.stride(3),
        V.stride(0), V.stride(1), V.stride(2), V.stride(3),
        Out.stride(0), Out.stride(1), Out.stride(2), Out.stride(3),
        Z, H, M, Dq, Dv,
        sm_scale,
        causal=causal,
        BLOCK_M=BLOCK_M,
        BLOCK_N=BLOCK_N,
        BLOCK_DMODEL_QK=BLOCK_DMODEL_QK,
        BLOCK_DMODEL_V=BLOCK_DMODEL_V,
        num_warps=4,
        num_stages=2,
    )

    return Out


class Solution:
    def solve(self, spec_path: str = None) -> dict:
        header = "import torch\nimport triton\nimport triton.language as tl\nimport math\n\n"
        kernel_src = inspect.getsource(flash_attn_fwd)
        func_src = inspect.getsource(flash_attn)
        code = header + kernel_src + "\n\n" + func_src + "\n"
        return {"code": code}
