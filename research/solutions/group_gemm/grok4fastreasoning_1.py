import torch
import triton
import triton.language as tl
from pathlib import Path
from typing import Dict, Optional

@triton.autotune(
    configs=[
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 64, 'BLOCK_K': 64}, num_warps=4, num_stages=4),
        triton.Config({'BLOCK_M': 64, 'BLOCK_N': 128, 'BLOCK_K': 64}, num_warps=4, num_stages=4),
        triton.Config({'BLOCK_M': 64, 'BLOCK_N': 64, 'BLOCK_K': 128}, num_warps=4, num_stages=4),
        triton.Config({'BLOCK_M': 64, 'BLOCK_N': 64, 'BLOCK_K': 64}, num_warps=8, num_stages=5),
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 128, 'BLOCK_K': 64}, num_warps=8, num_stages=3),
    ],
    key=['M', 'N', 'K'],
)
@triton.jit
def _bmm_kernel(
    A_PTR,
    B_PTR,
    C_PTR,
    STRIDE_BATCH_A,
    STRIDE_AM,
    STRIDE_AK,
    STRIDE_BATCH_B,
    STRIDE_BK,
    STRIDE_BN,
    STRIDE_BATCH_C,
    STRIDE_CM,
    STRIDE_CN,
    M,
    N,
    K,
    BB,
    BLOCK_M: tl.constexpr,
    BLOCK_N: tl.constexpr,
    BLOCK_K: tl.constexpr,
):
    pid_batch = tl.program_id(0)
    pid_M = tl.program_id(1)
    pid_N = tl.program_id(2)
    offs_m = pid_M * BLOCK_M + tl.arange(0, BLOCK_M)
    offs_n = pid_N * BLOCK_N + tl.arange(0, BLOCK_N)
    offs_k = tl.arange(0, BLOCK_K)
    acc = tl.zeros((BLOCK_M, BLOCK_N), dtype=tl.float32)
    A_batch_ptr = A_PTR + pid_batch * STRIDE_BATCH_A
    B_batch_ptr = B_PTR + pid_batch * STRIDE_BATCH_B
    C_batch_ptr = C_PTR + pid_batch * STRIDE_BATCH_C
    k0 = 0
    while k0 < K:
        k_idxs = k0 + offs_k
        A_ptrs = A_batch_ptr + (offs_m[:, None] * STRIDE_AM) + (k_idxs[None, :] * STRIDE_AK)
        B_ptrs = B_batch_ptr + (k_idxs[:, None] * STRIDE_BK) + (offs_n[None, :] * STRIDE_BN)
        a_mask = (offs_m[:, None] < M) & (k_idxs[None, :] < K)
        b_mask = (k_idxs[:, None] < K) & (offs_n[None, :] < N)
        a = tl.load(A_ptrs, mask=a_mask, other=0.0).to(tl.float32)
        b = tl.load(B_ptrs, mask=b_mask, other=0.0).to(tl.float32)
        acc += tl.dot(a, b)
        k0 += BLOCK_K
    c_mask = (offs_m[:, None] < M) & (offs_n[None, :] < N)
    c_ptrs = C_batch_ptr + (offs_m[:, None] * STRIDE_CM) + (offs_n[None, :] * STRIDE_CN)
    tl.store(c_ptrs, acc.to(tl.float16), mask=c_mask)

def bmm(A: torch.Tensor, B: torch.Tensor) -> torch.Tensor:
    BATCH, M, K_A = A.shape
    _, K_B, N = B.shape
    assert K_A == K_B
    K = K_A
    C = torch.empty((BATCH, M, N), dtype=torch.float16, device=A.device)
    STRIDE_BATCH_A = A.stride(0)
    STRIDE_AM = A.stride(1)
    STRIDE_AK = A.stride(2)
    STRIDE_BATCH_B = B.stride(0)
    STRIDE_BK = B.stride(1)
    STRIDE_BN = B.stride(2)
    STRIDE_BATCH_C = C.stride(0)
    STRIDE_CM = C.stride(1)
    STRIDE_CN = C.stride(2)
    grid = lambda meta: (
        BATCH,
        (M + meta['BLOCK_M'] - 1) // meta['BLOCK_M'],
        (N + meta['BLOCK_N'] - 1) // meta['BLOCK_N']
    )
    _bmm_kernel[grid](
        A,
        B,
        C,
        STRIDE_BATCH_A,
        STRIDE_AM,
        STRIDE_AK,
        STRIDE_BATCH_B,
        STRIDE_BK,
        STRIDE_BN,
        STRIDE_BATCH_C,
        STRIDE_CM,
        STRIDE_CN,
        M,
        N,
        K,
        BATCH,
    )
    return C

class Solution:
    def solve(self, spec_path: str = None) -> Dict[str, str]:
        current_file = Path(__file__).resolve()
        return {"code": current_file.read_text(encoding="utf-8")}