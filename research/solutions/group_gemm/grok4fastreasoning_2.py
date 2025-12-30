import torch
import triton
import triton.language as tl
from pathlib import Path

@triton.autotune(
    configs=[
        triton.Config({'BLOCK_M': 64, 'BLOCK_N': 64, 'BLOCK_K': 64}, num_stages=1, num_warps=8),
        triton.Config({'BLOCK_M': 64, 'BLOCK_N': 64, 'BLOCK_K': 32}, num_stages=2, num_warps=4),
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 64, 'BLOCK_K': 64}, num_stages=1, num_warps=8),
        triton.Config({'BLOCK_M': 64, 'BLOCK_N': 128, 'BLOCK_K': 64}, num_stages=1, num_warps=8),
    ],
    key=["M", "N", "K"],
)
@triton.jit
def _bmm_kernel(
    A_ptr,
    B_ptr,
    C_ptr,
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
    batch_id = tl.program_id(0)
    pid_m = tl.program_id(1)
    pid_n = tl.program_id(2)

    m_start = pid_m * BLOCK_M
    n_start = pid_n * BLOCK_N
    offs_m = m_start + tl.arange(0, BLOCK_M)
    offs_n = n_start + tl.arange(0, BLOCK_N)
    offs_k = tl.arange(0, BLOCK_K)

    acc = tl.zeros((BLOCK_M, BLOCK_N), dtype=tl.float32)

    a_batch_ptr = A_ptr + batch_id * stride_ab
    b_batch_ptr = B_ptr + batch_id * stride_bb
    c_batch_ptr = C_ptr + batch_id * stride_cb

    k0 = 0
    while k0 < K:
        k_idxs = k0 + offs_k
        a_ptrs = a_batch_ptr + (offs_m[:, None] * stride_am) + (k_idxs[None, :] * stride_ak)
        b_ptrs = b_batch_ptr + (k_idxs[:, None] * stride_bk) + (offs_n[None, :] * stride_bn)

        a_mask = (offs_m[:, None] < M) & (k_idxs[None, :] < K)
        b_mask = (k_idxs[:, None] < K) & (offs_n[None, :] < N)

        a = tl.load(a_ptrs, mask=a_mask, other=0.0).to(tl.float32)
        b = tl.load(b_ptrs, mask=b_mask, other=0.0).to(tl.float32)

        acc += tl.dot(a, b)
        k0 += BLOCK_K

    c_ptrs = c_batch_ptr + (offs_m[:, None] * stride_cm) + (offs_n[None, :] * stride_cn)
    c_mask = (offs_m[:, None] < M) & (offs_n[None, :] < N)
    tl.store(c_ptrs, acc.to(tl.float16), mask=c_mask)

def bmm(A: torch.Tensor, B: torch.Tensor) -> torch.Tensor:
    B_batch, M, K1 = A.shape
    K2, N = B.shape[-2:]
    assert K1 == K2
    assert A.shape[0] == B.shape[0] == B_batch
    K = K1

    C = torch.empty((B_batch, M, N), dtype=torch.float16, device=A.device, layout=A.layout)

    a_dtype_bytes = A.element_size()
    b_dtype_bytes = B.element_size()
    c_dtype_bytes = C.element_size()

    stride_ab = A.stride(0) * a_dtype_bytes
    stride_am = A.stride(1) * a_dtype_bytes
    stride_ak = A.stride(2) * a_dtype_bytes

    stride_bb = B.stride(0) * b_dtype_bytes
    stride_bk = B.stride(1) * b_dtype_bytes
    stride_bn = B.stride(2) * b_dtype_bytes

    stride_cb = C.stride(0) * c_dtype_bytes
    stride_cm = C.stride(1) * c_dtype_bytes
    stride_cn = C.stride(2) * c_dtype_bytes

    def grid(meta):
        return (
            B_batch,
            triton.cdiv(M, meta['BLOCK_M']),
            triton.cdiv(N, meta['BLOCK_N']),
        )

    _bmm_kernel[grid](
        A,
        B,
        C,
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
    )
    return C

class Solution:
    def solve(self, spec_path: str = None) -> dict:
        current_file = Path(__file__).resolve()
        return {"code": current_file.read_text(encoding="utf-8")}