import os
import torch
import torch.nn.functional as F
import triton
import triton.language as tl


@triton.jit
def gelu(x):
    return x * 0.5 * (1.0 + tl.extra.cuda.libdevice.erf(x * 0.7071067811865476))


matmul_configs = [
    triton.Config({"BLOCK_M": 128, "BLOCK_N": 128, "BLOCK_K": 32}, num_warps=8, num_stages=3),
    triton.Config({"BLOCK_M": 64, "BLOCK_N": 128, "BLOCK_K": 32}, num_warps=4, num_stages=4),
    triton.Config({"BLOCK_M": 128, "BLOCK_N": 64, "BLOCK_K": 32}, num_warps=4, num_stages=4),
    triton.Config({"BLOCK_M": 64, "BLOCK_N": 64, "BLOCK_K": 32}, num_warps=4, num_stages=3),
    triton.Config({"BLOCK_M": 256, "BLOCK_N": 64, "BLOCK_K": 32}, num_warps=8, num_stages=3),
    triton.Config({"BLOCK_M": 64, "BLOCK_N": 256, "BLOCK_K": 32}, num_warps=8, num_stages=3),
]


@triton.autotune(configs=matmul_configs, key=["M", "N", "K"])
@triton.jit
def matmul_kernel_fp16(
    A_ptr: tl.pointer_type(dtype=tl.float16),
    B_ptr: tl.pointer_type(dtype=tl.float16),
    C_ptr: tl.pointer_type(dtype=tl.float16),
    M,
    N,
    K,
    stride_am,
    stride_ak,
    stride_bk,
    stride_bn,
    stride_cm,
    stride_cn,
    BLOCK_M: tl.constexpr,
    BLOCK_N: tl.constexpr,
    BLOCK_K: tl.constexpr,
):
    pid_m = tl.program_id(axis=0)
    pid_n = tl.program_id(axis=1)

    offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
    offs_n = pid_n * BLOCK_N + tl.arange(0, BLOCK_N)
    offs_k = tl.arange(0, BLOCK_K)

    a_ptrs = A_ptr + offs_m[:, None] * stride_am + offs_k[None, :] * stride_ak
    b_ptrs = B_ptr + offs_k[:, None] * stride_bk + offs_n[None, :] * stride_bn

    acc = tl.zeros((BLOCK_M, BLOCK_N), dtype=tl.float32)

    num_k = tl.cdiv(K, BLOCK_K)
    for _ in range(0, num_k):
        a_mask = (offs_m[:, None] < M) & (offs_k[None, :] < K)
        b_mask = (offs_k[:, None] < K) & (offs_n[None, :] < N)
        a = tl.load(a_ptrs, mask=a_mask, other=0.0)
        b = tl.load(b_ptrs, mask=b_mask, other=0.0)
        acc += tl.dot(a, b, out_dtype=tl.float32)
        a_ptrs += BLOCK_K * stride_ak
        b_ptrs += BLOCK_K * stride_bk
        offs_k += BLOCK_K

    acc = gelu(acc)

    offs_m_broadcast = offs_m[:, None]
    offs_n_broadcast = offs_n[None, :]
    c_ptrs = C_ptr + offs_m_broadcast * stride_cm + offs_n_broadcast * stride_cn
    c_mask = (offs_m_broadcast < M) & (offs_n_broadcast < N)
    c = acc.to(tl.float16)
    tl.store(c_ptrs, c, mask=c_mask)


