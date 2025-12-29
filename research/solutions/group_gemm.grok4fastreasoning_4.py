import torch
import triton
import triton.language as tl
from pathlib import Path
from typing import Dict

@triton.autotune(
    configs=[
        triton.Config({'BLOCK_M': 64, 'BLOCK_N': 64, 'BLOCK_K': 64, 'num_warps': 4, 'num_stages': 2}),
        triton.Config({'BLOCK_M': 64, 'BLOCK_N': 64, 'BLOCK_K': 64, 'num_warps': 8, 'num_stages': 1}),
        triton.Config({'BLOCK_M': 64, 'BLOCK_N': 64, 'BLOCK_K': 64, 'num_warps': 4, 'num_stages': 4}),
        triton.Config({'BLOCK_M': 64, 'BLOCK_N': 64, 'BLOCK_K': 64, 'num_warps': 8, 'num_stages': 2}),
    ],
    key=["M", "N", "K"],
)
@triton.jit
def batched_matmul_kernel(
    A_PTR, B_PTR, C_PTR,
    stride_ab, stride_am, stride_ak,
    stride_bb, stride_bk, stride_bn,
    stride_cb, stride_cm, stride_cn,
    BATCH, M, N, K,
    BLOCK_M: tl.constexpr,
    BLOCK_N: tl.constexpr,
    BLOCK_K: tl.constexpr,
):
    pid_batch = tl.program_id(0)
    pid_m = tl.program_id(1)
    pid_n = tl.program_id(2)
    offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
    offs_n = pid_n * BLOCK_N + tl.arange(0, BLOCK_N)
    offs_k = tl.arange(0, BLOCK_K)
    acc = tl.zeros((BLOCK_M, BLOCK_N), dtype=tl.float32)
    A_batch_ptr = A_PTR + pid_batch * stride_ab
    B_batch_ptr = B_PTR + pid_batch * stride_bb
    C_batch_ptr = C_PTR + pid_batch * stride_cb
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
    c_mask = (offs_m[:, None] < M) & (offs_n[None, :] < N)
    C_ptrs = C_batch_ptr + (offs_m[:, None] * stride_cm) + (offs_n[None, :] * stride_cn)
    tl.store(C_ptrs, acc.to(tl.float16), mask=c_mask)

def bmm(A: torch.Tensor, B: torch.Tensor) -> torch.Tensor:
    BATCH, M, K = A.shape
    assert A.shape[0] == B.shape[0] and A.shape[2] == B.shape[1]
    N = B.shape[2]
    C = torch.empty((BATCH, M, N), dtype=torch.float16, device=A.device)
    stride_ab, stride_am, stride_ak = A.stride()
    stride_bb, stride_bk, stride_bn = B.stride()
    stride_cb, stride_cm, stride_cn = C.stride()
    BLOCK_M = 64
    BLOCK_N = 64
    BLOCK_K = 64
    grid = (
        BATCH,
        (M + BLOCK_M - 1) // BLOCK_M,
        (N + BLOCK_N - 1) // BLOCK_N
    )
    batched_matmul_kernel[grid](
        A.data_ptr(),
        B.data_ptr(),
        C.data_ptr(),
        stride_ab, stride_am, stride_ak,
        stride_bb, stride_bk, stride_bn,
        stride_cb, stride_cm, stride_cn,
        BATCH, M, N, K
    )
    return C

class Solution:
    def solve(self, spec_path: str = None) -> Dict[str, str]:
        current_file = Path(__file__).resolve()
        return {"code": current_file.read_text(encoding="utf-8")}