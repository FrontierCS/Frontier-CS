import os
import textwrap

KERNEL_CODE = textwrap.dedent(r'''
import torch
import triton
import triton.language as tl

_INV_SQRT2 = 0.7071067811865476

def _gelu(x):
    return 0.5 * x * (1.0 + tl.extra.cuda.libdevice.erf(x * _INV_SQRT2))

_HAS_BLOCK_PTR = hasattr(tl, "make_block_ptr") and hasattr(tl, "advance")

configs = [
    triton.Config({"BLOCK_M": 64, "BLOCK_N": 128, "BLOCK_K": 32, "GROUP_M": 8}, num_warps=8, num_stages=5),
    triton.Config({"BLOCK_M": 64, "BLOCK_N": 128, "BLOCK_K": 64, "GROUP_M": 8}, num_warps=8, num_stages=4),
    triton.Config({"BLOCK_M": 128, "BLOCK_N": 64, "BLOCK_K": 32, "GROUP_M": 4}, num_warps=8, num_stages=4),
]

if _HAS_BLOCK_PTR:
    @triton.autotune(configs=configs, key=["M", "N", "K"])
    @triton.jit
    def _linear_gelu_kernel(
        X_ptr, W_ptr, B_ptr, Y_ptr,
        stride_xm: tl.constexpr, stride_xk: tl.constexpr,
        stride_wk: tl.constexpr, stride_wn: tl.constexpr,
        stride_ym: tl.constexpr, stride_yn: tl.constexpr,
        M: tl.constexpr, N: tl.constexpr, K: tl.constexpr,
        BLOCK_M: tl.constexpr, BLOCK_N: tl.constexpr, BLOCK_K: tl.constexpr,
        GROUP_M: tl.constexpr,
    ):
        pid = tl.program_id(0)
        grid_m = tl.cdiv(M, BLOCK_M)
        grid_n = tl.cdiv(N, BLOCK_N)

        group_size = GROUP_M
        num_pid_in_group = group_size * grid_n
        group_id = pid // num_pid_in_group
        first_pid_m = group_id * group_size
        group_m = tl.minimum(grid_m - first_pid_m, group_size)
        pid_in_group = pid % num_pid_in_group
        pid_m = first_pid_m + (pid_in_group % group_m)
        pid_n = pid_in_group // group_m

        offs_m = pid_m * BLOCK_M
        offs_n = pid_n * BLOCK_N

        X_blk = tl.make_block_ptr(
            base=X_ptr,
            shape=(M, K),
            strides=(stride_xm, stride_xk),
            offsets=(offs_m, 0),
            block_shape=(BLOCK_M, BLOCK_K),
            order=(1, 0),
        )
        W_blk = tl.make_block_ptr(
            base=W_ptr,
            shape=(K, N),
            strides=(stride_wk, stride_wn),
            offsets=(0, offs_n),
            block_shape=(BLOCK_K, BLOCK_N),
            order=(0, 1),
        )

        acc = tl.zeros((BLOCK_M, BLOCK_N), dtype=tl.float32)

        tl.multiple_of(offs_n, 8)
        tl.multiple_of(offs_m, 8)

        for _ in tl.static_range(0, K, BLOCK_K):
            a = tl.load(X_blk, boundary_check=(0, 1), padding_option="zero").to(tl.float16)
            b = tl.load(W_blk, boundary_check=(0, 1), padding_option="zero").to(tl.float16)
            acc = tl.dot(a, b, acc, out_dtype=tl.float32)
            X_blk = tl.advance(X_blk, (0, BLOCK_K))
            W_blk = tl.advance(W_blk, (BLOCK_K, 0))

        offs_n_vec = offs_n + tl.arange(0, BLOCK_N)
        bias = tl.load(B_ptr + offs_n_vec, mask=offs_n_vec < N, other=0.0).to(tl.float32)
        acc = acc + bias[None, :]

        acc = _gelu(acc)

        Y_blk = tl.make_block_ptr(
            base=Y_ptr,
            shape=(M, N),
            strides=(stride_ym, stride_yn),
            offsets=(offs_m, offs_n),
            block_shape=(BLOCK_M, BLOCK_N),
            order=(1, 0),
        )
        tl.store(Y_blk, acc.to(tl.float16), boundary_check=(0, 1))
else:
    @triton.autotune(configs=configs, key=["M", "N", "K"])
    @triton.jit
    def _linear_gelu_kernel(
        X_ptr, W_ptr, B_ptr, Y_ptr,
        stride_xm: tl.constexpr, stride_xk: tl.constexpr,
        stride_wk: tl.constexpr, stride_wn: tl.constexpr,
        stride_ym: tl.constexpr, stride_yn: tl.constexpr,
        M: tl.constexpr, N: tl.constexpr, K: tl.constexpr,
        BLOCK_M: tl.constexpr, BLOCK_N: tl.constexpr, BLOCK_K: tl.constexpr,
        GROUP_M: tl.constexpr,
    ):
        pid = tl.program_id(0)
        grid_m = tl.cdiv(M, BLOCK_M)
        grid_n = tl.cdiv(N, BLOCK_N)

        group_size = GROUP_M
        num_pid_in_group = group_size * grid_n
        group_id = pid // num_pid_in_group
        first_pid_m = group_id * group_size
        group_m = tl.minimum(grid_m - first_pid_m, group_size)
        pid_in_group = pid % num_pid_in_group
        pid_m = first_pid_m + (pid_in_group % group_m)
        pid_n = pid_in_group // group_m

        rm = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
        rn = pid_n * BLOCK_N + tl.arange(0, BLOCK_N)
        rk = tl.arange(0, BLOCK_K)

        tl.multiple_of(rn, 8)
        tl.multiple_of(rm, 8)

        acc = tl.zeros((BLOCK_M, BLOCK_N), dtype=tl.float32)

        X_ptrs = X_ptr + rm[:, None] * stride_xm + rk[None, :] * stride_xk
        W_ptrs = W_ptr + rk[:, None] * stride_wk + rn[None, :] * stride_wn

        for k in tl.static_range(0, K, BLOCK_K):
            x = tl.load(X_ptrs, mask=(rm[:, None] < M) & (k + rk[None, :] < K), other=0.0).to(tl.float16)
            w = tl.load(W_ptrs, mask=(k + rk[:, None] < K) & (rn[None, :] < N), other=0.0).to(tl.float16)
            acc += tl.dot(x, w, out_dtype=tl.float32)
            X_ptrs += BLOCK_K * stride_xk
            W_ptrs += BLOCK_K * stride_wk

        bias = tl.load(B_ptr + rn, mask=rn < N, other=0.0).to(tl.float32)
        acc = acc + bias[None, :]

        acc = _gelu(acc)

        Y_ptrs = Y_ptr + rm[:, None] * stride_ym + rn[None, :] * stride_yn
        tl.store(Y_ptrs, acc.to(tl.float16), mask=(rm[:, None] < M) & (rn[None, :] < N))

def linear_gelu(X: torch.Tensor, W: torch.Tensor, B: torch.Tensor) -> torch.Tensor:
    assert X.is_cuda and W.is_cuda and B.is_cuda
    assert X.dtype == torch.float16 and W.dtype == torch.float16
    assert B.dtype == torch.float32
    assert X.ndim == 2 and W.ndim == 2 and B.ndim == 1
    M, K = X.shape
    Kw, N = W.shape
    assert K == Kw
    assert B.shape[0] == N

    Y = torch.empty((M, N), device=X.device, dtype=torch.float16)

    grid = lambda META: (triton.cdiv(M, META["BLOCK_M"]) * triton.cdiv(N, META["BLOCK_N"]),)
    _linear_gelu_kernel[grid](
        X, W, B, Y,
        X.stride(0), X.stride(1),
        W.stride(0), W.stride(1),
        Y.stride(0), Y.stride(1),
        M=M, N=N, K=K,
    )
    return Y
''').strip() + "\n"

class Solution:
    def solve(self, spec_path: str = None) -> dict:
        return {"code": KERNEL_CODE}