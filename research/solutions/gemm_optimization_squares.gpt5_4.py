import torch
import triton
import triton.language as tl


class Solution:
    def solve(self, spec_path: str = None) -> dict:
        code = r'''
import torch
import triton
import triton.language as tl

@triton.jit
def gelu(x):
    return x * 0.5 * (1.0 + tl.extra.cuda.libdevice.erf(x * 0.7071067811865476))


@triton.autotune(
    configs=[
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 128, 'BLOCK_K': 32, 'GROUP_M': 8},  num_stages=4, num_warps=8),
        triton.Config({'BLOCK_M': 64,  'BLOCK_N': 256, 'BLOCK_K': 32, 'GROUP_M': 8},  num_stages=4, num_warps=8),
        triton.Config({'BLOCK_M': 256, 'BLOCK_N': 64,  'BLOCK_K': 32, 'GROUP_M': 8},  num_stages=4, num_warps=8),
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 256, 'BLOCK_K': 32, 'GROUP_M': 8},  num_stages=5, num_warps=8),
        triton.Config({'BLOCK_M': 256, 'BLOCK_N': 128, 'BLOCK_K': 32, 'GROUP_M': 8},  num_stages=5, num_warps=8),
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 128, 'BLOCK_K': 64, 'GROUP_M': 8},  num_stages=4, num_warps=8),
        triton.Config({'BLOCK_M': 64,  'BLOCK_N': 128, 'BLOCK_K': 64, 'GROUP_M': 8},  num_stages=4, num_warps=4),
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 64,  'BLOCK_K': 64, 'GROUP_M': 8},  num_stages=4, num_warps=4),
    ],
    key=['M', 'N', 'K']
)
@triton.jit
def _matmul_gelu_kernel(
    A_ptr, B_ptr, C_ptr,
    M, N, K,
    stride_am, stride_ak,
    stride_bk, stride_bn,
    stride_cm, stride_cn,
    USE_BF16: tl.constexpr,    # if true, compute in bf16 for tl.dot; else use fp16
    OUT_FP32: tl.constexpr,    # store as fp32
    OUT_BF16: tl.constexpr,    # else store as bf16 if true, otherwise fp16
    BLOCK_M: tl.constexpr, BLOCK_N: tl.constexpr, BLOCK_K: tl.constexpr,
    GROUP_M: tl.constexpr
):
    pid = tl.program_id(0)
    num_pid_m = tl.cdiv(M, BLOCK_M)
    num_pid_n = tl.cdiv(N, BLOCK_N)
    group_size = GROUP_M * num_pid_n
    group_id = pid // group_size
    first_pid_m = group_id * GROUP_M
    pid_in_group = pid % group_size
    pid_m = first_pid_m + (pid_in_group % GROUP_M)
    pid_n = pid_in_group // GROUP_M

    offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
    offs_n = pid_n * BLOCK_N + tl.arange(0, BLOCK_N)
    offs_k = tl.arange(0, BLOCK_K)

    a_ptrs = A_ptr + (offs_m[:, None] * stride_am + offs_k[None, :] * stride_ak)
    b_ptrs = B_ptr + (offs_k[:, None] * stride_bk + offs_n[None, :] * stride_bn)

    acc = tl.zeros((BLOCK_M, BLOCK_N), dtype=tl.float32)

    k_iter = 0
    while k_iter < K:
        k_mask = (k_iter + offs_k) < K
        a = tl.load(a_ptrs, mask=(offs_m[:, None] < M) & (k_mask[None, :]), other=0.0)
        b = tl.load(b_ptrs, mask=(k_mask[:, None]) & (offs_n[None, :] < N), other=0.0)

        if USE_BF16:
            a = a.to(tl.bfloat16)
            b = b.to(tl.bfloat16)
        else:
            a = a.to(tl.float16)
            b = b.to(tl.float16)

        acc += tl.dot(a, b)

        a_ptrs += BLOCK_K * stride_ak
        b_ptrs += BLOCK_K * stride_bk
        k_iter += BLOCK_K

    acc = gelu(acc)

    # Write-back
    c_ptrs = C_ptr + (offs_m[:, None] * stride_cm + offs_n[None, :] * stride_cn)
    mask = (offs_m[:, None] < M) & (offs_n[None, :] < N)
    if OUT_FP32:
        out = acc
    elif OUT_BF16:
        out = acc.to(tl.bfloat16)
    else:
        out = acc.to(tl.float16)
    tl.store(c_ptrs, out, mask=mask)


def _result_dtype(a: torch.dtype, b: torch.dtype) -> torch.dtype:
    return torch.result_type(a, b)


def _pick_compute_cast_dtype(a: torch.Tensor, b: torch.Tensor) -> str:
    # Returns "bf16" or "fp16" for the internal tl.dot inputs
    # Prefer bf16 for float32 inputs to preserve range, otherwise follow operands
    if a.dtype == torch.bfloat16 or b.dtype == torch.bfloat16:
        return "bf16"
    if a.dtype == torch.float32 or b.dtype == torch.float32:
        return "bf16"
    # Default to fp16
    return "fp16"


def matmul(a: torch.Tensor, b: torch.Tensor) -> torch.Tensor:
    """
    Matrix multiplication with GELU activation.

    Args:
        a: (M, K)
        b: (K, N)
    Returns:
        (M, N) with GELU applied
    """
    assert a.ndim == 2 and b.ndim == 2, "matmul requires 2D tensors"
    assert a.shape[1] == b.shape[0], "incompatible matrix dimensions"
    assert a.is_cuda and b.is_cuda, "tensors must be on CUDA device"
    M, K = a.shape
    K2, N = b.shape
    out_dtype = _result_dtype(a.dtype, b.dtype)
    c = torch.empty((M, N), device=a.device, dtype=out_dtype)

    USE_BF16 = _pick_compute_cast_dtype(a, b) == "bf16"
    OUT_FP32 = out_dtype == torch.float32
    OUT_BF16 = out_dtype == torch.bfloat16

    grid = lambda META: (triton.cdiv(M, META['BLOCK_M']) * triton.cdiv(N, META['BLOCK_N']),)

    _matmul_gelu_kernel[grid](
        a, b, c,
        M, N, K,
        a.stride(0), a.stride(1),
        b.stride(0), b.stride(1),
        c.stride(0), c.stride(1),
        USE_BF16=USE_BF16,
        OUT_FP32=OUT_FP32,
        OUT_BF16=OUT_BF16,
    )
    return c
'''
        return {"code": code}