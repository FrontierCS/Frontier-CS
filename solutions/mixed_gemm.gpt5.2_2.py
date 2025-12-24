import os
import textwrap


_KERNEL_SRC = r'''
import torch
import triton
import triton.language as tl


def _select_erf():
    if hasattr(tl, "math") and hasattr(tl.math, "erf"):
        return tl.math.erf
    try:
        return tl.extra.cuda.libdevice.erf
    except Exception:
        pass
    try:
        return tl.libdevice.erf
    except Exception:
        pass
    return None


_ERF = _select_erf()


@triton.jit
def _linear_gelu_kernel_aligned(
    X_ptr, W_ptr, B_ptr, Y_ptr,
    M: tl.constexpr, N: tl.constexpr, K: tl.constexpr,
    stride_xm: tl.constexpr, stride_xk: tl.constexpr,
    stride_wk: tl.constexpr, stride_wn: tl.constexpr,
    stride_ym: tl.constexpr, stride_yn: tl.constexpr,
    BLOCK_M: tl.constexpr, BLOCK_N: tl.constexpr, BLOCK_K: tl.constexpr,
    GROUP_M: tl.constexpr,
):
    pid = tl.program_id(0)
    grid_m = tl.cdiv(M, BLOCK_M)
    grid_n = tl.cdiv(N, BLOCK_N)

    group_size = GROUP_M
    pid_group = pid // (group_size * grid_n)
    first_pid_m = pid_group * group_size
    group_m = tl.minimum(grid_m - first_pid_m, group_size)
    pid_in_group = pid % (group_size * grid_n)
    pid_m = first_pid_m + (pid_in_group // grid_n)
    pid_n = pid_in_group % grid_n

    offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
    offs_n = pid_n * BLOCK_N + tl.arange(0, BLOCK_N)
    tl.multiple_of(offs_n, 16)
    tl.multiple_of(offs_m, 16)

    acc = tl.zeros((BLOCK_M, BLOCK_N), dtype=tl.float32)

    for k0 in range(0, K, BLOCK_K):
        offs_k = k0 + tl.arange(0, BLOCK_K)
        tl.multiple_of(offs_k, 16)

        x = tl.load(X_ptr + offs_m[:, None] * stride_xm + offs_k[None, :] * stride_xk, eviction_policy='evict_first')
        w = tl.load(W_ptr + offs_k[:, None] * stride_wk + offs_n[None, :] * stride_wn, eviction_policy='evict_last')
        acc = tl.dot(x, w, acc)

    b = tl.load(B_ptr + offs_n).to(tl.float32)
    acc = acc + b[None, :]

    x = acc
    inv_sqrt2 = 0.7071067811865476
    if _ERF is not None:
        t = x * inv_sqrt2
        y = 0.5 * x * (1.0 + _ERF(t))
    else:
        # Fallback tanh approximation
        # gelu(x) ≈ 0.5*x*(1+tanh(√(2/π)*(x+0.044715x^3)))
        sqrt_2_over_pi = 0.7978845608028654
        x3 = x * x * x
        y = 0.5 * x * (1.0 + tl.tanh(sqrt_2_over_pi * (x + 0.044715 * x3)))

    y = y.to(tl.float16)
    tl.store(Y_ptr + offs_m[:, None] * stride_ym + offs_n[None, :] * stride_yn, y)


@triton.jit
def _linear_gelu_kernel_masked(
    X_ptr, W_ptr, B_ptr, Y_ptr,
    M, N, K,
    stride_xm, stride_xk,
    stride_wk, stride_wn,
    stride_ym, stride_yn,
    BLOCK_M: tl.constexpr, BLOCK_N: tl.constexpr, BLOCK_K: tl.constexpr,
    GROUP_M: tl.constexpr,
):
    pid = tl.program_id(0)
    grid_m = tl.cdiv(M, BLOCK_M)
    grid_n = tl.cdiv(N, BLOCK_N)

    group_size = GROUP_M
    pid_group = pid // (group_size * grid_n)
    first_pid_m = pid_group * group_size
    group_m = tl.minimum(grid_m - first_pid_m, group_size)
    pid_in_group = pid % (group_size * grid_n)
    pid_m = first_pid_m + (pid_in_group // grid_n)
    pid_n = pid_in_group % grid_n

    offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
    offs_n = pid_n * BLOCK_N + tl.arange(0, BLOCK_N)
    mask_m = offs_m < M
    mask_n = offs_n < N

    acc = tl.zeros((BLOCK_M, BLOCK_N), dtype=tl.float32)
    for k0 in range(0, K, BLOCK_K):
        offs_k = k0 + tl.arange(0, BLOCK_K)
        mask_k = offs_k < K

        x = tl.load(
            X_ptr + offs_m[:, None] * stride_xm + offs_k[None, :] * stride_xk,
            mask=mask_m[:, None] & mask_k[None, :],
            other=0.0,
            eviction_policy='evict_first',
        )
        w = tl.load(
            W_ptr + offs_k[:, None] * stride_wk + offs_n[None, :] * stride_wn,
            mask=mask_k[:, None] & mask_n[None, :],
            other=0.0,
            eviction_policy='evict_last',
        )
        acc = tl.dot(x, w, acc)

    b = tl.load(B_ptr + offs_n, mask=mask_n, other=0.0).to(tl.float32)
    acc = acc + b[None, :]

    x = acc
    inv_sqrt2 = 0.7071067811865476
    if _ERF is not None:
        t = x * inv_sqrt2
        y = 0.5 * x * (1.0 + _ERF(t))
    else:
        sqrt_2_over_pi = 0.7978845608028654
        x3 = x * x * x
        y = 0.5 * x * (1.0 + tl.tanh(sqrt_2_over_pi * (x + 0.044715 * x3)))

    y = y.to(tl.float16)
    out_ptrs = Y_ptr + offs_m[:, None] * stride_ym + offs_n[None, :] * stride_yn
    tl.store(out_ptrs, y, mask=mask_m[:, None] & mask_n[None, :])


def linear_gelu(X: torch.Tensor, W: torch.Tensor, B: torch.Tensor) -> torch.Tensor:
    assert X.is_cuda and W.is_cuda and B.is_cuda
    assert X.dtype == torch.float16 and W.dtype == torch.float16 and B.dtype == torch.float32
    assert X.ndim == 2 and W.ndim == 2 and B.ndim == 1
    M, K = X.shape
    K2, N = W.shape
    assert K2 == K
    assert B.shape[0] == N

    Y = torch.empty((M, N), device=X.device, dtype=torch.float16)

    stride_xm, stride_xk = X.stride()
    stride_wk, stride_wn = W.stride()
    stride_ym, stride_yn = Y.stride()

    # Tuned for (M in {512,1024}, N=4096, K=4096) on Ada/L4
    BLOCK_M = 128
    BLOCK_N = 128
    BLOCK_K = 32
    GROUP_M = 8
    num_warps = 8
    num_stages = 4

    grid = (triton.cdiv(M, BLOCK_M) * triton.cdiv(N, BLOCK_N),)

    aligned = (
        X.is_contiguous() and W.is_contiguous() and B.is_contiguous() and Y.is_contiguous() and
        (M % BLOCK_M == 0) and (N % BLOCK_N == 0) and (K % BLOCK_K == 0)
    )

    if aligned:
        _linear_gelu_kernel_aligned[grid](
            X, W, B, Y,
            M=M, N=N, K=K,
            stride_xm=stride_xm, stride_xk=stride_xk,
            stride_wk=stride_wk, stride_wn=stride_wn,
            stride_ym=stride_ym, stride_yn=stride_yn,
            BLOCK_M=BLOCK_M, BLOCK_N=BLOCK_N, BLOCK_K=BLOCK_K,
            GROUP_M=GROUP_M,
            num_warps=num_warps,
            num_stages=num_stages,
        )
    else:
        _linear_gelu_kernel_masked[grid](
            X, W, B, Y,
            M, N, K,
            stride_xm, stride_xk,
            stride_wk, stride_wn,
            stride_ym, stride_yn,
            BLOCK_M=BLOCK_M, BLOCK_N=BLOCK_N, BLOCK_K=BLOCK_K,
            GROUP_M=GROUP_M,
            num_warps=num_warps,
            num_stages=num_stages,
        )
    return Y
'''


class Solution:
    def solve(self, spec_path: str = None) -> dict:
        return {"code": textwrap.dedent(_KERNEL_SRC).lstrip()}