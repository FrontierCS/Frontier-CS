import torch
import triton
import triton.language as tl
from typing import Optional, Dict
from pathlib import Path

@triton.autotune(
    configs=[
        triton.Config({'BLOCK_M': 64, 'BLOCK_N': 64, 'BLOCK_K': 32, 'GROUP_M': 8}, num_warps=4),
        triton.Config({'BLOCK_M': 64, 'BLOCK_N': 64, 'BLOCK_K': 32, 'GROUP_M': 8}, num_warps=8),
        triton.Config({'BLOCK_M': 64, 'BLOCK_N': 32, 'BLOCK_K': 32, 'GROUP_M': 8}, num_warps=4),
        triton.Config({'BLOCK_M': 32, 'BLOCK_N': 64, 'BLOCK_K': 32, 'GROUP_M': 8}, num_warps=4),
        triton.Config({'BLOCK_M': 32, 'BLOCK_N': 32, 'BLOCK_K': 64, 'GROUP_M': 8}, num_warps=4),
        triton.Config({'BLOCK_M': 32, 'BLOCK_N': 32, 'BLOCK_K': 32, 'GROUP_M': 8}, num_warps=4),
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 128, 'BLOCK_K': 16, 'GROUP_M': 8}, num_warps=8),
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 128, 'BLOCK_K': 16, 'GROUP_M': 8}, num_warps=4),
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 64, 'BLOCK_K': 32, 'GROUP_M': 8}, num_warps=4),
        triton.Config({'BLOCK_M': 64, 'BLOCK_N': 128, 'BLOCK_K': 32, 'GROUP_M': 8}, num_warps=4),
        triton.Config({'BLOCK_M': 64, 'BLOCK_N': 64, 'BLOCK_K': 64, 'GROUP_M': 8}, num_warps=4),
        triton.Config({'BLOCK_M': 64, 'BLOCK_N': 64, 'BLOCK_K': 64, 'GROUP_M': 8}, num_warps=8),
    ],
    key=['M', 'N', 'K']
)
@triton.jit
def _bmm_kernel(
    A, B, C,
    stride_ab, stride_am, stride_ak,
    stride_bb, stride_bk, stride_bn,
    stride_cb, stride_cm, stride_cn,
    Batches, M, N, K,
    BLOCK_M: tl.constexpr, BLOCK_N: tl.constexpr, BLOCK_K: tl.constexpr,
    GROUP_M: tl.constexpr
):
    batch_id = tl.program_id(0)
    pid = tl.program_id(1)
    
    num_pid_m = tl.cdiv(M, BLOCK_M)
    num_pid_n = tl.cdiv(N, BLOCK_N)
    num_pid_in_group = GROUP_M * num_pid_n
    group_id = pid // num_pid_in_group
    first_pid_m = group_id * GROUP_M
    group_size_m = min(num_pid_m - first_pid_m, GROUP_M)
    pid_m = first_pid_m + (pid % group_size_m)
    pid_n = (pid % num_pid_in_group) // group_size_m
    
    offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
    offs_n = pid_n * BLOCK_N + tl.arange(0, BLOCK_N)
    offs_k = tl.arange(0, BLOCK_K)
    
    a_ptrs = (A + batch_id * stride_ab + 
              offs_m[:, None] * stride_am + 
              offs_k[None, :] * stride_ak)
    b_ptrs = (B + batch_id * stride_bb + 
              offs_k[:, None] * stride_bk + 
              offs_n[None, :] * stride_bn)
    
    accumulator = tl.zeros((BLOCK_M, BLOCK_N), dtype=tl.float32)
    
    for k in range(0, K, BLOCK_K):
        a = tl.load(a_ptrs, 
                    mask=(offs_m[:, None] < M) & (offs_k[None, :] < K - k), 
                    other=0.0).to(tl.float32)
        b = tl.load(b_ptrs, 
                    mask=(offs_k[:, None] < K - k) & (offs_n[None, :] < N), 
                    other=0.0).to(tl.float32)
        
        accumulator += tl.dot(a, b)
        
        a_ptrs += BLOCK_K * stride_ak
        b_ptrs += BLOCK_K * stride_bk
    
    offs_cm = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
    offs_cn = pid_n * BLOCK_N + tl.arange(0, BLOCK_N)
    c_ptrs = (C + batch_id * stride_cb + 
              offs_cm[:, None] * stride_cm + 
              offs_cn[None, :] * stride_cn)
    c_mask = (offs_cm[:, None] < M) & (offs_cn[None, :] < N)
    tl.store(c_ptrs, accumulator.to(tl.float16), mask=c_mask)

def bmm(A: torch.Tensor, B: torch.Tensor) -> torch.Tensor:
    if A.dim() != 3 or B.dim() != 3:
        raise ValueError(f"Input tensors must be 3D, got shapes {A.shape}, {B.shape}")
    
    Batches, M, K = A.shape
    Batches_B, K_B, N = B.shape
    
    if Batches != Batches_B:
        raise ValueError(f"Batch size mismatch: {Batches} != {Batches_B}")
    if K != K_B:
        raise ValueError(f"K dimension mismatch: {K} != {K_B}")
    
    C = torch.empty((Batches, M, N), device=A.device, dtype=torch.float16)
    
    grid = lambda META: (
        Batches,
        triton.cdiv(M, META['BLOCK_M']) * triton.cdiv(N, META['BLOCK_N']),
    )
    
    _bmm_kernel[grid](
        A, B, C,
        A.stride(0), A.stride(1), A.stride(2),
        B.stride(0), B.stride(1), B.stride(2),
        C.stride(0), C.stride(1), C.stride(2),
        Batches, M, N, K,
    )
    
    return C

class Solution:
    def solve(self, spec_path: Optional[str] = None) -> Dict[str, str]:
        current_file = Path(__file__).resolve()
        return {"code": current_file.read_text(encoding="utf-8")}
