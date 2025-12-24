import math

_KERNEL_SRC = r'''
import math
import torch
import triton
import triton.language as tl

_tmp_cache = {}

def _get_tmp(name: str, like: torch.Tensor) -> torch.Tensor:
    key = (name, like.device, like.dtype, tuple(like.shape))
    t = _tmp_cache.get(key)
    if t is None or t.device != like.device or t.dtype != like.dtype or t.shape != like.shape:
        t = torch.empty_like(like)
        _tmp_cache[key] = t
    return t

@triton.jit
def _gate_mul_sigmoid_kernel(X_ptr, G_ptr, Y_ptr, n_elements: tl.constexpr, BLOCK: tl.constexpr):
    pid = tl.program_id(0)
    offs = pid * BLOCK + tl.arange(0, BLOCK)
    mask = offs < n_elements
    x = tl.load(X_ptr + offs, mask=mask, other=0.0).to(tl.float16)
    g = tl.load(G_ptr + offs, mask=mask, other=0.0).to(tl.float32)
    gate = tl.sigmoid(g).to(tl.float16)
    y = x * gate
    tl.store(Y_ptr + offs, y, mask=mask)

@triton.jit
def _flash_attn_fwd_kernel(
    Q_ptr, K_ptr, V_ptr, O_ptr,
    stride_qz, stride_qh, stride_qm, stride_qd,
    stride_kz, stride_kh, stride_kn, stride_kd,
    stride_vz, stride_vh, stride_vn, stride_vd,
    stride_oz, stride_oh, stride_om, stride_od,
    H: tl.constexpr, M: tl.constexpr, N: tl.constexpr,
    DQ: tl.constexpr, DV: tl.constexpr,
    sm_scale: tl.constexpr,
    BLOCK_M: tl.constexpr, BLOCK_N: tl.constexpr
):
    pid_m = tl.program_id(0)
    pid_bh = tl.program_id(1)

    z = pid_bh // H
    h = pid_bh - z * H

    tl.multiple_of(stride_qm, 16)
    tl.multiple_of(stride_kn, 16)
    tl.multiple_of(stride_vn, 16)
    tl.multiple_of(stride_om, 16)

    q_base = Q_ptr + z * stride_qz + h * stride_qh
    k_base = K_ptr + z * stride_kz + h * stride_kh
    v_base = V_ptr + z * stride_vz + h * stride_vh
    o_base = O_ptr + z * stride_oz + h * stride_oh

    offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
    offs_d = tl.arange(0, DQ)
    offs_dv = tl.arange(0, DV)

    mask_m = offs_m < M

    q_ptrs = q_base + offs_m[:, None] * stride_qm + offs_d[None, :] * stride_qd
    q = tl.load(q_ptrs, mask=mask_m[:, None], other=0.0).to(tl.float16)

    m_i = tl.full([BLOCK_M], -float("inf"), tl.float32)
    l_i = tl.zeros([BLOCK_M], tl.float32)
    acc = tl.zeros([BLOCK_M, DV], tl.float32)

    offs_n_base = tl.arange(0, BLOCK_N)

    for start_n in tl.static_range(0, N, BLOCK_N):
        offs_n = start_n + offs_n_base
        mask_n = offs_n < N

        k_ptrs = k_base + offs_n[:, None] * stride_kn + offs_d[None, :] * stride_kd
        k = tl.load(k_ptrs, mask=mask_n[:, None], other=0.0).to(tl.float16)

        qk = tl.dot(q, tl.trans(k)).to(tl.float32) * sm_scale
        qk = tl.where(mask_n[None, :], qk, -1.0e9)

        m_ij = tl.max(qk, axis=1)
        m_new = tl.maximum(m_i, m_ij)
        alpha = tl.exp(m_i - m_new)

        p = tl.exp(qk - m_new[:, None]).to(tl.float32)

        l_i = l_i * alpha + tl.sum(p, axis=1)

        v_ptrs = v_base + offs_n[:, None] * stride_vn + offs_dv[None, :] * stride_vd
        v = tl.load(v_ptrs, mask=mask_n[:, None], other=0.0).to(tl.float16)

        acc = acc * alpha[:, None] + tl.dot(p.to(tl.float16), v).to(tl.float32)

        m_i = m_new

    l_safe = tl.where(mask_m, l_i, 1.0)
    out = (acc / l_safe[:, None]).to(tl.float16)

    o_ptrs = o_base + offs_m[:, None] * stride_om + offs_dv[None, :] * stride_od
    tl.store(o_ptrs, out, mask=mask_m[:, None])

def gdpa_attn(Q: torch.Tensor, K: torch.Tensor, V: torch.Tensor, GQ: torch.Tensor, GK: torch.Tensor) -> torch.Tensor:
    assert Q.is_cuda and K.is_cuda and V.is_cuda and GQ.is_cuda and GK.is_cuda
    assert Q.dtype == torch.float16 and K.dtype == torch.float16 and V.dtype == torch.float16
    assert GQ.dtype == torch.float16 and GK.dtype == torch.float16
    assert Q.ndim == 4 and K.ndim == 4 and V.ndim == 4 and GQ.ndim == 4 and GK.ndim == 4
    Z, H, M, DQ = Q.shape
    Zk, Hk, N, DQk = K.shape
    Zv, Hv, Nv, DV = V.shape
    assert Zk == Z and Zv == Z
    assert Hk == H and Hv == H
    assert N == M and Nv == N
    assert DQk == DQ
    assert GQ.shape == Q.shape and GK.shape == K.shape

    if not (Q.is_contiguous() and K.is_contiguous() and V.is_contiguous() and GQ.is_contiguous() and GK.is_contiguous()):
        Q = Q.contiguous()
        K = K.contiguous()
        V = V.contiguous()
        GQ = GQ.contiguous()
        GK = GK.contiguous()

    if DQ != 64 or DV != 64:
        Qg = Q * torch.sigmoid(GQ)
        Kg = K * torch.sigmoid(GK)
        scale = 1.0 / math.sqrt(DQ)
        att = torch.matmul(Qg, Kg.transpose(-2, -1)) * scale
        p = torch.softmax(att, dim=-1)
        out = torch.matmul(p, V)
        return out.to(torch.float16)

    Qg = _get_tmp("Qg", Q)
    Kg = _get_tmp("Kg", K)

    block = 8192
    grid_q = (triton.cdiv(Q.numel(), block),)
    grid_k = (triton.cdiv(K.numel(), block),)
    _gate_mul_sigmoid_kernel[grid_q](Q, GQ, Qg, n_elements=Q.numel(), BLOCK=block, num_warps=8)
    _gate_mul_sigmoid_kernel[grid_k](K, GK, Kg, n_elements=K.numel(), BLOCK=block, num_warps=8)

    O = torch.empty((Z, H, M, DV), device=Q.device, dtype=torch.float16)

    if N == 1024:
        BLOCK_M = 128
        BLOCK_N = 128
        num_warps = 8
        num_stages = 3
    else:
        BLOCK_M = 128
        BLOCK_N = 64
        num_warps = 4
        num_stages = 4

    sm_scale = 1.0 / math.sqrt(DQ)

    grid = (triton.cdiv(M, BLOCK_M), Z * H)

    _flash_attn_fwd_kernel[grid](
        Qg, Kg, V, O,
        Qg.stride(0), Qg.stride(1), Qg.stride(2), Qg.stride(3),
        Kg.stride(0), Kg.stride(1), Kg.stride(2), Kg.stride(3),
        V.stride(0), V.stride(1), V.stride(2), V.stride(3),
        O.stride(0), O.stride(1), O.stride(2), O.stride(3),
        H=H, M=M, N=N,
        DQ=64, DV=64,
        sm_scale=sm_scale,
        BLOCK_M=BLOCK_M, BLOCK_N=BLOCK_N,
        num_warps=num_warps,
        num_stages=num_stages
    )
    return O
'''

exec(_KERNEL_SRC, globals())


class Solution:
    def solve(self, spec_path: str = None) -> dict:
        return {"code": _KERNEL_SRC}
