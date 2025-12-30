import torch
import triton
import triton.language as tl

@triton.autotune(
    configs=[
        triton.Config({'BLOCK_M': 1, 'BLOCK_N': 128, 'BLOCK_D': 64, 'GROUP_SIZE': 8}, num_stages=3, num_warps=4),
        triton.Config({'BLOCK_M': 1, 'BLOCK_N': 256, 'BLOCK_D': 64, 'GROUP_SIZE': 8}, num_stages=3, num_warps=4),
        triton.Config({'BLOCK_M': 1, 'BLOCK_N': 512, 'BLOCK_D': 64, 'GROUP_SIZE': 8}, num_stages=3, num_warps=8),
        triton.Config({'BLOCK_M': 1, 'BLOCK_N': 1024, 'BLOCK_D': 64, 'GROUP_SIZE': 8}, num_stages=2, num_warps=8),
        triton.Config({'BLOCK_M': 4, 'BLOCK_N': 128, 'BLOCK_D': 64, 'GROUP_SIZE': 8}, num_stages=3, num_warps=4),
        triton.Config({'BLOCK_M': 4, 'BLOCK_N': 256, 'BLOCK_D': 64, 'GROUP_SIZE': 8}, num_stages=3, num_warps=4),
    ],
    key=['M', 'N', 'Dq', 'Dv']
)
@triton.jit
def decoding_attn_kernel(
    Q, K, V, Out,
    stride_qz, stride_qh, stride_qm, stride_qd,
    stride_kz, stride_kh, stride_kn, stride_kd,
    stride_vz, stride_vh, stride_vn, stride_vd,
    stride_oz, stride_oh, stride_om, stride_od,
    Z, H, M, N, Dq, Dv,
    BLOCK_M: tl.constexpr, BLOCK_N: tl.constexpr, BLOCK_D: tl.constexpr, GROUP_SIZE: tl.constexpr
):
    pid_z = tl.program_id(0)
    pid_h = tl.program_id(1)
    pid_m = tl.program_id(2)
    
    offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
    offs_d = tl.arange(0, BLOCK_D)
    
    q_ptrs = Q + pid_z * stride_qz + pid_h * stride_qh + offs_m[:, None] * stride_qm + offs_d[None, :] * stride_qd
    out_ptrs = Out + pid_z * stride_oz + pid_h * stride_oh + offs_m[:, None] * stride_om + offs_d[None, :] * stride_od
    
    m_i = tl.zeros([BLOCK_M], dtype=tl.float32) - float('inf')
    l_i = tl.zeros([BLOCK_M], dtype=tl.float32)
    acc = tl.zeros([BLOCK_M, BLOCK_D], dtype=tl.float32)
    
    dq_inv = tl.math.rsqrt(Dq * 1.0)
    
    for start_n in range(0, N, BLOCK_N):
        start_n = tl.multiple_of(start_n, BLOCK_N)
        offs_n = start_n + tl.arange(0, BLOCK_N)
        
        k_ptrs = K + pid_z * stride_kz + pid_h * stride_kh + offs_n[None, :] * stride_kn + offs_d[:, None] * stride_kd
        v_ptrs = V + pid_z * stride_vz + pid_h * stride_vh + offs_n[:, None] * stride_vn + offs_d[None, :] * stride_vd
        
        q = tl.load(q_ptrs, mask=offs_m[:, None] < M, other=0.0)
        k = tl.load(k_ptrs, mask=(offs_n[None, :] < N) & (offs_d[:, None] < Dq), other=0.0)
        v = tl.load(v_ptrs, mask=(offs_n[:, None] < N) & (offs_d[None, :] < Dv), other=0.0)
        
        q = q.to(tl.float32)
        k = k.to(tl.float32)
        v = v.to(tl.float32)
        
        s = tl.dot(q, k) * dq_inv
        
        m_ij = tl.maximum(m_i, tl.max(s, axis=1))
        p = tl.exp(s - m_ij[:, None])
        
        l_ij = tl.sum(p, axis=1)
        alpha = tl.exp(m_i - m_ij)
        
        acc = acc * alpha[:, None]
        l_i = l_i * alpha + l_ij
        
        p = p / l_i[:, None]
        acc += tl.dot(p.to(v.dtype), v)
        
        m_i = m_ij
        l_i = l_i
    
    acc = acc.to(tl.float16)
    tl.store(out_ptrs, acc, mask=(offs_m[:, None] < M) & (offs_d[None, :] < Dv))

def decoding_attn(Q: torch.Tensor, K: torch.Tensor, V: torch.Tensor) -> torch.Tensor:
    Z, H, M, Dq = Q.shape
    _, _, N, Dv = V.shape
    
    Out = torch.empty((Z, H, M, Dv), device=Q.device, dtype=Q.dtype)
    
    grid = (Z, H, triton.cdiv(M, 1))
    
    decoding_attn_kernel[grid](
        Q, K, V, Out,
        Q.stride(0), Q.stride(1), Q.stride(2), Q.stride(3),
        K.stride(0), K.stride(1), K.stride(2), K.stride(3),
        V.stride(0), V.stride(1), V.stride(2), V.stride(3),
        Out.stride(0), Out.stride(1), Out.stride(2), Out.stride(3),
        Z, H, M, N, Dq, Dv
    )
    
    return Out

class Solution:
    def solve(self, spec_path: str = None) -> dict:
        import inspect
        code = inspect.getsource(inspect.getmodule(inspect.currentframe()))
        return {"code": code}