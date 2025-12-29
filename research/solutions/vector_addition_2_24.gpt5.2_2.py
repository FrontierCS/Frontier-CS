import torch
import triton
import triton.language as tl

N_ELEMENTS = 16777216

@triton.jit
def _add_kernel(x_ptr, y_ptr, o_ptr, BLOCK: tl.constexpr, ITERS: tl.constexpr):
    tl.multiple_of(x_ptr, 16)
    tl.multiple_of(y_ptr, 16)
    tl.multiple_of(o_ptr, 16)

    pid = tl.program_id(0)
    base = pid * (BLOCK * ITERS)
    tl.multiple_of(base, 256)

    r = tl.arange(0, BLOCK)
    for i in tl.static_range(ITERS):
        offs = base + i * BLOCK + r
        x = tl.load(x_ptr + offs, cache_modifier=".cg", eviction_policy="evict_last")
        y = tl.load(y_ptr + offs, cache_modifier=".cg", eviction_policy="evict_last")
        tl.store(o_ptr + offs, x + y, cache_modifier=".wb")


def add(x: torch.Tensor, y: torch.Tensor) -> torch.Tensor:
    if not (isinstance(x, torch.Tensor) and isinstance(y, torch.Tensor)):
        raise TypeError("x and y must be torch.Tensor")
    if x.numel() != N_ELEMENTS or y.numel() != N_ELEMENTS:
        raise AssertionError(f"Expected vectors of length {N_ELEMENTS}")
    if x.device != y.device:
        raise AssertionError("x and y must be on the same device")
    if x.dtype != y.dtype:
        raise AssertionError("x and y must have the same dtype")
    if not (x.is_contiguous() and y.is_contiguous()):
        x = x.contiguous()
        y = y.contiguous()

    if not x.is_cuda:
        return x + y

    if x.dtype == torch.float64:
        return x + y

    out = torch.empty_like(x)

    BLOCK = 1024
    ITERS = 8
    grid = (N_ELEMENTS // (BLOCK * ITERS),)

    _add_kernel[grid](
        x, y, out,
        BLOCK=BLOCK,
        ITERS=ITERS,
        num_warps=8,
        num_stages=1,
    )
    return out


_PROGRAM_CODE = (
    "import torch\n"
    "import triton\n"
    "import triton.language as tl\n"
    "\n"
    "N_ELEMENTS = 16777216\n"
    "\n"
    "@triton.jit\n"
    "def _add_kernel(x_ptr, y_ptr, o_ptr, BLOCK: tl.constexpr, ITERS: tl.constexpr):\n"
    "    tl.multiple_of(x_ptr, 16)\n"
    "    tl.multiple_of(y_ptr, 16)\n"
    "    tl.multiple_of(o_ptr, 16)\n"
    "    pid = tl.program_id(0)\n"
    "    base = pid * (BLOCK * ITERS)\n"
    "    tl.multiple_of(base, 256)\n"
    "    r = tl.arange(0, BLOCK)\n"
    "    for i in tl.static_range(ITERS):\n"
    "        offs = base + i * BLOCK + r\n"
    "        x = tl.load(x_ptr + offs, cache_modifier='.cg', eviction_policy='evict_last')\n"
    "        y = tl.load(y_ptr + offs, cache_modifier='.cg', eviction_policy='evict_last')\n"
    "        tl.store(o_ptr + offs, x + y, cache_modifier='.wb')\n"
    "\n"
    "def add(x: torch.Tensor, y: torch.Tensor) -> torch.Tensor:\n"
    "    if x.numel() != N_ELEMENTS or y.numel() != N_ELEMENTS:\n"
    "        raise AssertionError(f'Expected vectors of length {N_ELEMENTS}')\n"
    "    if x.device != y.device:\n"
    "        raise AssertionError('x and y must be on the same device')\n"
    "    if x.dtype != y.dtype:\n"
    "        raise AssertionError('x and y must have the same dtype')\n"
    "    if not (x.is_contiguous() and y.is_contiguous()):\n"
    "        x = x.contiguous()\n"
    "        y = y.contiguous()\n"
    "    if not x.is_cuda:\n"
    "        return x + y\n"
    "    if x.dtype == torch.float64:\n"
    "        return x + y\n"
    "    out = torch.empty_like(x)\n"
    "    BLOCK = 1024\n"
    "    ITERS = 8\n"
    "    grid = (N_ELEMENTS // (BLOCK * ITERS),)\n"
    "    _add_kernel[grid](x, y, out, BLOCK=BLOCK, ITERS=ITERS, num_warps=8, num_stages=1)\n"
    "    return out\n"
)

class Solution:
    def solve(self, spec_path: str = None) -> dict:
        return {"code": _PROGRAM_CODE}