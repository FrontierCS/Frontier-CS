import torch
import triton
import triton.language as tl

@triton.autotune(
    configs=[
        triton.Config({'BLOCK_M': 1, 'BLOCK_N': 64, 'BLOCK_D': 32}, num_stages=1, num_warps=4),
        triton.Config({'BLOCK_M': 1, 'BLOCK_N': 128, 'BLOCK_D': 32}, num_stages=1, num_warps=4),
        triton.Config({'BLOCK_M': 1, 'BLOCK_N': 256, 'BLOCK_D': 32}, num_stages=1, num_warps=4),
        triton.Config({'BLOCK_M': 1, 'BLOCK_N': 512, 'BLOCK_D': 32}, num_stages=1, num_warps=4),
        triton.Config({'BLOCK_M': 1, 'BLOCK_N': 64, 'BLOCK_D': 64}, num_stages=1, num_warps=8),
        triton.Config({'BLOCK_M': 1, 'BLOCK_N': 128, 'BLOCK_D': 64}, num_stages=1, num_warps=8),
        triton.Config({'BLOCK_M': 1, 'BLOCK_N': 256, 'BLOCK_D': 64}, num_stages=1, num_warps=8),
        triton.Config({'BLOCK_M': 1, 'BLOCK_N': 512, 'BLOCK_D': 64}, num_stages=1, num_warps=8),
        triton.Config({'BLOCK_M': 1, 'BLOCK_N': 64, 'BLOCK_D': 128}, num_stages=2, num_warps=4),
        triton.Config({'BLOCK_M': 1, 'BLOCK_N': 128, 'BLOCK_D': 128}, num_stages=2, num_warps=8),
        triton.Config({'BLOCK_M': 1, 'BLOCK_N': 256, 'BLOCK_D': 128}, num_stages=2, num_warps=8),
    ],
    key=['Z', 'H', 'M', 'N', 'Dq', 'Dv'],
)
@triton.jit
def _decoding_attn_kernel(
    Q, K, V, Out,
    stride_qz, stride_qh, stride_qm, stride_qd,
    stride_kz, stride_kh, stride_kn, stride_kd,
    stride_vz, stride_vh, stride_vn, stride_vd,
    stride_oz, stride_oh, stride_om, stride_od,
    Z, H, M, N, Dq, Dv,
    IS_CAUSAL: tl.constexpr,
    BLOCK_M: tl.constexpr,
    BLOCK_N: tl.constexpr,
    BLOCK_D: tl.constexpr,
):
    pid_batch = tl.program_id(0)
    pid_head = tl.program_id(1)
    pid_m = tl.program_id(2)
    
    offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
    offs_n = tl.arange(0, BLOCK_N)
    offs_d = tl.arange(0, BLOCK_D)
    
    Q_ptr = Q + pid_batch * stride_qz + pid_head * stride_qh + offs_m[:, None] * stride_qm + offs_d[None, :] * stride_qd
    K_ptr = K + pid_batch * stride_kz + pid_head * stride_kh + offs_n[:, None] * stride_kn + offs_d[None, :] * stride_kd
    V_ptr = V + pid_batch * stride_vz + pid_head * stride_vh + offs_n[:, None] * stride_vn + offs_d[None, :] * stride_vd
    Out_ptr = Out + pid_batch * stride_oz + pid_head * stride_oh + offs_m[:, None] * stride_om + offs_d[None, :] * stride_od
    
    q = tl.load(Q_ptr, mask=(offs_m[:, None] < M) & (offs_d[None, :] < Dq), other=0.0)
    
    m_i = tl.full([BLOCK_M], float("-inf"), dtype=tl.float32)
    l_i = tl.zeros([BLOCK_M], dtype=tl.float32)
    acc = tl.zeros([BLOCK_M, BLOCK_D], dtype=tl.float32)
    
    scale = 1.0 / tl.sqrt(Dq * 1.0)
    
    for start_n in range(0, N, BLOCK_N):
        k = tl.load(K_ptr + start_n * stride_kn, mask=(start_n + offs_n[:, None] < N) & (offs_d[None, :] < Dq), other=0.0)
        v = tl.load(V_ptr + start_n * stride_vn, mask=(start_n + offs_n[:, None] < N) & (offs_d[None, :] < Dv), other=0.0)
        
        qk = tl.zeros([BLOCK_M, BLOCK_N], dtype=tl.float32)
        if BLOCK_D == Dq:
            qk = tl.dot(q, tl.trans(k))
        else:
            for d in range(0, Dq, BLOCK_D):
                q_block = tl.load(Q_ptr + d * stride_qd, mask=(offs_m[:, None] < M) & (d + offs_d[None, :] < Dq), other=0.0)
                k_block = tl.load(K_ptr + start_n * stride_kn + d * stride_kd, mask=(start_n + offs_n[:, None] < N) & (d + offs_d[None, :] < Dq), other=0.0)
                qk += tl.dot(q_block, tl.trans(k_block))
        
        qk = qk * scale
        
        if IS_CAUSAL:
            mask = (start_n + offs_n[None, :]) <= offs_m[:, None]
            qk = qk + tl.where(mask, 0.0, float("-inf"))
        
        m_ij = tl.max(qk, 1)
        p = tl.exp(qk - m_ij[:, None])
        
        l_ij = tl.sum(p, 1)
        alpha = tl.exp(m_i - m_ij)
        l_i = l_i * alpha + l_ij
        
        if BLOCK_D == Dv:
            acc = acc * alpha[:, None] + tl.dot(p.to(tl.float16), v)
        else:
            for d in range(0, Dv, BLOCK_D):
                v_block = tl.load(V_ptr + start_n * stride_vn + d * stride_vd, mask=(start_n + offs_n[:, None] < N) & (d + offs_d[None, :] < Dv), other=0.0)
                acc_block = tl.load(Out_ptr + d * stride_od, mask=(offs_m[:, None] < M) & (d + offs_d[None, :] < Dv), other=0.0)
                acc_block = acc_block * alpha[:, None] + tl.dot(p.to(tl.float16), v_block)
                tl.store(Out_ptr + d * stride_od, acc_block.to(tl.float16), mask=(offs_m[:, None] < M) & (d + offs_d[None, :] < Dv))
        
        m_i = m_ij
    
    if BLOCK_D == Dv:
        acc = acc / l_i[:, None]
        tl.store(Out_ptr, acc.to(tl.float16), mask=(offs_m[:, None] < M) & (offs_d[None, :] < Dv))

