import os
import textwrap

KERNEL_CODE = r'''
import math
import torch
import triton
import triton.language as tl

_LOG2E = 1.4426950408889634

@triton.jit
def _flash_attn_fwd(
    Q_ptr, K_ptr, V_ptr, O_ptr,
    stride_qz: tl.constexpr, stride_qh: tl.constexpr, stride_qm: tl.constexpr, stride_qd: tl.constexpr,
    stride_kz: tl.constexpr, stride_kh: tl.constexpr, stride_kn: tl.constexpr, stride_kd: tl.constexpr,
    stride_vz: tl.constexpr, stride_vh: tl.constexpr, stride_vn: tl.constexpr, stride_vd: tl.constexpr,
    stride_oz: tl.constexpr, stride_oh: tl.constexpr, stride_om: tl.constexpr, stride_od: tl.constexpr,
    M: tl.constexpr, N: tl.constexpr,
    sm_scale,
    CAUSAL: tl.constexpr,
    BLOCK_M: tl.constexpr, BLOCK_N: tl.constexpr,
    D_HEAD: tl.constexpr, D_VAL: tl.constexpr,
):
    pid_m = tl.program_id(0)
    pid_bh = tl.program_id(1)

    # (z, h)
    # H is not passed; infer by strides not possible reliably -> compute via pointer base using pid_bh as linear head-batch index
    # We assume memory layout is (Z, H, ..) and pid_bh enumerates Z*H, with Z typically small.
    # Since we have no H parameter, we treat pid_bh as a flattened dimension and use stride_{?}z / stride_{?}h structure:
    # base = pid_bh * stride_qh when Z==1; for general Z we can't unflatten without H.
    # Therefore we require Z==1 in benchmark setting; still allow Z>1 by passing pid_bh over Z*H in python with known H and computing z,h in python? Not possible in kernel.
    # Workaround: treat pid_bh as "group" dimension where Q/K/V pointers are already offset by z and h via strides with packed indexing:
    # Use: base = (pid_bh // H)*stride_z + (pid_bh % H)*stride_h in python by providing H to kernel.
    # So we do require H passed. Kept here as constexpr arg.
    pass
'''

