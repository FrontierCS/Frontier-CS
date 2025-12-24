import torch
import triton
import triton.language as tl
from pathlib import Path

@triton.autotune(
    configs=[
        # Basic configurations for balanced M, N, K
        triton.Config({'BLOCK_M': 32, 'BLOCK_N': 32, 'BLOCK_K': 32}, num_stages=2, num_warps=4),
        triton.Config({'BLOCK_M': 64, 'BLOCK_N': 32, 'BLOCK_K': 32}, num_stages=3, num_warps=4),
        triton.Config({'BLOCK_M': 32, 'BLOCK_N': 64, 'BLOCK_K': 32}, num_stages=3, num_warps=4),
        triton.Config({'BLOCK_M': 64, 'BLOCK_N': 64, 'BLOCK_K': 32}, num_stages=4, num_warps=8),
        triton.Config({'BLOCK_M': 64, 'BLOCK_N': 64, 'BLOCK_K': 32}, num_stages=3, num_warps=4),
        
        # Configurations with larger K blocks
        triton.Config({'BLOCK_M': 32, 'BLOCK_N': 32, 'BLOCK_K': 64}, num_stages=2, num_warps=4),
        triton.Config({'BLOCK_M': 64, 'BLOCK_N': 32, 'BLOCK_K': 64}, num_stages=3, num_warps=4),
        triton.Config({'BLOCK_M': 32, 'BLOCK_N': 64, 'BLOCK_K': 64}, num_stages=3, num_warps=4),
        triton.Config({'BLOCK_M': 64, 'BLOCK_N': 64, 'BLOCK_K': 64}, num_stages=3, num_warps=8),
        
        # Configurations with larger M/N blocks for rectangular matrices
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 32, 'BLOCK_K': 32}, num_stages=3, num_warps=8),
        triton.Config({'BLOCK_M': 32, 'BLOCK_N': 128, 'BLOCK_K': 32}, num_stages=3, num_warps=8),
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 64, 'BLOCK_K': 32}, num_stages=3, num_warps=8),
        triton.Config({'BLOCK_M': 64, 'BLOCK_N': 128, 'BLOCK_K': 32}, num_stages=3, num_warps=8),
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 128, 'BLOCK_K': 32}, num_stages=2, num_warps=8),
        
        # Configurations with even larger K blocks for K-bound problems
        triton.Config({'BLOCK_M': 32, 'BLOCK_N': 32, 'BLOCK_K': 128}, num_stages=2, num_warps=4),
        triton.Config({'BLOCK_M': 64, 'BLOCK_N': 64, 'BLOCK_K': 128}, num_stages=3, num_warps=8),
    ],
    key=['M', 'N', 'K'],
)
@triton.jit
def _bmm_kernel(
    A, B, C,
    Batches, M, N, K,
    stride_ab, stride_am, stride_ak,
    stride_bb, stride_bk, stride_bn,
    stride_cb, stride_cm, stride_cn,
    BLOCK_M: tl.constexpr, BLOCK_N: tl.constexpr, BLOCK_K: tl.constexpr,
):
    pid_m = tl.program_id(0)
    pid_n = tl.program_id(1)
    pid_batch = tl.program_id(2)

    offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
    offs_n = pid_n * BLOCK_N + tl.arange(0, BLOCK_N)
    offs_k = tl.arange(0, BLOCK_K)

    A_batch_ptr = A + pid_batch * stride_ab
    B_batch_ptr = B + pid_batch * stride_bb
    
    acc = tl.zeros((BLOCK_M, BLOCK_N), dtype=tl.float32)

    k0 = 0
    while k0 < K:
        k_idxs = k0 + offs_k
        
        A_ptrs = A_batch_ptr + (offs_m[:, None] * stride_am + k_idxs[None, :] * stride_ak)
        B_ptrs = B_batch_ptr + (k_idxs[:, None] * stride_bk + offs_n[None, :] * stride_bn)

        a_mask = (offs_m[:, None] < M) & (k_idxs[None, :] < K)
        b_mask = (k_idxs[:, None] < K) & (offs_n[None, :] < N)
        
        a = tl.load(A_ptrs, mask=a_mask, other=0.0).to(tl.float32)
        b = tl.load(B_ptrs, mask=b_mask, other=0.0).to(tl.float32)

        acc += tl.dot(a, b)
        
        k0 += BLOCK_K

    C_batch_ptr = C + pid_batch * stride_cb
    c_ptrs = C_batch_ptr + (offs_m[:, None] * stride_cm + offs_n[None, :] * stride_cn)
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
    Batches, M, K = A.shape
    _, K_B, N = B.shape

    assert K == K_B, "Inner dimensions of A and B must match"
    assert Batches == B.shape[0], "Batch dimensions of A and B must match"

    C = torch.empty((Batches, M, N), device=A.device, dtype=torch.float16)

    grid = lambda META: (
        triton.cdiv(M, META['BLOCK_M']),
        triton.cdiv(N, META['BLOCK_N']),
        Batches
    )

    _bmm_kernel[grid](
        A, B, C,
        Batches, M, N, K,
        A.stride(0), A.stride(1), A.stride(2),
        B.stride(0), B.stride(1), B.stride(2),
        C.stride(0), C.stride(1), C.stride(2),
    )

    return C

class Solution:
    def solve(self, spec_path: str = None) -> dict:
        """
        Returns a dict with either:
        - {"code": "python_code_string"}
        - {"program_path": "path/to/kernel.py"}
        """
        current_file = Path(__file__).resolve()
        return {"code": current_file.read_text(encoding="utf-8")}
