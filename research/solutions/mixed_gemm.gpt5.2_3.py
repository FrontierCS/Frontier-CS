import os
import textwrap
import torch
import triton
import triton.language as tl


def _select_erf_and_gelu():
    if hasattr(tl, "math") and hasattr(tl.math, "erf"):
        _erf = tl.math.erf

        def _gelu(x):
            return x * 0.5 * (1.0 + _erf(x * 0.7071067811865476))

        return _erf, _gelu

    try:
        _erf = tl.extra.cuda.libdevice.erf  # type: ignore[attr-defined]

        def _gelu(x):
            return x * 0.5 * (1.0 + _erf(x * 0.7071067811865476))

        return _erf, _gelu
    except Exception:
        _erf = None

        def _gelu(x):
            c = 0.7978845608028654
            return 0.5 * x * (1.0 + tl.tanh(c * (x + 0.044715 * x * x * x)))

        return _erf, _gelu


_TL_ERF, _TL_GELU = _select_erf_and_gelu()


@triton.jit
def _linear_gelu_kernel(
    X_ptr,
    W_ptr,
    B_ptr,
    Y_ptr,
    M: tl.int32,
    N: tl.int32,
    stride_xm: tl.int32,
    stride_xk: tl.int32,
    stride_wk: tl.int32,
    stride_wn: tl.int32,
    stride_ym: tl.int32,
    stride_yn: tl.int32,
    K: tl.constexpr,
    BLOCK_M: tl.constexpr,
    BLOCK_N: tl.constexpr,
    BLOCK_K: tl.constexpr,
    GROUP_M: tl.constexpr,
):
    pid = tl.program_id(0)
    num_pid_m = tl.cdiv(M, BLOCK_M)
    num_pid_n = tl.cdiv(N, BLOCK_N)
    num_pid_in_group = GROUP_M * num_pid_n
    group_id = pid // num_pid_in_group
    first_pid_m = group_id * GROUP_M
    pid_in_group = pid % num_pid_in_group
    pid_m = first_pid_m + (pid_in_group % GROUP_M)
    pid_n = pid_in_group // GROUP_M

    offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
    offs_n = pid_n * BLOCK_N + tl.arange(0, BLOCK_N)
    offs_k = tl.arange(0, BLOCK_K)

    acc = tl.zeros((BLOCK_M, BLOCK_N), dtype=tl.float32)

    a_ptrs = X_ptr + offs_m[:, None] * stride_xm + offs_k[None, :] * stride_xk
    b_ptrs = W_ptr + offs_k[:, None] * stride_wk + offs_n[None, :] * stride_wn

    mask_m = offs_m < M
    mask_n = offs_n < N

    tl.multiple_of(stride_xk, 1)
    tl.multiple_of(stride_wn, 1)

    for k in tl.static_range(0, K, BLOCK_K):
        a = tl.load(a_ptrs, mask=mask_m[:, None], other=0.0)
        b = tl.load(b_ptrs, mask=mask_n[None, :], other=0.0)
        acc += tl.dot(a, b)
        a_ptrs += BLOCK_K * stride_xk
        b_ptrs += BLOCK_K * stride_wk

    bias = tl.load(B_ptr + offs_n, mask=mask_n, other=0.0).to(tl.float32)
    x = acc + bias[None, :]
    y = _TL_GELU(x).to(tl.float16)

    out_ptrs = Y_ptr + offs_m[:, None] * stride_ym + offs_n[None, :] * stride_yn
    tl.store(out_ptrs, y, mask=mask_m[:, None] & mask_n[None, :])


def linear_gelu(X: torch.Tensor, W: torch.Tensor, B: torch.Tensor) -> torch.Tensor:
    if not (X.is_cuda and W.is_cuda and B.is_cuda):
        raise ValueError("X, W, B must be CUDA tensors")
    if X.dtype != torch.float16 or W.dtype != torch.float16:
        raise ValueError("X and W must be torch.float16")
    if B.dtype != torch.float32:
        B = B.float()
    if X.dim() != 2 or W.dim() != 2 or B.dim() != 1:
        raise ValueError("X must be (M,K), W must be (K,N), B must be (N,)")
    M, K = X.shape
    K2, N = W.shape
    if K2 != K:
        raise ValueError(f"Shape mismatch: X is (M={M},K={K}) but W is (K={K2},N={N})")
    if B.numel() != N:
        raise ValueError(f"Shape mismatch: B has {B.numel()} elements but N={N}")

    if not X.is_contiguous():
        X = X.contiguous()
    if not W.is_contiguous():
        W = W.contiguous()
    if not B.is_contiguous():
        B = B.contiguous()

    Y = torch.empty((M, N), device=X.device, dtype=torch.float16)

    BLOCK_M = 64
    BLOCK_N = 128
    BLOCK_K = 64
    GROUP_M = 8

    grid = (triton.cdiv(M, BLOCK_M) * triton.cdiv(N, BLOCK_N),)

    _linear_gelu_kernel[grid](
        X,
        W,
        B,
        Y,
        M,
        N,
        X.stride(0),
        X.stride(1),
        W.stride(0),
        W.stride(1),
        Y.stride(0),
        Y.stride(1),
        K=K,
        BLOCK_M=BLOCK_M,
        BLOCK_N=BLOCK_N,
        BLOCK_K=BLOCK_K,
        GROUP_M=GROUP_M,
        num_warps=8,
        num_stages=4,
    )
    return Y


