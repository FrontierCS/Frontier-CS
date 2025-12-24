class Solution:
    def solve(self, spec_path: str = None) -> dict:
        code = """
import torch
import triton
import triton.language as tl

@triton.jit
def add_kernel(
    x_ptr, y_ptr, output_ptr,
    n_elements: tl.constexpr,
    BLOCK_SIZE: tl.constexpr
):
    pid = tl.program_id(0)
    block_start = pid * BLOCK_SIZE
    offsets = block_start + tl.arange(0, BLOCK_SIZE)
    mask = offsets < n_elements
    x = tl.load(x_ptr + offsets, mask=mask)
    y = tl.load(y_ptr + offsets, mask=mask)
    z = x + y
    tl.store(output_ptr + offsets, z, mask=mask)

def add(x: torch.Tensor, y: torch.Tensor) -> torch.Tensor:
    output = torch.empty_like(x)
    N = x.numel()
    assert x.shape == y.shape == (N,)
    BLOCK_SIZE = 1024
    grid = lambda meta: (triton.cdiv(N, meta["BLOCK_SIZE"]),)
    add_kernel[grid](x, y, output, N, BLOCK_SIZE=BLOCK_SIZE)
    return output
"""
        return {"code": code}
