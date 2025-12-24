import torch
import triton
import triton.language as tl


@triton.jit
def gelu(x):
    return x * 0.5 * (1.0 + tl.extra.cuda.libdevice.erf(x * 0.7071067811865476))


@triton.autotune(
    configs=[
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 128, 'BLOCK_K': 32}, num_warps=8, num_stages=3),
        triton.Config({'BLOCK_M': 64, 'BLOCK_N': 256, 'BLOCK_K': 32}, num_warps=8, num_stages=4),
        triton.Config({'BLOCK_M': 256, 'BLOCK_N': 64, 'BLOCK_K': 32}, num_warps=8, num_stages=4),
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 64, 'BLOCK_K': 32}, num_warps=4, num_stages=3),
        triton.Config({'BLOCK_M': 64, 'BLOCK_N': 128, 'BLOCK_K': 32}, num_warps=4, num_stages=3),
        triton.Config({'BLOCK_M': 64, 'BLOCK_N': 64, 'BLOCK_K': 64}, num_warps=4, num_stages=4),
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 128, 'BLOCK_K': 64}, num_warps=8, num_stages=4),
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 256, 'BLOCK_K': 32}, num_warps=8, num_stages=4),
        triton.Config({'BLOCK_M': 256, 'BLOCK_N': 128, 'BLOCK_K': 32}, num_warps=8, num_stages=4),
        triton.Config({'BLOCK_M': 32, 'BLOCK_N': 64, 'BLOCK_K': 32}, num_warps=4, num_stages=2),
        triton.Config({'BLOCK_M': 64, 'BLOCK_N': 32, 'BLOCK_K': 32}, num_warps=4, num_stages=2),
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
    ALLOW_TF32: tl.constexpr,
    BLOCK_M: tl.constexpr, BLOCK_N: tl.constexpr, BLOCK_K: tl.constexpr,
):
    pid_m = tl.program_id(0)
    pid_n = tl.program_id(1)

    offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
    offs_n = pid_n * BLOCK_N + tl.arange(0, BLOCK_N)
    offs_k = tl.arange(0, BLOCK_K)

    a_ptrs = A_ptr + (offs_m[:, None] * stride_am + offs_k[None, :] * stride_ak)
    b_ptrs = B_ptr + (offs_k[:, None] * stride_bk + offs_n[None, :] * stride_bn)

    acc = tl.zeros((BLOCK_M, BLOCK_N), dtype=tl.float32)

    k_iters = (K + BLOCK_K - 1) // BLOCK_K
    for _ in range(0, k_iters):
        k_mask_a = (offs_k[None, :] + 0) < K
        k_mask_b = (offs_k[:, None] + 0) < K
        a = tl.load(a_ptrs, mask=(offs_m[:, None] < M) & k_mask_a, other=0.0)
        b = tl.load(b_ptrs, mask=k_mask_b & (offs_n[None, :] < N), other=0.0)
        acc += tl.dot(a, b, allow_tf32=ALLOW_TF32)
        a_ptrs += BLOCK_K * stride_ak
        b_ptrs += BLOCK_K * stride_bk
        offs_k += BLOCK_K

    acc = gelu(acc)

    c_ptrs = C_ptr + (offs_m[:, None] * stride_cm + offs_n[None, :] * stride_cn)
    mask_store = (offs_m[:, None] < M) & (offs_n[None, :] < N)
    tl.store(c_ptrs, acc, mask=mask_store)