# Replace kernel with version that includes H parameter and correct indexing.
KERNEL_CODE = r'''
import math
import torch
import triton
import triton.language as tl

_LOG2E = 1.4426950408889634

@triton.jit
def _flash_attn_fwd(
    Q_ptr, K_ptr, V_ptr, O_ptr,
    stride_qz, stride_qh, stride_qm, stride_qd,
    stride_kz, stride_kh, stride_kn, stride_kd,
    stride_vz, stride_vh, stride_vn, stride_vd,
    stride_oz, stride_oh, stride_om, stride_od,
    H: tl.constexpr,
    M: tl.constexpr, N: tl.constexpr,
    sm_scale,
    CAUSAL: tl.constexpr,
    BLOCK_M: tl.constexpr, BLOCK_N: tl.constexpr,
    D_HEAD: tl.constexpr, D_VAL: tl.constexpr,
):
    pid_m = tl.program_id(0)
    pid_bh = tl.program_id(1)

    z = pid_bh // H
    h = pid_bh - z * H

    qkv_offset_q = z * stride_qz + h * stride_qh
    qkv_offset_k = z * stride_kz + h * stride_kh
    qkv_offset_v = z * stride_vz + h * stride_vh
    qkv_offset_o = z * stride_oz + h * stride_oh

    offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
    offs_d = tl.arange(0, D_HEAD)
    offs_dv = tl.arange(0, D_VAL)

    row_mask = offs_m < M

    q_ptrs = Q_ptr + qkv_offset_q + offs_m[:, None] * stride_qm + offs_d[None, :] * stride_qd
    q = tl.load(q_ptrs, mask=row_mask[:, None], other=0.0).to(tl.float16)

    m_i = tl.where(row_mask, -float("inf"), 0.0).to(tl.float32)
    l_i = tl.where(row_mask, 0.0, 1.0).to(tl.float32)
    acc = tl.zeros((BLOCK_M, D_VAL), dtype=tl.float32)

    for start_n in tl.static_range(0, N, BLOCK_N):
        offs_n = start_n + tl.arange(0, BLOCK_N)
        col_mask = offs_n < N

        k_ptrs = K_ptr + qkv_offset_k + offs_n[:, None] * stride_kn + offs_d[None, :] * stride_kd
        v_ptrs = V_ptr + qkv_offset_v + offs_n[:, None] * stride_vn + offs_dv[None, :] * stride_vd

        k = tl.load(k_ptrs, mask=col_mask[:, None], other=0.0, cache_modifier=".cg").to(tl.float16)
        v = tl.load(v_ptrs, mask=col_mask[:, None], other=0.0, cache_modifier=".cg").to(tl.float16)

        qk = tl.dot(q, tl.trans(k)).to(tl.float32) * sm_scale

        if CAUSAL:
            causal_mask = offs_n[None, :] <= offs_m[:, None]
            score_mask = row_mask[:, None] & col_mask[None, :] & causal_mask
        else:
            score_mask = row_mask[:, None] & col_mask[None, :]

        qk = tl.where(score_mask, qk, -float("inf"))

        m_ij = tl.maximum(m_i, tl.max(qk, axis=1))
        qk = qk - m_ij[:, None]

        p_fp32 = tl.exp2(qk * _LOG2E)
        l_ij = tl.sum(p_fp32, axis=1)

        p = p_fp32.to(tl.float16)
        pv = tl.dot(p, v).to(tl.float32)

        l_i_prev = l_i
        alpha = tl.exp2((m_i - m_ij) * _LOG2E)
        l_i = l_i_prev * alpha + l_ij

        acc_scale = (l_i_prev * alpha) / l_i
        acc = acc * acc_scale[:, None] + pv / l_i[:, None]
        m_i = m_ij

    o_ptrs = O_ptr + qkv_offset_o + offs_m[:, None] * stride_om + offs_dv[None, :] * stride_od
    tl.store(o_ptrs, acc.to(tl.float16), mask=row_mask[:, None])

def flash_attn(Q: torch.Tensor, K: torch.Tensor, V: torch.Tensor, causal: bool = True) -> torch.Tensor:
    assert Q.is_cuda and K.is_cuda and V.is_cuda
    assert Q.dtype == torch.float16 and K.dtype == torch.float16 and V.dtype == torch.float16
    assert Q.ndim == 4 and K.ndim == 4 and V.ndim == 4
    Z, H, M, D = Q.shape
    Zk, Hk, N, Dk = K.shape
    Zv, Hv, Nv, DV = V.shape
    assert Z == Zk == Zv and H == Hk == Hv and N == Nv and D == Dk
    assert K.shape[2] == N and V.shape[2] == N

    # Tuned for (M,N) in {512,1024,2048}, D=64, DV=64 on L4
    BLOCK_M = 128
    BLOCK_N = 128
    num_warps = 8
    num_stages = 3

    if D % 16 != 0:
        # fallback (rare)
        scores = torch.matmul(Q.float(), K.float().transpose(-1, -2)) * (1.0 / math.sqrt(D))
        if causal:
            i = torch.arange(M, device=Q.device)
            j = torch.arange(N, device=Q.device)
            mask = j[None, :] > i[:, None]
            scores = scores.masked_fill(mask, float("-inf"))
        P = torch.softmax(scores, dim=-1).to(torch.float16)
        O = torch.matmul(P, V)
        return O

    O = torch.empty((Z, H, M, DV), device=Q.device, dtype=torch.float16)

    sm_scale = 1.0 / math.sqrt(D)

    grid = (triton.cdiv(M, BLOCK_M), Z * H)

    _flash_attn_fwd[grid](
        Q, K, V, O,
        Q.stride(0), Q.stride(1), Q.stride(2), Q.stride(3),
        K.stride(0), K.stride(1), K.stride(2), K.stride(3),
        V.stride(0), V.stride(1), V.stride(2), V.stride(3),
        O.stride(0), O.stride(1), O.stride(2), O.stride(3),
        H=H,
        M=M, N=N,
        sm_scale=sm_scale,
        CAUSAL=causal,
        BLOCK_M=BLOCK_M, BLOCK_N=BLOCK_N,
        D_HEAD=D, D_VAL=DV,
        num_warps=num_warps,
        num_stages=num_stages,
    )
    return O
'''

class Solution:
    def solve(self, spec_path: str = None) -> dict:
        return {"code": textwrap.dedent(KERNEL_CODE)}
