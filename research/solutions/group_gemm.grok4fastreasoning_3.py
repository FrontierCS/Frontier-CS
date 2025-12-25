import torch
import triton
import triton.language as tl
from typing import Dict, Optional
from pathlib import Path

def bmm(A: torch.Tensor, B: torch.Tensor) -> torch.Tensor:
    BATCH, M, K = A.shape
    _, _, N = B.shape
    assert B.shape[0] == BATCH and B.shape[1] == K
    if M == 0 or N == 0 or K == 0:
        return torch.empty((BATCH, M, N), dtype=torch.float16, device=A.device)
    C = torch.empty((BATCH, M, N), dtype=torch.float16, device=A.device)

    A_ptr = A.data_ptr()
    B_ptr = B.data_ptr()
    C_ptr = C.data_ptr()

    STRIDE_AM = A.stride(1) * A.element_size()
    STRIDE_AK = A.stride(2) * A.element_size()
    BATCH_STRIDE_A = A.stride(0) * A.element_size()

    STRIDE_BK = B.stride(1) * B.element_size()
    STRIDE_BN = B.stride(2) * B.element_size()
    BATCH_STRIDE_B = B.stride(0) * B.element_size()

    STRIDE_CM = C.stride(1) * C.element_size()
    STRIDE_CN = C.stride(2) * C.element_size()
    BATCH_STRIDE_C = C.stride(0) * C.element_size()

    configs = [
        triton.Config({'BLOCK_M': 64, 'BLOCK_N': 64, 'BLOCK_K': 64}, num_stages=4, num_warps=4),
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 128, 'BLOCK_K': 64}, num_stages=3, num_warps=8),
        triton.Config({'BLOCK_M': 64, 'BLOCK_N': 128, 'BLOCK_K': 64}, num_stages=4, num_warps=4),
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 64, 'BLOCK_K': 64}, num_stages=4, num_warps=4),
        triton.Config({'BLOCK_M': 64, 'BLOCK_N': 64, 'BLOCK_K': 32}, num_stages=5, num_warps=4),
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 128, 'BLOCK_K': 32}, num_stages=4, num_warps=8),
    ]

    @triton.autotune(configs=configs, key=['M', 'N', 'K'])
    @triton.jit
    def kernel(
        A_PTR, B_PTR, C_PTR,
        STRIDE_AM, STRIDE_AK, STRIDE_BK, STRIDE_BN,
        STRIDE_CM, STRIDE_CN,
        BATCH_STRIDE_A, BATCH_STRIDE_B, BATCH_STRIDE_C,
        M, N, K, BATCH,
        BLOCK_M: tl.constexpr,
        BLOCK_N: tl.constexpr,
        BLOCK_K: tl.constexpr,
    ):
        pid_batch = tl.program_id(0)
        pid_m = tl.program_id(1)
        pid_n = tl.program_id(2)

        block_start_m = pid_m * BLOCK_M
        block_start_n = pid_n * BLOCK_N

        offs_m = tl.arange(0, BLOCK_M)
        offs_n = tl.arange(0, BLOCK_N)
        offs_k = tl.arange(0, BLOCK_K)

        acc = tl.zeros((BLOCK_M, BLOCK_N), dtype=tl.float32)

        lo = 0
        while lo < K:
            k_offs = lo + offs_k

            a_ptrs = A_PTR + pid_batch * BATCH_STRIDE_A + \
                     (block_start_m + offs_m)[:, None] * STRIDE_AM + \
                     k_offs[None, :] * STRIDE_AK

            b_ptrs = B_PTR + pid_batch * BATCH_STRIDE_B + \
                     k_offs[:, None] * STRIDE_BK + \
                     (block_start_n + offs_n)[None, :] * STRIDE_BN

            a_mask = (block_start_m + offs_m)[:, None] < M
            a_mask &= k_offs[None, :] < K
            b_mask = k_offs[:, None] < K
            b_mask &= (block_start_n + offs_n)[None, :] < N

            a = tl.load(a_ptrs, mask=a_mask, other=0.0).to(tl.float32)
            b = tl.load(b_ptrs, mask=b_mask, other=0.0).to(tl.float32)

            acc += tl.dot(a, b)

            lo += BLOCK_K

        c_ptrs = C_PTR + pid_batch * BATCH_STRIDE_C + \
                 (block_start_m + offs_m)[:, None] * STRIDE_CM + \
                 (block_start_n + offs_n)[None, :] * STRIDE_CN

        c_mask = (block_start_m + offs_m)[:, None] < M
        c_mask &= (block_start_n + offs_n)[None, :] < N

        tl.store(c_ptrs, acc.to(tl.float16), mask=c_mask)

    grid = lambda meta: (BATCH, triton.cdiv(M, meta['BLOCK_M']), triton.cdiv(N, meta['BLOCK_N']))
    kernel[grid](
        A_ptr, B_ptr, C_ptr,
        STRIDE_AM, STRIDE_AK, STRIDE_BK, STRIDE_BN,
        STRIDE_CM, STRIDE_CN,
        BATCH_STRIDE_A, BATCH_STRIDE_B, BATCH_STRIDE_C,
        M, N, K, BATCH,
    )
    return C

class Solution:
    def solve(self, spec_path: Optional[str] = None) -> Dict[str, str]:
        current_file = Path(__file__).resolve()
        return {"code": current_file.read_text(encoding="utf-8")}
