import textwrap

KERNEL_CODE = textwrap.dedent(r'''
import torch
import triton
import triton.language as tl

try:
    _erf = tl.extra.cuda.libdevice.erf
except Exception:
    from triton.language.extra.cuda import libdevice as _libdevice
    _erf = _libdevice.erf


@triton.jit
def _linear_bias_gelu_kernel(
    X_ptr, W_ptr, B_ptr, Y_ptr,
    M: tl.constexpr, N: tl.constexpr, K: tl.constexpr,
    stride_xm: tl.constexpr, stride_xk: tl.constexpr,
    stride_wk: tl.constexpr, stride_wn: tl.constexpr,
    stride_ym: tl.constexpr, stride_yn: tl.constexpr,
    BLOCK_M: tl.constexpr, BLOCK_N: tl.constexpr, BLOCK_K: tl.constexpr,
    GROUP_M: tl.constexpr,
    EVEN_M: tl.constexpr, EVEN_N: tl.constexpr, EVEN_K: tl.constexpr,
):
    pid = tl.program_id(0)
    num_pid_m = tl.cdiv(M, BLOCK_M)
    num_pid_n = tl.cdiv(N, BLOCK_N)

    num_pid_in_group = GROUP_M * num_pid_n
    group_id = pid // num_pid_in_group
    first_pid_m = group_id * GROUP_M
    group_size_m = tl.minimum(num_pid_m - first_pid_m, GROUP_M)
    pid_in_group = pid - group_id * num_pid_in_group
    pid_m = first_pid_m + (pid_in_group % group_size_m)
    pid_n = pid_in_group // group_size_m

    offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
    offs_n = pid_n * BLOCK_N + tl.arange(0, BLOCK_N)
    offs_k = tl.arange(0, BLOCK_K)

    tl.multiple_of(offs_m, 8)
    tl.multiple_of(offs_n, 8)
    tl.multiple_of(offs_k, 8)

    acc = tl.zeros((BLOCK_M, BLOCK_N), dtype=tl.float32)

    x_ptrs = X_ptr + (offs_m[:, None] * stride_xm + offs_k[None, :] * stride_xk)
    w_ptrs = W_ptr + (offs_k[:, None] * stride_wk + offs_n[None, :] * stride_wn)

    if EVEN_M and EVEN_N and EVEN_K:
        for k in tl.static_range(0, K, BLOCK_K):
            a = tl.load(x_ptrs)
            b = tl.load(w_ptrs)
            acc += tl.dot(a, b)
            x_ptrs += BLOCK_K * stride_xk
            w_ptrs += BLOCK_K * stride_wk
        bias = tl.load(B_ptr + offs_n).to(tl.float32)
        acc += bias[None, :]
        x = acc
        y = 0.5 * x * (1.0 + _erf(x * 0.7071067811865476))
        y = y.to(tl.float16)
        y_ptrs = Y_ptr + (offs_m[:, None] * stride_ym + offs_n[None, :] * stride_yn)
        tl.store(y_ptrs, y)
    else:
        m_mask = offs_m < M
        n_mask = offs_n < N
        for k in tl.static_range(0, K, BLOCK_K):
            k_mask = (k + offs_k) < K
            a = tl.load(x_ptrs, mask=m_mask[:, None] & k_mask[None, :], other=0.0)
            b = tl.load(w_ptrs, mask=k_mask[:, None] & n_mask[None, :], other=0.0)
            acc += tl.dot(a, b)
            x_ptrs += BLOCK_K * stride_xk
            w_ptrs += BLOCK_K * stride_wk
        bias = tl.load(B_ptr + offs_n, mask=n_mask, other=0.0).to(tl.float32)
        acc += bias[None, :]
        x = acc
        y = 0.5 * x * (1.0 + _erf(x * 0.7071067811865476))
        y = y.to(tl.float16)
        y_ptrs = Y_ptr + (offs_m[:, None] * stride_ym + offs_n[None, :] * stride_yn)
        tl.store(y_ptrs, y, mask=m_mask[:, None] & n_mask[None, :])


def linear_gelu(X: torch.Tensor, W: torch.Tensor, B: torch.Tensor) -> torch.Tensor:
    if not (X.is_cuda and W.is_cuda and B.is_cuda):
        raise ValueError("X, W, B must be CUDA tensors")
    if X.dtype != torch.float16 or W.dtype != torch.float16:
        raise ValueError("X and W must be float16")
    if B.dtype != torch.float32:
        raise ValueError("B must be float32")
    if X.ndim != 2 or W.ndim != 2 or B.ndim != 1:
        raise ValueError("X and W must be 2D and B must be 1D")
    M, K = X.shape
    K2, N = W.shape
    if K2 != K or B.numel() != N:
        raise ValueError("Shape mismatch")

    Y = torch.empty((M, N), device=X.device, dtype=torch.float16)

    stride_xm, stride_xk = X.stride()
    stride_wk, stride_wn = W.stride()
    stride_ym, stride_yn = Y.stride()

    # Optimized for the benchmark shapes; still supports arbitrary sizes via masked path.
    BLOCK_M = 128
    BLOCK_N = 128
    BLOCK_K = 32
    GROUP_M = 8

    even_m = (M % BLOCK_M) == 0
    even_n = (N % BLOCK_N) == 0
    even_k = (K % BLOCK_K) == 0

    grid = (triton.cdiv(M, BLOCK_M) * triton.cdiv(N, BLOCK_N),)

    _linear_bias_gelu_kernel[grid](
        X, W, B, Y,
        M=M, N=N, K=K,
        stride_xm=stride_xm, stride_xk=stride_xk,
        stride_wk=stride_wk, stride_wn=stride_wn,
        stride_ym=stride_ym, stride_yn=stride_yn,
        BLOCK_M=BLOCK_M, BLOCK_N=BLOCK_N, BLOCK_K=BLOCK_K,
        GROUP_M=GROUP_M,
        EVEN_M=even_m, EVEN_N=even_n, EVEN_K=even_k,
        num_warps=8,
        num_stages=4,
    )
    return Y
''').lstrip()


class Solution:
    def solve(self, spec_path: str = None) -> dict:
        return {"code": KERNEL_CODE}