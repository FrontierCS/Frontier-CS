import torch
import triton
import triton.language as tl
from typing import Optional

@triton.jit
def _fwd_kernel(
    Q_ptr, K_ptr, V_ptr, O_ptr,
    stride_qz, stride_qh, stride_qm, stride_qd,
    stride_kz, stride_kh, stride_kn, stride_kd,
    stride_vz, stride_vh, stride_vn, stride_vd,
    stride_oz, stride_oh, stride_om, stride_od,
    Z, H, M, N, Dq, Dv,
    scale: tl.constexpr,
    BLOCK_M: tl.constexpr,
    BLOCK_N: tl.constexpr,
    BLOCK_D: tl.constexpr,
    CAUSAL: tl.constexpr,
    USE_BLOCK_PTR: tl.constexpr
):
    pid_bh = tl.program_id(0)
    pid_m = tl.program_id(1)
    
    batch_id = pid_bh // H
    head_id = pid_bh % H
    
    offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
    offs_n = tl.arange(0, BLOCK_N)
    offs_dq = tl.arange(0, BLOCK_D)
    offs_dv = tl.arange(0, BLOCK_D)
    
    q_offset = batch_id * stride_qz + head_id * stride_qh
    k_offset = batch_id * stride_kz + head_id * stride_kh
    v_offset = batch_id * stride_vz + head_id * stride_vh
    o_offset = batch_id * stride_oz + head_id * stride_oh
    
    if USE_BLOCK_PTR:
        q_block_ptr = tl.make_block_ptr(
            base=Q_ptr + q_offset,
            shape=(M, Dq),
            strides=(stride_qm, stride_qd),
            offsets=(pid_m * BLOCK_M, 0),
            block_shape=(BLOCK_M, BLOCK_D),
            order=(1, 0)
        )
        q = tl.load(q_block_ptr, boundary_check=(0, 1))
    else:
        q_ptrs = Q_ptr + q_offset + offs_m[:, None] * stride_qm + offs_dq[None, :] * stride_qd
        q = tl.load(q_ptrs, mask=offs_m[:, None] < M, other=0.0)
    
    m_i = tl.full([BLOCK_M], float('-inf'), dtype=tl.float32)
    l_i = tl.zeros([BLOCK_M], dtype=tl.float32)
    o_i = tl.zeros([BLOCK_M, BLOCK_D], dtype=tl.float32)
    
    num_n_blocks = tl.cdiv(N, BLOCK_N)
    
    for n_block_id in range(num_n_blocks):
        n_start = n_block_id * BLOCK_N
        
        if USE_BLOCK_PTR:
            k_block_ptr = tl.make_block_ptr(
                base=K_ptr + k_offset,
                shape=(N, Dq),
                strides=(stride_kn, stride_kd),
                offsets=(n_start, 0),
                block_shape=(BLOCK_N, BLOCK_D),
                order=(1, 0)
            )
            v_block_ptr = tl.make_block_ptr(
                base=V_ptr + v_offset,
                shape=(N, Dv),
                strides=(stride_vn, stride_vd),
                offsets=(n_start, 0),
                block_shape=(BLOCK_N, BLOCK_D),
                order=(1, 0)
            )
            k = tl.load(k_block_ptr, boundary_check=(0, 1))
            v = tl.load(v_block_ptr, boundary_check=(0, 1))
        else:
            n_offs = n_start + offs_n
            k_ptrs = K_ptr + k_offset + n_offs[:, None] * stride_kn + offs_dq[None, :] * stride_kd
            v_ptrs = V_ptr + v_offset + n_offs[:, None] * stride_vn + offs_dv[None, :] * stride_vd
            k = tl.load(k_ptrs, mask=n_offs[:, None] < N, other=0.0)
            v = tl.load(v_ptrs, mask=n_offs[:, None] < N, other=0.0)
        
        s_ij = tl.dot(q, tl.trans(k))
        s_ij = s_ij * scale
        
        if CAUSAL:
            m_offs = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
            n_offs = n_start + offs_n
            mask = m_offs[:, None] >= n_offs[None, :]
            s_ij = tl.where(mask, s_ij, float('-inf'))
        
        m_ij = tl.max(s_ij, 1)
        m_ij = tl.maximum(m_i, m_ij)
        
        p_ij = tl.exp(s_ij - m_ij[:, None])
        
        l_ij = tl.sum(p_ij, 1)
        alpha = tl.exp(m_i - m_ij)
        l_i = l_i * alpha + l_ij
        
        o_i = o_i * alpha[:, None] + tl.dot(p_ij.to(v.dtype), v)
        
        m_i = m_ij
    
    o_i = o_i / l_i[:, None]
    
    if USE_BLOCK_PTR:
        o_block_ptr = tl.make_block_ptr(
            base=O_ptr + o_offset,
            shape=(M, Dv),
            strides=(stride_om, stride_od),
            offsets=(pid_m * BLOCK_M, 0),
            block_shape=(BLOCK_M, BLOCK_D),
            order=(1, 0)
        )
        tl.store(o_block_ptr, o_i, boundary_check=(0, 1))
    else:
        o_ptrs = O_ptr + o_offset + offs_m[:, None] * stride_om + offs_dv[None, :] * stride_od
        tl.store(o_ptrs, o_i, mask=offs_m[:, None] < M)

def flash_attn(Q: torch.Tensor, K: torch.Tensor, V: torch.Tensor, causal: bool = True) -> torch.Tensor:
    Z, H, M, Dq = Q.shape
    N = K.shape[2]
    Dv = V.shape[3]
    
    assert K.shape[0] == Z and K.shape[1] == H and K.shape[3] == Dq
    assert V.shape[0] == Z and V.shape[1] == H and V.shape[2] == N
    
    scale = 1.0 / (Dq ** 0.5)
    O = torch.empty((Z, H, M, Dv), device=Q.device, dtype=Q.dtype)
    
    BLOCK_M = 128
    BLOCK_N = 64
    BLOCK_D = 64 if Dq <= 64 else 128
    
    grid = (Z * H, triton.cdiv(M, BLOCK_M))
    
    use_block_ptr = M >= 512 and N >= 512
    
    _fwd_kernel[grid](
        Q, K, V, O,
        Q.stride(0), Q.stride(1), Q.stride(2), Q.stride(3),
        K.stride(0), K.stride(1), K.stride(2), K.stride(3),
        V.stride(0), V.stride(1), V.stride(2), V.stride(3),
        O.stride(0), O.stride(1), O.stride(2), O.stride(3),
        Z, H, M, N, Dq, Dv,
        scale,
        BLOCK_M=BLOCK_M,
        BLOCK_N=BLOCK_N,
        BLOCK_D=BLOCK_D,
        CAUSAL=causal,
        USE_BLOCK_PTR=use_block_ptr,
        num_stages=3,
        num_warps=4
    )
    
    return O

class Solution:
    def solve(self, spec_path: str = None) -> dict:
        return {"code": self._get_code()}
    
    def _get_code(self) -> str:
        import inspect
        return inspect.getsource(flash_attn)