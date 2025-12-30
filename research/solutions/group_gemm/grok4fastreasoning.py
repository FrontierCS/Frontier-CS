import torch
import triton
import triton.language as tl
from pathlib import Path
from typing import Optional, Dict

def bmm(A: torch.Tensor, B: torch.Tensor) -> torch.Tensor:
    """
    Batched matrix multiplication.
    
    Args:
        A: Input tensor of shape (B, M, K) - batch of M×K matrices
        B: Input tensor of shape (B, K, N) - batch of K×N matrices
    
    Returns:
        Output tensor of shape (B, M, N) - batch of M×N result matrices
    """
    assert A.shape[0] == B.shape[0]
    assert A.shape[2] == B.shape[1]
    B_batch, M, K = A.shape
    _, _, N = B.shape
    C = torch.empty((B_batch, M, N), dtype=torch.float16, device=A.device, memory_format=torch.contiguous_format)

    # Compute strides in bytes
    itemsize_a = A.element_size()
    itemsize_b = B.element_size()
    itemsize_c = C.element_size()
    stride_a_b = A.stride(0) * itemsize_a
    stride_a_m = A.stride(1) * itemsize_a
    stride_a_k = A.stride(2) * itemsize_a
    stride_b_b = B.stride(0) * itemsize_b
    stride_b_k = B.stride(1) * itemsize_b
    stride_b_n = B.stride(2) * itemsize_b
    stride_c_b = C.stride(0) * itemsize_c
    stride_c_m = C.stride(1) * itemsize_c
    stride_c_n = C.stride(2) * itemsize_c

    configs = [
        triton.Config({'BLOCK_M': 64, 'BLOCK_N': 64, 'BLOCK_K': 64}, num_warps=4, num_stages=1),
        triton.Config({'BLOCK_M': 64, 'BLOCK_N': 64, 'BLOCK_K': 32}, num_warps=4, num_stages=2),
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 128, 'BLOCK_K': 64}, num_warps=8, num_stages=3),
        triton.Config({'BLOCK_M': 32, 'BLOCK_N': 32, 'BLOCK_K': 16}, num_warps=2, num_stages=1),
    ]

    @triton.autotune(configs=configs, key=["M", "N", "K"])
    @triton.jit
    def bmm_kernel(
        A_PTR,
        B_PTR,
        C_PTR,
        stride_a_m: tl.int32,
        stride_a_k: tl.int32,
        stride_a_b: tl.int32,
        stride_b_k: tl.int32,
        stride_b_n: tl.int32,
        stride_b_b: tl.int32,
        stride_c_m: tl.int32,
        stride_c_n: tl.int32,
        stride_c_b: tl.int32,
        M: tl.int32,
        N: tl.int32,
        K: tl.int32,
        BLOCK_M: tl.constexpr,
        BLOCK_N: tl.constexpr,
        BLOCK_K: tl.constexpr,
        num_warps: tl.constexpr,
        num_stages: tl.constexpr,
    ):
        batch_idx = tl.program_id(0)
        A_batch_ptr = A_PTR + batch_idx * stride_a_b
        B_batch_ptr = B_PTR + batch_idx * stride_b_b
        C_batch_ptr = C_PTR + batch_idx * stride_c_b

        pid_m = tl.program_id(1)
        pid_n = tl.program_id(2)
        offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
        offs_n = pid_n * BLOCK_N + tl.arange(0, BLOCK_N)

        acc = tl.zeros((BLOCK_M, BLOCK_N), dtype=tl.float32)
        lo = 0
        while lo < K:
            offs_k = tl.arange(0, BLOCK_K)
            k_idx = lo + offs_k
            a_ptrs = A_batch_ptr + (offs_m[:, None] * stride_a_m) + (k_idx[None, :] * stride_a_k)
            b_ptrs = B_batch_ptr + (k_idx[:, None] * stride_b_k) + (offs_n[None, :] * stride_b_n)
            a_mask = (offs_m[:, None] < M) & (k_idx[None, :] < K)
            b_mask = (k_idx[:, None] < K) & (offs_n[None, :] < N)
            a = tl.load(a_ptrs, mask=a_mask, other=0.0).to(tl.float32)
            b = tl.load(b_ptrs, mask=b_mask, other=0.0).to(tl.float32)
            acc += tl.dot(a, b)
            lo += BLOCK_K

        c_ptrs = C_batch_ptr + (offs_m[:, None] * stride_c_m) + (offs_n[None, :] * stride_c_n)
        c_mask = (offs_m[:, None] < M) & (offs_n[None, :] < N)
        tl.store(c_ptrs, acc.to(tl.float16), mask=c_mask)

    grid = lambda meta: (B_batch, triton.cdiv(M, meta["BLOCK_M"]), triton.cdiv(N, meta["BLOCK_N"]))
    bmm_kernel[grid](
        A, B, C,
        tl.int32(stride_a_m), tl.int32(stride_a_k), tl.int32(stride_a_b),
        tl.int32(stride_b_k), tl.int32(stride_b_n), tl.int32(stride_b_b),
        tl.int32(stride_c_m), tl.int32(stride_c_n), tl.int32(stride_c_b),
        tl.int32(M), tl.int32(N), tl.int32(K),
    )
    return C

class Solution:
    def solve(self, spec_path: Optional[str] = None) -> Dict[str, str]:
        current_file = Path(__file__).resolve()
        return {"code": current_file.read_text(encoding="utf-8")}