import math
import torch
import triton
import triton.language as tl


@triton.jit
def _add_kernel(x_ptr, y_ptr, o_ptr, n_elements, BLOCK: tl.constexpr, VEC: tl.constexpr):
    pid = tl.program_id(0)
    block_start = pid * BLOCK * VEC
    ar0 = tl.arange(0, BLOCK)[:, None]
    ar1 = tl.arange(0, VEC)[None, :]
    offsets = block_start + ar0 * VEC + ar1
    mask = offsets < n_elements

    x = tl.load(x_ptr + offsets, mask=mask, other=0)
    y = tl.load(y_ptr + offsets, mask=mask, other=0)
    z = x + y
    tl.store(o_ptr + offsets, z, mask=mask)


def add(x: torch.Tensor, y: torch.Tensor) -> torch.Tensor:
    assert x.shape == y.shape, "Input tensors must have the same shape"
    assert x.is_contiguous() and y.is_contiguous(), "Inputs must be contiguous"
    assert x.device.type == "cuda" and y.device.type == "cuda", "Inputs must be on CUDA device"
    assert x.dtype == y.dtype, "Inputs must have the same dtype"

    n_elements = x.numel()
    out = torch.empty_like(x)

    # Choose vectorization factor based on alignment and dtype size (target 16B vector width)
    elem_bytes = x.element_size()
    max_vec = max(1, 16 // elem_bytes)
    aligned16 = (x.data_ptr() % 16 == 0) and (y.data_ptr() % 16 == 0) and (out.data_ptr() % 16 == 0)
    vec = max_vec if aligned16 else 1

    # Choose tile size: bytes per program ~ 32KB-64KB; adapt BLOCK with vectorization
    target_tile_elems = 8192  # elements per program
    block = max(256, target_tile_elems // vec)

    # Heuristic for kernel launch parameters
    if block * vec >= 8192:
        num_warps = 8
    else:
        num_warps = 4
    num_stages = 2

    grid = lambda META: (triton.cdiv(n_elements, META["BLOCK"] * META["VEC"]),)

    _add_kernel[grid](
        x, y, out, n_elements,
        BLOCK=block,
        VEC=vec,
        num_warps=num_warps,
        num_stages=num_stages,
    )
    return out


class Solution:
    def solve(self, spec_path: str = None) -> dict:
        code = '''
import math
import torch
import triton
import triton.language as tl


@triton.jit
def _add_kernel(x_ptr, y_ptr, o_ptr, n_elements, BLOCK: tl.constexpr, VEC: tl.constexpr):
    pid = tl.program_id(0)
    block_start = pid * BLOCK * VEC
    ar0 = tl.arange(0, BLOCK)[:, None]
    ar1 = tl.arange(0, VEC)[None, :]
    offsets = block_start + ar0 * VEC + ar1
    mask = offsets < n_elements

    x = tl.load(x_ptr + offsets, mask=mask, other=0)
    y = tl.load(y_ptr + offsets, mask=mask, other=0)
    z = x + y
    tl.store(o_ptr + offsets, z, mask=mask)


def add(x: torch.Tensor, y: torch.Tensor) -> torch.Tensor:
    assert x.shape == y.shape, "Input tensors must have the same shape"
    assert x.is_contiguous() and y.is_contiguous(), "Inputs must be contiguous"
    assert x.device.type == "cuda" and y.device.type == "cuda", "Inputs must be on CUDA device"
    assert x.dtype == y.dtype, "Inputs must have the same dtype"

    n_elements = x.numel()
    out = torch.empty_like(x)

    elem_bytes = x.element_size()
    max_vec = max(1, 16 // elem_bytes)
    aligned16 = (x.data_ptr() % 16 == 0) and (y.data_ptr() % 16 == 0) and (out.data_ptr() % 16 == 0)
    vec = max_vec if aligned16 else 1

    target_tile_elems = 8192
    block = max(256, target_tile_elems // vec)

    if block * vec >= 8192:
        num_warps = 8
    else:
        num_warps = 4
    num_stages = 2

    grid = lambda META: (triton.cdiv(n_elements, META["BLOCK"] * META["VEC"]),)

    _add_kernel[grid](
        x, y, out, n_elements,
        BLOCK=block,
        VEC=vec,
        num_warps=num_warps,
        num_stages=num_stages,
    )
    return out
'''
        return {"code": code}
