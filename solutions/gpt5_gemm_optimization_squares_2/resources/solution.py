import torch
import triton
import triton.language as tl


@triton.jit
def gelu(x):
    return x * 0.5 * (1.0 + tl.extra.cuda.libdevice.erf(x * 0.7071067811865476))


@triton.autotune(
    configs=[
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 128, 'BLOCK_K': 32, 'GROUP_M': 8}, num_stages=3, num_warps=8),
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 64,  'BLOCK_K': 32, 'GROUP_M': 8}, num_stages=4, num_warps=4),
        triton.Config({'BLOCK_M': 64,  'BLOCK_N': 128, 'BLOCK_K': 32, 'GROUP_M': 8}, num_stages=4, num_warps=4),
        triton.Config({'BLOCK_M': 64,  'BLOCK_N': 64,  'BLOCK_K': 32, 'GROUP_M': 8}, num_stages=3, num_warps=4),
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 256, 'BLOCK_K': 32, 'GROUP_M': 4}, num_stages=4, num_warps=8),
        triton.Config({'BLOCK_M': 256, 'BLOCK_N': 128, 'BLOCK_K': 32, 'GROUP_M': 4}, num_stages=4, num_warps=8),
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 128, 'BLOCK_K': 64, 'GROUP_M': 8}, num_stages=4, num_warps=8),
    ],
    key=['M', 'N', 'K'],
)
@triton.jit
def _matmul_gelu_kernel(
    a_ptr, b_ptr, c_ptr,
    M, N, K,
    stride_am, stride_ak,
    stride_bk, stride_bn,
    stride_cm, stride_cn,
    OUT_FP16: tl.constexpr, OUT_BF16: tl.constexpr, OUT_FP32: tl.constexpr,
    BLOCK_M: tl.constexpr, BLOCK_N: tl.constexpr, BLOCK_K: tl.constexpr,
    GROUP_M: tl.constexpr,
):
    pid_m = tl.program_id(axis=0)
    pid_n = tl.program_id(axis=1)

    offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
    offs_n = pid_n * BLOCK_N + tl.arange(0, BLOCK_N)
    offs_k = tl.arange(0, BLOCK_K)

    a_ptrs = a_ptr + (offs_m[:, None] * stride_am + offs_k[None, :] * stride_ak)
    b_ptrs = b_ptr + (offs_k[:, None] * stride_bk + offs_n[None, :] * stride_bn)

    acc = tl.zeros((BLOCK_M, BLOCK_N), dtype=tl.float32)

    k_iter = tl.cdiv(K, BLOCK_K)
    for _ in range(0, k_iter):
        k_current = _ * BLOCK_K
        a_mask = (offs_m[:, None] < M) & (k_current + offs_k[None, :] < K)
        b_mask = (k_current + offs_k[:, None] < K) & (offs_n[None, :] < N)

        a = tl.load(a_ptrs, mask=a_mask, other=0.0)
        b = tl.load(b_ptrs, mask=b_mask, other=0.0)

        acc += tl.dot(a, b)

        a_ptrs += BLOCK_K * stride_ak
        b_ptrs += BLOCK_K * stride_bk

    acc = gelu(acc)

    c_ptrs = c_ptr + (offs_m[:, None] * stride_cm + offs_n[None, :] * stride_cn)
    c_mask = (offs_m[:, None] < M) & (offs_n[None, :] < N)

    out = acc
    if OUT_FP16:
        out = out.to(tl.float16)
    elif OUT_BF16:
        out = out.to(tl.bfloat16)
    elif OUT_FP32:
        out = out.to(tl.float32)

    tl.store(c_ptrs, out, mask=c_mask)


def matmul(a: torch.Tensor, b: torch.Tensor) -> torch.Tensor:
    if a.ndim != 2 or b.ndim != 2:
        raise ValueError("Inputs must be 2D tensors")
    if a.shape[1] != b.shape[0]:
        raise ValueError("Inner dimensions must match")
    if not a.is_cuda or not b.is_cuda:
        raise ValueError("Inputs must be CUDA tensors")

    M, K = a.shape
    K2, N = b.shape
    assert K2 == K

    dtype = a.dtype
    if dtype != b.dtype:
        raise ValueError("Input tensors must have the same dtype")
    supported = dtype in (torch.float16, torch.bfloat16, torch.float32)

    # Choose output dtype: match input dtype if fp16/bf16, else fp32
    if dtype in (torch.float16, torch.bfloat16):
        out_dtype = dtype
        out_fp16 = int(dtype == torch.float16)
        out_bf16 = int(dtype == torch.bfloat16)
        out_fp32 = 0
    elif dtype == torch.float32:
        # Compute in triton and output fp32, but will be slower; fallback if extremely small
        out_dtype = torch.float32
        out_fp16 = 0
        out_bf16 = 0
        out_fp32 = 1
    else:
        # unsupported dtype: fallback to PyTorch
        out = a @ b
        return out * 0.5 * (1.0 + torch.erf(out * 0.7071067811865476))

    c = torch.empty((M, N), device=a.device, dtype=out_dtype)

    grid = (
        triton.cdiv(M, 128),  # heuristic, autotuner will adjust
        triton.cdiv(N, 128),
    )
    # Launch kernel
    _matmul_gelu_kernel[grid](
        a, b, c,
        M, N, K,
        a.stride(0), a.stride(1),
        b.stride(0), b.stride(1),
        c.stride(0), c.stride(1),
        OUT_FP16=out_fp16, OUT_BF16=out_bf16, OUT_FP32=out_fp32,
    )
    return c


