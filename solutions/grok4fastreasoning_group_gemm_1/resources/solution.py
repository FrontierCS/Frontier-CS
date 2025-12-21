import torch
import triton
import triton.language as tl
from pathlib import Path
from typing import Optional

def cdiv(x: int, y: int) -> int:
    return (x + y - 1) // y

configs = [
    triton.Config({'BLOCK_M': 64, 'BLOCK_N': 64, 'BLOCK_K': 64, 'num_warps': 4, 'num_stages': 4}),
    triton.Config({'BLOCK_M': 128, 'BLOCK_N': 64, 'BLOCK_K': 64, 'num_warps': 8, 'num_stages': 4}),
    triton.Config({'BLOCK_M': 64, 'BLOCK_N': 128, 'BLOCK_K': 64, 'num_warps': 8, 'num_stages': 4}),
    triton.Config({'BLOCK_M': 128, 'BLOCK_N': 128, 'BLOCK_K': 64, 'num_warps': 8, 'num_stages': 4}),
    triton.Config({'BLOCK_M': 64, 'BLOCK_N': 64, 'BLOCK_K': 32, 'num_warps': 4, 'num_stages': 3}),
]

@triton.autotune(
    configs=configs,
    key=["M", "N", "K"],
)
@triton.jit
def kernel(
    A_ptr, B_ptr, C_ptr,
    stride_ab, stride_am, stride_ak,
    stride_bb, stride_bk, stride_bn,
    stride_cb, stride_cm, stride_cn,
    BATCH, M, N, K,
    BLOCK_M: tl.constexpr,
    BLOCK_N: tl.constexpr,
    BLOCK_K: tl.constexpr,
):
    pid_b, pid_m, pid_n = tl.program_id(0), tl.program_id(1), tl.program_id(2)
    if pid_b >= BATCH:
        return

    offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
    offs_n = pid_n * BLOCK_N + tl.arange(0, BLOCK_N)
    acc = tl.zeros((BLOCK_M, BLOCK_N), dtype=tl.float32)

    k0 = 0
    while k0 < K:
        offs_k = tl.arange(0, BLOCK_K)
        k_idxs = k0 + offs_k

        a_batch_ptr = A_ptr + pid_b * stride_ab
        a_ptrs = a_batch_ptr + offs_m[:, None] * stride_am + k_idxs[None, :] * stride_ak
        a_mask = (offs_m[:, None] < M) & (k_idxs[None, :] < K)
        a = tl.load(a_ptrs, mask=a_mask, other=0.0).to(tl.float32)

        b_batch_ptr = B_ptr + pid_b * stride_bb
        b_ptrs = b_batch_ptr + k_idxs[:, None] * stride_bk + offs_n[None, :] * stride_bn
        b_mask = (k_idxs[:, None] < K) & (offs_n[None, :] < N)
        b = tl.load(b_ptrs, mask=b_mask, other=0.0).to(tl.float32)

        acc += tl.dot(a, b)
        k0 += BLOCK_K

    c_batch_ptr = C_ptr + pid_b * stride_cb
    c_ptrs = c_batch_ptr + offs_m[:, None] * stride_cm + offs_n[None, :] * stride_cn
    c_mask = (offs_m[:, None] < M) & (offs_n[None, :] < N)
    tl.store(c_ptrs, acc.to(tl.float16), mask=c_mask)


def bmm(A: torch.Tensor, B: torch.Tensor) -> torch.Tensor:
    B_batch, M, K = A.shape
    _, K_b, N = B.shape
    assert K_b == K and B_batch == B.shape[0]
    C = torch.empty((B_batch, M, N), dtype=torch.float16, device=A.device)

    stride_ab = A.stride(0)
    stride_am = A.stride(1)
    stride_ak = A.stride(2)
    stride_bb = B.stride(0)
    stride_bk = B.stride(1)
    stride_bn = B.stride(2)
    stride_cb = C.stride(0)
    stride_cm = C.stride(1)
    stride_cn = C.stride(2)

    def grid(meta):
        return (
            B_batch,
            cdiv(M, meta['BLOCK_M']),
            cdiv(N, meta['BLOCK_N']),
        )

    kernel[grid](
        A.data_ptr(), B.data_ptr(), C.data_ptr(),
        stride_ab, stride_am, stride_ak,
        stride_bb, stride_bk, stride_bn,
        stride_cb, stride_cm, stride_cn,
        B_batch, M, N, K,
    )
    return C


class Solution:
    def solve(self, spec_path: str = None) -> dict:
        current_file = Path(__file__).resolve()
        return {"code": current_file.read_text(encoding="utf-8")}
