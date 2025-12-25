import torch
import triton
import triton.language as tl


@triton.autotune(
    configs=[
        triton.Config({'BLOCK_M': 64, 'BLOCK_N': 128, 'BLOCK_K': 32, 'num_warps': 4}),
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 64, 'BLOCK_K': 32, 'num_warps': 4}),
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 128, 'BLOCK_K': 32, 'num_warps': 8}),
        triton.Config({'BLOCK_M': 64, 'BLOCK_N': 256, 'BLOCK_K': 32, 'num_warps': 8}),
        triton.Config({'BLOCK_M': 256, 'BLOCK_N': 64, 'BLOCK_K': 32, 'num_warps': 8}),
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 256, 'BLOCK_K': 32, 'num_warps': 8}),
        triton.Config({'BLOCK_M': 256, 'BLOCK_N': 128, 'BLOCK_K': 32, 'num_warps': 8}),
    ],
    key=['M', 'N', 'Dq', 'Dv'],
)
@triton.jit
def _decoding_attn_kernel(
    Q, K, V, O,
    stride_qz, stride_qh, stride_qm, stride_qd,
    stride_kz, stride_kh, stride_kn, stride_kd,
    stride_vz, stride_vh, stride_vn, stride_vd,
    stride_oz, stride_oh, stride_om, stride_od,
    Z, H, M, N, Dq, Dv,
    scale: tl.constexpr,
    BLOCK_M: tl.constexpr,
    BLOCK_N: tl.constexpr,
    BLOCK_K: tl.constexpr,
):
    pid_z = tl.program_id(0)
    pid_h = tl.program_id(1)
    pid_m = tl.program_id(2)
    
    start_m = pid_m * BLOCK_M
    offs_m = start_m + tl.arange(0, BLOCK_M)
    offs_n = tl.arange(0, BLOCK_N)
    offs_k = tl.arange(0, BLOCK_K)
    
    Q_ptr = (
        Q
        + pid_z * stride_qz
        + pid_h * stride_qh
        + offs_m[:, None] * stride_qm
        + offs_k[None, :] * stride_qd
    )
    
    K_ptr = (
        K
        + pid_z * stride_kz
        + pid_h * stride_kh
        + offs_n[None, :] * stride_kn
        + offs_k[:, None] * stride_kd
    )
    
    V_ptr = (
        V
        + pid_z * stride_vz
        + pid_h * stride_vh
        + offs_n[:, None] * stride_vn
        + tl.arange(0, BLOCK_K)[None, :] * stride_vd
    )
    
    O_ptr = (
        O
        + pid_z * stride_oz
        + pid_h * stride_oh
        + offs_m[:, None] * stride_om
        + tl.arange(0, BLOCK_K)[None, :] * stride_od
    )
    
    m_mask = offs_m < M
    k_q_mask = offs_k < Dq
    k_v_mask = tl.arange(0, BLOCK_K) < Dv
    
    acc = tl.zeros((BLOCK_M, Dv), dtype=tl.float32)
    max_logits = tl.full((BLOCK_M,), float('-inf'), dtype=tl.float32)
    lse = tl.zeros((BLOCK_M,), dtype=tl.float32)
    
    for n_start in range(0, N, BLOCK_N):
        n_mask = n_start + offs_n < N
        
        q = tl.load(Q_ptr, mask=m_mask[:, None] & k_q_mask[None, :], other=0.0)
        k = tl.load(K_ptr + n_start * stride_kn, mask=n_mask[None, :] & k_q_mask[:, None], other=0.0)
        
        qk = tl.dot(q, k, allow_tf32=False)
        qk = qk * scale
        
        n_mask_expanded = tl.broadcast_to(n_mask[None, :], (BLOCK_M, BLOCK_N))
        qk = tl.where(n_mask_expanded, qk, float('-inf'))
        
        m_curr = tl.maximum(tl.max(qk, axis=1), max_logits)
        exp_qk = tl.exp(qk - m_curr[:, None])
        exp_qk = tl.where(n_mask_expanded, exp_qk, 0.0)
        
        lse = lse * tl.exp(max_logits - m_curr) + tl.sum(exp_qk, axis=1)
        max_logits = m_curr
        
        v = tl.load(
            V_ptr + n_start * stride_vn,
            mask=n_mask[:, None] & k_v_mask[None, :],
            other=0.0
        )
        
        exp_qk = exp_qk.to(v.dtype)
        acc += tl.dot(exp_qk, v, allow_tf32=False)
    
    acc = acc / lse[:, None]
    acc = acc.to(tl.float16)
    
    tl.store(
        O_ptr,
        acc,
        mask=m_mask[:, None] & k_v_mask[None, :]
    )


