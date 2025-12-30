import torch
import triton
import triton.language as tl
import math


@triton.autotune(
    configs=[
        triton.Config({'BLOCK_M': 1, 'BLOCK_N': 128, 'BLOCK_D': 64, 'NUM_WARPS': 4}),
        triton.Config({'BLOCK_M': 1, 'BLOCK_N': 256, 'BLOCK_D': 64, 'NUM_WARPS': 4}),
        triton.Config({'BLOCK_M': 1, 'BLOCK_N': 512, 'BLOCK_D': 64, 'NUM_WARPS': 8}),
        triton.Config({'BLOCK_M': 1, 'BLOCK_N': 1024, 'BLOCK_D': 64, 'NUM_WARPS': 8}),
        triton.Config({'BLOCK_M': 2, 'BLOCK_N': 128, 'BLOCK_D': 64, 'NUM_WARPS': 4}),
        triton.Config({'BLOCK_M': 2, 'BLOCK_N': 256, 'BLOCK_D': 64, 'NUM_WARPS': 4}),
        triton.Config({'BLOCK_M': 4, 'BLOCK_N': 128, 'BLOCK_D': 64, 'NUM_WARPS': 4}),
        triton.Config({'BLOCK_M': 4, 'BLOCK_N': 256, 'BLOCK_D': 64, 'NUM_WARPS': 4}),
    ],
    key=['M', 'N', 'Dq'],
)
@triton.jit
def _decoding_attn_kernel(
    Q_ptr,
    K_ptr,
    V_ptr,
    Out_ptr,
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
    Z,
    H,
    M,
    N,
    Dq,
    Dv,
    scale,
    BLOCK_M: tl.constexpr,
    BLOCK_N: tl.constexpr,
    BLOCK_D: tl.constexpr,
):
    pid_z = tl.program_id(0)
    pid_h = tl.program_id(1)
    pid_m = tl.program_id(2)
    
    offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
    offs_d = tl.arange(0, BLOCK_D)
    offs_n = tl.arange(0, BLOCK_N)
    
    q_ptrs = Q_ptr + pid_z * stride_qz + pid_h * stride_qh + offs_m[:, None] * stride_qm + offs_d[None, :] * stride_qd
    k_ptrs = K_ptr + pid_z * stride_kz + pid_h * stride_kh + offs_n[:, None] * stride_kn + offs_d[None, :] * stride_kd
    v_ptrs = V_ptr + pid_z * stride_vz + pid_h * stride_vh + offs_n[:, None] * stride_vn + tl.arange(0, Dv)[None, :] * stride_vd
    
    out_ptrs = Out_ptr + pid_z * stride_oz + pid_h * stride_oh + offs_m[:, None] * stride_om + tl.arange(0, Dv)[None, :] * stride_od
    
    m_i = tl.full((BLOCK_M,), float('-inf'), dtype=tl.float32)
    l_i = tl.zeros((BLOCK_M,), dtype=tl.float32)
    acc = tl.zeros((BLOCK_M, Dv), dtype=tl.float32)
    
    for start_n in range(0, N, BLOCK_N):
        mask_n = start_n + offs_n < N
        mask_m = offs_m < M
        
        q = tl.load(q_ptrs, mask=mask_m[:, None] & (offs_d[None, :] < Dq), other=0.0)
        k = tl.load(k_ptrs, mask=mask_n[:, None] & (offs_d[None, :] < Dq), other=0.0)
        v = tl.load(v_ptrs, mask=mask_n[:, None] & (tl.arange(0, Dv)[None, :] < Dv), other=0.0)
        
        s = tl.dot(q, tl.trans(k))
        s = s * scale
        
        if BLOCK_M == 1:
            s = tl.where(start_n + offs_n <= offs_m, s, float('-inf'))
        else:
            mask_causal = (start_n + offs_n[None, :]) <= (offs_m[:, None])
            s = tl.where(mask_causal, s, float('-inf'))
        
        m_ij = tl.maximum(m_i, tl.max(s, axis=1))
        p = tl.exp(s - m_ij[:, None])
        l_ij = tl.exp(m_i - m_ij) * l_i + tl.sum(p, axis=1)
        
        acc_scale = tl.exp(m_i - m_ij)[:, None]
        acc = acc * acc_scale + tl.dot(p.to(v.dtype), v)
        
        m_i = m_ij
        l_i = l_ij
        
        k_ptrs += BLOCK_N * stride_kn
        v_ptrs += BLOCK_N * stride_vn
    
    acc = acc / l_i[:, None]
    tl.store(out_ptrs, acc.to(Out_ptr.dtype.element_ty), mask=mask_m[:, None] & (tl.arange(0, Dv)[None, :] < Dv))


