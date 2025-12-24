import torch
import triton
import triton.language as tl
from typing import Optional, Dict
from pathlib import Path

@triton.autotune(
    configs=[
        triton.Config({'BLOCK_M': 16, 'BLOCK_N': 16, 'BLOCK_K': 16}, num_warps=4, num_stages=4),
        triton.Config({'BLOCK_M': 32, 'BLOCK_N': 32, 'BLOCK_K': 16}, num_warps=4, num_stages=4),
        triton.Config({'BLOCK_M': 32, 'BLOCK_N': 32, 'BLOCK_K': 32}, num_warps=4, num_stages=4),
        triton.Config({'BLOCK_M': 64, 'BLOCK_N': 32, 'BLOCK_K': 16}, num_warps=4, num_stages=4),
        triton.Config({'BLOCK_M': 64, 'BLOCK_N': 32, 'BLOCK_K': 32}, num_warps=4, num_stages=4),
        triton.Config({'BLOCK_M': 32, 'BLOCK_N': 64, 'BLOCK_K': 16}, num_warps=4, num_stages=4),
        triton.Config({'BLOCK_M': 32, 'BLOCK_N': 64, 'BLOCK_K': 32}, num_warps=4, num_stages=4),
        triton.Config({'BLOCK_M': 64, 'BLOCK_N': 64, 'BLOCK_K': 16}, num_warps=8, num_stages=4),
        triton.Config({'BLOCK_M': 64, 'BLOCK_N': 64, 'BLOCK_K': 32}, num_warps=8, num_stages=4),
        triton.Config({'BLOCK_M': 64, 'BLOCK_N': 64, 'BLOCK_K': 64}, num_warps=8, num_stages=4),
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 64, 'BLOCK_K': 16}, num_warps=8, num_stages=4),
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 64, 'BLOCK_K': 32}, num_warps=8, num_stages=4),
        triton.Config({'BLOCK_M': 64, 'BLOCK_N': 128, 'BLOCK_K': 16}, num_warps=8, num_stages=4),
        triton.Config({'BLOCK_M': 64, 'BLOCK_N': 128, 'BLOCK_K': 32}, num_warps=8, num_stages=4),
    ],
    key=['M', 'N', 'K'],
)
@triton.jit
def _bmm_kernel(
    A_ptr,
    B_ptr,
    C_ptr,
    Batches,
    M,
    N,
    K,
    stride_ab,
    stride_am,
    stride_ak,
    stride_bb,
    stride_bk,
    stride_bn,
    stride_cb,
    stride_cm,
    stride_cn,
    BLOCK_M: tl.constexpr,
    BLOCK_N: tl.constexpr,
    BLOCK_K: tl.constexpr,
):
    pid_b = tl.program_id(0)
    pid = tl.program_id(1)
    num_pid_m = tl.cdiv(M, BLOCK_M)
    num_pid_n = tl.cdiv(N, BLOCK_N)
    pid_m = pid // num_pid_n
    pid_n = pid % num_pid_n
    
    offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
    offs_n = pid_n * BLOCK_N + tl.arange(0, BLOCK_N)
    offs_k = tl.arange(0, BLOCK_K)
    
    A_batch_ptr = A_ptr + pid_b * stride_ab
    B_batch_ptr = B_ptr + pid_b * stride_bb
    C_batch_ptr = C_ptr + pid_b * stride_cb
    
    acc = tl.zeros((BLOCK_M, BLOCK_N), dtype=tl.float32)
    
    k0 = 0
    while k0 < K:
        k_idxs = k0 + offs_k
        
        A_ptrs = A_batch_ptr + (offs_m[:, None] * stride_am) + (k_idxs[None, :] * stride_ak)
        B_ptrs = B_batch_ptr + (k_idxs[:, None] * stride_bk) + (offs_n[None, :] * stride_bn)
        
        a_mask = (offs_m[:, None] < M) & (k_idxs[None, :] < K)
        b_mask = (k_idxs[:, None] < K) & (offs_n[None, :] < N)
        
        a = tl.load(A_ptrs, mask=a_mask, other=0.0).to(tl.float32)
        b = tl.load(B_ptrs, mask=b_mask, other=0.0).to(tl.float32)
        
        acc += tl.dot(a, b)
        k0 += BLOCK_K
    
    c_ptrs = C_batch_ptr + (offs_m[:, None] * stride_cm) + (offs_n[None, :] * stride_cn)
    c_mask = (offs_m[:, None] < M) & (offs_n[None, :] < N)
    tl.store(c_ptrs, acc.to(tl.float16), mask=c_mask)

def bmm(A: torch.Tensor, B: torch.Tensor) -> torch.Tensor:
    """
    Batched matrix multiplication.
    
    Args:
        A: Input tensor of shape (B, M, K) - batch of M×K matrices
        B: Input tensor of shape (B, K, N) - batch of K×N matrices
    
    Returns:
        Output tensor of shape (B, M, N) - batch of M×N result matrices
    """
    assert A.dim() == 3 and B.dim() == 3
    assert A.shape[0] == B.shape[0]
    assert A.shape[2] == B.shape[1]
    
    B, M, K = A.shape
    K, N = B.shape[1], B.shape[2]
    
    C = torch.empty((B, M, N), device=A.device, dtype=A.dtype)
    
    if M == 0 or N == 0 or K == 0:
        return C
    
    grid = (B, triton.cdiv(M, 16) * triton.cdiv(N, 16))
    
    _bmm_kernel[grid](
        A,
        B,
        C,
        Batches=B,
        M=M,
        N=N,
        K=K,
        stride_ab=A.stride(0),
        stride_am=A.stride(1),
        stride_ak=A.stride(2),
        stride_bb=B.stride(0),
        stride_bk=B.stride(1),
        stride_bn=B.stride(2),
        stride_cb=C.stride(0),
        stride_cm=C.stride(1),
        stride_cn=C.stride(2),
    )
    
    return C

class Solution:
    def solve(self, spec_path: str = None) -> dict:
        current_file = Path(__file__).resolve()
        return {"code": current_file.read_text(encoding="utf-8")}
