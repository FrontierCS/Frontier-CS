import os
import math
import torch
import triton
import triton.language as tl


@triton.jit
def _linear_gelu_kernel(
    X_ptr,
    W_ptr,
    B_ptr,
    Y_ptr,
    stride_xm: tl.constexpr,
    stride_xk: tl.constexpr,
    stride_wk: tl.constexpr,
    stride_wn: tl.constexpr,
    stride_ym: tl.constexpr,
    stride_yn: tl.constexpr,
    M: tl.constexpr,
    N: tl.constexpr,
    K: tl.constexpr,
    BLOCK_M: tl.constexpr,
    BLOCK_N: tl.constexpr,
    BLOCK_K: tl.constexpr,
    GROUP_M: tl.constexpr,
):
    pid = tl.program_id(0)

    grid_m = tl.cdiv(M, BLOCK_M)
    grid_n = tl.cdiv(N, BLOCK_N)

    group_size = GROUP_M
    pid_in_group = pid % (group_size * grid_n)
    group_id = pid // (group_size * grid_n)

    first_pid_m = group_id * group_size
    pid_m = first_pid_m + (pid_in_group % group_size)
    pid_n = pid_in_group // group_size

    offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
    offs_n = pid_n * BLOCK_N + tl.arange(0, BLOCK_N)

    acc = tl.zeros((BLOCK_M, BLOCK_N), dtype=tl.float32)

    a_ptrs = tl.make_block_ptr(
        base=X_ptr,
        shape=(M, K),
        strides=(stride_xm, stride_xk),
        offsets=(pid_m * BLOCK_M, 0),
        block_shape=(BLOCK_M, BLOCK_K),
        order=(1, 0),
    )
    b_ptrs = tl.make_block_ptr(
        base=W_ptr,
        shape=(K, N),
        strides=(stride_wk, stride_wn),
        offsets=(0, pid_n * BLOCK_N),
        block_shape=(BLOCK_K, BLOCK_N),
        order=(0, 1),
    )

    for _ in range(0, K, BLOCK_K):
        a = tl.load(a_ptrs, boundary_check=(0, 1), padding_option="zero").to(tl.float16)
        b = tl.load(b_ptrs, boundary_check=(0, 1), padding_option="zero").to(tl.float16)
        acc += tl.dot(a, b)
        a_ptrs = tl.advance(a_ptrs, (0, BLOCK_K))
        b_ptrs = tl.advance(b_ptrs, (BLOCK_K, 0))

    bias = tl.load(B_ptr + offs_n, mask=offs_n < N, other=0.0).to(tl.float32)
    acc = acc + bias[None, :]

    inv_sqrt2 = 0.7071067811865476
    gelu = acc * 0.5 * (1.0 + tl.extra.cuda.libdevice.erf(acc * inv_sqrt2))

    y_ptrs = Y_ptr + offs_m[:, None] * stride_ym + offs_n[None, :] * stride_yn
    mask = (offs_m[:, None] < M) & (offs_n[None, :] < N)
    tl.store(y_ptrs, gelu.to(tl.float16), mask=mask)


def linear_gelu(X: torch.Tensor, W: torch.Tensor, B: torch.Tensor) -> torch.Tensor:
    if not X.is_cuda or not W.is_cuda or not B.is_cuda:
        raise ValueError("X, W, B must be CUDA tensors")
    if X.dtype != torch.float16 or W.dtype != torch.float16:
        raise ValueError("X and W must be float16")
    if B.dtype != torch.float32:
        B = B.to(torch.float32)
    if X.dim() != 2 or W.dim() != 2 or B.dim() != 1:
        raise ValueError("Expected X: (M,K), W: (K,N), B: (N,)")

    M, K = X.shape
    K2, N = W.shape
    if K2 != K:
        raise ValueError(f"Shape mismatch: X is (M,K)={X.shape}, W is (K,N)={W.shape}")

    if not X.is_contiguous():
        X = X.contiguous()
    if not W.is_contiguous():
        W = W.contiguous()
    if not B.is_contiguous():
        B = B.contiguous()

    Y = torch.empty((M, N), device=X.device, dtype=torch.float16)

    # Heuristics tuned for M in {512, 1024}, K=N=4096 on NVIDIA L4
    if N >= 4096:
        BLOCK_N = 128
    else:
        BLOCK_N = 128 if N % 128 == 0 else 64

    if M >= 1024:
        BLOCK_M = 128
    else:
        BLOCK_M = 128 if M % 128 == 0 else 64

    BLOCK_K = 32
    GROUP_M = 8

    num_warps = 8 if (BLOCK_M >= 128 and BLOCK_N >= 128) else 4
    num_stages = 5

    grid = (triton.cdiv(M, BLOCK_M) * triton.cdiv(N, BLOCK_N),)

    _linear_gelu_kernel[grid](
        X,
        W,
        B,
        Y,
        stride_xm=X.stride(0),
        stride_xk=X.stride(1),
        stride_wk=W.stride(0),
        stride_wn=W.stride(1),
        stride_ym=Y.stride(0),
        stride_yn=Y.stride(1),
        M=M,
        N=N,
        K=K,
        BLOCK_M=BLOCK_M,
        BLOCK_N=BLOCK_N,
        BLOCK_K=BLOCK_K,
        GROUP_M=GROUP_M,
        num_warps=num_warps,
        num_stages=num_stages,
    )
    return Y


class Solution:
    def solve(self, spec_path: str = None) -> dict:
        return {"program_path": os.path.abspath(__file__)}