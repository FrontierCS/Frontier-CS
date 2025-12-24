import torch
import triton
import triton.language as tl
import math

@triton.autotune(
    configs=[
        triton.Config({'BLOCK_M': 1, 'BLOCK_N': 64, 'BLOCK_D': 32, 'N_STAGES': 3}, num_warps=4),
        triton.Config({'BLOCK_M': 1, 'BLOCK_N': 128, 'BLOCK_D': 32, 'N_STAGES': 3}, num_warps=4),
        triton.Config({'BLOCK_M': 1, 'BLOCK_N': 256, 'BLOCK_D': 32, 'N_STAGES': 3}, num_warps=4),
        triton.Config({'BLOCK_M': 1, 'BLOCK_N': 512, 'BLOCK_D': 32, 'N_STAGES': 3}, num_warps=4),
        triton.Config({'BLOCK_M': 1, 'BLOCK_N': 1024, 'BLOCK_D': 32, 'N_STAGES': 3}, num_warps=8),
        triton.Config({'BLOCK_M': 2, 'BLOCK_N': 64, 'BLOCK_D': 32, 'N_STAGES': 3}, num_warps=4),
        triton.Config({'BLOCK_M': 2, 'BLOCK_N': 128, 'BLOCK_D': 32, 'N_STAGES': 3}, num_warps=4),
        triton.Config({'BLOCK_M': 4, 'BLOCK_N': 64, 'BLOCK_D': 32, 'N_STAGES': 3}, num_warps=4),
        triton.Config({'BLOCK_M': 4, 'BLOCK_N': 128, 'BLOCK_D': 32, 'N_STAGES': 3}, num_warps=4),
        triton.Config({'BLOCK_M': 1, 'BLOCK_N': 64, 'BLOCK_D': 64, 'N_STAGES': 3}, num_warps=4),
        triton.Config({'BLOCK_M': 1, 'BLOCK_N': 128, 'BLOCK_D': 64, 'N_STAGES': 3}, num_warps=4),
        triton.Config({'BLOCK_M': 1, 'BLOCK_N': 256, 'BLOCK_D': 64, 'N_STAGES': 3}, num_warps=8),
        triton.Config({'BLOCK_M': 1, 'BLOCK_N': 512, 'BLOCK_D': 64, 'N_STAGES': 3}, num_warps=8),
    ],
    key=['M', 'N', 'Dq', 'Dv'],
)
@triton.jit
def decoding_attn_kernel(
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
    N_STAGES: tl.constexpr,
):
    # Program ID
    pid = tl.program_id(0)
    num_pid_m = tl.cdiv(M, BLOCK_M)
    num_pid_n = tl.cdiv(N, BLOCK_N)
    pid_z = pid // (H * num_pid_m)
    pid_h = (pid // num_pid_m) % H
    pid_m = pid % num_pid_m
    
    # Offsets
    off_z = pid_z
    off_h = pid_h
    off_m = pid_m * BLOCK_M
    
    # Initialize output accumulator
    acc = tl.zeros((BLOCK_M, Dv), dtype=tl.float32)
    m_i = tl.full((BLOCK_M,), float('-inf'), dtype=tl.float32)
    l_i = tl.zeros((BLOCK_M,), dtype=tl.float32)
    
    # Pointers
    q_ptr = Q + off_z * stride_qz + off_h * stride_qh + off_m * stride_qm
    k_ptr_base = K + off_z * stride_kz + off_h * stride_kh
    v_ptr_base = V + off_z * stride_vz + off_h * stride_vh
    
    # Loop over N in blocks
    for start_n in range(0, N, BLOCK_N):
        start_n = tl.multiple_of(start_n, BLOCK_N)
        
        # Load K block
        k_ptr = k_ptr_base + start_n * stride_kn
        k_offsets = start_n + tl.arange(0, BLOCK_N)[None, :]
        k_mask = k_offsets < N
        
        # Load V block
        v_ptr = v_ptr_base + start_n * stride_vn
        
        # Loop over Dq in blocks for QK^T
        for start_d in range(0, Dq, BLOCK_D):
            # Load Q block
            q_offsets = off_m + tl.arange(0, BLOCK_M)[:, None]
            q_mask = q_offsets < M
            q = tl.load(
                q_ptr + start_d * stride_qd,
                mask=q_mask & (tl.arange(0, BLOCK_D)[None, :] < Dq - start_d),
                other=0.0
            )
            
            # Load K block for this D segment
            k = tl.load(
                k_ptr + start_d * stride_kd,
                mask=k_mask & (tl.arange(0, BLOCK_D)[None, :] < Dq - start_d),
                other=0.0
            )
            
            # Compute QK^T for this segment
            s_ij = tl.dot(q, k, trans_b=True)
            if start_d == 0:
                S = s_ij * scale
            else:
                S += s_ij * scale
        
        # Online softmax update
        m_ij = tl.max(S, axis=1)
        m_new = tl.maximum(m_i, m_ij)
        
        alpha = tl.exp(m_i - m_new)
        beta = tl.exp(m_ij - m_new)
        
        # Update numerator and denominator
        l_i = l_i * alpha + tl.sum(beta[:, None] * tl.exp(S - m_new[:, None]), axis=1)
        
        # Load V and update accumulator
        for start_dv in range(0, Dv, BLOCK_D):
            v = tl.load(
                v_ptr + start_dv * stride_vd,
                mask=k_mask & (tl.arange(0, BLOCK_D)[None, :] < Dv - start_dv),
                other=0.0
            )
            
            p = tl.exp(S - m_new[:, None])
            acc_update = tl.dot(p, v)
            
            if start_dv == 0:
                acc = acc_update * beta[:, None]
            else:
                acc_off = start_dv // BLOCK_D
                acc[:, start_dv:start_dv+BLOCK_D] = (
                    acc[:, start_dv:start_dv+BLOCK_D] * alpha[:, None] + 
                    acc_update * beta[:, None]
                )
        
        m_i = m_new
    
    # Normalize and store output
    acc = acc / l_i[:, None]
    
    # Store output
    out_ptr = Out + off_z * stride_oz + off_h * stride_oh + off_m * stride_om
    for d in range(0, Dv, BLOCK_D):
        out_offsets = off_m + tl.arange(0, BLOCK_M)[:, None]
        out_mask = out_offsets < M
        
        tl.store(
            out_ptr + d * stride_od,
            acc[:, d:d+BLOCK_D].to(tl.float16),
            mask=out_mask & (tl.arange(0, BLOCK_D)[None, :] < Dv - d)
        )

def decoding_attn(Q: torch.Tensor, K: torch.Tensor, V: torch.Tensor) -> torch.Tensor:
    """
    Decoding attention computation.
    
    Args:
        Q: Input tensor of shape (Z, H, M, Dq) - query tensor (float16)
        K: Input tensor of shape (Z, H, N, Dq) - key tensor (float16)
        V: Input tensor of shape (Z, H, N, Dv) - value tensor (float16)
    
    Returns:
        Output tensor of shape (Z, H, M, Dv) - attention output (float16)
    """
    # Check inputs
    assert Q.dtype == torch.float16 and K.dtype == torch.float16 and V.dtype == torch.float16
    assert Q.is_cuda and K.is_cuda and V.is_cuda
    
    Z, H, M, Dq = Q.shape
    _, _, N, _ = K.shape
    _, _, _, Dv = V.shape
    
    # Allocate output
    Out = torch.empty((Z, H, M, Dv), device=Q.device, dtype=torch.float16)
    
    # Scale factor
    scale = 1.0 / math.sqrt(Dq)
    
    # Grid dimensions
    grid = (Z * H * triton.cdiv(M, 1),)
    
    # Launch kernel
    decoding_attn_kernel[grid](
        Q, K, V, Out,
        Q.stride(0), Q.stride(1), Q.stride(2), Q.stride(3),
        K.stride(0), K.stride(1), K.stride(2), K.stride(3),
        V.stride(0), V.stride(1), V.stride(2), V.stride(3),
        Out.stride(0), Out.stride(1), Out.stride(2), Out.stride(3),
        Z, H, M, N, Dq, Dv,
        scale=scale,
        BLOCK_M=1,
        BLOCK_N=256 if N >= 1024 else 128,
        BLOCK_D=32 if Dq <= 32 else 64,
        N_STAGES=3,
    )
    
    return Out

class Solution:
    def solve(self, spec_path: str = None) -> dict:
        return {"code": __import__('inspect').getsource(__module__)}
