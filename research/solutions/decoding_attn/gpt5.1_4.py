import math
import os
import torch
import triton
import triton.language as tl


@triton.autotune(
    configs=[
        triton.Config({'BLOCK_N': 64}, num_warps=2),
        triton.Config({'BLOCK_N': 128}, num_warps=2),
        triton.Config({'BLOCK_N': 256}, num_warps=4),
        triton.Config({'BLOCK_N': 512}, num_warps=4),
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
    scale,
    N_CTX: tl.constexpr,
    D_HEAD: tl.constexpr,
    D_VALUE: tl.constexpr,
    BLOCK_N: tl.constexpr,
):
    pid = tl.program_id(axis=0)

    # Map program id to (z, h, m)
    m_idx = pid % M
    tmp = pid // M
    h_idx = tmp % H
    z_idx = tmp // H

    # Offsets along head dimensions
    offs_dq = tl.arange(0, D_HEAD)
    offs_dv = tl.arange(0, D_VALUE)

    # Load query vector q[z,h,m,:]
    q_ptrs = (
        Q_ptr
        + z_idx * stride_qz
        + h_idx * stride_qh
        + m_idx * stride_qm
        + offs_dq * stride_qd
    )
    q = tl.load(q_ptrs, mask=offs_dq < D_HEAD, other=0.0).to(tl.float32)

    NEG_INF = -1e9
    m_i = tl.full([1], NEG_INF, tl.float32)
    l_i = tl.zeros([1], tl.float32)
    acc = tl.zeros([D_VALUE], tl.float32)

    # Iterate over key/value sequence dimension in blocks of BLOCK_N
    for start_n in range(0, N_CTX, BLOCK_N):
        offs_n = start_n + tl.arange(0, BLOCK_N)
        mask_n = offs_n < N_CTX

        # Load K block: [BLOCK_N, D_HEAD]
        k_ptrs = (
            K_ptr
            + z_idx * stride_kz
            + h_idx * stride_kh
            + offs_n[:, None] * stride_kn
            + offs_dq[None, :] * stride_kd
        )
        k = tl.load(
            k_ptrs,
            mask=mask_n[:, None] & (offs_dq[None, :] < D_HEAD),
            other=0.0,
        ).to(tl.float32)

        # Compute scores = q · k^T / sqrt(D_HEAD)
        scores = tl.sum(k * q[None, :], axis=1) * scale
        scores = tl.where(mask_n, scores, NEG_INF)

        # Numerically stable streaming softmax update
        scores_max = tl.max(scores, axis=0)
        new_m = tl.maximum(m_i, scores_max)
        p = tl.exp(scores - new_m)
        p = tl.where(mask_n, p, 0.0)
        p_sum = tl.sum(p, axis=0)

        alpha = tl.exp(m_i - new_m)
        l_i_new = l_i * alpha + p_sum

        # Load V block: [BLOCK_N, D_VALUE]
        v_ptrs = (
            V_ptr
            + z_idx * stride_vz
            + h_idx * stride_vh
            + offs_n[:, None] * stride_vn
            + offs_dv[None, :] * stride_vd
        )
        v = tl.load(
            v_ptrs,
            mask=mask_n[:, None] & (offs_dv[None, :] < D_VALUE),
            other=0.0,
        ).to(tl.float32)

        # Accumulate weighted values
        weighted_v = tl.sum(v * p[:, None], axis=0)

        factor_old = (l_i * alpha) / l_i_new
        factor_new = 1.0 / l_i_new
        acc = acc * factor_old + weighted_v * factor_new

        m_i = new_m
        l_i = l_i_new

    # Store result
    out_ptrs = (
        Out_ptr
        + z_idx * stride_oz
        + h_idx * stride_oh
        + m_idx * stride_om
        + offs_dv * stride_od
    )
    tl.store(out_ptrs, acc.to(tl.float16), mask=offs_dv < D_VALUE)


def decoding_attn(Q: torch.Tensor, K: torch.Tensor, V: torch.Tensor) -> torch.Tensor:
    """
    Decoding attention computation using a Triton kernel.

    Args:
        Q: (Z, H, M, Dq) float16 CUDA tensor
        K: (Z, H, N, Dq) float16 CUDA tensor
        V: (Z, H, N, Dv) float16 CUDA tensor

    Returns:
        (Z, H, M, Dv) float16 CUDA tensor
    """
    if not (isinstance(Q, torch.Tensor) and isinstance(K, torch.Tensor) and isinstance(V, torch.Tensor)):
        raise TypeError("Q, K, V must be torch.Tensors")

    if Q.ndim != 4 or K.ndim != 4 or V.ndim != 4:
        raise ValueError("Q, K, V must be 4D tensors (Z, H, *, D)")

    if Q.shape[0] != K.shape[0] or Q.shape[0] != V.shape[0]:
        raise ValueError("Batch dimension Z must match for Q, K, V")
    if Q.shape[1] != K.shape[1] or Q.shape[1] != V.shape[1]:
        raise ValueError("Head dimension H must match for Q, K, V")
    if K.shape[2] != V.shape[2]:
        raise ValueError("Sequence length N must match for K and V")
    if Q.shape[3] != K.shape[3]:
        raise ValueError("Dq must match between Q and K")

    Z, H, M, Dq = Q.shape
    N = K.shape[2]
    Dv = V.shape[3]

    # CPU or non-CUDA fallback: use PyTorch implementation
    if not (Q.is_cuda and K.is_cuda and V.is_cuda):
        scale = 1.0 / math.sqrt(Dq)
        scores = torch.matmul(Q.to(torch.float32), K.transpose(-2, -1).to(torch.float32)) * scale
        probs = torch.softmax(scores, dim=-1)
        out = torch.matmul(probs, V.to(torch.float32))
        return out.to(Q.dtype)

    Q_ = Q.contiguous()
    K_ = K.contiguous()
    V_ = V.contiguous()

    Out = torch.empty((Z, H, M, Dv), device=Q.device, dtype=Q.dtype)

    scale = 1.0 / math.sqrt(Dq)

    grid = lambda META: (Z * H * M,)

    decoding_attn_kernel[grid](
        Q_, K_, V_, Out,
        Q_.stride(0), Q_.stride(1), Q_.stride(2), Q_.stride(3),
        K_.stride(0), K_.stride(1), K_.stride(2), K_.stride(3),
        V_.stride(0), V_.stride(1), V_.stride(2), V_.stride(3),
        Out.stride(0), Out.stride(1), Out.stride(2), Out.stride(3),
        Z, H, M,
        scale,
        N_CTX=N,
        D_HEAD=Dq,
        D_VALUE=Dv,
    )

    return Out


class Solution:
    def solve(self, spec_path: str = None) -> dict:
        return {"program_path": os.path.abspath(__file__)}