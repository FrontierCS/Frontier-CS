import torch
import triton
import triton.language as tl

@triton.jit
def _fwd_kernel(
    Q, K, V, sm_scale, Out,
    stride_qz, stride_qh, stride_qm, stride_qd,
    stride_kz, stride_kh, stride_kn, stride_kd,
    stride_vz, stride_vh, stride_vn, stride_vd,
    stride_oz, stride_oh, stride_om, stride_od,
    Z, H, M, N, Dq, Dv,
    BLOCK_M: tl.constexpr, BLOCK_N: tl.constexpr, BLOCK_Dq: tl.constexpr, BLOCK_Dv: tl.constexpr,
    IS_CAUSAL: tl.constexpr
):
    start_m = tl.program_id(0)
    off_hz = tl.program_id(1)
    
    q_offset = off_hz * stride_qh
    k_offset = off_hz * stride_kh
    v_offset = off_hz * stride_vh
    o_offset = off_hz * stride_oh
    
    offs_m = start_m * BLOCK_M + tl.arange(0, BLOCK_M)
    offs_n = tl.arange(0, BLOCK_N)
    offs_dq = tl.arange(0, BLOCK_Dq)
    offs_dv = tl.arange(0, BLOCK_Dv)
    
    q_ptrs = Q + q_offset + (offs_m[:, None] * stride_qm + offs_dq[None, :] * stride_qd)
    k_ptrs = K + k_offset + (offs_n[:, None] * stride_kn + offs_dq[None, :] * stride_kd)
    v_ptrs = V + v_offset + (offs_n[:, None] * stride_vn + offs_dv[None, :] * stride_vd)
    o_ptrs = Out + o_offset + (offs_m[:, None] * stride_om + offs_dv[None, :] * stride_od)
    
    m_i = tl.zeros([BLOCK_M], dtype=tl.float32) - float('inf')
    l_i = tl.zeros([BLOCK_M], dtype=tl.float32)
    acc = tl.zeros([BLOCK_M, BLOCK_Dv], dtype=tl.float32)
    
    q = tl.load(q_ptrs, mask=offs_m[:, None] < M, other=0.0)
    q = (q * sm_scale).to(tl.float32)
    
    lo = 0
    hi = tl.minimum(N, start_m * BLOCK_M + BLOCK_M) if IS_CAUSAL else N
    
    for start_n in range(lo, hi, BLOCK_N):
        start_n = tl.multiple_of(start_n, BLOCK_N)
        
        k = tl.load(k_ptrs + start_n * stride_kn, mask=(start_n + offs_n[:, None]) < N, other=0.0)
        v = tl.load(v_ptrs + start_n * stride_vn, mask=(start_n + offs_n[:, None]) < N, other=0.0)
        
        k = k.to(tl.float32)
        v = v.to(tl.float32)
        
        qk = tl.dot(q, tl.trans(k))
        
        if IS_CAUSAL:
            causal_mask = (start_m * BLOCK_M + offs_m[:, None]) >= (start_n + offs_n[None, :])
            qk = tl.where(causal_mask, qk, float('-inf'))
        
        m_ij = tl.max(qk, 1)
        p = tl.exp(qk - m_ij[:, None])
        
        if IS_CAUSAL:
            p = tl.where(causal_mask, p, 0.0)
        
        l_ij = tl.sum(p, 1)
        alpha = tl.exp(m_i - m_ij)
        
        acc = acc * alpha[:, None]
        p = p.to(v.dtype)
        acc += tl.dot(p, v)
        
        m_i = tl.maximum(m_i, m_ij)
        l_i = l_i * alpha + l_ij
    
    acc = acc / l_i[:, None]
    tl.store(o_ptrs, acc.to(Out.dtype.element_ty), mask=offs_m[:, None] < M)

def flash_attn(Q: torch.Tensor, K: torch.Tensor, V: torch.Tensor, causal: bool = True) -> torch.Tensor:
    Z, H, M, Dq = Q.shape
    N = K.shape[2]
    Dv = V.shape[3]
    
    Out = torch.empty((Z, H, M, Dv), device=Q.device, dtype=Q.dtype)
    
    sm_scale = 1.0 / (Dq ** 0.5)
    
    BLOCK_M = 64
    BLOCK_N = 64
    
    if Dq > 128:
        BLOCK_Dq = 64
    else:
        BLOCK_Dq = Dq
    
    if Dv > 128:
        BLOCK_Dv = 64
    else:
        BLOCK_Dv = Dv
    
    grid = (triton.cdiv(M, BLOCK_M), Z * H)
    
    _fwd_kernel[grid](
        Q, K, V, sm_scale, Out,
        Q.stride(0), Q.stride(1), Q.stride(2), Q.stride(3),
        K.stride(0), K.stride(1), K.stride(2), K.stride(3),
        V.stride(0), V.stride(1), V.stride(2), V.stride(3),
        Out.stride(0), Out.stride(1), Out.stride(2), Out.stride(3),
        Z, H, M, N, Dq, Dv,
        BLOCK_M=BLOCK_M, BLOCK_N=BLOCK_N, BLOCK_Dq=BLOCK_Dq, BLOCK_Dv=BLOCK_Dv,
        IS_CAUSAL=causal,
        num_warps=4,
        num_stages=3
    )
    
    return Out

class Solution:
    def solve(self, spec_path: str = None) -> dict:
        return {"code": self._get_code()}
    
    @staticmethod
    def _get_code() -> str:
        import inspect
        return inspect.getsource(inspect.getmodule(inspect.currentframe()))