def decoding_attn(Q: torch.Tensor, K: torch.Tensor, V: torch.Tensor) -> torch.Tensor:
    Z, H, M, Dq = Q.shape
    _, _, N, Dv = V.shape
    
    Out = torch.empty((Z, H, M, Dv), device=Q.device, dtype=Q.dtype)
    
    grid = (Z, H, triton.cdiv(M, 1))
    
    _decoding_attn_kernel[grid](
        Q, K, V, Out,
        Q.stride(0), Q.stride(1), Q.stride(2), Q.stride(3),
        K.stride(0), K.stride(1), K.stride(2), K.stride(3),
        V.stride(0), V.stride(1), V.stride(2), V.stride(3),
        Out.stride(0), Out.stride(1), Out.stride(2), Out.stride(3),
        Z, H, M, N, Dq, Dv,
        IS_CAUSAL=False,
        BLOCK_M=1,
        BLOCK_N=256,
        BLOCK_D=64,
    )
    
    return Out

class Solution:
    def solve(self, spec_path: str = None) -> dict:
        code = """import torch
import triton
import triton.language as tl

@triton.autotune(
    configs=[
        triton.Config({'BLOCK_M': 1, 'BLOCK_N': 64, 'BLOCK_D': 32}, num_stages=1, num_warps=4),
        triton.Config({'BLOCK_M': 1, 'BLOCK_N': 128, 'BLOCK_D': 32}, num_stages=1, num_warps=4),
        triton.Config({'BLOCK_M': 1, 'BLOCK_N': 256, 'BLOCK_D': 32}, num_stages=1, num_warps=4),
        triton.Config({'BLOCK_M': 1, 'BLOCK_N': 512, 'BLOCK_D': 32}, num_stages=1, num_warps=4),
        triton.Config({'BLOCK_M': 1, 'BLOCK_N': 64, 'BLOCK_D': 64}, num_stages=1, num_warps=8),
        triton.Config({'BLOCK_M': 1, 'BLOCK_N': 128, 'BLOCK_D': 64}, num_stages=1, num_warps=8),
        triton.Config({'BLOCK_M': 1, 'BLOCK_N': 256, 'BLOCK_D': 64}, num_stages=1, num_warps=8),
        triton.Config({'BLOCK_M': 1, 'BLOCK_N': 512, 'BLOCK_D': 64}, num_stages=1, num_warps=8),
        triton.Config({'BLOCK_M': 1, 'BLOCK_N': 64, 'BLOCK_D': 128}, num_stages=2, num_warps=4),
        triton.Config({'BLOCK_M': 1, 'BLOCK_N': 128, 'BLOCK_D': 128}, num_stages=2, num_warps=8),
        triton.Config({'BLOCK_M': 1, 'BLOCK_N': 256, 'BLOCK_D': 128}, num_stages=2, num_warps=8),
    ],
    key=['Z', 'H', 'M', 'N', 'Dq', 'Dv'],
)
@triton.jit
def _decoding_attn_kernel(
    Q, K, V, Out,
    stride_qz, stride_qh, stride_qm, stride_qd,
    stride_kz, stride_kh, stride_kn, stride_kd,
    stride_vz, stride_vh, stride_vn, stride_vd,
    stride_oz, stride_oh, stride_om, stride_od,
    Z, H, M, N, Dq, Dv,
    IS_CAUSAL: tl.constexpr,
    BLOCK_M: tl.constexpr,
    BLOCK_N: tl.constexpr,
    BLOCK_D: tl.constexpr,
):
    pid_batch = tl.program_id(0)
    pid_head = tl.program_id(1)
    pid_m = tl.program_id(2)
    
    offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
    offs_n = tl.arange(0, BLOCK_N)
    offs_d = tl.arange(0, BLOCK_D)
    
    Q_ptr = Q + pid_batch * stride_qz + pid_head * stride_qh + offs_m[:, None] * stride_qm + offs_d[None, :] * stride_qd
    K_ptr = K + pid_batch * stride_kz + pid_head * stride_kh + offs_n[:, None] * stride_kn + offs_d[None, :] * stride_kd
    V_ptr = V + pid_batch * stride_vz + pid_head * stride_vh + offs_n[:, None] * stride_vn + offs_d[None, :] * stride_vd
    Out_ptr = Out + pid_batch * stride_oz + pid_head * stride_oh + offs_m[:, None] * stride_om + offs_d[None, :] * stride_od
    
    q = tl.load(Q_ptr, mask=(offs_m[:, None] < M) & (offs_d[None, :] < Dq), other=0.0)
    
    m_i = tl.full([BLOCK_M], float("-inf"), dtype=tl.float32)
    l_i = tl.zeros([BLOCK_M], dtype=tl.float32)
    acc = tl.zeros([BLOCK_M, BLOCK_D], dtype=tl.float32)
    
    scale = 1.0 / tl.sqrt(Dq * 1.0)
    
    for start_n in range(0, N, BLOCK_N):
        k = tl.load(K_ptr + start_n * stride_kn, mask=(start_n + offs_n[:, None] < N) & (offs_d[None, :] < Dq), other=0.0)
        v = tl.load(V_ptr + start_n * stride_vn, mask=(start_n + offs_n[:, None] < N) & (offs_d[None, :] < Dv), other=0.0)
        
        qk = tl.zeros([BLOCK_M, BLOCK_N], dtype=tl.float32)
        if BLOCK_D == Dq:
            qk = tl.dot(q, tl.trans(k))
        else:
            for d in range(0, Dq, BLOCK_D):
                q_block = tl.load(Q_ptr + d * stride_qd, mask=(offs_m[:, None] < M) & (d + offs_d[None, :] < Dq), other=0.0)
                k_block = tl.load(K_ptr + start_n * stride_kn + d * stride_kd, mask=(start_n + offs_n[:, None] < N) & (d + offs_d[None, :] < Dq), other=0.0)
                qk += tl.dot(q_block, tl.trans(k_block))
        
        qk = qk * scale
        
        if IS_CAUSAL:
            mask = (start_n + offs_n[None, :]) <= offs_m[:, None]
            qk = qk + tl.where(mask, 0.0, float("-inf"))
        
        m_ij = tl.max(qk, 1)
        p = tl.exp(qk - m_ij[:, None])
        
        l_ij = tl.sum(p, 1)
        alpha = tl.exp(m_i - m_ij)
        l_i = l_i * alpha + l_ij
        
        if BLOCK_D == Dv:
            acc = acc * alpha[:, None] + tl.dot(p.to(tl.float16), v)
        else:
            for d in range(0, Dv, BLOCK_D):
                v_block = tl.load(V_ptr + start_n * stride_vn + d * stride_vd, mask=(start_n + offs_n[:, None] < N) & (d + offs_d[None, :] < Dv), other=0.0)
                acc_block = tl.load(Out_ptr + d * stride_od, mask=(offs_m[:, None] < M) & (d + offs_d[None, :] < Dv), other=0.0)
                acc_block = acc_block * alpha[:, None] + tl.dot(p.to(tl.float16), v_block)
                tl.store(Out_ptr + d * stride_od, acc_block.to(tl.float16), mask=(offs_m[:, None] < M) & (d + offs_d[None, :] < Dv))
        
        m_i = m_ij
    
    if BLOCK_D == Dv:
        acc = acc / l_i[:, None]
        tl.store(Out_ptr, acc.to(tl.float16), mask=(offs_m[:, None] < M) & (offs_d[None, :] < Dv))

def decoding_attn(Q: torch.Tensor, K: torch.Tensor, V: torch.Tensor) -> torch.Tensor:
    Z, H, M, Dq = Q.shape
    _, _, N, Dv = V.shape
    
    Out = torch.empty((Z, H, M, Dv), device=Q.device, dtype=Q.dtype)
    
    grid = (Z, H, triton.cdiv(M, 1))
    
    _decoding_attn_kernel[grid](
        Q, K, V, Out,
        Q.stride(0), Q.stride(1), Q.stride(2), Q.stride(3),
        K.stride(0), K.stride(1), K.stride(2), K.stride(3),
        V.stride(0), V.stride(1), V.stride(2), V.stride(3),
        Out.stride(0), Out.stride(1), Out.stride(2), Out.stride(3),
        Z, H, M, N, Dq, Dv,
        IS_CAUSAL=False,
        BLOCK_M=1,
        BLOCK_N=256,
        BLOCK_D=64,
    )
    
    return Out"""
        
        return {"code": code}