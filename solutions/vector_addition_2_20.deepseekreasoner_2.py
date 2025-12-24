import torch
import triton
import triton.language as tl
from typing import Optional

@triton.autotune(
    configs=[
        triton.Config({'BLOCK_SIZE': 256}, num_warps=4),
        triton.Config({'BLOCK_SIZE': 512}, num_warps=4),
        triton.Config({'BLOCK_SIZE': 1024}, num_warps=8),
        triton.Config({'BLOCK_SIZE': 2048}, num_warps=8),
        triton.Config({'BLOCK_SIZE': 4096}, num_warps=16),
    ],
    key=['n'],
)
@triton.jit
def _add_kernel(
    x_ptr,
    y_ptr,
    output_ptr,
    n,
    BLOCK_SIZE: tl.constexpr,
    VEC_SIZE: tl.constexpr,
):
    pid = tl.program_id(axis=0)
    vec_off = pid * BLOCK_SIZE * VEC_SIZE
    offsets = vec_off + tl.arange(0, BLOCK_SIZE)[:, None] * VEC_SIZE + tl.arange(0, VEC_SIZE)[None, :]
    mask = offsets < n
    
    x_vecs = tl.load(x_ptr + offsets, mask=mask, other=0.0)
    y_vecs = tl.load(y_ptr + offsets, mask=mask, other=0.0)
    result_vecs = x_vecs + y_vecs
    tl.store(output_ptr + offsets, result_vecs, mask=mask)

def add(x: torch.Tensor, y: torch.Tensor) -> torch.Tensor:
    n = x.numel()
    output = torch.empty_like(x)
    
    grid = lambda meta: (triton.cdiv(n, meta['BLOCK_SIZE'] * meta['VEC_SIZE']),)
    
    VEC_SIZE = 4 if x.dtype in [torch.float32, torch.int32] else 2
    
    _add_kernel[grid](
        x, y, output, n,
        VEC_SIZE=VEC_SIZE
    )
    return output

class Solution:
    def solve(self, spec_path: str = None) -> dict:
        code = """import torch
import triton
import triton.language as tl
from typing import Optional

@triton.autotune(
    configs=[
        triton.Config({'BLOCK_SIZE': 256}, num_warps=4),
        triton.Config({'BLOCK_SIZE': 512}, num_warps=4),
        triton.Config({'BLOCK_SIZE': 1024}, num_warps=8),
        triton.Config({'BLOCK_SIZE': 2048}, num_warps=8),
        triton.Config({'BLOCK_SIZE': 4096}, num_warps=16),
    ],
    key=['n'],
)
@triton.jit
def _add_kernel(
    x_ptr,
    y_ptr,
    output_ptr,
    n,
    BLOCK_SIZE: tl.constexpr,
    VEC_SIZE: tl.constexpr,
):
    pid = tl.program_id(axis=0)
    vec_off = pid * BLOCK_SIZE * VEC_SIZE
    offsets = vec_off + tl.arange(0, BLOCK_SIZE)[:, None] * VEC_SIZE + tl.arange(0, VEC_SIZE)[None, :]
    mask = offsets < n
    
    x_vecs = tl.load(x_ptr + offsets, mask=mask, other=0.0)
    y_vecs = tl.load(y_ptr + offsets, mask=mask, other=0.0)
    result_vecs = x_vecs + y_vecs
    tl.store(output_ptr + offsets, result_vecs, mask=mask)

def add(x: torch.Tensor, y: torch.Tensor) -> torch.Tensor:
    n = x.numel()
    output = torch.empty_like(x)
    
    grid = lambda meta: (triton.cdiv(n, meta['BLOCK_SIZE'] * meta['VEC_SIZE']),)
    
    if x.dtype in [torch.float32, torch.int32]:
        VEC_SIZE = 4
    elif x.dtype in [torch.float64, torch.int64]:
        VEC_SIZE = 2
    elif x.dtype in [torch.float16, torch.bfloat16, torch.int16]:
        VEC_SIZE = 8
    else:
        VEC_SIZE = 16
    
    _add_kernel[grid](
        x, y, output, n,
        VEC_SIZE=VEC_SIZE
    )
    return output"""
        
        return {"code": code}
