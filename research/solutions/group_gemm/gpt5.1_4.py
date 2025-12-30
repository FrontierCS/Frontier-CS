import torch
import triton
import triton.language as tl


# Triton BMM kernel
_bmm_configs = [
    triton.Config(
        {"BLOCK_M": 64, "BLOCK_N": 64, "BLOCK_K": 16},
        num_warps=4,
        num_stages=2,
    ),
    triton.Config(
        {"BLOCK_M": 64, "BLOCK_N": 64, "BLOCK_K": 32},
        num_warps=4,
        num_stages=3,
    ),
    triton.Config(
        {"BLOCK_M": 128, "BLOCK_N": 64, "BLOCK_K": 32},
        num_warps=8,
        num_stages=4,
    ),
    triton.Config(
        {"BLOCK_M": 64, "BLOCK_N": 128, "BLOCK_K": 32},
        num_warps=8,
        num_stages=4,
    ),
    triton.Config(
        {"BLOCK_M": 128, "BLOCK_N": 128, "BLOCK_K": 32},
        num_warps=8,
        num_stages=4,
    ),
]


@triton.autotune(configs=_bmm_configs, key=["M", "N", "K"])
@triton.jit
def _bmm_kernel(
    A_ptr, B_ptr, C_ptr,
    Batches, M, N, K,
    stride_ab, stride_am, stride_ak,
    stride_bb, stride_bk, stride_bn,
    stride_cb, stride_cm, stride_cn,
    BLOCK_M: tl.constexpr, BLOCK_N: tl.constexpr, BLOCK_K: tl.constexpr,
):
    pid_n = tl.program_id(0)
    pid_m = tl.program_id(1)
    pid_b = tl.program_id(2)

    offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
    offs_n = pid_n * BLOCK_N + tl.arange(0, BLOCK_N)
    offs_k = tl.arange(0, BLOCK_K)

    A_batch_ptr = A_ptr + pid_b * stride_ab
    B_batch_ptr = B_ptr + pid_b * stride_bb
    C_batch_ptr = C_ptr + pid_b * stride_cb

    acc = tl.zeros((BLOCK_M, BLOCK_N), dtype=tl.float32)

    k0 = 0
    while k0 < K:
        k_idxs = k0 + offs_k

        a_ptrs = A_batch_ptr + (offs_m[:, None] * stride_am) + (k_idxs[None, :] * stride_ak)
        b_ptrs = B_batch_ptr + (k_idxs[:, None] * stride_bk) + (offs_n[None, :] * stride_bn)

        a_mask = (offs_m[:, None] < M) & (k_idxs[None, :] < K)
        b_mask = (offs_n[None, :] < N) & (k_idxs[:, None] < K)

        a = tl.load(a_ptrs, mask=a_mask, other=0.0).to(tl.float32)
        b = tl.load(b_ptrs, mask=b_mask, other=0.0).to(tl.float32)

        acc += tl.dot(a, b)
        k0 += BLOCK_K

    c_ptrs = C_batch_ptr + (offs_m[:, None] * stride_cm) + (offs_n[None, :] * stride_cn)
    c_mask = (offs_m[:, None] < M) & (offs_n[None, :] < N)
    tl.store(c_ptrs, acc.to(tl.float16), mask=c_mask)


def bmm(A: torch.Tensor, B: torch.Tensor) -> torch.Tensor:
    """
    Batched matrix multiplication using Triton.

    Args:
        A: (B, M, K)
        B: (B, K, N)

    Returns:
        C: (B, M, N), dtype=float16
    """
    if A.dim() != 3 or B.dim() != 3:
        raise ValueError("A and B must be 3D tensors of shape (B, M, K) and (B, K, N)")
    if A.shape[0] != B.shape[0]:
        raise ValueError("Batch dimensions of A and B must match")
    if A.shape[2] != B.shape[1]:
        raise ValueError("Inner dimensions (K) of A and B must match")

    Batches, M, K = A.shape
    _, _, N = B.shape

    # Handle empty tensors early
    if Batches == 0 or M == 0 or N == 0 or K == 0:
        return A.new_empty((Batches, M, N), dtype=torch.float16)

    # Device / dtype checks
    if A.device.type != "cuda" or B.device.type != "cuda":
        return torch.bmm(A, B).to(torch.float16)

    if A.dtype != torch.float16 or B.dtype != torch.float16:
        A_mat = A.to(torch.float16)
        B_mat = B.to(torch.float16)
        return torch.bmm(A_mat, B_mat).to(torch.float16)

    C = torch.empty((Batches, M, N), device=A.device, dtype=torch.float16)

    a_stride_b, a_stride_m, a_stride_k = A.stride()
    b_stride_b, b_stride_k, b_stride_n = B.stride()
    c_stride_b, c_stride_m, c_stride_n = C.stride()

    def grid(meta):
        return (
            triton.cdiv(N, meta["BLOCK_N"]),
            triton.cdiv(M, meta["BLOCK_M"]),
            Batches,
        )

    _bmm_kernel[grid](
        A, B, C,
        Batches, M, N, K,
        a_stride_b, a_stride_m, a_stride_k,
        b_stride_b, b_stride_k, b_stride_n,
        c_stride_b, c_stride_m, c_stride_n,
    )

    return C


class Solution:
    def solve(self, spec_path: str = None) -> dict:
        from pathlib import Path

        current_file = Path(__file__).resolve()
        return {"code": current_file.read_text(encoding="utf-8")}