def matmul(a: torch.Tensor, b: torch.Tensor) -> torch.Tensor:
    assert a.ndim == 2 and b.ndim == 2, "Inputs must be 2D"
    assert a.shape[1] == b.shape[0], "Incompatible matrix shapes"
    assert a.is_cuda and b.is_cuda, "Inputs must be CUDA tensors"

    M, K = a.shape
    Kb, N = b.shape
    assert K == Kb

    # Determine output dtype
    if a.dtype == b.dtype:
        out_dtype = a.dtype
    else:
        out_dtype = torch.promote_types(a.dtype, b.dtype)

    # Supported compute dtypes
    supported_dtypes = {torch.float16, torch.bfloat16, torch.float32}
    if out_dtype not in supported_dtypes:
        out = a @ b
        return torch.nn.functional.gelu(out)

    # Cast inputs if necessary to a common dtype for compute
    # Prefer higher precision among inputs for compute to preserve accuracy
    if a.dtype != out_dtype:
        a_ = a.to(out_dtype)
    else:
        a_ = a
    if b.dtype != out_dtype:
        b_ = b.to(out_dtype)
    else:
        b_ = b

    # Allocate output; kernel writes GELU-activated result
    c = torch.empty((M, N), device=a.device, dtype=out_dtype)

    # Strides
    stride_am, stride_ak = a_.stride()
    stride_bk, stride_bn = b_.stride()
    stride_cm, stride_cn = c.stride()

    # Grid
    def grid(meta):
        return (
            triton.cdiv(M, meta['BLOCK_M']),
            triton.cdiv(N, meta['BLOCK_N']),
        )

    allow_tf32 = bool(torch.backends.cuda.matmul.allow_tf32) if out_dtype == torch.float32 else False

    _matmul_gelu_kernel[grid](
        a_, b_, c,
        M, N, K,
        stride_am, stride_ak,
        stride_bk, stride_bn,
        stride_cm, stride_cn,
        ALLOW_TF32=allow_tf32,
    )
    return c


