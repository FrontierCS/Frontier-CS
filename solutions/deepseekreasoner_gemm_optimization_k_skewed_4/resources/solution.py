import torch
import triton
import triton.language as tl
from typing import Optional, Dict, Any
import os


@triton.jit
def gelu(x):
    return x * 0.5 * (1.0 + tl.extra.cuda.libdevice.erf(x * 0.7071067811865476))


@triton.jit
def _matmul_kernel(
    a_ptr, b_ptr, c_ptr,
    M, N, K,
    stride_am, stride_ak,
    stride_bk, stride_bn,
    stride_cm, stride_cn,
    BLOCK_M: tl.constexpr,
    BLOCK_N: tl.constexpr,
    BLOCK_K: tl.constexpr,
    GROUP_M: tl.constexpr,
    EVEN_K: tl.constexpr,
    ACC_TYPE: tl.constexpr,
):
    pid = tl.program_id(0)
    num_pid_m = tl.cdiv(M, BLOCK_M)
    num_pid_n = tl.cdiv(N, BLOCK_N)
    num_pid_in_group = GROUP_M * num_pid_n
    group_id = pid // num_pid_in_group
    first_pid_m = group_id * GROUP_M
    group_size_m = min(num_pid_m - first_pid_m, GROUP_M)
    pid_m = first_pid_m + (pid % group_size_m)
    pid_n = (pid % num_pid_in_group) // group_size_m
    
    offs_am = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
    offs_bn = pid_n * BLOCK_N + tl.arange(0, BLOCK_N)
    offs_k = tl.arange(0, BLOCK_K)
    
    a_ptrs = a_ptr + (offs_am[:, None] * stride_am + offs_k[None, :] * stride_ak)
    b_ptrs = b_ptr + (offs_k[:, None] * stride_bk + offs_bn[None, :] * stride_bn)
    
    accumulator = tl.zeros((BLOCK_M, BLOCK_N), dtype=ACC_TYPE)
    
    if EVEN_K:
        for k in range(0, K, BLOCK_K):
            a = tl.load(a_ptrs, mask=offs_k[None, :] < K - k, other=0.0)
            b = tl.load(b_ptrs, mask=offs_k[:, None] < K - k, other=0.0)
            accumulator += tl.dot(a, b, allow_tf32=False)
            a_ptrs += BLOCK_K * stride_ak
            b_ptrs += BLOCK_K * stride_bk
    else:
        for k in range(0, K, BLOCK_K):
            k_remaining = K - k
            a_mask = (offs_am[:, None] < M) & (offs_k[None, :] < k_remaining)
            b_mask = (offs_k[:, None] < k_remaining) & (offs_bn[None, :] < N)
            a = tl.load(a_ptrs, mask=a_mask, other=0.0)
            b = tl.load(b_ptrs, mask=b_mask, other=0.0)
            accumulator += tl.dot(a, b, allow_tf32=False)
            a_ptrs += BLOCK_K * stride_ak
            b_ptrs += BLOCK_K * stride_bk
    
    c_ptrs = c_ptr + stride_cm * offs_am[:, None] + stride_cn * offs_bn[None, :]
    c_mask = (offs_am[:, None] < M) & (offs_bn[None, :] < N)
    c = gelu(accumulator.to(c_ptr.dtype.element_ty))
    tl.store(c_ptrs, c, mask=c_mask)


