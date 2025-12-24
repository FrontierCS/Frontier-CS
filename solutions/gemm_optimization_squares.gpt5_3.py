import os
import textwrap

class Solution:
    def solve(self, spec_path: str = None) -> dict:
        code = r'''
import torch
import triton
import triton.language as tl

@triton.jit
def gelu(x):
    return x * 0.5 * (1.0 + tl.extra.cuda.libdevice.erf(x * 0.7071067811865476))

def _div_up(a, b):
    return (a + b - 1) // b

def _get_autotune_configs():
    return [
        triton.Config(
            {'BLOCK_M': 128, 'BLOCK_N': 128, 'BLOCK_K': 32, 'GROUP_M': 8},
            num_warps=8, num_stages=4
        ),
        triton.Config(
            {'BLOCK_M': 128, 'BLOCK_N': 64, 'BLOCK_K': 32, 'GROUP_M': 8},
            num_warps=4, num_stages=4
        ),
        triton.Config(
            {'BLOCK_M': 64, 'BLOCK_N': 128, 'BLOCK_K': 32, 'GROUP_M': 8},
            num_warps=4, num_stages=4
        ),
        triton.Config(
            {'BLOCK_M': 64, 'BLOCK_N': 64, 'BLOCK_K': 32, 'GROUP_M': 8},
            num_warps=4, num_stages=4
        ),
        triton.Config(
            {'BLOCK_M': 128, 'BLOCK_N': 128, 'BLOCK_K': 64, 'GROUP_M': 4},
            num_warps=8, num_stages=4
        ),
        triton.Config(
            {'BLOCK_M': 128, 'BLOCK_N': 256, 'BLOCK_K': 32, 'GROUP_M': 4},
            num_warps=8, num_stages=4
        ),
        triton.Config(
            {'BLOCK_M': 256, 'BLOCK_N': 128, 'BLOCK_K': 32, 'GROUP_M': 4},
            num_warps=8, num_stages=4
        ),
        triton.Config(
            {'BLOCK_M': 64, 'BLOCK_N': 256, 'BLOCK_K': 32, 'GROUP_M': 4},
            num_warps=8, num_stages=4
        ),
        triton.Config(
            {'BLOCK_M': 256, 'BLOCK_N': 64, 'BLOCK_K': 32, 'GROUP_M': 4},
            num_warps=8, num_stages=4
        ),
    ]

@triton.autotune(configs=_get_autotune_configs(), key=['M', 'N', 'K'])
@triton.jit
def _matmul_gelu_kernel(
    A, B, C,
    M, N, K,
    stride_am, stride_ak,
    stride_bk, stride_bn,
    stride_cm, stride_cn,
    BLOCK_M: tl.constexpr, BLOCK_N: tl.constexpr, BLOCK_K: tl.constexpr,
    GROUP_M: tl.constexpr
):
    pid = tl.program_id(axis=0)
    num_pid_m = tl.cdiv(M, BLOCK_M)
    num_pid_n = tl.cdiv(N, BLOCK_N)

    # Grouped ordering on M to improve L2 hit rate
    group_size = GROUP_M
    num_pid_in_group = group_size * num_pid_n
    group_id = pid // num_pid_in_group
    first_pid_m = group_id * group_size
    pid_in_group = pid % num_pid_in_group
    pid_m = first_pid_m + pid_in_group % group_size
    pid_n = pid_in_group // group_size

    offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
    offs_n = pid_n * BLOCK_N + tl.arange(0, BLOCK_N)
    offs_k = tl.arange(0, BLOCK_K)

    a_ptrs = A + (offs_m[:, None] * stride_am + offs_k[None, :] * stride_ak)
    b_ptrs = B + (offs_k[:, None] * stride_bk + offs_n[None, :] * stride_bn)

    acc = tl.zeros((BLOCK_M, BLOCK_N), dtype=tl.float32)

    k_iter = 0
    while k_iter < K:
        k_mask = offs_k[None, :] + k_iter < K
        a_mask = (offs_m[:, None] < M) & k_mask
        b_mask = k_mask & (offs_n[None, :] < N)
        a = tl.load(a_ptrs, mask=a_mask, other=0.0)
        b = tl.load(b_ptrs, mask=b_mask, other=0.0)
        acc += tl.dot(a, b)
        k_iter += BLOCK_K
        a_ptrs += BLOCK_K * stride_ak
        b_ptrs += BLOCK_K * stride_bk

    acc = gelu(acc)

    c_ptrs = C + (offs_m[:, None] * stride_cm + offs_n[None, :] * stride_cn)
    c_mask = (offs_m[:, None] < M) & (offs_n[None, :] < N)
    # Cast to C's dtype at store
    acc_cast = acc.to(C.dtype.element_ty)
    tl.store(c_ptrs, acc_cast, mask=c_mask)

def _is_supported_dtype(dtype):
    return dtype in (torch.float16, torch.bfloat16, torch.float32)

def _promote_inputs(a: torch.Tensor, b: torch.Tensor):
    # Select a common dtype prioritizing higher precision if inputs differ
    if a.dtype == b.dtype:
        return a, b, a.dtype
    # Preference order: float32 > bfloat16 > float16
    if torch.float32 in (a.dtype, b.dtype):
        dt = torch.float32
    elif torch.bfloat16 in (a.dtype, b.dtype):
        dt = torch.bfloat16
    else:
        dt = torch.float16
    return a.to(dt), b.to(dt), dt

def matmul(a: torch.Tensor, b: torch.Tensor) -> torch.Tensor:
    """
    Matrix multiplication with GELU activation.
    Args:
        a: (M, K)
        b: (K, N)
    Returns:
        (M, N) with GELU applied
    """
    if a.ndim != 2 or b.ndim != 2:
        raise ValueError("Inputs must be 2D tensors")
    if a.shape[1] != b.shape[0]:
        raise ValueError("Incompatible shapes for matmul")
    if not a.is_cuda or not b.is_cuda:
        # CPU fallback
        c = a @ b
        return torch.nn.functional.gelu(c)
    a_prom, b_prom, common_dtype = _promote_inputs(a, b)
    if not _is_supported_dtype(common_dtype):
        # Fallback to torch for unsupported dtypes
        c = a @ b
        return torch.nn.functional.gelu(c)

    M, K = a_prom.shape
    K2, N = b_prom.shape
    assert K2 == K

    # Output tensor
    c = torch.empty((M, N), device=a_prom.device, dtype=common_dtype)

    grid = lambda META: (_div_up(M, META['BLOCK_M']) * _div_up(N, META['BLOCK_N']),)

    _matmul_gelu_kernel[grid](
        a_prom, b_prom, c,
        M, N, K,
        a_prom.stride(0), a_prom.stride(1),
        b_prom.stride(0), b_prom.stride(1),
        c.stride(0), c.stride(1),
    )
    return c
'''
        return {"code": textwrap.dedent(code)}
