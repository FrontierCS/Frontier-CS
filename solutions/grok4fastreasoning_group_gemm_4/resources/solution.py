import torch
import triton
import triton.language as tl
from pathlib import Path
from typing import Dict, Optional

@triton.autotune(
    configs=[
        triton.Config({'BLOCK_M': 64, 'BLOCK_N': 64, 'BLOCK_K': 64}),
        triton.Config({'BLOCK_M': 64, 'BLOCK_N': 64, 'BLOCK_K': 32}),
        triton.Config({'BLOCK_M': 32, 'BLOCK_N': 32, 'BLOCK_K': 32}),
    ],
    key=['M', 'N', 'K'],
)
@triton.jit
def bmm_kernel(
    A_PTR,
    B_PTR,
    C_PTR,
    STRIDE_BATCH_A: tl.int32,
    STRIDE_M_A: tl.int32,
    STRIDE_K_A: tl.int32,
    STRIDE_BATCH_B: tl.int32,
    STRIDE_K_B: tl.int32,
    STRIDE_N_B: tl.int32,
    STRIDE_BATCH_C: tl.int32,
    STRIDE_M_C: tl.int32,
    STRIDE_N_C: tl.int32,
    M: tl.int32,
    N: tl.int32,
    K: tl.int32,
    BLOCK_M: tl.constexpr,
    BLOCK_N: tl.constexpr,
    BLOCK_K: tl.constexpr,
):
    pid = tl.program_id(0)
    num_m = (M + BLOCK_M - 1) // BLOCK_M
    num_n = (N + BLOCK_N - 1) // BLOCK_N
    num_tiles = num_m * num_n
    pid_batch = pid // num_tiles
    pid_m = (pid // num_n) % num_m
    pid_n = pid % num_n

    offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
    offs_n = pid_n * BLOCK_N + tl.arange(0, BLOCK_N)

    A_batch_ptr = A_PTR + pid_batch * STRIDE_BATCH_A
    B_batch_ptr = B_PTR + pid_batch * STRIDE_BATCH_B
    C_batch_ptr = C_PTR + pid_batch * STRIDE_BATCH_C

    acc = tl.zeros((BLOCK_M, BLOCK_N), dtype=tl.float32)

    k0 = 0
    while k0 < K:
        offs_k = tl.arange(0, BLOCK_K)
        k_idxs = k0 + offs_k

        a_ptrs = A_batch_ptr + (offs_m[:, None] * STRIDE_M_A) + (k_idxs[None, :] * STRIDE_K_A)
        b_ptrs = B_batch_ptr + (k_idxs[:, None] * STRIDE_K_B) + (offs_n[None, :] * STRIDE_N_B)

        a_mask = (offs_m[:, None] < M) & (k_idxs[None, :] < K)
        b_mask = (k_idxs[:, None] < K) & (offs_n[None, :] < N)

        a = tl.load(a_ptrs, mask=a_mask, other=0.0, dtype=tl.float16).to(tl.float32)
        b = tl.load(b_ptrs, mask=b_mask, other=0.0, dtype=tl.float16).to(tl.float32)

        acc += tl.dot(a, b)
        k0 += BLOCK_K

    c_ptrs = C_batch_ptr + (offs_m[:, None] * STRIDE_M_C) + (offs_n[None, :] * STRIDE_N_C)
    c_mask = (offs_m[:, None] < M) & (offs_n[None, :] < N)
    tl.store(c_ptrs, acc.to(tl.float16), mask=c_mask)


def bmm(A: torch.Tensor, B: torch.Tensor) -> torch.Tensor:
    BATCH, M, K_A = A.shape
    B_B, K_B, N = B.shape
    assert BATCH == B_B and K_A == K_B
    K = K_A

    C = torch.empty((BATCH, M, N), dtype=torch.float16, device=A.device)

    size_a = A.element_size()
    stride_batch_a = A.stride(0) * size_a
    stride_m_a = A.stride(1) * size_a
    stride_k_a = A.stride(2) * size_a

    size_b = B.element_size()
    stride_batch_b = B.stride(0) * size_b
    stride_k_b = B.stride(1) * size_b
    stride_n_b = B.stride(2) * size_b

    size_c = C.element_size()
    stride_batch_c = C.stride(0) * size_c
    stride_m_c = C.stride(1) * size_c
    stride_n_c = C.stride(2) * size_c

    def grid(meta):
        return (BATCH * triton.cdiv(M, meta["BLOCK_M"]) * triton.cdiv(N, meta["BLOCK_N"]), )

    bmm_kernel[grid](
        A, B, C,
        stride_batch_a, stride_m_a, stride_k_a,
        stride_batch_b, stride_k_b, stride_n_b,
        stride_batch_c, stride_m_c, stride_n_c,
        M, N, K,
    )
    return C


class Solution:
    def solve(self, spec_path: str = None) -> Dict[str, str]:
        current_file = Path(__file__).resolve()
        return {"code": current_file.read_text(encoding="utf-8")}