@triton.jit
def _decoding_attn_small_kernel(
    Q_ptr,
    K_ptr,
    V_ptr,
    Out_ptr,
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
    Z,
    H,
    M,
    N,
    Dq,
    Dv,
    scale,
    BLOCK_M: tl.constexpr,
    BLOCK_N: tl.constexpr,
):
    pid_z = tl.program_id(0)
    pid_h = tl.program_id(1)
    
    offs_m = tl.arange(0, BLOCK_M)
    offs_d = tl.arange(0, Dq)
    offs_n = tl.arange(0, BLOCK_N)
    
    q_ptrs = Q_ptr + pid_z * stride_qz + pid_h * stride_qh + offs_m[:, None] * stride_qm + offs_d[None, :] * stride_qd
    k_ptrs = K_ptr + pid_z * stride_kz + pid_h * stride_kh + offs_n[:, None] * stride_kn + offs_d[None, :] * stride_kd
    v_ptrs = V_ptr + pid_z * stride_vz + pid_h * stride_vh + offs_n[:, None] * stride_vn + tl.arange(0, Dv)[None, :] * stride_vd
    
    out_ptrs = Out_ptr + pid_z * stride_oz + pid_h * stride_oh + offs_m[:, None] * stride_om + tl.arange(0, Dv)[None, :] * stride_od
    
    m_i = tl.full((BLOCK_M,), float('-inf'), dtype=tl.float32)
    l_i = tl.zeros((BLOCK_M,), dtype=tl.float32)
    acc = tl.zeros((BLOCK_M, Dv), dtype=tl.float32)
    
    for start_n in range(0, N, BLOCK_N):
        mask_n = start_n + offs_n < N
        
        q = tl.load(q_ptrs, mask=offs_m[:, None] < M, other=0.0)
        k = tl.load(k_ptrs, mask=mask_n[:, None], other=0.0)
        v = tl.load(v_ptrs, mask=mask_n[:, None], other=0.0)
        
        s = tl.dot(q, tl.trans(k))
        s = s * scale
        
        mask_causal = (start_n + offs_n[None, :]) <= (offs_m[:, None])
        s = tl.where(mask_causal, s, float('-inf'))
        
        m_ij = tl.maximum(m_i, tl.max(s, axis=1))
        p = tl.exp(s - m_ij[:, None])
        l_ij = tl.exp(m_i - m_ij) * l_i + tl.sum(p, axis=1)
        
        acc_scale = tl.exp(m_i - m_ij)[:, None]
        acc = acc * acc_scale + tl.dot(p.to(v.dtype), v)
        
        m_i = m_ij
        l_i = l_ij
        
        k_ptrs += BLOCK_N * stride_kn
        v_ptrs += BLOCK_N * stride_vn
    
    acc = acc / l_i[:, None]
    tl.store(out_ptrs, acc.to(Out_ptr.dtype.element_ty), mask=offs_m[:, None] < M)


def decoding_attn(Q: torch.Tensor, K: torch.Tensor, V: torch.Tensor) -> torch.Tensor:
    Z, H, M, Dq = Q.shape
    _, _, N, _ = K.shape
    _, _, _, Dv = V.shape
    
    out = torch.empty((Z, H, M, Dv), dtype=Q.dtype, device=Q.device)
    
    scale = 1.0 / math.sqrt(Dq)
    
    if M <= 4 and N <= 4096:
        BLOCK_M = triton.next_power_of_2(M)
        BLOCK_N = triton.next_power_of_2(min(128, N))
        
        grid = (Z, H)
        _decoding_attn_small_kernel[grid](
            Q, K, V, out,
            Q.stride(0), Q.stride(1), Q.stride(2), Q.stride(3),
            K.stride(0), K.stride(1), K.stride(2), K.stride(3),
            V.stride(0), V.stride(1), V.stride(2), V.stride(3),
            out.stride(0), out.stride(1), out.stride(2), out.stride(3),
            Z, H, M, N, Dq, Dv, scale,
            BLOCK_M=BLOCK_M, BLOCK_N=BLOCK_N,
        )
    else:
        grid = (Z, H, triton.cdiv(M, 1))
        _decoding_attn_kernel[grid](
            Q, K, V, out,
            Q.stride(0), Q.stride(1), Q.stride(2), Q.stride(3),
            K.stride(0), K.stride(1), K.stride(2), K.stride(3),
            V.stride(0), V.stride(1), V.stride(2), V.stride(3),
            out.stride(0), out.stride(1), out.stride(2), out.stride(3),
            Z, H, M, N, Dq, Dv, scale,
        )
    
    return out


class Solution:
    def solve(self, spec_path: str = None) -> dict:
        return {"code": __import__('inspect').getsource(globals()['decoding_attn'])}