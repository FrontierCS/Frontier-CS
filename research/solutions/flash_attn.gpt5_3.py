import os
import math
import torch
import triton
import triton.language as tl


@triton.jit
def _flash_attn_fwd_kernel(
    Q_ptr, K_ptr, V_ptr, O_ptr,
    stride_q_zh, stride_q_m, stride_q_d,
    stride_k_zh, stride_k_n, stride_k_d,
    stride_v_zh, stride_v_n, stride_v_d,
    stride_o_zh, stride_o_m, stride_o_d,
    ZH, M, N, D, Dv,
    sm_scale,
    causal: tl.constexpr,
    BLOCK_M: tl.constexpr,
    BLOCK_N: tl.constexpr,
    BLOCK_DMODEL: tl.constexpr,
    BLOCK_DV: tl.constexpr,
):
    pid_zh = tl.program_id(0)
    pid_m = tl.program_id(1)

    offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
    offs_n = tl.arange(0, BLOCK_N)
    offs_d = tl.arange(0, BLOCK_DMODEL)
    offs_dv = tl.arange(0, BLOCK_DV)

    # Load Q block
    q_ptrs = Q_ptr + pid_zh * stride_q_zh + offs_m[:, None] * stride_q_m + offs_d[None, :] * stride_q_d
    q = tl.load(q_ptrs, mask=(offs_m[:, None] < M) & (offs_d[None, :] < D), other=0.0).to(tl.float32)

    m_i = tl.full((BLOCK_M,), float('-inf'), tl.float32)
    l_i = tl.zeros((BLOCK_M,), tl.float32)
    acc = tl.zeros((BLOCK_M, BLOCK_DV), tl.float32)

    k_start = 0
    while k_start < N:
        k_ptrs = K_ptr + pid_zh * stride_k_zh + (k_start + offs_n)[None, :] * stride_k_n + offs_d[:, None] * stride_k_d
        v_ptrs = V_ptr + pid_zh * stride_v_zh + (k_start + offs_n)[:, None] * stride_v_n + offs_dv[None, :] * stride_v_d

        k = tl.load(k_ptrs, mask=(offs_d[:, None] < D) & ((k_start + offs_n)[None, :] < N), other=0.0).to(tl.float32)
        v = tl.load(v_ptrs, mask=((k_start + offs_n)[:, None] < N) & (offs_dv[None, :] < Dv), other=0.0).to(tl.float32)

        # Compute attention scores
        qk = tl.dot(q, k, trans_b=True) * sm_scale

        # Apply padding mask for out-of-bounds
        mask_m = offs_m < M
        mask_n = (k_start + offs_n) < N
        qk = tl.where(mask_m[:, None] & mask_n[None, :], qk, float('-inf'))

        # Apply causal mask
        if causal:
            row_idx = (pid_m * BLOCK_M) + offs_m
            col_idx = k_start + offs_n
            causal_mask = col_idx[None, :] <= row_idx[:, None]
            qk = tl.where(causal_mask, qk, float('-inf'))

        # Compute numerically stable softmax
        m_curr = tl.max(qk, axis=1)
        m_next = tl.maximum(m_i, m_curr)
        p = tl.exp(qk - m_next[:, None])
        alpha = tl.exp(m_i - m_next)
        l_next = l_i * alpha + tl.sum(p, axis=1)

        # Update accumulator
        acc = acc * alpha[:, None] + tl.dot(p, v)

        m_i = m_next
        l_i = l_next

        k_start += BLOCK_N

    # Normalize
    acc = acc / l_i[:, None]

    # Store results
    o_ptrs = O_ptr + pid_zh * stride_o_zh + offs_m[:, None] * stride_o_m + offs_dv[None, :] * stride_o_d
    tl.store(o_ptrs, acc.to(tl.float16), mask=(offs_m[:, None] < M) & (offs_dv[None, :] < Dv))


def flash_attn(Q: torch.Tensor, K: torch.Tensor, V: torch.Tensor, causal: bool = True) -> torch.Tensor:
    assert Q.is_cuda and K.is_cuda and V.is_cuda, "Inputs must be CUDA tensors"
    assert Q.dtype == torch.float16 and K.dtype == torch.float16 and V.dtype == torch.float16, "Inputs must be float16"
    assert Q.shape[0] == K.shape[0] == V.shape[0], "Batch size (Z) mismatch"
    assert Q.shape[1] == K.shape[1] == V.shape[1], "Num heads (H) mismatch"
    assert Q.shape[2] == K.shape[2] == V.shape[2], "Seq len mismatch between Q and K/V (M vs N)"
    Z, H, M, Dq = Q.shape
    _, _, N, Dk = K.shape
    _, _, Nv, Dv = V.shape
    assert Dq == Dk, "Q and K dimensions must match"
    assert N == Nv, "K and V sequence lengths must match"
    device = Q.device

    ZH = Z * H
    Q_ = Q.reshape(ZH, M, Dq).contiguous()
    K_ = K.reshape(ZH, N, Dk).contiguous()
    V_ = V.reshape(ZH, N, Dv).contiguous()

    O = torch.empty((ZH, M, Dv), device=device, dtype=torch.float16)

    # Strides
    stride_q_zh, stride_q_m, stride_q_d = Q_.stride()
    stride_k_zh, stride_k_n, stride_k_d = K_.stride()
    stride_v_zh, stride_v_n, stride_v_d = V_.stride()
    stride_o_zh, stride_o_m, stride_o_d = O.stride()

    # Block sizes heuristics
    # Favor larger M-tile to increase data reuse of K/V across rows; use moderate N tile for cache
    BLOCK_M = 128 if M >= 128 else 64
    BLOCK_N = 64 if N >= 64 else 32
    BLOCK_DMODEL = 64 if Dq <= 64 else 128
    BLOCK_DV = 64 if Dv <= 64 else 128
    num_warps = 4 if BLOCK_M * BLOCK_N <= 8192 else 8
    num_stages = 2

    sm_scale = 1.0 / math.sqrt(Dq)

    grid = (ZH, triton.cdiv(M, BLOCK_M))

    _flash_attn_fwd_kernel[grid](
        Q_, K_, V_, O,
        stride_q_zh, stride_q_m, stride_q_d,
        stride_k_zh, stride_k_n, stride_k_d,
        stride_v_zh, stride_v_n, stride_v_d,
        stride_o_zh, stride_o_m, stride_o_d,
        ZH, M, N, Dq, Dv,
        sm_scale,
        causal=causal,
        BLOCK_M=BLOCK_M, BLOCK_N=BLOCK_N, BLOCK_DMODEL=BLOCK_DMODEL, BLOCK_DV=BLOCK_DV,
        num_warps=num_warps, num_stages=num_stages,
    )

    return O.view(Z, H, M, Dv)


class Solution:
    def solve(self, spec_path: str = None) -> dict:
        src = []
        src.append("import math")
        src.append("import torch")
        src.append("import triton")
        src.append("import triton.language as tl")
        # Embed kernel source
        src.append(triton.runtime.jit.get_source(_flash_attn_fwd_kernel))
        # Embed flash_attn function
        src.append(inspect.getsource(flash_attn))
        code = "\n\n".join(src)
        return {"code": code}


import inspect
