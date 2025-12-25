import torch
import triton
import triton.language as tl
import math

@triton.autotune(
    configs=[
        triton.Config({'BLOCK_M': 64, 'BLOCK_N': 64, 'BLOCK_D': 64}, num_stages=3, num_warps=8),
        triton.Config({'BLOCK_M': 64, 'BLOCK_N': 128, 'BLOCK_D': 64}, num_stages=3, num_warps=8),
        triton.Config({'BLOCK_M': 64, 'BLOCK_N': 256, 'BLOCK_D': 64}, num_stages=3, num_warps=8),
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 64, 'BLOCK_D': 64}, num_stages=3, num_warps=8),
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 128, 'BLOCK_D': 64}, num_stages=3, num_warps=8),
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 256, 'BLOCK_D': 64}, num_stages=2, num_warps=8),
        triton.Config({'BLOCK_M': 256, 'BLOCK_N': 64, 'BLOCK_D': 64}, num_stages=2, num_warps=8),
        triton.Config({'BLOCK_M': 256, 'BLOCK_N': 128, 'BLOCK_D': 64}, num_stages=2, num_warps=8),
        triton.Config({'BLOCK_M': 32, 'BLOCK_N': 512, 'BLOCK_D': 64}, num_stages=2, num_warps=8),
        triton.Config({'BLOCK_M': 16, 'BLOCK_N': 1024, 'BLOCK_D': 64}, num_stages=1, num_warps=8),
    ],
    key=['M', 'N', 'Dq'],
)
@triton.jit
def _decoding_attn_kernel(
    Q, K, V, Out,
    stride_qz, stride_qh, stride_qm, stride_qd,
    stride_kz, stride_kh, stride_kn, stride_kd,
    stride_vz, stride_vh, stride_vn, stride_vd,
    stride_oz, stride_oh, stride_om, stride_od,
    Z, H, M, N, Dq, Dv,
    scale: tl.constexpr,
    BLOCK_M: tl.constexpr,
    BLOCK_N: tl.constexpr,
    BLOCK_D: tl.constexpr,
):
    pid_z = tl.program_id(0)
    pid_h = tl.program_id(1)
    pid_m = tl.program_id(2)
    
    offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
    offs_n = tl.arange(0, BLOCK_N)
    offs_dq = tl.arange(0, BLOCK_D)
    
    q_ptrs = Q + pid_z * stride_qz + pid_h * stride_qh + offs_m[:, None] * stride_qm + offs_dq[None, :] * stride_qd
    k_ptrs = K + pid_z * stride_kz + pid_h * stride_kh + offs_n[:, None] * stride_kn + offs_dq[None, :] * stride_kd
    
    q = tl.load(q_ptrs, mask=(offs_m[:, None] < M) & (offs_dq[None, :] < Dq), other=0.0).to(tl.float32)
    q = q * scale
    
    acc = tl.zeros([BLOCK_M, Dv], dtype=tl.float32)
    m_i = tl.full([BLOCK_M], float('-inf'), dtype=tl.float32)
    l_i = tl.zeros([BLOCK_M], dtype=tl.float32)
    
    offs_dv = tl.arange(0, BLOCK_D)
    v_ptrs_base = V + pid_z * stride_vz + pid_h * stride_vh + offs_n[:, None] * stride_vn + offs_dv[None, :] * stride_vd
    
    for start_n in range(0, N, BLOCK_N):
        start_n = tl.multiple_of(start_n, BLOCK_N)
        k = tl.load(k_ptrs + start_n * stride_kn, mask=(start_n + offs_n[:, None] < N) & (offs_dq[None, :] < Dq), other=0.0).to(tl.float32)
        
        qk = tl.dot(q, tl.trans(k))
        qk = tl.where(offs_m[:, None] < M, qk, float('-inf'))
        
        m_ij = tl.maximum(m_i, tl.max(qk, 1))
        p = tl.exp(qk - m_ij[:, None])
        l_ij = tl.exp(m_i - m_ij) * l_i + tl.sum(p, 1)
        
        alpha = tl.exp(m_i - m_ij) * l_i / l_ij
        beta = 1.0 / l_ij
        
        acc = acc * alpha[:, None]
        
        for start_dv in range(0, Dv, BLOCK_D):
            v_ptrs = v_ptrs_base + start_dv * stride_vd + start_n * stride_vn
            v = tl.load(v_ptrs, mask=(start_n + offs_n[:, None] < N) & (start_dv + offs_dv[None, :] < Dv), other=0.0).to(tl.float32)
            
            p_v = tl.dot(p, v)
            acc_inc = p_v * beta[:, None]
            acc = tl.where(start_dv + offs_dv[None, :] < Dv, acc + acc_inc, acc)
        
        m_i = m_ij
        l_i = l_ij
    
    out_ptrs = Out + pid_z * stride_oz + pid_h * stride_oh + offs_m[:, None] * stride_om + tl.arange(0, Dv)[None, :] * stride_od
    tl.store(out_ptrs, acc.to(Out.dtype.element_ty), mask=offs_m[:, None] < M)

def decoding_attn(Q: torch.Tensor, K: torch.Tensor, V: torch.Tensor) -> torch.Tensor:
    Z, H, M, Dq = Q.shape
    _, _, N, Dv = V.shape
    
    scale = 1.0 / math.sqrt(Dq)
    
    Out = torch.empty((Z, H, M, Dv), device=Q.device, dtype=Q.dtype)
    
    grid = (Z, H, triton.cdiv(M, 64))
    
    _decoding_attn_kernel[grid](
        Q, K, V, Out,
        Q.stride(0), Q.stride(1), Q.stride(2), Q.stride(3),
        K.stride(0), K.stride(1), K.stride(2), K.stride(3),
        V.stride(0), V.stride(1), V.stride(2), V.stride(3),
        Out.stride(0), Out.stride(1), Out.stride(2), Out.stride(3),
        Z, H, M, N, Dq, Dv,
        scale,
    )
    
    return Out

class Solution:
    def solve(self, spec_path: str = None) -> dict:
        if spec_path:
            with open(spec_path, 'r') as f:
                return {"code": f.read()}
        return {"code": open(__file__).read()}
