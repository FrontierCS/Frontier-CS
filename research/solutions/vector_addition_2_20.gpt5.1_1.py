import torch
import triton
import triton.language as tl

KERNEL_SRC = '''import torch
import triton
import triton.language as tl


@triton.jit
def _add_kernel(X_ptr, Y_ptr, Z_ptr, n_elements, BLOCK_SIZE: tl.constexpr):
    pid = tl.program_id(axis=0)
    offsets = pid * BLOCK_SIZE + tl.arange(0, BLOCK_SIZE)
    mask = offsets < n_elements
    x = tl.load(X_ptr + offsets, mask=mask, other=0)
    y = tl.load(Y_ptr + offsets, mask=mask, other=0)
    z = x + y
    tl.store(Z_ptr + offsets, z, mask=mask)


def add(x: torch.Tensor, y: torch.Tensor) -> torch.Tensor:
    if x.device.type != 'cuda' or y.device.type != 'cuda':
        raise ValueError('Input tensors must be on CUDA device')
    if x.shape != y.shape:
        raise ValueError('Input tensors must have the same shape')
    if x.dim() != 1:
        raise ValueError('Input tensors must be 1D vectors')

    n_elements = x.numel()
    out = torch.empty_like(x)

    BLOCK_SIZE = 2048
    grid = (triton.cdiv(n_elements, BLOCK_SIZE),)

    _add_kernel[grid](
        x,
        y,
        out,
        n_elements,
        BLOCK_SIZE=BLOCK_SIZE,
        num_warps=8,
        num_stages=1,
    )
    return out
'''

exec(KERNEL_SRC, globals(), globals())


class Solution:
    def solve(self, spec_path: str = None) -> dict:
        return {"code": KERNEL_SRC}