def matmul(a: torch.Tensor, b: torch.Tensor) -> torch.Tensor:
    assert a.shape[1] == b.shape[0], "Incompatible dimensions"
    assert a.is_cuda and b.is_cuda, "Inputs must be on GPU"
    
    M, K = a.shape
    K, N = b.shape
    
    c = torch.empty((M, N), device=a.device, dtype=a.dtype)
    
    def get_configs():
        configs = []
        for block_m in [64, 128]:
            for block_n in [64, 128]:
                for block_k in [32, 64, 128]:
                    for group_m in [8]:
                        for num_warps in [4, 8]:
                            for num_stages in [3, 4, 5]:
                                configs.append(triton.Config({
                                    'BLOCK_M': block_m,
                                    'BLOCK_N': block_n,
                                    'BLOCK_K': block_k,
                                    'GROUP_M': group_m,
                                }, num_warps=num_warps, num_stages=num_stages))
        return configs
    
    @triton.autotune(
        configs=get_configs(),
        key=['M', 'N', 'K'],
    )
    @triton.jit
    def tuned_matmul_kernel(
        a_ptr, b_ptr, c_ptr,
        M, N, K,
        stride_am, stride_ak,
        stride_bk, stride_bn,
        stride_cm, stride_cn,
        BLOCK_M: tl.constexpr,
        BLOCK_N: tl.constexpr,
        BLOCK_K: tl.constexpr,
        GROUP_M: tl.constexpr,
    ):
        _matmul_kernel(
            a_ptr, b_ptr, c_ptr,
            M, N, K,
            stride_am, stride_ak,
            stride_bk, stride_bn,
            stride_cm, stride_cn,
            BLOCK_M, BLOCK_N, BLOCK_K,
            GROUP_M, EVEN_K=(K % BLOCK_K == 0),
            ACC_TYPE=tl.float32 if a.dtype == torch.float32 else tl.float16,
        )
    
    grid = lambda META: (
        triton.cdiv(M, META['BLOCK_M']) * triton.cdiv(N, META['BLOCK_N']),
    )
    
    tuned_matmul_kernel[grid](
        a, b, c,
        M, N, K,
        a.stride(0), a.stride(1),
        b.stride(0), b.stride(1),
        c.stride(0), c.stride(1),
    )
    
    return c