def decoding_attn(Q: torch.Tensor, K: torch.Tensor, V: torch.Tensor) -> torch.Tensor:
    Z, H, M, Dq = Q.shape
    _, _, N, _ = K.shape
    _, _, _, Dv = V.shape
    
    scale = 1.0 / (Dq ** 0.5)
    
    O = torch.empty((Z, H, M, Dv), device=Q.device, dtype=Q.dtype)
    
    grid = (Z, H, triton.cdiv(M, 64))
    
    _decoding_attn_kernel[grid](
        Q, K, V, O,
        Q.stride(0), Q.stride(1), Q.stride(2), Q.stride(3),
        K.stride(0), K.stride(1), K.stride(2), K.stride(3),
        V.stride(0), V.stride(1), V.stride(2), V.stride(3),
        O.stride(0), O.stride(1), O.stride(2), O.stride(3),
        Z, H, M, N, Dq, Dv,
        scale=scale,
    )
    
    return O


class Solution:
    def solve(self, spec_path: str = None) -> dict:
        code = """
import torch
import triton
import triton.language as tl


@triton.autotune(
    configs=[
        triton.Config({'BLOCK_M': 64, 'BLOCK_N': 128, 'BLOCK_K': 32, 'num_warps': 4}),
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 64, 'BLOCK_K': 32, 'num_warps': 4}),
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 128, 'BLOCK_K': 32, 'num_warps': 8}),
        triton.Config({'BLOCK_M': 64, 'BLOCK_N': 256, 'BLOCK_K': 32, 'num_warps': 8}),
        triton.Config({'BLOCK_M': 256, 'BLOCK_N': 64, 'BLOCK_K': 32, 'num_warps': 8}),
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 256, 'BLOCK_K': 32, 'num_warps': 8}),
        triton.Config({'BLOCK_M': 256, 'BLOCK_N': 128, 'BLOCK_K': 32, 'num_warps': 8}),
        triton.Config({'BLOCK_M': 64, 'BLOCK_N': 512, 'BLOCK_K': 32, 'num_warps': 8}),
        triton.Config({'BLOCK_M': 512, 'BLOCK_N': 64, 'BLOCK_K': 32, 'num_warps': 8}),
    ],
    key=['M', 'N', 'Dq', 'Dv'],
)
@triton.jit
def _decoding_attn_kernel(
    Q, K, V, O,
    stride_qz, stride_qh, stride_qm, stride_qd,
    stride_kz, stride_kh, stride_kn, stride_kd,
    stride_vz, stride_vh, stride_vn, stride_vd,
    stride_oz, stride_oh, stride_om, stride_od,
    Z, H, M, N, Dq, Dv,
    scale: tl.constexpr,
    BLOCK_M: tl.constexpr,
    BLOCK_N: tl.constexpr,
    BLOCK_K: tl.constexpr,
):
    pid_z = tl.program_id(0)
    pid_h = tl.program_id(1)
    pid_m = tl.program_id(2)
    
    start_m = pid_m * BLOCK_M
    offs_m = start_m + tl.arange(0, BLOCK_M)
    offs_n = tl.arange(0, BLOCK_N)
    offs_k = tl.arange(0, BLOCK_K)
    
    Q_ptr = (
        Q
        + pid_z * stride_qz
        + pid_h * stride_qh
        + offs_m[:, None] * stride_qm
        + offs_k[None, :] * stride_qd
    )
    
    K_ptr = (
        K
        + pid_z * stride_kz
        + pid_h * stride_kh
        + offs_n[None, :] * stride_kn
        + offs_k[:, None] * stride_kd
    )
    
    V_ptr = (
        V
        + pid_z * stride_vz
        + pid_h * stride_vh
        + offs_n[:, None] * stride_vn
        + tl.arange(0, BLOCK_K)[None, :] * stride_vd
    )
    
    O_ptr = (
        O
        + pid_z * stride_oz
        + pid_h * stride_oh
        + offs_m[:, None] * stride_om
        + tl.arange(0, BLOCK_K)[None, :] * stride_od
    )
    
    m_mask = offs_m < M
    k_q_mask = offs_k < Dq
    k_v_mask = tl.arange(0, BLOCK_K) < Dv
    
    acc = tl.zeros((BLOCK_M, Dv), dtype=tl.float32)
    max_logits = tl.full((BLOCK_M,), float('-inf'), dtype=tl.float32)
    lse = tl.zeros((BLOCK_M,), dtype=tl.float32)
    
    for n_start in range(0, N, BLOCK_N):
        n_mask = n_start + offs_n < N
        
        q = tl.load(Q_ptr, mask=m_mask[:, None] & k_q_mask[None, :], other=0.0)
        k = tl.load(K_ptr + n_start * stride_kn, mask=n_mask[None, :] & k_q_mask[:, None], other=0.0)
        
        qk = tl.dot(q, k, allow_tf32=False)
        qk = qk * scale
        
        n_mask_expanded = tl.broadcast_to(n_mask[None, :], (BLOCK_M, BLOCK_N))
        qk = tl.where(n_mask_expanded, qk, float('-inf'))
        
        m_curr = tl.maximum(tl.max(qk, axis=1), max_logits)
        exp_qk = tl.exp(qk - m_curr[:, None])
        exp_qk = tl.where(n_mask_expanded, exp_qk, 0.0)
        
        lse = lse * tl.exp(max_logits - m_curr) + tl.sum(exp_qk, axis=1)
        max_logits = m_curr
        
        v = tl.load(
            V_ptr + n_start * stride_vn,
            mask=n_mask[:, None] & k_v_mask[None, :],
            other=0.0
        )
        
        exp_qk = exp_qk.to(v.dtype)
        acc += tl.dot(exp_qk, v, allow_tf32=False)
    
    acc = acc / lse[:, None]
    acc = acc.to(tl.float16)
    
    tl.store(
        O_ptr,
        acc,
        mask=m_mask[:, None] & k_v_mask[None, :]
    )


def decoding_attn(Q: torch.Tensor, K: torch.Tensor, V: torch.Tensor) -> torch.Tensor:
    Z, H, M, Dq = Q.shape
    _, _, N, _ = K.shape
    _, _, _, Dv = V.shape
    
    scale = 1.0 / (Dq ** 0.5)
    
    O = torch.empty((Z, H, M, Dv), device=Q.device, dtype=Q.dtype)
    
    grid = (Z, H, triton.cdiv(M, 64))
    
    _decoding_attn_kernel[grid](
        Q, K, V, O,
        Q.stride(0), Q.stride(1), Q.stride(2), Q.stride(3),
        K.stride(0), K.stride(1), K.stride(2), K.stride(3),
        V.stride(0), V.stride(1), V.stride(2), V.stride(3),
        O.stride(0), O.stride(1), O.stride(2), O.stride(3),
        Z, H, M, N, Dq, Dv,
        scale=scale,
    )
    
    return O
"""
        return {"code": code}
