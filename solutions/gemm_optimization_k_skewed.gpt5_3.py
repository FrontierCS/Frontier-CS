import torch
import triton
import triton.language as tl


@triton.jit
def gelu(x):
    return x * 0.5 * (1.0 + tl.extra.cuda.libdevice.erf(x * 0.7071067811865476))


@triton.autotune(
    configs=[
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 128, 'BLOCK_K': 32}, num_warps=8, num_stages=3),
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 256, 'BLOCK_K': 32}, num_warps=8, num_stages=3),
        triton.Config({'BLOCK_M': 256, 'BLOCK_N': 128, 'BLOCK_K': 32}, num_warps=8, num_stages=3),
        triton.Config({'BLOCK_M': 64, 'BLOCK_N': 256, 'BLOCK_K': 32}, num_warps=4, num_stages=3),
        triton.Config({'BLOCK_M': 256, 'BLOCK_N': 64, 'BLOCK_K': 32}, num_warps=4, num_stages=3),
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 128, 'BLOCK_K': 64}, num_warps=8, num_stages=4),
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 256, 'BLOCK_K': 64}, num_warps=8, num_stages=4),
        triton.Config({'BLOCK_M': 256, 'BLOCK_N': 128, 'BLOCK_K': 64}, num_warps=8, num_stages=4),
        triton.Config({'BLOCK_M': 64, 'BLOCK_N': 128, 'BLOCK_K': 32}, num_warps=4, num_stages=3),
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 64, 'BLOCK_K': 32}, num_warps=4, num_stages=3),
        triton.Config({'BLOCK_M': 64, 'BLOCK_N': 64, 'BLOCK_K': 32}, num_warps=4, num_stages=3),
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 128, 'BLOCK_K': 16}, num_warps=4, num_stages=2),
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
    BLOCK_M: tl.constexpr, BLOCK_N: tl.constexpr, BLOCK_K: tl.constexpr
):
    pid_m = tl.program_id(0)
    pid_n = tl.program_id(1)

    offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
    offs_n = pid_n * BLOCK_N + tl.arange(0, BLOCK_N)
    offs_k = tl.arange(0, BLOCK_K)

    a_ptrs = a_ptr + (offs_m[:, None] * stride_am + offs_k[None, :] * stride_ak)
    b_ptrs = b_ptr + (offs_k[:, None] * stride_bk + offs_n[None, :] * stride_bn)

    acc = tl.zeros((BLOCK_M, BLOCK_N), dtype=tl.float32)

    k = 0
    while k < K:
        a_mask = (offs_m[:, None] < M) & (k + offs_k[None, :] < K)
        b_mask = (k + offs_k[:, None] < K) & (offs_n[None, :] < N)
        a = tl.load(a_ptrs, mask=a_mask, other=0.0)
        b = tl.load(b_ptrs, mask=b_mask, other=0.0)
        acc += tl.dot(a, b)

        k += BLOCK_K
        a_ptrs += BLOCK_K * stride_ak
        b_ptrs += BLOCK_K * stride_bk

    acc = gelu(acc)

    c_ptrs = c_ptr + (offs_m[:, None] * stride_cm + offs_n[None, :] * stride_cn)
    c_mask = (offs_m[:, None] < M) & (offs_n[None, :] < N)
    tl.store(c_ptrs, acc, mask=c_mask)


def matmul(a: torch.Tensor, b: torch.Tensor) -> torch.Tensor:
    if a.dim() != 2 or b.dim() != 2:
        raise ValueError("Inputs must be 2D tensors")
    if a.shape[1] != b.shape[0]:
        raise ValueError("Incompatible dimensions for matmul")

    M, K = a.shape
    Kb, N = b.shape
    assert K == Kb

    if not a.is_cuda or not b.is_cuda:
        out = a @ b
        out = torch.nn.functional.gelu(out)
        return out

    if a.dtype not in (torch.float16, torch.bfloat16, torch.float32) or b.dtype not in (torch.float16, torch.bfloat16, torch.float32):
        out = a @ b
        out = torch.nn.functional.gelu(out)
        return out

    # Output dtype: match a.dtype if a and b have the same dtype, else float32
    out_dtype = a.dtype if a.dtype == b.dtype else torch.float32
    c = torch.empty((M, N), device=a.device, dtype=out_dtype)

    grid = lambda META: (triton.cdiv(M, META['BLOCK_M']), triton.cdiv(N, META['BLOCK_N']))

    _matmul_gelu_kernel[grid](
        a, b, c,
        M, N, K,
        a.stride(0), a.stride(1),
        b.stride(0), b.stride(1),
        c.stride(0), c.stride(1),
    )
    return c


