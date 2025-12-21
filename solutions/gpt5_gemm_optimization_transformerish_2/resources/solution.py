import os
import torch
import triton
import triton.language as tl


@triton.jit
def gelu(x):
    return x * 0.5 * (1.0 + tl.extra.cuda.libdevice.erf(x * 0.7071067811865476))


@triton.autotune(
    configs=[
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 128, 'BLOCK_K': 32}, num_stages=3, num_warps=8),
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 256, 'BLOCK_K': 32}, num_stages=3, num_warps=8),
        triton.Config({'BLOCK_M': 256, 'BLOCK_N': 128, 'BLOCK_K': 32}, num_stages=3, num_warps=8),
        triton.Config({'BLOCK_M': 64, 'BLOCK_N': 256, 'BLOCK_K': 64}, num_stages=4, num_warps=8),
        triton.Config({'BLOCK_M': 256, 'BLOCK_N': 64, 'BLOCK_K': 64}, num_stages=4, num_warps=8),
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 128, 'BLOCK_K': 64}, num_stages=4, num_warps=8),
        triton.Config({'BLOCK_M': 64, 'BLOCK_N': 128, 'BLOCK_K': 64}, num_stages=4, num_warps=8),
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 64, 'BLOCK_K': 64}, num_stages=4, num_warps=4),
        triton.Config({'BLOCK_M': 64, 'BLOCK_N': 64, 'BLOCK_K': 64}, num_stages=4, num_warps=4),
        triton.Config({'BLOCK_M': 256, 'BLOCK_N': 256, 'BLOCK_K': 32}, num_stages=3, num_warps=8),
        triton.Config({'BLOCK_M': 64, 'BLOCK_N': 128, 'BLOCK_K': 32}, num_stages=3, num_warps=4),
    ],
    key=['M', 'N', 'K'],
)
@triton.jit
def _matmul_gelu_kernel(
    A_ptr, B_ptr, C_ptr,
    M, N, K,
    stride_am, stride_ak,
    stride_bk, stride_bn,
    stride_cm, stride_cn,
    USE_TF32: tl.constexpr,
    C_IS_FP16: tl.constexpr,
    C_IS_BF16: tl.constexpr,
    BLOCK_M: tl.constexpr, BLOCK_N: tl.constexpr, BLOCK_K: tl.constexpr
):
    pid_m = tl.program_id(axis=0)
    pid_n = tl.program_id(axis=1)

    offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
    offs_n = pid_n * BLOCK_N + tl.arange(0, BLOCK_N)
    offs_k = tl.arange(0, BLOCK_K)

    a_ptrs = A_ptr + (offs_m[:, None] * stride_am + offs_k[None, :] * stride_ak)
    b_ptrs = B_ptr + (offs_k[:, None] * stride_bk + offs_n[None, :] * stride_bn)

    acc = tl.zeros((BLOCK_M, BLOCK_N), dtype=tl.float32)

    k = 0
    while k < K:
        a_mask = (offs_m[:, None] < M) & (k + offs_k[None, :] < K)
        b_mask = (k + offs_k[:, None] < K) & (offs_n[None, :] < N)

        a = tl.load(a_ptrs, mask=a_mask, other=0.0)
        b = tl.load(b_ptrs, mask=b_mask, other=0.0)

        if USE_TF32:
            acc += tl.dot(a, b, allow_tf32=True)
        else:
            a16 = a.to(tl.float16)
            b16 = b.to(tl.float16)
            acc += tl.dot(a16, b16)

        k += BLOCK_K
        a_ptrs += BLOCK_K * stride_ak
        b_ptrs += BLOCK_K * stride_bk

    # Apply GELU activation
    acc = gelu(acc)

    c_ptrs = C_ptr + (offs_m[:, None] * stride_cm + offs_n[None, :] * stride_cn)
    c_mask = (offs_m[:, None] < M) & (offs_n[None, :] < N)

    if C_IS_FP16:
        out = acc.to(tl.float16)
    elif C_IS_BF16:
        out = acc.to(tl.bfloat16)
    else:
        out = acc  # float32

    tl.store(c_ptrs, out, mask=c_mask)


def matmul(a: torch.Tensor, b: torch.Tensor) -> torch.Tensor:
    assert a.ndim == 2 and b.ndim == 2, "Inputs must be 2D tensors"
    M, K1 = a.shape
    K2, N = b.shape
    assert K1 == K2, "Inner dimensions must match"

    assert a.is_cuda and b.is_cuda, "Inputs must be CUDA tensors"
    assert a.device == b.device, "Inputs must be on the same device"
    dtype = a.dtype
    assert dtype in (torch.float16, torch.bfloat16, torch.float32), "Only float16, bfloat16, float32 supported"
    assert b.dtype == dtype, "a and b must have the same dtype"

    # Allocate output
    c = torch.empty((M, N), device=a.device, dtype=dtype)

    # Strides
    stride_am = a.stride(0)
    stride_ak = a.stride(1)
    stride_bk = b.stride(0)
    stride_bn = b.stride(1)
    stride_cm = c.stride(0)
    stride_cn = c.stride(1)

    # Use TF32 if inputs are fp32 and TF32 is allowed
    use_tf32 = (dtype == torch.float32)
    if use_tf32:
        # Respect PyTorch global toggle for TF32 matmul as a hint
        try:
            use_tf32 = bool(torch.backends.cuda.matmul.allow_tf32)
        except Exception:
            use_tf32 = True

    def grid(meta):
        return (
            triton.cdiv(M, meta['BLOCK_M']),
            triton.cdiv(N, meta['BLOCK_N']),
        )

    _matmul_gelu_kernel[grid](
        a, b, c,
        M, N, K1,
        stride_am, stride_ak,
        stride_bk, stride_bn,
        stride_cm, stride_cn,
        use_tf32,
        int(dtype == torch.float16),
        int(dtype == torch.bfloat16),
    )
    return c


class Solution:
    def solve(self, spec_path: str = None) -> dict:
        return {"program_path": __file__}