class Solution:
    def solve(self, spec_path: str = None) -> dict:
        code = '''
import torch
import triton
import triton.language as tl


@triton.jit
def gelu(x):
    return x * 0.5 * (1.0 + tl.extra.cuda.libdevice.erf(x * 0.7071067811865476))


@triton.autotune(
    configs=[
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 128, 'BLOCK_K': 32, 'GROUP_M': 8}, num_stages=3, num_warps=8),
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 64,  'BLOCK_K': 32, 'GROUP_M': 8}, num_stages=4, num_warps=4),
        triton.Config({'BLOCK_M': 64,  'BLOCK_N': 128, 'BLOCK_K': 32, 'GROUP_M': 8}, num_stages=4, num_warps=4),
        triton.Config({'BLOCK_M': 64,  'BLOCK_N': 64,  'BLOCK_K': 32, 'GROUP_M': 8}, num_stages=3, num_warps=4),
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 256, 'BLOCK_K': 32, 'GROUP_M': 4}, num_stages=4, num_warps=8),
        triton.Config({'BLOCK_M': 256, 'BLOCK_N': 128, 'BLOCK_K': 32, 'GROUP_M': 4}, num_stages=4, num_warps=8),
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 128, 'BLOCK_K': 64, 'GROUP_M': 8}, num_stages=4, num_warps=8),
    ],
    key=['M', 'N', 'K'],
)
@triton.jit
def _matmul_gelu_kernel(
    a_ptr, b_ptr, c_ptr,
    M, N, K,
    stride_am, stride_ak,
    stride_bk, stride_bn,
    stride_cm, stride_cn,
    OUT_FP16: tl.constexpr, OUT_BF16: tl.constexpr, OUT_FP32: tl.constexpr,
    BLOCK_M: tl.constexpr, BLOCK_N: tl.constexpr, BLOCK_K: tl.constexpr,
    GROUP_M: tl.constexpr,
):
    pid_m = tl.program_id(axis=0)
    pid_n = tl.program_id(axis=1)

    offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
    offs_n = pid_n * BLOCK_N + tl.arange(0, BLOCK_N)
    offs_k = tl.arange(0, BLOCK_K)

    a_ptrs = a_ptr + (offs_m[:, None] * stride_am + offs_k[None, :] * stride_ak)
    b_ptrs = b_ptr + (offs_k[:, None] * stride_bk + offs_n[None, :] * stride_bn)

    acc = tl.zeros((BLOCK_M, BLOCK_N), dtype=tl.float32)

    k_iter = tl.cdiv(K, BLOCK_K)
    for _ in range(0, k_iter):
        k_current = _ * BLOCK_K
        a_mask = (offs_m[:, None] < M) & (k_current + offs_k[None, :] < K)
        b_mask = (k_current + offs_k[:, None] < K) & (offs_n[None, :] < N)

        a = tl.load(a_ptrs, mask=a_mask, other=0.0)
        b = tl.load(b_ptrs, mask=b_mask, other=0.0)

        acc += tl.dot(a, b)

        a_ptrs += BLOCK_K * stride_ak
        b_ptrs += BLOCK_K * stride_bk

    acc = gelu(acc)

    c_ptrs = c_ptr + (offs_m[:, None] * stride_cm + offs_n[None, :] * stride_cn)
    c_mask = (offs_m[:, None] < M) & (offs_n[None, :] < N)

    out = acc
    if OUT_FP16:
        out = out.to(tl.float16)
    elif OUT_BF16:
        out = out.to(tl.bfloat16)
    elif OUT_FP32:
        out = out.to(tl.float32)

    tl.store(c_ptrs, out, mask=c_mask)


def matmul(a: torch.Tensor, b: torch.Tensor) -> torch.Tensor:
    if a.ndim != 2 or b.ndim != 2:
        raise ValueError("Inputs must be 2D tensors")
    if a.shape[1] != b.shape[0]:
        raise ValueError("Inner dimensions must match")
    if not a.is_cuda or not b.is_cuda:
        raise ValueError("Inputs must be CUDA tensors")

    M, K = a.shape
    K2, N = b.shape
    assert K2 == K

    dtype = a.dtype
    if dtype != b.dtype:
        raise ValueError("Input tensors must have the same dtype")
    if dtype in (torch.float16, torch.bfloat16):
        out_dtype = dtype
        out_fp16 = int(dtype == torch.float16)
        out_bf16 = int(dtype == torch.bfloat16)
        out_fp32 = 0
    elif dtype == torch.float32:
        out_dtype = torch.float32
        out_fp16 = 0
        out_bf16 = 0
        out_fp32 = 1
    else:
        out = a @ b
        return out * 0.5 * (1.0 + torch.erf(out * 0.7071067811865476))

    c = torch.empty((M, N), device=a.device, dtype=out_dtype)

    grid = (
        triton.cdiv(M, 128),
        triton.cdiv(N, 128),
    )

    _matmul_gelu_kernel[grid](
        a, b, c,
        M, N, K,
        a.stride(0), a.stride(1),
        b.stride(0), b.stride(1),
        c.stride(0), c.stride(1),
        OUT_FP16=out_fp16, OUT_BF16=out_bf16, OUT_FP32=out_fp32,
    )
    return c
'''
        return {"code": code}