class Solution:
    def solve(self, spec_path: Optional[str] = None) -> Dict[str, Any]:
        if spec_path:
            with open(spec_path, 'w') as f:
                f.write((
                    "import torch\nimport triton\nimport triton.language as tl\n\n"
                    + "from typing import Optional\n\n"
                    + "@triton.jit\ndef gelu(x):\n"
                    + "    return x * 0.5 * (1.0 + tl.extra.cuda.libdevice.erf(x * 0.7071067811865476))\n\n"
                    + "@triton.jit\ndef _matmul_kernel(a_ptr, b_ptr, c_ptr, M, N, K, stride_am, stride_ak, stride_bk, stride_bn, stride_cm, stride_cn, BLOCK_M: tl.constexpr, BLOCK_N: tl.constexpr, BLOCK_K: tl.constexpr, GROUP_M: tl.constexpr, EVEN_K: tl.constexpr, ACC_TYPE: tl.constexpr):\n"
                    + "    pid = tl.program_id(0)\n    num_pid_m = tl.cdiv(M, BLOCK_M)\n    num_pid_n = tl.cdiv(N, BLOCK_N)\n    num_pid_in_group = GROUP_M * num_pid_n\n    group_id = pid // num_pid_in_group\n    first_pid_m = group_id * GROUP_M\n    group_size_m = min(num_pid_m - first_pid_m, GROUP_M)\n    pid_m = first_pid_m + (pid % group_size_m)\n    pid_n = (pid % num_pid_in_group) // group_size_m\n    \n    offs_am = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)\n    offs_bn = pid_n * BLOCK_N + tl.arange(0, BLOCK_N)\n    offs_k = tl.arange(0, BLOCK_K)\n    \n    a_ptrs = a_ptr + (offs_am[:, None] * stride_am + offs_k[None, :] * stride_ak)\n    b_ptrs = b_ptr + (offs_k[:, None] * stride_bk + offs_bn[None, :] * stride_bn)\n    \n    accumulator = tl.zeros((BLOCK_M, BLOCK_N), dtype=ACC_TYPE)\n    \n    if EVEN_K:\n        for k in range(0, K, BLOCK_K):\n            a = tl.load(a_ptrs, mask=offs_k[None, :] < K - k, other=0.0)\n            b = tl.load(b_ptrs, mask=offs_k[:, None] < K - k, other=0.0)\n            accumulator += tl.dot(a, b, allow_tf32=False)\n            a_ptrs += BLOCK_K * stride_ak\n            b_ptrs += BLOCK_K * stride_bk\n    else:\n        for k in range(0, K, BLOCK_K):\n            k_remaining = K - k\n            a_mask = (offs_am[:, None] < M) & (offs_k[None, :] < k_remaining)\n            b_mask = (offs_k[:, None] < k_remaining) & (offs_bn[None, :] < N)\n            a = tl.load(a_ptrs, mask=a_mask, other=0.0)\n            b = tl.load(b_ptrs, mask=b_mask, other=0.0)\n            accumulator += tl.dot(a, b, allow_tf32=False)\n            a_ptrs += BLOCK_K * stride_ak\n            b_ptrs += BLOCK_K * stride_bk\n    \n    c_ptrs = c_ptr + stride_cm * offs_am[:, None] + stride_cn * offs_bn[None, :]\n    c_mask = (offs_am[:, None] < M) & (offs_bn[None, :] < N)\n    c = gelu(accumulator.to(c_ptr.dtype.element_ty))\n    tl.store(c_ptrs, c, mask=c_mask)\n\n"
                    + "def matmul(a: torch.Tensor, b: torch.Tensor) -> torch.Tensor:\n"
                    + "    assert a.shape[1] == b.shape[0], \"Incompatible dimensions\"\n    assert a.is_cuda and b.is_cuda, \"Inputs must be on GPU\"\n    \n    M, K = a.shape\n    K, N = b.shape\n    \n    c = torch.empty((M, N), device=a.device, dtype=a.dtype)\n    \n    def get_configs():\n        configs = []\n        for block_m in [64, 128]:\n            for block_n in [64, 128]:\n                for block_k in [32, 64, 128]:\n                    for group_m in [8]:\n                        for num_warps in [4, 8]:\n                            for num_stages in [3, 4, 5]:\n                                configs.append(triton.Config({\n                                    'BLOCK_M': block_m,\n                                    'BLOCK_N': block_n,\n                                    'BLOCK_K': block_k,\n                                    'GROUP_M': group_m,\n                                }, num_warps=num_warps, num_stages=num_stages))\n        return configs\n    \n    @triton.autotune(\n        configs=get_configs(),\n        key=['M', 'N', 'K'],\n    )\n    @triton.jit\n    def tuned_matmul_kernel(a_ptr, b_ptr, c_ptr, M, N, K, stride_am, stride_ak, stride_bk, stride_bn, stride_cm, stride_cn, BLOCK_M: tl.constexpr, BLOCK_N: tl.constexpr, BLOCK_K: tl.constexpr, GROUP_M: tl.constexpr):\n        _matmul_kernel(\n            a_ptr, b_ptr, c_ptr,\n            M, N, K,\n            stride_am, stride_ak,\n            stride_bk, stride_bn,\n            stride_cm, stride_cn,\n            BLOCK_M, BLOCK_N, BLOCK_K,\n            GROUP_M, EVEN_K=(K % BLOCK_K == 0),\n            ACC_TYPE=tl.float32 if a.dtype == torch.float32 else tl.float16,\n        )\n    \n    grid = lambda META: (\n        triton.cdiv(M, META['BLOCK_M']) * triton.cdiv(N, META['BLOCK_N']),\n    )\n    \n    tuned_matmul_kernel[grid](\n        a, b, c,\n        M, N, K,\n        a.stride(0), a.stride(1),\n        b.stride(0), b.stride(1),\n        c.stride(0), c.stride(1),\n    )\n    \n    return c\n"
                ))
            return {"program_path": spec_path}
        else:
            code = (
                "import torch\nimport triton\nimport triton.language as tl\n\n"
                + "from typing import Optional\n\n"
                + "@triton.jit\ndef gelu(x):\n"
                + "    return x * 0.5 * (1.0 + tl.extra.cuda.libdevice.erf(x * 0.7071067811865476))\n\n"
                + "@triton.jit\ndef _matmul_kernel(a_ptr, b_ptr, c_ptr, M, N, K, stride_am, stride_ak, stride_bk, stride_bn, stride_cm, stride_cn, BLOCK_M: tl.constexpr, BLOCK_N: tl.constexpr, BLOCK_K: tl.constexpr, GROUP_M: tl.constexpr, EVEN_K: tl.constexpr, ACC_TYPE: tl.constexpr):\n"
                + "    pid = tl.program_id(0)\n    num_pid_m = tl.cdiv(M, BLOCK_M)\n    num_pid_n = tl.cdiv(N, BLOCK_N)\n    num_pid_in_group = GROUP_M * num_pid_n\n    group_id = pid // num_pid_in_group\n    first_pid_m = group_id * GROUP_M\n    group_size_m = min(num_pid_m - first_pid_m, GROUP_M)\n    pid_m = first_pid_m + (pid % group_size_m)\n    pid_n = (pid % num_pid_in_group) // group_size_m\n    \n    offs_am = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)\n    offs_bn = pid_n * BLOCK_N + tl.arange(0, BLOCK_N)\n    offs_k = tl.arange(0, BLOCK_K)\n    \n    a_ptrs = a_ptr + (offs_am[:, None] * stride_am + offs_k[None, :] * stride_ak)\n    b_ptrs = b_ptr + (offs_k[:, None] * stride_bk + offs_bn[None, :] * stride_bn)\n    \n    accumulator = tl.zeros((BLOCK_M, BLOCK_N), dtype=ACC_TYPE)\n    \n    if EVEN_K:\n        for k in range(0, K, BLOCK_K):\n            a = tl.load(a_ptrs, mask=offs_k[None, :] < K - k, other=0.0)\n            b = tl.load(b_ptrs, mask=offs_k[:, None] < K - k, other=0.0)\n            accumulator += tl.dot(a, b, allow_tf32=False)\n            a_ptrs += BLOCK_K * stride_ak\n            b_ptrs += BLOCK_K * stride_bk\n    else:\n        for k in range(0, K, BLOCK_K):\n            k_remaining = K - k\n            a_mask = (offs_am[:, None] < M) & (offs_k[None, :] < k_remaining)\n            b_mask = (offs_k[:, None] < k_remaining) & (offs_bn[None, :] < N)\n            a = tl.load(a_ptrs, mask=a_mask, other=0.0)\n            b = tl.load(b_ptrs, mask=b_mask, other=0.0)\n            accumulator += tl.dot(a, b, allow_tf32=False)\n            a_ptrs += BLOCK_K * stride_ak\n            b_ptrs += BLOCK_K * stride_bk\n    \n    c_ptrs = c_ptr + stride_cm * offs_am[:, None] + stride_cn * offs_bn[None, :]\n    c_mask = (offs_am[:, None] < M) & (offs_bn[None, :] < N)\n    c = gelu(accumulator.to(c_ptr.dtype.element_ty))\n    tl.store(c_ptrs, c, mask=c_mask)\n\n"
                + "def matmul(a: torch.Tensor, b: torch.Tensor) -> torch.Tensor:\n"
                + "    assert a.shape[1] == b.shape[0], \"Incompatible dimensions\"\n    assert a.is_cuda and b.is_cuda, \"Inputs must be on GPU\"\n    \n    M, K = a.shape\n    K, N = b.shape\n    \n    c = torch.empty((M, N), device=a.device, dtype=a.dtype)\n    \n    def get_configs():\n        configs = []\n        for block_m in [64, 128]:\n            for block_n in [64, 128]:\n                for block_k in [32, 64, 128]:\n                    for group_m in [8]:\n                        for num_warps in [4, 8]:\n                            for num_stages in [3, 4, 5]:\n                                configs.append(triton.Config({\n                                    'BLOCK_M': block_m,\n                                    'BLOCK_N': block_n,\n                                    'BLOCK_K': block_k,\n                                    'GROUP_M': group_m,\n                                }, num_warps=num_warps, num_stages=num_stages))\n        return configs\n    \n    @triton.autotune(\n        configs=get_configs(),\n        key=['M', 'N', 'K'],\n    )\n    @triton.jit\n    def tuned_matmul_kernel(a_ptr, b_ptr, c_ptr, M, N, K, stride_am, stride_ak, stride_bk, stride_bn, stride_cm, stride_cn, BLOCK_M: tl.constexpr, BLOCK_N: tl.constexpr, BLOCK_K: tl.constexpr, GROUP_M: tl.constexpr):\n        _matmul_kernel(\n            a_ptr, b_ptr, c_ptr,\n            M, N, K,\n            stride_am, stride_ak,\n            stride_bk, stride_bn,\n            stride_cm, stride_cn,\n            BLOCK_M, BLOCK_N, BLOCK_K,\n            GROUP_M, EVEN_K=(K % BLOCK_K == 0),\n            ACC_TYPE=tl.float32 if a.dtype == torch.float32 else tl.float16,\n        )\n    \n    grid = lambda META: (\n        triton.cdiv(M, META['BLOCK_M']) * triton.cdiv(N, META['BLOCK_N']),\n    )\n    \n    tuned_matmul_kernel[grid](\n        a, b, c,\n        M, N, K,\n        a.stride(0), a.stride(1),\n        b.stride(0), b.stride(1),\n        c.stride(0), c.stride(1),\n    )\n    \n    return c\n"
            )
            return {"code": code}