_KERNEL_CODE = textwrap.dedent(
    r"""
    import torch
    import triton
    import triton.language as tl

    def _select_erf_and_gelu():
        if hasattr(tl, "math") and hasattr(tl.math, "erf"):
            _erf = tl.math.erf
            def _gelu(x):
                return x * 0.5 * (1.0 + _erf(x * 0.7071067811865476))
            return _erf, _gelu
        try:
            _erf = tl.extra.cuda.libdevice.erf  # type: ignore[attr-defined]
            def _gelu(x):
                return x * 0.5 * (1.0 + _erf(x * 0.7071067811865476))
            return _erf, _gelu
        except Exception:
            _erf = None
            def _gelu(x):
                c = 0.7978845608028654
                return 0.5 * x * (1.0 + tl.tanh(c * (x + 0.044715 * x * x * x)))
            return _erf, _gelu

    _TL_ERF, _TL_GELU = _select_erf_and_gelu()

    @triton.jit
    def _linear_gelu_kernel(
        X_ptr,
        W_ptr,
        B_ptr,
        Y_ptr,
        M: tl.int32,
        N: tl.int32,
        stride_xm: tl.int32,
        stride_xk: tl.int32,
        stride_wk: tl.int32,
        stride_wn: tl.int32,
        stride_ym: tl.int32,
        stride_yn: tl.int32,
        K: tl.constexpr,
        BLOCK_M: tl.constexpr,
        BLOCK_N: tl.constexpr,
        BLOCK_K: tl.constexpr,
        GROUP_M: tl.constexpr,
    ):
        pid = tl.program_id(0)
        num_pid_m = tl.cdiv(M, BLOCK_M)
        num_pid_n = tl.cdiv(N, BLOCK_N)
        num_pid_in_group = GROUP_M * num_pid_n
        group_id = pid // num_pid_in_group
        first_pid_m = group_id * GROUP_M
        pid_in_group = pid % num_pid_in_group
        pid_m = first_pid_m + (pid_in_group % GROUP_M)
        pid_n = pid_in_group // GROUP_M

        offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
        offs_n = pid_n * BLOCK_N + tl.arange(0, BLOCK_N)
        offs_k = tl.arange(0, BLOCK_K)

        acc = tl.zeros((BLOCK_M, BLOCK_N), dtype=tl.float32)

        a_ptrs = X_ptr + offs_m[:, None] * stride_xm + offs_k[None, :] * stride_xk
        b_ptrs = W_ptr + offs_k[:, None] * stride_wk + offs_n[None, :] * stride_wn

        mask_m = offs_m < M
        mask_n = offs_n < N

        tl.multiple_of(stride_xk, 1)
        tl.multiple_of(stride_wn, 1)

        for k in tl.static_range(0, K, BLOCK_K):
            a = tl.load(a_ptrs, mask=mask_m[:, None], other=0.0)
            b = tl.load(b_ptrs, mask=mask_n[None, :], other=0.0)
            acc += tl.dot(a, b)
            a_ptrs += BLOCK_K * stride_xk
            b_ptrs += BLOCK_K * stride_wk

        bias = tl.load(B_ptr + offs_n, mask=mask_n, other=0.0).to(tl.float32)
        x = acc + bias[None, :]
        y = _TL_GELU(x).to(tl.float16)

        out_ptrs = Y_ptr + offs_m[:, None] * stride_ym + offs_n[None, :] * stride_yn
        tl.store(out_ptrs, y, mask=mask_m[:, None] & mask_n[None, :])

    def linear_gelu(X: torch.Tensor, W: torch.Tensor, B: torch.Tensor) -> torch.Tensor:
        if not (X.is_cuda and W.is_cuda and B.is_cuda):
            raise ValueError("X, W, B must be CUDA tensors")
        if X.dtype != torch.float16 or W.dtype != torch.float16:
            raise ValueError("X and W must be torch.float16")
        if B.dtype != torch.float32:
            B = B.float()
        if X.dim() != 2 or W.dim() != 2 or B.dim() != 1:
            raise ValueError("X must be (M,K), W must be (K,N), B must be (N,)")
        M, K = X.shape
        K2, N = W.shape
        if K2 != K:
            raise ValueError(f"Shape mismatch: X is (M={M},K={K}) but W is (K={K2},N={N})")
        if B.numel() != N:
            raise ValueError(f"Shape mismatch: B has {B.numel()} elements but N={N}")

        if not X.is_contiguous():
            X = X.contiguous()
        if not W.is_contiguous():
            W = W.contiguous()
        if not B.is_contiguous():
            B = B.contiguous()

        Y = torch.empty((M, N), device=X.device, dtype=torch.float16)

        BLOCK_M = 64
        BLOCK_N = 128
        BLOCK_K = 64
        GROUP_M = 8

        grid = (triton.cdiv(M, BLOCK_M) * triton.cdiv(N, BLOCK_N),)

        _linear_gelu_kernel[grid](
            X, W, B, Y,
            M, N,
            X.stride(0), X.stride(1),
            W.stride(0), W.stride(1),
            Y.stride(0), Y.stride(1),
            K=K,
            BLOCK_M=BLOCK_M, BLOCK_N=BLOCK_N, BLOCK_K=BLOCK_K, GROUP_M=GROUP_M,
            num_warps=8, num_stages=4,
        )
        return Y
    """
).lstrip()


class Solution:
    def solve(self, spec_path: str = None) -> dict:
        return {"code": _KERNEL_CODE}