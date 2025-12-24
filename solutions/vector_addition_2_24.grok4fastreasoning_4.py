import torch
import triton
import triton.language as tl

class Solution:
    def solve(self, spec_path: str = None) -> dict:
        code = """
import torch
import triton
import triton.language as tl

@triton.jit
def add_kernel(
    x_ptr, y_ptr, z_ptr,
    n: tl.int32,
    BLOCK_SIZE: tl.constexpr
):
    pid = tl.program_id(0)
    block_start = pid * BLOCK_SIZE
    offsets = block_start + tl.arange(0, BLOCK_SIZE)
    mask = offsets < n
    x = tl.load(x_ptr + offsets, mask=mask)
    y = tl.load(y_ptr + offsets, mask=mask)
    z = x + y
    tl.store(z_ptr + offsets, z, mask=mask)

def add(x: torch.Tensor, y: torch.Tensor) -> torch.Tensor:
    n = x.numel()
    z = torch.empty_like(x)
    BLOCK_SIZE = 1024
    grid = (triton.cdiv(n, BLOCK_SIZE), )
    add_kernel[grid](x, y, z, n, BLOCK_SIZE=BLOCK_SIZE)
    return z
"""
        return {"code": code}