class Solution:
    def solve(self, spec_path: str = None) -> dict:
        code = (
            "import torch\n"
            "import triton\n"
            "import triton.language as tl\n"
            "\n"
            "@triton.jit\n"
            "def gelu(x):\n"
            "    return x * 0.5 * (1.0 + tl.extra.cuda.libdevice.erf(x * 0.7071067811865476))\n"
            "\n"
            "@triton.autotune(\n"
            "    configs=[\n"
            "        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 128, 'BLOCK_K': 32}, num_warps=8, num_stages=3),\n"
            "        triton.Config({'BLOCK_M': 64, 'BLOCK_N': 256, 'BLOCK_K': 32}, num_warps=8, num_stages=4),\n"
            "        triton.Config({'BLOCK_M': 256, 'BLOCK_N': 64, 'BLOCK_K': 32}, num_warps=8, num_stages=4),\n"
            "        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 64, 'BLOCK_K': 32}, num_warps=4, num_stages=3),\n"
            "        triton.Config({'BLOCK_M': 64, 'BLOCK_N': 128, 'BLOCK_K': 32}, num_warps=4, num_stages=3),\n"
            "        triton.Config({'BLOCK_M': 64, 'BLOCK_N': 64, 'BLOCK_K': 64}, num_warps=4, num_stages=4),\n"
            "        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 128, 'BLOCK_K': 64}, num_warps=8, num_stages=4),\n"
            "        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 256, 'BLOCK_K': 32}, num_warps=8, num_stages=4),\n"
            "        triton.Config({'BLOCK_M': 256, 'BLOCK_N': 128, 'BLOCK_K': 32}, num_warps=8, num_stages=4),\n"
            "        triton.Config({'BLOCK_M': 32, 'BLOCK_N': 64, 'BLOCK_K': 32}, num_warps=4, num_stages=2),\n"
            "        triton.Config({'BLOCK_M': 64, 'BLOCK_N': 32, 'BLOCK_K': 32}, num_warps=4, num_stages=2),\n"
            "    ],\n"
            "    key=['M', 'N', 'K'],\n"
            ")\n"
            "@triton.jit\n"
            "def _matmul_gelu_kernel(\n"
            "    A_ptr, B_ptr, C_ptr,\n"
            "    M, N, K,\n"
            "    stride_am, stride_ak,\n"
            "    stride_bk, stride_bn,\n"
            "    stride_cm, stride_cn,\n"
            "    ALLOW_TF32: tl.constexpr,\n"
            "    BLOCK_M: tl.constexpr, BLOCK_N: tl.constexpr, BLOCK_K: tl.constexpr,\n"
            "):\n"
            "    pid_m = tl.program_id(0)\n"
            "    pid_n = tl.program_id(1)\n"
            "\n"
            "    offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)\n"
            "    offs_n = pid_n * BLOCK_N + tl.arange(0, BLOCK_N)\n"
            "    offs_k = tl.arange(0, BLOCK_K)\n"
            "\n"
            "    a_ptrs = A_ptr + (offs_m[:, None] * stride_am + offs_k[None, :] * stride_ak)\n"
            "    b_ptrs = B_ptr + (offs_k[:, None] * stride_bk + offs_n[None, :] * stride_bn)\n"
            "\n"
            "    acc = tl.zeros((BLOCK_M, BLOCK_N), dtype=tl.float32)\n"
            "\n"
            "    k_iters = (K + BLOCK_K - 1) // BLOCK_K\n"
            "    for _ in range(0, k_iters):\n"
            "        k_mask_a = (offs_k[None, :] + 0) < K\n"
            "        k_mask_b = (offs_k[:, None] + 0) < K\n"
            "        a = tl.load(a_ptrs, mask=(offs_m[:, None] < M) & k_mask_a, other=0.0)\n"
            "        b = tl.load(b_ptrs, mask=k_mask_b & (offs_n[None, :] < N), other=0.0)\n"
            "        acc += tl.dot(a, b, allow_tf32=ALLOW_TF32)\n"
            "        a_ptrs += BLOCK_K * stride_ak\n"
            "        b_ptrs += BLOCK_K * stride_bk\n"
            "        offs_k += BLOCK_K\n"
            "\n"
            "    acc = gelu(acc)\n"
            "\n"
            "    c_ptrs = C_ptr + (offs_m[:, None] * stride_cm + offs_n[None, :] * stride_cn)\n"
            "    mask_store = (offs_m[:, None] < M) & (offs_n[None, :] < N)\n"
            "    tl.store(c_ptrs, acc, mask=mask_store)\n"
            "\n"
            "def matmul(a: torch.Tensor, b: torch.Tensor) -> torch.Tensor:\n"
            "    assert a.ndim == 2 and b.ndim == 2, 'Inputs must be 2D'\n"
            "    assert a.shape[1] == b.shape[0], 'Incompatible matrix shapes'\n"
            "    assert a.is_cuda and b.is_cuda, 'Inputs must be CUDA tensors'\n"
            "\n"
            "    M, K = a.shape\n"
            "    Kb, N = b.shape\n"
            "    assert K == Kb\n"
            "\n"
            "    if a.dtype == b.dtype:\n"
            "        out_dtype = a.dtype\n"
            "    else:\n"
            "        out_dtype = torch.promote_types(a.dtype, b.dtype)\n"
            "\n"
            "    supported_dtypes = {torch.float16, torch.bfloat16, torch.float32}\n"
            "    if out_dtype not in supported_dtypes:\n"
            "        out = a @ b\n"
            "        return torch.nn.functional.gelu(out)\n"
            "\n"
            "    a_ = a.to(out_dtype) if a.dtype != out_dtype else a\n"
            "    b_ = b.to(out_dtype) if b.dtype != out_dtype else b\n"
            "\n"
            "    c = torch.empty((M, N), device=a.device, dtype=out_dtype)\n"
            "\n"
            "    stride_am, stride_ak = a_.stride()\n"
            "    stride_bk, stride_bn = b_.stride()\n"
            "    stride_cm, stride_cn = c.stride()\n"
            "\n"
            "    def grid(meta):\n"
            "        return (\n"
            "            triton.cdiv(M, meta['BLOCK_M']),\n"
            "            triton.cdiv(N, meta['BLOCK_N']),\n"
            "        )\n"
            "\n"
            "    allow_tf32 = bool(torch.backends.cuda.matmul.allow_tf32) if out_dtype == torch.float32 else False\n"
            "\n"
            "    _matmul_gelu_kernel[grid](\n"
            "        a_, b_, c,\n"
            "        M, N, K,\n"
            "        stride_am, stride_ak,\n"
            "        stride_bk, stride_bn,\n"
            "        stride_cm, stride_cn,\n"
            "        ALLOW_TF32=allow_tf32,\n"
            "    )\n"
            "    return c\n"
        )
        return {"code": code}
