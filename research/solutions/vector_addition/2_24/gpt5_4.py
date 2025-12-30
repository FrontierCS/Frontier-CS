import torch
import triton
import triton.language as tl


@triton.autotune(
    configs=[
        triton.Config({"BLOCK_SIZE": 2048, "num_warps": 4}, num_stages=1),
        triton.Config({"BLOCK_SIZE": 4096, "num_warps": 4}, num_stages=1),
        triton.Config({"BLOCK_SIZE": 4096, "num_warps": 8}, num_stages=1),
        triton.Config({"BLOCK_SIZE": 8192, "num_warps": 8}, num_stages=1),
        triton.Config({"BLOCK_SIZE": 16384, "num_warps": 8}, num_stages=1),
    ],
    key=["n_elements"],
)
@triton.jit
def _vec_add_kernel_fp32(
    x_ptr: tl.pointer_type(dtype=tl.float32),
    y_ptr: tl.pointer_type(dtype=tl.float32),
    out_ptr: tl.pointer_type(dtype=tl.float32),
    n_elements: tl.int32,
    BLOCK_SIZE: tl.constexpr,
):
    tl.static_assert(BLOCK_SIZE % 256 == 0)
    pid = tl.program_id(axis=0)
    block_start = pid * BLOCK_SIZE
    offsets = block_start + tl.arange(0, BLOCK_SIZE)
    mask = offsets < n_elements
    x = tl.load(x_ptr + offsets, mask=mask, other=0.0)
    y = tl.load(y_ptr + offsets, mask=mask, other=0.0)
    tl.store(out_ptr + offsets, x + y, mask=mask)


@triton.autotune(
    configs=[
        triton.Config({"BLOCK_SIZE": 2048, "num_warps": 4}, num_stages=1),
        triton.Config({"BLOCK_SIZE": 4096, "num_warps": 4}, num_stages=1),
        triton.Config({"BLOCK_SIZE": 4096, "num_warps": 8}, num_stages=1),
        triton.Config({"BLOCK_SIZE": 8192, "num_warps": 8}, num_stages=1),
        triton.Config({"BLOCK_SIZE": 16384, "num_warps": 8}, num_stages=1),
    ],
    key=["n_elements"],
)
@triton.jit
def _vec_add_kernel_fp16(
    x_ptr: tl.pointer_type(dtype=tl.float16),
    y_ptr: tl.pointer_type(dtype=tl.float16),
    out_ptr: tl.pointer_type(dtype=tl.float16),
    n_elements: tl.int32,
    BLOCK_SIZE: tl.constexpr,
):
    tl.static_assert(BLOCK_SIZE % 256 == 0)
    pid = tl.program_id(axis=0)
    block_start = pid * BLOCK_SIZE
    offsets = block_start + tl.arange(0, BLOCK_SIZE)
    mask = offsets < n_elements
    x = tl.load(x_ptr + offsets, mask=mask, other=0.0)
    y = tl.load(y_ptr + offsets, mask=mask, other=0.0)
    tl.store(out_ptr + offsets, x + y, mask=mask)


@triton.autotune(
    configs=[
        triton.Config({"BLOCK_SIZE": 2048, "num_warps": 4}, num_stages=1),
        triton.Config({"BLOCK_SIZE": 4096, "num_warps": 4}, num_stages=1),
        triton.Config({"BLOCK_SIZE": 4096, "num_warps": 8}, num_stages=1),
        triton.Config({"BLOCK_SIZE": 8192, "num_warps": 8}, num_stages=1),
        triton.Config({"BLOCK_SIZE": 16384, "num_warps": 8}, num_stages=1),
    ],
    key=["n_elements"],
)
@triton.jit
def _vec_add_kernel_bf16(
    x_ptr: tl.pointer_type(dtype=tl.bfloat16),
    y_ptr: tl.pointer_type(dtype=tl.bfloat16),
    out_ptr: tl.pointer_type(dtype=tl.bfloat16),
    n_elements: tl.int32,
    BLOCK_SIZE: tl.constexpr,
):
    tl.static_assert(BLOCK_SIZE % 256 == 0)
    pid = tl.program_id(axis=0)
    block_start = pid * BLOCK_SIZE
    offsets = block_start + tl.arange(0, BLOCK_SIZE)
    mask = offsets < n_elements
    x = tl.load(x_ptr + offsets, mask=mask, other=0.0)
    y = tl.load(y_ptr + offsets, mask=mask, other=0.0)
    tl.store(out_ptr + offsets, x + y, mask=mask)


