import torch
import triton
import triton.language as tl

@triton.jit
def add_kernel(
    x_ptr,
    y_ptr,
    output_ptr,
    n_elements,
    BLOCK_SIZE: tl.constexpr,
):
    pid = tl.program_id(axis=0)
    block_start = pid * BLOCK_SIZE
    offsets = block_start + tl.arange(0, BLOCK_SIZE)
    
    mask = offsets < n_elements
    x = tl.load(x_ptr + offsets, mask=mask)
    y = tl.load(y_ptr + offsets, mask=mask)
    output = x + y
    tl.store(output_ptr + offsets, output, mask=mask)

@triton.jit
def add_kernel_vectorized(
    x_ptr,
    y_ptr,
    output_ptr,
    n_elements,
    BLOCK_SIZE: tl.constexpr,
    VECTOR_SIZE: tl.constexpr,
):
    pid = tl.program_id(axis=0)
    block_start = pid * BLOCK_SIZE * VECTOR_SIZE
    offsets = block_start + tl.arange(0, BLOCK_SIZE)[:, None] * VECTOR_SIZE + tl.arange(0, VECTOR_SIZE)[None, :]
    offsets = tl.reshape(offsets, (-1,))
    
    mask = offsets < n_elements
    x = tl.load(x_ptr + offsets, mask=mask)
    y = tl.load(y_ptr + offsets, mask=mask)
    output = x + y
    tl.store(output_ptr + offsets, output, mask=mask)

@triton.autotune(
    configs=[
        triton.Config({'BLOCK_SIZE': 256, 'VECTOR_SIZE': 4}, num_warps=4),
        triton.Config({'BLOCK_SIZE': 512, 'VECTOR_SIZE': 4}, num_warps=4),
        triton.Config({'BLOCK_SIZE': 1024, 'VECTOR_SIZE': 4}, num_warps=8),
        triton.Config({'BLOCK_SIZE': 2048, 'VECTOR_SIZE': 4}, num_warps=8),
        triton.Config({'BLOCK_SIZE': 4096, 'VECTOR_SIZE': 4}, num_warps=16),
        triton.Config({'BLOCK_SIZE': 256, 'VECTOR_SIZE': 8}, num_warps=4),
        triton.Config({'BLOCK_SIZE': 512, 'VECTOR_SIZE': 8}, num_warps=4),
        triton.Config({'BLOCK_SIZE': 1024, 'VECTOR_SIZE': 8}, num_warps=8),
        triton.Config({'BLOCK_SIZE': 2048, 'VECTOR_SIZE': 8}, num_warps=8),
        triton.Config({'BLOCK_SIZE': 4096, 'VECTOR_SIZE': 8}, num_warps=16),
    ],
    key=['n_elements'],
)
@triton.jit
def add_kernel_autotuned(
    x_ptr,
    y_ptr,
    output_ptr,
    n_elements,
    BLOCK_SIZE: tl.constexpr,
    VECTOR_SIZE: tl.constexpr,
):
    pid = tl.program_id(axis=0)
    block_start = pid * BLOCK_SIZE * VECTOR_SIZE
    offsets = block_start + tl.arange(0, BLOCK_SIZE)[:, None] * VECTOR_SIZE + tl.arange(0, VECTOR_SIZE)[None, :]
    offsets = tl.reshape(offsets, (-1,))
    
    mask = offsets < n_elements
    x = tl.load(x_ptr + offsets, mask=mask)
    y = tl.load(y_ptr + offsets, mask=mask)
    output = x + y
    tl.store(output_ptr + offsets, output, mask=mask)

def add(x: torch.Tensor, y: torch.Tensor) -> torch.Tensor:
    n_elements = x.numel()
    output = torch.empty_like(x)
    
    assert x.is_cuda and y.is_cuda, "Inputs must be on GPU"
    assert x.is_contiguous() and y.is_contiguous(), "Inputs must be contiguous"
    assert x.shape == y.shape, "Inputs must have same shape"
    
    grid = lambda meta: (triton.cdiv(n_elements, meta['BLOCK_SIZE'] * meta['VECTOR_SIZE']),)
    
    add_kernel_autotuned[grid](
        x, y, output, n_elements,
    )
    
    return output

