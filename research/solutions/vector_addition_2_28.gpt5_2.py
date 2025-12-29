import torch
import triton
import triton.language as tl


class Solution:
    def solve(self, spec_path: str = None) -> dict:
        code = '''
import torch
import triton
import triton.language as tl

@triton.autotune(
    configs=[
        triton.Config({"BLOCK_SIZE": 4096}, num_warps=4, num_stages=2),
        triton.Config({"BLOCK_SIZE": 8192}, num_warps=8, num_stages=2),
        triton.Config({"BLOCK_SIZE": 16384}, num_warps=8, num_stages=2),
    ],
    key=["n_elements"],
)
@triton.jit
def _vec_add_kernel(
    x_ptr: tl.pointer_type(tl.float32),
    y_ptr: tl.pointer_type(tl.float32),
    out_ptr: tl.pointer_type(tl.float32),
    n_elements: tl.int32,
    BLOCK_SIZE: tl.constexpr,
):
    pid = tl.program_id(axis=0)
    offsets = pid * BLOCK_SIZE + tl.arange(0, BLOCK_SIZE)
    mask = offsets < n_elements
    x = tl.load(x_ptr + offsets, mask=mask, other=0.0, cache_modifier=".cg")
    y = tl.load(y_ptr + offsets, mask=mask, other=0.0, cache_modifier=".cg")
    z = x + y
    tl.store(out_ptr + offsets, z, mask=mask)

def add(x: torch.Tensor, y: torch.Tensor) -> torch.Tensor:
    """
    Element-wise addition of two vectors.

    Args:
        x: Input tensor of shape (268435456,)
        y: Input tensor of shape (268435456,)

    Returns:
        Output tensor of shape (268435456,) with x + y
    """
    assert x.is_cuda and y.is_cuda, "Inputs must be CUDA tensors"
    assert x.is_contiguous() and y.is_contiguous(), "Inputs must be contiguous"
    assert x.numel() == y.numel(), "Inputs must have the same number of elements"
    # Use float32 for maximum bandwidth; problem spec implies float32 (1GB per vector)
    if x.dtype != torch.float32:
        x = x.to(torch.float32)
    if y.dtype != torch.float32:
        y = y.to(torch.float32)
    n_elements = x.numel()
    out = torch.empty_like(x, dtype=torch.float32)
    grid = lambda meta: (triton.cdiv(n_elements, meta["BLOCK_SIZE"]),)
    _vec_add_kernel[grid](x, y, out, n_elements)
    return out
'''
        return {"code": code}