@triton.autotune(
    configs=[
        triton.Config({"BLOCK_SIZE": 1024, "num_warps": 4}, num_stages=1),
        triton.Config({"BLOCK_SIZE": 2048, "num_warps": 4}, num_stages=1),
        triton.Config({"BLOCK_SIZE": 4096, "num_warps": 8}, num_stages=1),
        triton.Config({"BLOCK_SIZE": 8192, "num_warps": 8}, num_stages=1),
    ],
    key=["n_elements"],
)
@triton.jit
def _vec_add_kernel_fp64(
    x_ptr: tl.pointer_type(dtype=tl.float64),
    y_ptr: tl.pointer_type(dtype=tl.float64),
    out_ptr: tl.pointer_type(dtype=tl.float64),
    n_elements: tl.int32,
    BLOCK_SIZE: tl.constexpr,
):
    tl.static_assert(BLOCK_SIZE % 256 == 0)
    pid = tl.program_id(axis=0)
    block_start = pid * BLOCK_SIZE
    offsets = block_start + tl.arange(0, BLOCK_SIZE)
    mask = offsets < n_elements
    x = tl.load(x_ptr + offsets, mask=mask, other=0.0)
    y = tl.load(y_ptr + offsets, mask=mask, other=0.0)
    tl.store(out_ptr + offsets, x + y, mask=mask)


def add(x: torch.Tensor, y: torch.Tensor) -> torch.Tensor:
    if x.shape != y.shape:
        raise ValueError("Input tensors must have the same shape")
    if x.numel() == 0:
        return torch.empty_like(x)
    if x.dtype != y.dtype:
        y = y.to(x.dtype)
    if not x.is_contiguous():
        x = x.contiguous()
    if not y.is_contiguous():
        y = y.contiguous()
    if x.device != y.device:
        y = y.to(x.device)
    if x.device.type != "cuda":
        return x + y

    n_elements = x.numel()
    out = torch.empty_like(x)

    grid = lambda META: (triton.cdiv(n_elements, META["BLOCK_SIZE"]),)

    dt = x.dtype
    if dt == torch.float32:
        _vec_add_kernel_fp32[grid](x, y, out, n_elements)
    elif dt in (torch.float16, torch.half):
        _vec_add_kernel_fp16[grid](x, y, out, n_elements)
    elif dt == torch.bfloat16:
        _vec_add_kernel_bf16[grid](x, y, out, n_elements)
    elif dt == torch.float64:
        _vec_add_kernel_fp64[grid](x, y, out, n_elements)
    else:
        # Fallback to PyTorch for unsupported dtypes
        out = x + y
    return out


