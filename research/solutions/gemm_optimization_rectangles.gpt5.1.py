import torch
import torch.nn.functional as F
import triton
import triton.language as tl
import sys
import inspect


@triton.jit
def gelu(x):
    return x * 0.5 * (1.0 + tl.extra.cuda.libdevice.erf(x * 0.7071067811865476))


_matmul_configs = [
    triton.Config(
        {'BLOCK_M': 128, 'BLOCK_N': 128, 'BLOCK_K': 32, 'GROUP_M': 8},
        num_stages=3,
        num_warps=8,
    ),
    triton.Config(
        {'BLOCK_M': 64, 'BLOCK_N': 128, 'BLOCK_K': 32, 'GROUP_M': 8},
        num_stages=4,
        num_warps=4,
    ),
    triton.Config(
        {'BLOCK_M': 128, 'BLOCK_N': 64, 'BLOCK_K': 32, 'GROUP_M': 8},
        num_stages=4,
        num_warps=4,
    ),
    triton.Config(
        {'BLOCK_M': 64, 'BLOCK_N': 64, 'BLOCK_K': 32, 'GROUP_M': 8},
        num_stages=4,
        num_warps=4,
    ),
    triton.Config(
        {'BLOCK_M': 256, 'BLOCK_N': 64, 'BLOCK_K': 32, 'GROUP_M': 4},
        num_stages=4,
        num_warps=8,
    ),
    triton.Config(
        {'BLOCK_M': 64, 'BLOCK_N': 256, 'BLOCK_K': 32, 'GROUP_M': 4},
        num_stages=4,
        num_warps=8,
    ),
    triton.Config(
        {'BLOCK_M': 256, 'BLOCK_N': 128, 'BLOCK_K': 32, 'GROUP_M': 4},
        num_stages=4,
        num_warps=8,
    ),
    triton.Config(
        {'BLOCK_M': 128, 'BLOCK_N': 256, 'BLOCK_K': 32, 'GROUP_M': 4},
        num_stages=4,
        num_warps=8,
    ),
]


@triton.autotune(configs=_matmul_configs, key=['M', 'N', 'K'])
@triton.jit
def _matmul_kernel(
    A, B, C,
    M, N, K,
    stride_am, stride_ak,
    stride_bk, stride_bn,
    stride_cm, stride_cn,
    BLOCK_M: tl.constexpr, BLOCK_N: tl.constexpr, BLOCK_K: tl.constexpr,
    GROUP_M: tl.constexpr,
):
    pid = tl.program_id(axis=0)

    num_pid_m = tl.cdiv(M, BLOCK_M)
    num_pid_n = tl.cdiv(N, BLOCK_N)

    num_pid_in_group = GROUP_M * num_pid_n
    group_id = pid // num_pid_in_group
    first_pid_m = group_id * GROUP_M
    group_size_m = tl.minimum(num_pid_m - first_pid_m, GROUP_M)
    pid_in_group = pid % num_pid_in_group

    pid_m = first_pid_m + (pid_in_group % group_size_m)
    pid_n = pid_in_group // group_size_m

    offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
    offs_n = pid_n * BLOCK_N + tl.arange(0, BLOCK_N)

    offs_m_broadcast = offs_m[:, None]
    offs_n_broadcast = offs_n[None, :]

    acc = tl.zeros((BLOCK_M, BLOCK_N), dtype=tl.float32)

    k = 0
    while k < K:
        offs_k = k + tl.arange(0, BLOCK_K)

        a_ptrs = A + offs_m_broadcast * stride_am + offs_k[None, :] * stride_ak
        b_ptrs = B + offs_k[:, None] * stride_bk + offs_n_broadcast * stride_bn

        a_mask = (offs_m_broadcast < M) & (offs_k[None, :] < K)
        b_mask = (offs_k[:, None] < K) & (offs_n_broadcast < N)

        a = tl.load(a_ptrs, mask=a_mask, other=0.0)
        b = tl.load(b_ptrs, mask=b_mask, other=0.0)

        acc += tl.dot(a, b)

        k += BLOCK_K

    acc = gelu(acc)

    c_ptrs = C + offs_m_broadcast * stride_cm + offs_n_broadcast * stride_cn
    c_mask = (offs_m_broadcast < M) & (offs_n_broadcast < N)
    tl.store(c_ptrs, acc, mask=c_mask)


def _launch_triton_matmul(a: torch.Tensor, b: torch.Tensor) -> torch.Tensor:
    M, K = a.shape
    K2, N = b.shape
    if K2 != K:
        raise ValueError(f"Incompatible shapes for matmul: {a.shape} and {b.shape}")

    c = torch.empty((M, N), device=a.device, dtype=a.dtype)

    grid = lambda META: (
        triton.cdiv(M, META['BLOCK_M']) * triton.cdiv(N, META['BLOCK_N']),
    )

    _matmul_kernel[grid](
        a, b, c,
        M, N, K,
        a.stride(0), a.stride(1),
        b.stride(0), b.stride(1),
        c.stride(0), c.stride(1),
    )
    return c


def matmul(a: torch.Tensor, b: torch.Tensor) -> torch.Tensor:
    if a.ndim != 2 or b.ndim != 2:
        raise ValueError("matmul expects 2D tensors")

    if a.device.type != 'cuda' or b.device.type != 'cuda':
        return F.gelu(a @ b)

    if a.dtype != b.dtype:
        return F.gelu(a.float() @ b.float()).to(torch.result_type(a, b))

    if a.dtype not in (torch.float16, torch.float32, torch.bfloat16):
        return F.gelu(a @ b)

    return _launch_triton_matmul(a, b)


class Solution:
    def solve(self, spec_path: str = None) -> dict:
        try:
            source = inspect.getsource(sys.modules[__name__])
        except OSError:
            return {"program_path": __file__}
        return {"code": source}