import torch
import triton
import triton.language as tl

BLOCK_SIZE = 4096


@triton.jit
def _add_kernel(x_ptr, y_ptr, out_ptr, n_elements, BLOCK_SIZE: tl.constexpr):
    pid = tl.program_id(axis=0)
    block_start = pid * BLOCK_SIZE
    offsets = block_start + tl.arange(0, BLOCK_SIZE)
    mask = offsets < n_elements
    x = tl.load(x_ptr + offsets, mask=mask)
    y = tl.load(y_ptr + offsets, mask=mask)
    tl.store(out_ptr + offsets, x + y, mask=mask)


def add(x: torch.Tensor, y: torch.Tensor) -> torch.Tensor:
    if x.numel() != y.numel():
        raise ValueError("Input tensors must have the same number of elements")
    n_elements = x.numel()
    if n_elements == 0:
        return x + y
    if not x.is_cuda or not y.is_cuda:
        return x + y
    if x.device != y.device:
        raise ValueError("Input tensors must be on the same device")
    if not x.is_contiguous():
        x = x.contiguous()
    if not y.is_contiguous():
        y = y.contiguous()
    out = torch.empty_like(x)
    grid = (triton.cdiv(n_elements, BLOCK_SIZE),)
    _add_kernel[grid](
        x,
        y,
        out,
        n_elements,
        BLOCK_SIZE=BLOCK_SIZE,
        num_warps=8,
        num_stages=4,
    )
    return out


class Solution:
    def solve(self, spec_path: str = None) -> dict:
        kernel_code = (
            "import torch\n"
            "import triton\n"
            "import triton.language as tl\n"
            "\n"
            "BLOCK_SIZE = 4096\n"
            "\n"
            "@triton.jit\n"
            "def _add_kernel(x_ptr, y_ptr, out_ptr, n_elements, BLOCK_SIZE: tl.constexpr):\n"
            "    pid = tl.program_id(axis=0)\n"
            "    block_start = pid * BLOCK_SIZE\n"
            "    offsets = block_start + tl.arange(0, BLOCK_SIZE)\n"
            "    mask = offsets < n_elements\n"
            "    x = tl.load(x_ptr + offsets, mask=mask)\n"
            "    y = tl.load(y_ptr + offsets, mask=mask)\n"
            "    tl.store(out_ptr + offsets, x + y, mask=mask)\n"
            "\n"
            "def add(x: torch.Tensor, y: torch.Tensor) -> torch.Tensor:\n"
            "    if x.numel() != y.numel():\n"
            "        raise ValueError('Input tensors must have the same number of elements')\n"
            "    n_elements = x.numel()\n"
            "    if n_elements == 0:\n"
            "        return x + y\n"
            "    if not x.is_cuda or not y.is_cuda:\n"
            "        return x + y\n"
            "    if x.device != y.device:\n"
            "        raise ValueError('Input tensors must be on the same device')\n"
            "    if not x.is_contiguous():\n"
            "        x = x.contiguous()\n"
            "    if not y.is_contiguous():\n"
            "        y = y.contiguous()\n"
            "    out = torch.empty_like(x)\n"
            "    grid = (triton.cdiv(n_elements, BLOCK_SIZE),)\n"
            "    _add_kernel[grid](\n"
            "        x,\n"
            "        y,\n"
            "        out,\n"
            "        n_elements,\n"
            "        BLOCK_SIZE=BLOCK_SIZE,\n"
            "        num_warps=8,\n"
            "        num_stages=4,\n"
            "    )\n"
            "    return out\n"
        )
        return {"code": kernel_code}