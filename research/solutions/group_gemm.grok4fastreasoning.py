import torch
import triton
import triton.language as tl
from pathlib import Path
from typing import Dict, Optional

@triton.autotune(
    configs=[
        triton.Config({'BLOCK_M': 64, 'BLOCK_N': 64, 'BLOCK_K': 64}, num_stages=4, num_warps=4),
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 64, 'BLOCK_K': 64}, num_stages=4, num_warps=8),
        triton.Config({'BLOCK_M': 64, 'BLOCK_N': 128, 'BLOCK_K': 64}, num_stages=4, num_warps=8),
        triton.Config({'BLOCK_M': 64, 'BLOCK_N': 64, 'BLOCK_K': 128}, num_stages=3, num_warps=4),
    ],
    key=['M', 'N', 'K']
)
@triton.jit
def _bmm_kernel(
    A_PTR,
    B_PTR,
    C_PTR,
    stride_ab,
    stride_am,
    stride_ak,
    stride_bb,
    stride_bk,
    stride_bn,
    stride_cb,
    stride_cm,
    stride_cn,
    M,
    N,
    K,
    BLOCK_M: tl.constexpr,
    BLOCK_N: tl.constexpr,
    BLOCK_K: tl.constexpr,
):
    batch_id = tl.program_id(2)
    A_batch_ptr = A_PTR + batch_id * stride_ab * tl.sizeof(tl.float16)
    B_batch_ptr = B_PTR + batch_id * stride_bb * tl.sizeof(tl.float16)
    C_batch_ptr = C_PTR + batch_id * stride_cb * tl.sizeof(tl.float16)

    pid_m = tl.program_id(0)
    pid_n = tl.program_id(1)
    offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
    offs_n = pid_n * BLOCK_N + tl.arange(0, BLOCK_N)
    offs_k = tl.arange(0, BLOCK_K)

    acc = tl.zeros((BLOCK_M, BLOCK_N), dtype=tl.float32)

    k0 = 0
    while k0 < K:
        k_idxs = k0 + offs_k
        a_ptrs = A_batch_ptr + (offs_m[:, None] * stride_am + k_idxs[None, :] * stride_ak) * tl.sizeof(tl.float16)
        b_ptrs = B_batch_ptr + (k_idxs[:, None] * stride_bk + offs_n[None, :] * stride_bn) * tl.sizeof(tl.float16)

        a_mask = (offs_m[:, None] < M) & (k_idxs[None, :] < K)
        b_mask = (k_idxs[:, None] < K) & (offs_n[None, :] < N)

        a = tl.load(a_ptrs, mask=a_mask, other=0.0).to(tl.float32)
        b = tl.load(b_ptrs, mask=b_mask, other=0.0).to(tl.float32)
        acc += tl.dot(a, b)
        k0 += BLOCK_K

    c_ptrs = C_batch_ptr + (offs_m[:, None] * stride_cm + offs_n[None, :] * stride_cn) * tl.sizeof(tl.float16)
    c_mask = (offs_m[:, None] < M) & (offs_n[None, :] < N)
    tl.store(c_ptrs, acc.to(tl.float16), mask=c_mask)


def bmm(A: torch.Tensor, B: torch.Tensor) -> torch.Tensor:
    B_ = A.shape[0]
    M = A.shape[1]
    K = A.shape[2]
    N = B.shape[2]
    C = torch.empty((B_, M, N), dtype=torch.float16, device=A.device)

    stride_ab = A.stride(0)
    stride_am = A.stride(1)
    stride_ak = A.stride(2)

    stride_bb = B.stride(0)
    stride_bk = B.stride(1)
    stride_bn = B.stride(2)

    stride_cb = M * N
    stride_cm = N
    stride_cn = 1

    grid = lambda meta: (triton.cdiv(M, meta['BLOCK_M']), triton.cdiv(N, meta['BLOCK_N']), B_)
    _bmm_kernel[grid](
        A_ptr=A.data_ptr(),
        B_ptr=B.data_ptr(),
        C_ptr=C.data_ptr(),
        stride_ab=stride_ab,
        stride_am=stride_am,
        stride_ak=stride_ak,
        stride_bb=stride_bb,
        stride_bk=stride_bk,
        stride_bn=stride_bn,
        stride_cb=stride_cb,
        stride_cm=stride_cm,
        stride_cn=stride_cn,
        M=M,
        N=N,
        K=K,
    )
    return C


class Solution:
    def solve(self, spec_path: str = None) -> Dict[str, str]:
        if spec_path is not None:
            return {"code": Path(spec_path).read_text(encoding="utf-8")}
        current_file = Path(__file__).resolve()
        return {"code": current_file.read_text(encoding="utf-8")}
