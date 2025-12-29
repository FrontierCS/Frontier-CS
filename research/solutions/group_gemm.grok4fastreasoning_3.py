import torch
import triton
import triton.language as tl
from typing import Optional, Dict
from pathlib import Path

configs = [
    triton.Config({'BLOCK_M': 64, 'BLOCK_N': 64, 'BLOCK_K': 64}, num_warps=8, num_stages=3),
    triton.Config({'BLOCK_M': 128, 'BLOCK_N': 128, 'BLOCK_K': 64}, num_warps=8, num_stages=3),
    triton.Config({'BLOCK_M': 64, 'BLOCK_N': 128, 'BLOCK_K': 64}, num_warps=8, num_stages=3),
]

@triton.autotune(configs=configs, key=["M", "N", "K"])
@triton.jit
def _bmm_kernel(
    A_ptr, B_ptr, C_ptr,
    stride_ab, stride_am, stride_ak,
    stride_bb, stride_bk, stride_bn,
    stride_cb, stride_cm, stride_cn,
    B, M, N, K,
    BLOCK_M: tl.constexpr,
    BLOCK_N: tl.constexpr,
    BLOCK_K: tl.constexpr
):
    pid_batch = tl.program_id(0)
    pid_m = tl.program_id(1)
    pid_n = tl.program_id(2)
    block_start_m = pid_m * BLOCK_M
    block_start_n = pid_n * BLOCK_N
    offs_m = block_start_m + tl.arange(0, BLOCK_M)
    offs_n = block_start_n + tl.arange(0, BLOCK_N)
    offs_k = tl.arange(0, BLOCK_K)
    acc = tl.zeros((BLOCK_M, BLOCK_N), dtype=tl.float32)
    A_batch_ptr = A_ptr + pid_batch * stride_ab
    B_batch_ptr = B_ptr + pid_batch * stride_bb
    C_batch_ptr = C_ptr + pid_batch * stride_cb
    k = 0
    while k < K:
        k_idxs = k + offs_k
        A_ptrs = A_batch_ptr + offs_m[:, None] * stride_am + k_idxs[None, :] * stride_ak
        B_ptrs = B_batch_ptr + k_idxs[:, None] * stride_bk + offs_n[None, :] * stride_bn
        a_mask = (offs_m[:, None] < M) & (k_idxs[None, :] < K)
        b_mask = (k_idxs[:, None] < K) & (offs_n[None, :] < N)
        a = tl.load(A_ptrs, mask=a_mask, other=0.0).to(tl.float32)
        b = tl.load(B_ptrs, mask=b_mask, other=0.0).to(tl.float32)
        acc += tl.dot(a, b)
        k += BLOCK_K
    c_ptrs = C_batch_ptr + offs_m[:, None] * stride_cm + offs_n[None, :] * stride_cn
    c_mask = (offs_m[:, None] < M) & (offs_n[None, :] < N)
    tl.store(c_ptrs, acc.to(tl.float16), mask=c_mask)

def bmm(A: torch.Tensor, B: torch.Tensor) -> torch.Tensor:
    B_, M, K = A.shape
    B_b, K_b, N = B.shape
    assert B_ == B_b and K == K_b, "Incompatible shapes"
    if B_ == 0 or M == 0 or N == 0 or K == 0:
        return torch.empty((B_, M, N), dtype=torch.float16, device=A.device)
    C = torch.empty((B_, M, N), dtype=torch.float16, device=A.device)
    es_a = A.element_size()
    stride_ab = A.stride(0) * es_a
    stride_am = A.stride(1) * es_a
    stride_ak = A.stride(2) * es_a
    es_b = B.element_size()
    stride_bb = B.stride(0) * es_b
    stride_bk = B.stride(1) * es_b
    stride_bn = B.stride(2) * es_b
    es_c = C.element_size()
    stride_cb = C.stride(0) * es_c
    stride_cm = C.stride(1) * es_c
    stride_cn = C.stride(2) * es_c
    def spec():
        return {
            "A_ptr": A.data_ptr(),
            "B_ptr": B.data_ptr(),
            "C_ptr": C.data_ptr(),
            "stride_ab": stride_ab,
            "stride_am": stride_am,
            "stride_ak": stride_ak,
            "stride_bb": stride_bb,
            "stride_bk": stride_bk,
            "stride_bn": stride_bn,
            "stride_cb": stride_cb,
            "stride_cm": stride_cm,
            "stride_cn": stride_cn,
            "B": B_,
            "M": M,
            "N": N,
            "K": K,
        }
    grid = lambda meta: (
        B_,
        triton.cdiv(M, meta["BLOCK_M"]),
        triton.cdiv(N, meta["BLOCK_N"]),
    )
    _bmm_kernel[grid](**spec())
    return C

class Solution:
    def solve(self, spec_path: str = None) -> Dict[str, str]:
        current_file = Path(__file__).resolve()
        return {"code": current_file.read_text(encoding="utf-8")}