@triton.autotune(configs=matmul_configs, key=["M", "N", "K"])
@triton.jit
def matmul_kernel_fp32(
    A_ptr: tl.pointer_type(dtype=tl.float32),
    B_ptr: tl.pointer_type(dtype=tl.float32),
    C_ptr: tl.pointer_type(dtype=tl.float32),
    M,
    N,
    K,
    stride_am,
    stride_ak,
    stride_bk,
    stride_bn,
    stride_cm,
    stride_cn,
    BLOCK_M: tl.constexpr,
    BLOCK_N: tl.constexpr,
    BLOCK_K: tl.constexpr,
):
    pid_m = tl.program_id(axis=0)
    pid_n = tl.program_id(axis=1)

    offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
    offs_n = pid_n * BLOCK_N + tl.arange(0, BLOCK_N)
    offs_k = tl.arange(0, BLOCK_K)

    a_ptrs = A_ptr + offs_m[:, None] * stride_am + offs_k[None, :] * stride_ak
    b_ptrs = B_ptr + offs_k[:, None] * stride_bk + offs_n[None, :] * stride_bn

    acc = tl.zeros((BLOCK_M, BLOCK_N), dtype=tl.float32)

    num_k = tl.cdiv(K, BLOCK_K)
    for _ in range(0, num_k):
        a_mask = (offs_m[:, None] < M) & (offs_k[None, :] < K)
        b_mask = (offs_k[:, None] < K) & (offs_n[None, :] < N)
        a = tl.load(a_ptrs, mask=a_mask, other=0.0)
        b = tl.load(b_ptrs, mask=b_mask, other=0.0)
        acc += tl.dot(a, b)
        a_ptrs += BLOCK_K * stride_ak
        b_ptrs += BLOCK_K * stride_bk
        offs_k += BLOCK_K

    acc = gelu(acc)

    offs_m_broadcast = offs_m[:, None]
    offs_n_broadcast = offs_n[None, :]
    c_ptrs = C_ptr + offs_m_broadcast * stride_cm + offs_n_broadcast * stride_cn
    c_mask = (offs_m_broadcast < M) & (offs_n_broadcast < N)
    tl.store(c_ptrs, acc, mask=c_mask)


def matmul(a: torch.Tensor, b: torch.Tensor) -> torch.Tensor:
    if a.ndim != 2 or b.ndim != 2:
        raise ValueError("matmul expects 2D tensors")
    if a.shape[1] != b.shape[0]:
        raise ValueError("Incompatible shapes for matmul")
    if not a.is_cuda or not b.is_cuda:
        return F.gelu(a @ b)

    if a.dtype != b.dtype:
        # Upcast to float32 for mixed dtypes
        dtype = torch.float32
        a = a.to(dtype)
        b = b.to(dtype)
    else:
        dtype = a.dtype

    if dtype not in (torch.float16, torch.float32, torch.bfloat16):
        dtype = torch.float32
        a = a.to(dtype)
        b = b.to(dtype)

    # Handle bfloat16 by converting to float16 for kernel
    if dtype == torch.bfloat16:
        a = a.to(torch.float16)
        b = b.to(torch.float16)
        dtype = torch.float16

    M, K = a.shape
    Kb, N = b.shape
    if Kb != K:
        raise ValueError("Inner dimensions must match")

    # Make tensors contiguous for better performance
    if not a.is_contiguous():
        a = a.contiguous()
    if not b.is_contiguous():
        b = b.contiguous()

    c = torch.empty((M, N), device=a.device, dtype=dtype)

    stride_am, stride_ak = a.stride()
    stride_bk, stride_bn = b.stride()
    stride_cm, stride_cn = c.stride()

    def grid(meta):
        return (
            triton.cdiv(M, meta["BLOCK_M"]),
            triton.cdiv(N, meta["BLOCK_N"]),
        )

    if dtype == torch.float16:
        matmul_kernel_fp16[grid](
            a,
            b,
            c,
            M,
            N,
            K,
            stride_am,
            stride_ak,
            stride_bk,
            stride_bn,
            stride_cm,
            stride_cn,
        )
    else:
        matmul_kernel_fp32[grid](
            a,
            b,
            c,
            M,
            N,
            K,
            stride_am,
            stride_ak,
            stride_bk,
            stride_bn,
            stride_cm,
            stride_cn,
        )

    return c


class Solution:
    def solve(self, spec_path: str = None) -> dict:
        return {"program_path": os.path.abspath(__file__)}
