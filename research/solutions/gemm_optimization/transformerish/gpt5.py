import os
import sys
import inspect
import torch
import triton
import triton.language as tl


@triton.jit
def gelu(x):
    return x * 0.5 * (1.0 + tl.extra.cuda.libdevice.erf(x * 0.7071067811865476))


def _get_out_dtype_tl(dtype: torch.dtype):
    if dtype == torch.float16:
        return tl.float16
    if dtype == torch.bfloat16:
        return tl.bfloat16
    if dtype == torch.float32:
        return tl.float32
    # default fallback
    return tl.float32


def _promote_out_dtype(a: torch.Tensor, b: torch.Tensor):
    # Prefer higher precision when mixing, but cap to float32
    if a.dtype == b.dtype:
        return a.dtype
    # Handle typical mix cases
    if torch.float32 in (a.dtype, b.dtype):
        return torch.float32
    if torch.bfloat16 in (a.dtype, b.dtype):
        return torch.bfloat16
    return torch.float16


def _is_supported_dtype(dtype: torch.dtype):
    return dtype in (torch.float16, torch.bfloat16, torch.float32)


# Autotune configurations targeting L4 and transformer-ish sizes
_mm_configs = [
    triton.Config({"BLOCK_M": 128, "BLOCK_N": 128, "BLOCK_K": 32}, num_warps=8, num_stages=4),
    triton.Config({"BLOCK_M": 128, "BLOCK_N": 256, "BLOCK_K": 32}, num_warps=8, num_stages=4),
    triton.Config({"BLOCK_M": 256, "BLOCK_N": 128, "BLOCK_K": 32}, num_warps=8, num_stages=4),
    triton.Config({"BLOCK_M": 64,  "BLOCK_N": 256, "BLOCK_K": 32}, num_warps=4, num_stages=4),
    triton.Config({"BLOCK_M": 256, "BLOCK_N": 64,  "BLOCK_K": 32}, num_warps=4, num_stages=4),
    triton.Config({"BLOCK_M": 128, "BLOCK_N": 64,  "BLOCK_K": 32}, num_warps=4, num_stages=4),
    triton.Config({"BLOCK_M": 64,  "BLOCK_N": 128, "BLOCK_K": 32}, num_warps=4, num_stages=4),
    triton.Config({"BLOCK_M": 128, "BLOCK_N": 128, "BLOCK_K": 64}, num_warps=8, num_stages=3),
    triton.Config({"BLOCK_M": 128, "BLOCK_N": 64,  "BLOCK_K": 64}, num_warps=4, num_stages=3),
    triton.Config({"BLOCK_M": 64,  "BLOCK_N": 128, "BLOCK_K": 64}, num_warps=4, num_stages=3),
]


@triton.autotune(configs=_mm_configs, key=['M', 'N', 'K'])
@triton.jit
def _matmul_kernel(
    A_ptr, B_ptr, C_ptr,
    M, N, K,
    stride_am, stride_ak,
    stride_bk, stride_bn,
    stride_cm, stride_cn,
    OUT_DTYPE: tl.constexpr,
    BLOCK_M: tl.constexpr, BLOCK_N: tl.constexpr, BLOCK_K: tl.constexpr
):
    pid_m = tl.program_id(axis=0)
    pid_n = tl.program_id(axis=1)

    offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
    offs_n = pid_n * BLOCK_N + tl.arange(0, BLOCK_N)
    offs_k = tl.arange(0, BLOCK_K)

    acc = tl.zeros((BLOCK_M, BLOCK_N), dtype=tl.float32)

    a_ptrs = A_ptr + offs_m[:, None] * stride_am + offs_k[None, :] * stride_ak
    b_ptrs = B_ptr + offs_k[:, None] * stride_bk + offs_n[None, :] * stride_bn

    k_rem = K
    while k_rem > 0:
        a_mask = (offs_m[:, None] < M) & (offs_k[None, :] < K)
        b_mask = (offs_n[None, :] < N) & (offs_k[:, None] < K)
        a = tl.load(a_ptrs, mask=a_mask, other=0.0)
        b = tl.load(b_ptrs, mask=b_mask, other=0.0)
        acc += tl.dot(a, b)
        a_ptrs += BLOCK_K * stride_ak
        b_ptrs += BLOCK_K * stride_bk
        k_rem -= BLOCK_K

    acc = gelu(acc)
    c = tl.cast(acc, OUT_DTYPE)

    c_ptrs = C_ptr + offs_m[:, None] * stride_cm + offs_n[None, :] * stride_cn
    c_mask = (offs_m[:, None] < M) & (offs_n[None, :] < N)
    tl.store(c_ptrs, c, mask=c_mask)


def matmul(a: torch.Tensor, b: torch.Tensor) -> torch.Tensor:
    """
    Matrix multiplication with GELU activation.

    Args:
        a: Input tensor of shape (M, K)
        b: Input tensor of shape (K, N)

    Returns:
        Output tensor of shape (M, N) with GELU activation applied
    """
    assert a.ndim == 2 and b.ndim == 2, "Inputs must be 2D"
    M, K1 = a.shape
    K2, N = b.shape
    assert K1 == K2, "Inner dimensions must match"

    # Device checks
    assert a.is_cuda and b.is_cuda, "Inputs must be CUDA tensors"
    device = a.device
    assert b.device == device, "Inputs must be on the same device"

    # Decide output dtype
    out_dtype = _promote_out_dtype(a, b)
    if not _is_supported_dtype(out_dtype):
        # Fallback to PyTorch for unsupported dtypes
        c = a.to(torch.float32) @ b.to(torch.float32)
        c = torch.nn.functional.gelu(c)
        return c.to(out_dtype)

    # Ensure strides and handle non-contiguous memory
    a_contig = a
    b_contig = b
    # Triton expects explicit strides; non-contiguous is supported directly.
    # However, we ensure last dim is aligned for potential performance.
    # We'll let Triton handle as strides.
    # Create output
    c = torch.empty((M, N), device=device, dtype=out_dtype)

    # Strides
    stride_am = a_contig.stride(0)
    stride_ak = a_contig.stride(1)
    stride_bk = b_contig.stride(0)
    stride_bn = b_contig.stride(1)
    stride_cm = c.stride(0)
    stride_cn = c.stride(1)

    # Grid
    def grid(meta):
        return (triton.cdiv(M, meta['BLOCK_M']), triton.cdiv(N, meta['BLOCK_N']))

    OUT_DTYPE_TL = _get_out_dtype_tl(out_dtype)

    _matmul_kernel[grid](
        a_contig, b_contig, c,
        M, N, K1,
        stride_am, stride_ak,
        stride_bk, stride_bn,
        stride_cm, stride_cn,
        OUT_DTYPE=OUT_DTYPE_TL,
    )

    return c


class Solution:
    def solve(self, spec_path: str = None) -> dict:
        try:
            path = __file__
            if isinstance(path, str) and os.path.exists(path):
                return {"program_path": path}
        except Exception:
            pass
        try:
            src = inspect.getsource(sys.modules[__name__])
            return {"code": src}
        except Exception:
            # As a last resort, just return the function only
            return {"code": "import torch\nimport triton\nimport triton.language as tl\n\n" + inspect.getsource(gelu) + "\n" + inspect.getsource(_get_out_dtype_tl) + "\n" + inspect.getsource(_promote_out_dtype) + "\n" + inspect.getsource(_is_supported_dtype) + "\n" + "_mm_configs=[]\n" + inspect.getsource(_matmul_kernel) + "\n" + inspect.getsource(matmul)}