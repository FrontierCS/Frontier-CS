import os
import sys
import math
import inspect
import torch

try:
    import triton
    import triton.language as tl
except Exception:
    triton = None
    tl = None


def _get_erf():
    if tl is None:
        return None
    try:
        return tl.extra.cuda.libdevice.erf
    except Exception:
        pass
    try:
        return tl.libdevice.erf
    except Exception:
        pass
    try:
        return tl.math.erf
    except Exception:
        pass
    return None


if triton is not None:
    _erf = _get_erf()

    @triton.autotune(
        configs=[
            triton.Config(
                {"BLOCK_M": 128, "BLOCK_N": 128, "BLOCK_K": 32, "GROUP_M": 8},
                num_warps=8,
                num_stages=5,
            ),
            triton.Config(
                {"BLOCK_M": 64, "BLOCK_N": 128, "BLOCK_K": 32, "GROUP_M": 8},
                num_warps=4,
                num_stages=5,
            ),
            triton.Config(
                {"BLOCK_M": 128, "BLOCK_N": 64, "BLOCK_K": 32, "GROUP_M": 8},
                num_warps=4,
                num_stages=5,
            ),
            triton.Config(
                {"BLOCK_M": 64, "BLOCK_N": 256, "BLOCK_K": 32, "GROUP_M": 8},
                num_warps=8,
                num_stages=4,
            ),
            triton.Config(
                {"BLOCK_M": 128, "BLOCK_N": 256, "BLOCK_K": 32, "GROUP_M": 8},
                num_warps=8,
                num_stages=4,
            ),
            triton.Config(
                {"BLOCK_M": 128, "BLOCK_N": 128, "BLOCK_K": 64, "GROUP_M": 8},
                num_warps=8,
                num_stages=4,
            ),
            triton.Config(
                {"BLOCK_M": 64, "BLOCK_N": 64, "BLOCK_K": 64, "GROUP_M": 8},
                num_warps=4,
                num_stages=5,
            ),
        ],
        key=["M", "N", "K"],
    )
    @triton.jit
    def _linear_gelu_kernel(
        X_ptr,
        W_ptr,
        B_ptr,
        Y_ptr,
        M: tl.constexpr,
        N: tl.constexpr,
        K: tl.constexpr,
        stride_xm,
        stride_xk,
        stride_wk,
        stride_wn,
        stride_ym,
        stride_yn,
        BLOCK_M: tl.constexpr,
        BLOCK_N: tl.constexpr,
        BLOCK_K: tl.constexpr,
        GROUP_M: tl.constexpr,
    ):
        pid = tl.program_id(0)

        grid_m = tl.cdiv(M, BLOCK_M)
        grid_n = tl.cdiv(N, BLOCK_N)

        group = GROUP_M
        num_pid_in_group = group * grid_n
        pid_group = pid // num_pid_in_group
        first_pid_m = pid_group * group
        group_size_m = tl.minimum(grid_m - first_pid_m, group)
        pid_in_group = pid - pid_group * num_pid_in_group
        pid_m = first_pid_m + (pid_in_group % group_size_m)
        pid_n = pid_in_group // group_size_m

        offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
        offs_n = pid_n * BLOCK_N + tl.arange(0, BLOCK_N)
        offs_k = tl.arange(0, BLOCK_K)

        m_mask = offs_m < M
        n_mask = offs_n < N

        x_ptrs = X_ptr + (offs_m[:, None] * stride_xm + offs_k[None, :] * stride_xk)
        w_ptrs = W_ptr + (offs_k[:, None] * stride_wk + offs_n[None, :] * stride_wn)

        acc = tl.zeros((BLOCK_M, BLOCK_N), dtype=tl.float32)

        k = 0
        while k < K:
            k_mask = (k + offs_k) < K
            x = tl.load(x_ptrs, mask=m_mask[:, None] & k_mask[None, :], other=0.0)
            w = tl.load(w_ptrs, mask=k_mask[:, None] & n_mask[None, :], other=0.0)
            acc += tl.dot(x, w)
            x_ptrs += BLOCK_K * stride_xk
            w_ptrs += BLOCK_K * stride_wk
            k += BLOCK_K

        b = tl.load(B_ptr + offs_n, mask=n_mask, other=0.0).to(tl.float32)
        acc += b[None, :]

        x = acc
        if _erf is None:
            # Fallback approximation (should not be used in expected environment)
            # gelu(x) ~ 0.5*x*(1+tanh(sqrt(2/pi)*(x+0.044715*x^3)))
            c = 0.7978845608028654
            y = 0.5 * x * (1.0 + tl.tanh(c * (x + 0.044715 * x * x * x)))
        else:
            inv_sqrt2 = 0.7071067811865476
            y = 0.5 * x * (1.0 + _erf(x * inv_sqrt2))

        y = y.to(tl.float16)

        y_ptrs = Y_ptr + (offs_m[:, None] * stride_ym + offs_n[None, :] * stride_yn)
        tl.store(y_ptrs, y, mask=m_mask[:, None] & n_mask[None, :])


def linear_gelu(X: torch.Tensor, W: torch.Tensor, B: torch.Tensor) -> torch.Tensor:
    if not (isinstance(X, torch.Tensor) and isinstance(W, torch.Tensor) and isinstance(B, torch.Tensor)):
        raise TypeError("X, W, B must be torch.Tensor")

    if X.ndim != 2 or W.ndim != 2 or B.ndim != 1:
        raise ValueError("Expected X: (M,K), W: (K,N), B: (N,)")

    if X.dtype != torch.float16 or W.dtype != torch.float16 or B.dtype != torch.float32:
        raise TypeError("Expected dtypes: X float16, W float16, B float32")

    M, K = X.shape
    Kw, N = W.shape
    if Kw != K:
        raise ValueError("Shape mismatch: X is (M,K) and W is (K,N)")
    if B.shape[0] != N:
        raise ValueError("Shape mismatch: B must have shape (N,)")

    if not X.is_cuda or not W.is_cuda or not B.is_cuda:
        x = X.float().matmul(W.float()) + B
        y = x * 0.5 * (1.0 + torch.erf(x * 0.7071067811865476))
        return y.to(torch.float16)

    if triton is None:
        x = X.float().matmul(W.float()) + B
        y = x * 0.5 * (1.0 + torch.erf(x * 0.7071067811865476))
        return y.to(torch.float16)

    Y = torch.empty((M, N), device=X.device, dtype=torch.float16)

    stride_xm, stride_xk = X.stride()
    stride_wk, stride_wn = W.stride()
    stride_ym, stride_yn = Y.stride()

    def grid(meta):
        return (triton.cdiv(M, meta["BLOCK_M"]) * triton.cdiv(N, meta["BLOCK_N"]),)

    _linear_gelu_kernel[grid](
        X,
        W,
        B,
        Y,
        M=M,
        N=N,
        K=K,
        stride_xm=stride_xm,
        stride_xk=stride_xk,
        stride_wk=stride_wk,
        stride_wn=stride_wn,
        stride_ym=stride_ym,
        stride_yn=stride_yn,
    )
    return Y


class Solution:
    def solve(self, spec_path: str = None) -> dict:
        try:
            path = __file__
            if path and os.path.exists(path):
                with open(path, "r", encoding="utf-8") as f:
                    return {"code": f.read()}
        except Exception:
            pass
        try:
            src = inspect.getsource(sys.modules[__name__])
            return {"code": src}
        except Exception:
            return {"code": ""}