class Solution:
    def solve(self, spec_path: str = None) -> dict:
        code = '''import torch
import triton
import triton.language as tl

@triton.jit
def add_kernel(
    x_ptr,
    y_ptr,
    output_ptr,
    n_elements,
    BLOCK_SIZE: tl.constexpr,
):
    pid = tl.program_id(axis=0)
    block_start = pid * BLOCK_SIZE
    offsets = block_start + tl.arange(0, BLOCK_SIZE)
    
    mask = offsets < n_elements
    x = tl.load(x_ptr + offsets, mask=mask)
    y = tl.load(y_ptr + offsets, mask=mask)
    output = x + y
    tl.store(output_ptr + offsets, output, mask=mask)

@triton.jit
def add_kernel_vectorized(
    x_ptr,
    y_ptr,
    output_ptr,
    n_elements,
    BLOCK_SIZE: tl.constexpr,
    VECTOR_SIZE: tl.constexpr,
):
    pid = tl.program_id(axis=0)
    block_start = pid * BLOCK_SIZE * VECTOR_SIZE
    offsets = block_start + tl.arange(0, BLOCK_SIZE)[:, None] * VECTOR_SIZE + tl.arange(0, VECTOR_SIZE)[None, :]
    offsets = tl.reshape(offsets, (-1,))
    
    mask = offsets < n_elements
    x = tl.load(x_ptr + offsets, mask=mask)
    y = tl.load(y_ptr + offsets, mask=mask)
    output = x + y
    tl.store(output_ptr + offsets, output, mask=mask)

@triton.autotune(
    configs=[
        triton.Config({'BLOCK_SIZE': 256, 'VECTOR_SIZE': 4}, num_warps=4),
        triton.Config({'BLOCK_SIZE': 512, 'VECTOR_SIZE': 4}, num_warps=4),
        triton.Config({'BLOCK_SIZE': 1024, 'VECTOR_SIZE': 4}, num_warps=8),
        triton.Config({'BLOCK_SIZE': 2048, 'VECTOR_SIZE': 4}, num_warps=8),
        triton.Config({'BLOCK_SIZE': 4096, 'VECTOR_SIZE': 4}, num_warps=16),
        triton.Config({'BLOCK_SIZE': 256, 'VECTOR_SIZE': 8}, num_warps=4),
        triton.Config({'BLOCK_SIZE': 512, 'VECTOR_SIZE': 8}, num_warps=4),
        triton.Config({'BLOCK_SIZE': 1024, 'VECTOR_SIZE': 8}, num_warps=8),
        triton.Config({'BLOCK_SIZE': 2048, 'VECTOR_SIZE': 8}, num_warps=8),
        triton.Config({'BLOCK_SIZE': 4096, 'VECTOR_SIZE': 8}, num_warps=16),
    ],
    key=['n_elements'],
)
@triton.jit
def add_kernel_autotuned(
    x_ptr,
    y_ptr,
    output_ptr,
    n_elements,
    BLOCK_SIZE: tl.constexpr,
    VECTOR_SIZE: tl.constexpr,
):
    pid = tl.program_id(axis=0)
    block_start = pid * BLOCK_SIZE * VECTOR_SIZE
    offsets = block_start + tl.arange(0, BLOCK_SIZE)[:, None] * VECTOR_SIZE + tl.arange(0, VECTOR_SIZE)[None, :]
    offsets = tl.reshape(offsets, (-1,))
    
    mask = offsets < n_elements
    x = tl.load(x_ptr + offsets, mask=mask)
    y = tl.load(y_ptr + offsets, mask=mask)
    output = x + y
    tl.store(output_ptr + offsets, output, mask=mask)

def add(x: torch.Tensor, y: torch.Tensor) -> torch.Tensor:
    n_elements = x.numel()
    output = torch.empty_like(x)
    
    assert x.is_cuda and y.is_cuda, "Inputs must be on GPU"
    assert x.is_contiguous() and y.is_contiguous(), "Inputs must be contiguous"
    assert x.shape == y.shape, "Inputs must have same shape"
    
    grid = lambda meta: (triton.cdiv(n_elements, meta['BLOCK_SIZE'] * meta['VECTOR_SIZE']),)
    
    add_kernel_autotuned[grid](
        x, y, output, n_elements,
    )
    
    return output'''
        
        return {"code": code}
