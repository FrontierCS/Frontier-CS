import torch
import triton
import triton.language as tl
from pathlib import Path
from typing import Dict, Optional

configs = [
    triton.Config({'BLOCK_M': 64, 'BLOCK_N': 64, 'BLOCK_K': 64}, num_warps=4, num_stages=2),
    triton.Config({'BLOCK_M': 128, 'BLOCK_N': 128, 'BLOCK_K': 64}, num_warps=8, num_stages=4),
    triton.Config({'BLOCK_M': 64, 'BLOCK_N': 128, 'BLOCK_K': 32}, num_warps=4, num_stages=3),
    triton.Config({'BLOCK_M': 32, 'BLOCK_N': 32, 'BLOCK_K': 32}, num_warps=4, num_stages=2),
    triton.Config({'BLOCK_M': 16, 'BLOCK_N': 16, 'BLOCK_K': 16}, num_warps=4, num_stages=1),
]

@triton.autotune(configs=configs, key=['M', 'N', 'K'])
@triton.jit
def _bmm_kernel(
    A_ptr,
    B_ptr,
    C_ptr,
    M,
    N,
    K,
    stride_am,
    stride_ak,
    stride_bk,
    stride_bn,
    stride_cm,
    stride_cn,
    batch_stride_a,
    batch_stride_b,
    batch_stride_c,
    BLOCK_M: tl.constexpr,
    BLOCK_N: tl.constexpr,
    BLOCK_K: tl.constexpr,
    num_warps: tl.constexpr,
    num_stages: tl.constexpr,
):
    pid_batch = tl.program_id(0)
    pid_m = tl.program_id(1)
    pid_n = tl.program_id(2)
    offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
    offs_n = pid_n * BLOCK_N + tl.arange(0, BLOCK_N)
    acc = tl.zeros((BLOCK_M, BLOCK_N), dtype=tl.float32)
    k = 0
    while k < K:
        offs_k = tl.arange(0, BLOCK_K)
        k_idx = k + offs_k
        a_ptrs = A_ptr + pid_batch * batch_stride_a + offs_m[:, None] * stride_am + k_idx[None, :] * stride_ak
        b_ptrs = B_ptr + pid_batch * batch_stride_b + k_idx[:, None] * stride_bk + offs_n[None, :] * stride_bn
        a_mask = (offs_m[:, None] < M) & (k_idx[None, :] < K)
        b_mask = (k_idx[:, None] < K) & (offs_n[None, :] < N)
        a = tl.load(a_ptrs, mask=a_mask, other=0.0).to(tl.float32)
        b = tl.load(b_ptrs, mask=b_mask, other=0.0).to(tl.float32)
        acc += tl.dot(a, b)
        k += BLOCK_K
    c_ptrs = C_ptr + pid_batch * batch_stride_c + offs_m[:, None] * stride_cm + offs_n[None, :] * stride_cn
    c_mask = (offs_m[:, None] < M) & (offs_n[None, :] < N)
    tl.store(c_ptrs, acc.to(tl.float16), mask=c_mask)

def bmm(A: torch.Tensor, B: torch.Tensor) -> torch.Tensor:
    BATCH, M, K1 = A.shape
    B_, K2, N = B.shape
    assert BATCH == B_ and K1 == K2
    K = K1
    C = torch.empty((BATCH, M, N), dtype=torch.float16, device=A.device)
    def grid_fn(config):
        return (
            BATCH,
            triton.cdiv(M, config['BLOCK_M']),
            triton.cdiv(N, config['BLOCK_N']),
        )
    _bmm_kernel[grid_fn](
        A.data_ptr(),
        B.data_ptr(),
        C.data_ptr(),
        M,
        N,
        K,
        A.stride(1),
        A.stride(2),
        B.stride(1),
        B.stride(2),
        C.stride(1),
        C.stride(2),
        A.stride(0),
        B.stride(0),
        C.stride(0),
    )
    return C

class Solution:
    def solve(self, spec_path: Optional[str] = None) -> Dict[str, str]:
        current_file = Path(__file__).resolve()
        return {"code": current_file.read_text(encoding="utf-8")}