class Solution:
    def solve(self, spec_path: str = None) -> dict:
        src = (
            "import torch\n"
            "import triton\n"
            "import triton.language as tl\n\n"
            "@triton.jit\n"
            "def gelu(x):\n"
            "    return x * 0.5 * (1.0 + tl.extra.cuda.libdevice.erf(x * 0.7071067811865476))\n\n"
            "@triton.autotune(\n"
            "    configs=[\n"
            "        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 128, 'BLOCK_K': 32}, num_warps=8, num_stages=3),\n"
            "        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 256, 'BLOCK_K': 32}, num_warps=8, num_stages=3),\n"
            "        triton.Config({'BLOCK_M': 256, 'BLOCK_N': 128, 'BLOCK_K': 32}, num_warps=8, num_stages=3),\n"
            "        triton.Config({'BLOCK_M': 64, 'BLOCK_N': 256, 'BLOCK_K': 32}, num_warps=4, num_stages=3),\n"
            "        triton.Config({'BLOCK_M': 256, 'BLOCK_N': 64, 'BLOCK_K': 32}, num_warps=4, num_stages=3),\n"
            "        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 128, 'BLOCK_K': 64}, num_warps=8, num_stages=4),\n"
            "        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 256, 'BLOCK_K': 64}, num_warps=8, num_stages=4),\n"
            "        triton.Config({'BLOCK_M': 256, 'BLOCK_N': 128, 'BLOCK_K': 64}, num_warps=8, num_stages=4),\n"
            "        triton.Config({'BLOCK_M': 64, 'BLOCK_N': 128, 'BLOCK_K': 32}, num_warps=4, num_stages=3),\n"
            "        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 64, 'BLOCK_K': 32}, num_warps=4, num_stages=3),\n"
            "        triton.Config({'BLOCK_M': 64, 'BLOCK_N': 64, 'BLOCK_K': 32}, num_warps=4, num_stages=3),\n"
            "        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 128, 'BLOCK_K': 16}, num_warps=4, num_stages=2),\n"
            "    ],\n"
            "    key=['M', 'N', 'K'],\n"
            ")\n"
            "@triton.jit\n"
            "def _matmul_gelu_kernel(\n"
            "    a_ptr, b_ptr, c_ptr,\n"
            "    M, N, K,\n"
            "    stride_am, stride_ak,\n"
            "    stride_bk, stride_bn,\n"
            "    stride_cm, stride_cn,\n"
            "    BLOCK_M: tl.constexpr, BLOCK_N: tl.constexpr, BLOCK_K: tl.constexpr\n"
            "):\n"
            "    pid_m = tl.program_id(0)\n"
            "    pid_n = tl.program_id(1)\n\n"
            "    offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)\n"
            "    offs_n = pid_n * BLOCK_N + tl.arange(0, BLOCK_N)\n"
            "    offs_k = tl.arange(0, BLOCK_K)\n\n"
            "    a_ptrs = a_ptr + (offs_m[:, None] * stride_am + offs_k[None, :] * stride_ak)\n"
            "    b_ptrs = b_ptr + (offs_k[:, None] * stride_bk + offs_n[None, :] * stride_bn)\n\n"
            "    acc = tl.zeros((BLOCK_M, BLOCK_N), dtype=tl.float32)\n\n"
            "    k = 0\n"
            "    while k < K:\n"
            "        a_mask = (offs_m[:, None] < M) & (k + offs_k[None, :] < K)\n"
            "        b_mask = (k + offs_k[:, None] < K) & (offs_n[None, :] < N)\n"
            "        a = tl.load(a_ptrs, mask=a_mask, other=0.0)\n"
            "        b = tl.load(b_ptrs, mask=b_mask, other=0.0)\n"
            "        acc += tl.dot(a, b)\n\n"
            "        k += BLOCK_K\n"
            "        a_ptrs += BLOCK_K * stride_ak\n"
            "        b_ptrs += BLOCK_K * stride_bk\n\n"
            "    acc = gelu(acc)\n\n"
            "    c_ptrs = c_ptr + (offs_m[:, None] * stride_cm + offs_n[None, :] * stride_cn)\n"
            "    c_mask = (offs_m[:, None] < M) & (offs_n[None, :] < N)\n"
            "    tl.store(c_ptrs, acc, mask=c_mask)\n\n"
            "def matmul(a: torch.Tensor, b: torch.Tensor) -> torch.Tensor:\n"
            "    if a.dim() != 2 or b.dim() != 2:\n"
            "        raise ValueError('Inputs must be 2D tensors')\n"
            "    if a.shape[1] != b.shape[0]:\n"
            "        raise ValueError('Incompatible dimensions for matmul')\n\n"
            "    M, K = a.shape\n"
            "    Kb, N = b.shape\n"
            "    assert K == Kb\n\n"
            "    if not a.is_cuda or not b.is_cuda:\n"
            "        out = a @ b\n"
            "        out = torch.nn.functional.gelu(out)\n"
            "        return out\n\n"
            "    if a.dtype not in (torch.float16, torch.bfloat16, torch.float32) or b.dtype not in (torch.float16, torch.bfloat16, torch.float32):\n"
            "        out = a @ b\n"
            "        out = torch.nn.functional.gelu(out)\n"
            "        return out\n\n"
            "    out_dtype = a.dtype if a.dtype == b.dtype else torch.float32\n"
            "    c = torch.empty((M, N), device=a.device, dtype=out_dtype)\n\n"
            "    grid = lambda META: (triton.cdiv(M, META['BLOCK_M']), triton.cdiv(N, META['BLOCK_N']))\n\n"
            "    _matmul_gelu_kernel[grid](\n"
            "        a, b, c,\n"
            "        M, N, K,\n"
            "        a.stride(0), a.stride(1),\n"
            "        b.stride(0), b.stride(1),\n"
            "        c.stride(0), c.stride(1),\n"
            "    )\n"
            "    return c\n"
        )
        return {"code": src}
