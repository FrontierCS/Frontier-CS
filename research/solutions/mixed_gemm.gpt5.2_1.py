import os
import textwrap

KERNEL_CODE = r'''
import torch
import triton
import triton.language as tl
from triton.language.extra.cuda import libdevice


@triton.jit
def _linear_gelu_kernel(
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
    pid_in_group = pid - pid_group * group_size * grid_n
    pid_m = first_pid_m + (pid_in_group % group_size)
    pid_n = pid_in_group // group_size

    offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
    offs_n = pid_n * BLOCK_N + tl.arange(0, BLOCK_N)

    acc = tl.zeros((BLOCK_M, BLOCK_N), dtype=tl.float32)

    tl.multiple_of(stride_xk, 8)
    tl.multiple_of(stride_wn, 8)
    tl.multiple_of(stride_wk, 8)

    for k0 in tl.static_range(0, K, BLOCK_K):
        offs_k = k0 + tl.arange(0, BLOCK_K)

        a_ptrs = X_ptr + offs_m[:, None] * stride_xm + offs_k[None, :] * stride_xk
        b_ptrs = W_ptr + offs_k[:, None] * stride_wk + offs_n[None, :] * stride_wn

        a = tl.load(a_ptrs, mask=(offs_m[:, None] < M) & (offs_k[None, :] < K), other=0.0).to(tl.float16)
        b = tl.load(b_ptrs, mask=(offs_k[:, None] < K) & (offs_n[None, :] < N), other=0.0).to(tl.float16)

        acc = tl.dot(a, b, acc)

    bias = tl.load(B_ptr + offs_n, mask=offs_n < N, other=0.0).to(tl.float32)
    acc = acc + bias[None, :]

    x = acc
    t = x * 0.7071067811865476
    y = x * 0.5 * (1.0 + libdevice.erf(t))

    out = y.to(tl.float16)

    y_ptrs = Y_ptr + offs_m[:, None] * stride_ym + offs_n[None, :] * stride_yn
    tl.store(y_ptrs, out, mask=(offs_m[:, None] < M) & (offs_n[None, :] < N))


def linear_gelu(X: torch.Tensor, W: torch.Tensor, B: torch.Tensor) -> torch.Tensor:
    assert X.is_cuda and W.is_cuda and B.is_cuda
    assert X.dtype == torch.float16 and W.dtype == torch.float16 and B.dtype == torch.float32
    assert X.dim() == 2 and W.dim() == 2 and B.dim() == 1
    M, K = X.shape
    KW, N = W.shape
    assert K == KW
    assert B.shape[0] == N

    if not X.is_contiguous():
        X = X.contiguous()
    if not W.is_contiguous():
        W = W.contiguous()
    if not B.is_contiguous():
        B = B.contiguous()

    Y = torch.empty((M, N), device=X.device, dtype=torch.float16)

    if M <= 512:
        BLOCK_M = 64
        num_warps = 4
        num_stages = 4
    else:
        BLOCK_M = 128
        num_warps = 8
        num_stages = 4

    BLOCK_N = 128
    BLOCK_K = 64
    GROUP_M = 8

    grid = (triton.cdiv(M, BLOCK_M) * triton.cdiv(N, BLOCK_N),)

    _linear_gelu_kernel[grid](
        X, W, B, Y,
        M=M, N=N, K=K,
        stride_xm=X.stride(0), stride_xk=X.stride(1),
        stride_wk=W.stride(0), stride_wn=W.stride(1),
        stride_ym=Y.stride(0), stride_yn=Y.stride(1),
        BLOCK_M=BLOCK_M, BLOCK_N=BLOCK_N, BLOCK_K=BLOCK_K,
        GROUP_M=GROUP_M,
        num_warps=num_warps,
        num_stages=num_stages,
    )
    return Y
'''

class Solution:
    def solve(self, spec_path: str = None) -> dict:
        if spec_path is not None and isinstance(spec_path, str) and len(spec_path) > 0:
            try:
                os.makedirs(os.path.dirname(spec_path), exist_ok=True)
            except Exception:
                pass
            try:
                with open(spec_path, "w", encoding="utf-8") as f:
                    f.write(textwrap.dedent(KERNEL_CODE).lstrip())
                return {"program_path": spec_path}
            except Exception:
                pass
        return {"code": textwrap.dedent(KERNEL_CODE).lstrip()}