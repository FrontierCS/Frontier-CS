import torch
import triton
import triton.language as tl
from pathlib import Path


@triton.autotune(
    configs=[
        triton.Config(
            {'BLOCK_M': 64, 'BLOCK_N': 64, 'BLOCK_K': 32, 'GROUP_M': 8},
            num_stages=2,
            num_warps=4,
        ),
        triton.Config(
            {'BLOCK_M': 64, 'BLOCK_N': 64, 'BLOCK_K': 64, 'GROUP_M': 8},
            num_stages=2,
            num_warps=4,
        ),
        triton.Config(
            {'BLOCK_M': 32, 'BLOCK_N': 64, 'BLOCK_K': 32, 'GROUP_M': 8},
            num_stages=2,
            num_warps=4,
        ),
        triton.Config(
            {'BLOCK_M': 64, 'BLOCK_N': 32, 'BLOCK_K': 32, 'GROUP_M': 8},
            num_stages=2,
            num_warps=4,
        ),
    ],
    key=["M", "N", "K"],
)
@triton.jit
def _bmm_kernel(
    A_ptr,
    B_ptr,
    C_ptr,
    Batches,
    M,
    N,
    K,
    stride_ab,
    stride_am,
    stride_ak,
    stride_bb,
    stride_bk,
    stride_bn,
    stride_cb,
    stride_cm,
    stride_cn,
    BLOCK_M: tl.constexpr,
    BLOCK_N: tl.constexpr,
    BLOCK_K: tl.constexpr,
    GROUP_M: tl.constexpr,
):
    pid_mn = tl.program_id(axis=0)
    batch_id = tl.program_id(axis=1)

    num_pid_m = tl.cdiv(M, BLOCK_M)
    num_pid_n = tl.cdiv(N, BLOCK_N)
    num_pid_in_group = GROUP_M * num_pid_n
    group_id = pid_mn // num_pid_in_group
    first_pid_m = group_id * GROUP_M
    pid_in_group = pid_mn % num_pid_in_group
    pid_m = first_pid_m + (pid_in_group % GROUP_M)
    pid_n = pid_in_group // GROUP_M

    if pid_m >= num_pid_m:
        return

    offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
    offs_n = pid_n * BLOCK_N + tl.arange(0, BLOCK_N)

    A_batch_ptr = A_ptr + batch_id * stride_ab
    B_batch_ptr = B_ptr + batch_id * stride_bb
    C_batch_ptr = C_ptr + batch_id * stride_cb

    acc = tl.zeros((BLOCK_M, BLOCK_N), dtype=tl.float32)

    offs_k = tl.arange(0, BLOCK_K)
    k0 = 0
    while k0 < K:
        k_idxs = k0 + offs_k

        a_ptrs = (
            A_batch_ptr
            + offs_m[:, None] * stride_am
            + k_idxs[None, :] * stride_ak
        )
        b_ptrs = (
            B_batch_ptr
            + k_idxs[:, None] * stride_bk
            + offs_n[None, :] * stride_bn
        )

        a_mask = (offs_m[:, None] < M) & (k_idxs[None, :] < K)
        b_mask = (offs_n[None, :] < N) & (k_idxs[:, None] < K)

        a = tl.load(a_ptrs, mask=a_mask, other=0.0).to(tl.float32)
        b = tl.load(b_ptrs, mask=b_mask, other=0.0).to(tl.float32)

        acc += tl.dot(a, b)

        k0 += BLOCK_K

    c_ptrs = (
        C_batch_ptr
        + offs_m[:, None] * stride_cm
        + offs_n[None, :] * stride_cn
    )
    c_mask = (offs_m[:, None] < M) & (offs_n[None, :] < N)
    tl.store(c_ptrs, acc.to(tl.float16), mask=c_mask)


def bmm(A: torch.Tensor, B: torch.Tensor) -> torch.Tensor:
    if A.ndim != 3 or B.ndim != 3:
        raise ValueError("A and B must be 3D tensors of shape (B, M, K) and (B, K, N) respectively.")

    if A.device.type != "cuda" or B.device.type != "cuda":
        raise ValueError("Inputs must be CUDA tensors.")

    Batches, M, K = A.shape
    B2, K2, N = B.shape
    if B2 != Batches or K2 != K:
        raise ValueError("Shape mismatch: A is (B, M, K), B must be (B, K, N).")

    C = torch.empty((Batches, M, N), device=A.device, dtype=torch.float16)

    stride_ab, stride_am, stride_ak = A.stride()
    stride_bb, stride_bk, stride_bn = B.stride()
    stride_cb, stride_cm, stride_cn = C.stride()

    grid = lambda META: (
        triton.cdiv(M, META["BLOCK_M"]) * triton.cdiv(N, META["BLOCK_N"]),
        Batches,
    )

    _bmm_kernel[grid](
        A,
        B,
        C,
        Batches,
        M,
        N,
        K,
        stride_ab,
        stride_am,
        stride_ak,
        stride_bb,
        stride_bk,
        stride_bn,
        stride_cb,
        stride_cm,
        stride_cn,
    )

    return C


class Solution:
    def solve(self, spec_path: str = None) -> dict:
        current_file = Path(__file__).resolve()
        return {"code": current_file.read_text(encoding="utf-8")}