class Solution:
    def solve(self, spec_path: str = None) -> dict:
        code = '''
import torch
import triton
import triton.language as tl


@triton.autotune(
    configs=[
        triton.Config({"BLOCK_SIZE": 2048, "num_warps": 4}, num_stages=1),
        triton.Config({"BLOCK_SIZE": 4096, "num_warps": 4}, num_stages=1),
        triton.Config({"BLOCK_SIZE": 4096, "num_warps": 8}, num_stages=1),
        triton.Config({"BLOCK_SIZE": 8192, "num_warps": 8}, num_stages=1),
        triton.Config({"BLOCK_SIZE": 16384, "num_warps": 8}, num_stages=1),
    ],
    key=["n_elements"],
)
@triton.jit
def _vec_add_kernel_fp32(
    x_ptr: tl.pointer_type(dtype=tl.float32),
    y_ptr: tl.pointer_type(dtype=tl.float32),
    out_ptr: tl.pointer_type(dtype=tl.float32),
    n_elements: tl.int32,
    BLOCK_SIZE: tl.constexpr,
):
    tl.static_assert(BLOCK_SIZE % 256 == 0)
    pid = tl.program_id(axis=0)
    block_start = pid * BLOCK_SIZE
    offsets = block_start + tl.arange(0, BLOCK_SIZE)
    mask = offsets < n_elements
    x = tl.load(x_ptr + offsets, mask=mask, other=0.0)
    y = tl.load(y_ptr + offsets, mask=mask, other=0.0)
    tl.store(out_ptr + offsets, x + y, mask=mask)


@triton.autotune(
    configs=[
        triton.Config({"BLOCK_SIZE": 2048, "num_warps": 4}, num_stages=1),
        triton.Config({"BLOCK_SIZE": 4096, "num_warps": 4}, num_stages=1),
        triton.Config({"BLOCK_SIZE": 4096, "num_warps": 8}, num_stages=1),
        triton.Config({"BLOCK_SIZE": 8192, "num_warps": 8}, num_stages=1),
        triton.Config({"BLOCK_SIZE": 16384, "num_warps": 8}, num_stages=1),
    ],
    key=["n_elements"],
)
@triton.jit
def _vec_add_kernel_fp16(
    x_ptr: tl.pointer_type(dtype=tl.float16),
    y_ptr: tl.pointer_type(dtype=tl.float16),
    out_ptr: tl.pointer_type(dtype=tl.float16),
    n_elements: tl.int32,
    BLOCK_SIZE: tl.constexpr,
):
    tl.static_assert(BLOCK_SIZE % 256 == 0)
    pid = tl.program_id(axis=0)
    block_start = pid * BLOCK_SIZE
    offsets = block_start + tl.arange(0, BLOCK_SIZE)
    mask = offsets < n_elements
    x = tl.load(x_ptr + offsets, mask=mask, other=0.0)
    y = tl.load(y_ptr + offsets, mask=mask, other=0.0)
    tl.store(out_ptr + offsets, x + y, mask=mask)


@triton.autotune(
    configs=[
        triton.Config({"BLOCK_SIZE": 2048, "num_warps": 4}, num_stages=1),
        triton.Config({"BLOCK_SIZE": 4096, "num_warps": 4}, num_stages=1),
        triton.Config({"BLOCK_SIZE": 4096, "num_warps": 8}, num_stages=1),
        triton.Config({"BLOCK_SIZE": 8192, "num_warps": 8}, num_stages=1),
        triton.Config({"BLOCK_SIZE": 16384, "num_warps": 8}, num_stages=1),
    ],
    key=["n_elements"],
)
@triton.jit
def _vec_add_kernel_bf16(
    x_ptr: tl.pointer_type(dtype=tl.bfloat16),
    y_ptr: tl.pointer_type(dtype=tl.bfloat16),
    out_ptr: tl.pointer_type(dtype=tl.bfloat16),
    n_elements: tl.int32,
    BLOCK_SIZE: tl.constexpr,
):
    tl.static_assert(BLOCK_SIZE % 256 == 0)
    pid = tl.program_id(axis=0)
    block_start = pid * BLOCK_SIZE
    offsets = block_start + tl.arange(0, BLOCK_SIZE)
    mask = offsets < n_elements
    x = tl.load(x_ptr + offsets, mask=mask, other=0.0)
    y = tl.load(y_ptr + offsets, mask=mask, other=0.0)
    tl.store(out_ptr + offsets, x + y, mask=mask)


@triton.autotune(
    configs=[
        triton.Config({"BLOCK_SIZE": 1024, "num_warps": 4}, num_stages=1),
        triton.Config({"BLOCK_SIZE": 2048, "num_warps": 4}, num_stages=1),
        triton.Config({"BLOCK_SIZE": 4096, "num_warps": 8}, num_stages=1),
        triton.Config({"BLOCK_SIZE": 8192, "num_warps": 8}, num_stages=1),
    ],
    key=["n_elements"],
)
@triton.jit
def _vec_add_kernel_fp64(
    x_ptr: tl.pointer_type(dtype=tl.float64),
    y_ptr: tl.pointer_type(dtype=tl.float64),
    out_ptr: tl.pointer_type(dtype=tl.float64),
    n_elements: tl.int32,
    BLOCK_SIZE: tl.constexpr,
):
    tl.static_assert(BLOCK_SIZE % 256 == 0)
    pid = tl.program_id(axis=0)
    block_start = pid * BLOCK_SIZE
    offsets = block_start + tl.arange(0, BLOCK_SIZE)
    mask = offsets < n_elements
    x = tl.load(x_ptr + offsets, mask=mask, other=0.0)
    y = tl.load(y_ptr + offsets, mask=mask, other=0.0)
    tl.store(out_ptr + offsets, x + y, mask=mask)


def add(x: torch.Tensor, y: torch.Tensor) -> torch.Tensor:
    if x.shape != y.shape:
        raise ValueError("Input tensors must have the same shape")
    if x.numel() == 0:
        return torch.empty_like(x)
    if x.dtype != y.dtype:
        y = y.to(x.dtype)
    if not x.is_contiguous():
        x = x.contiguous()
    if not y.is_contiguous():
        y = y.contiguous()
    if x.device != y.device:
        y = y.to(x.device)
    if x.device.type != "cuda":
        return x + y

    n_elements = x.numel()
    out = torch.empty_like(x)

    grid = lambda META: (triton.cdiv(n_elements, META["BLOCK_SIZE"]),)

    dt = x.dtype
    if dt == torch.float32:
        _vec_add_kernel_fp32[grid](x, y, out, n_elements)
    elif dt in (torch.float16, torch.half):
        _vec_add_kernel_fp16[grid](x, y, out, n_elements)
    elif dt == torch.bfloat16:
        _vec_add_kernel_bf16[grid](x, y, out, n_elements)
    elif dt == torch.float64:
        _vec_add_kernel_fp64[grid](x, y, out, n_elements)
    else:
        out = x + y
    return out
'''
        return {"code": code}