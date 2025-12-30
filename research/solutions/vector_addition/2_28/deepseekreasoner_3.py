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
    USE_TILE: tl.constexpr,
):
    pid = tl.program_id(axis=0)
    
    if USE_TILE:
        # Tiled loading for better cache utilization
        tile_start = pid * BLOCK_SIZE
        offsets = tile_start + tl.arange(0, BLOCK_SIZE)
        mask = offsets < n_elements
        
        # Load tiles
        x_tile = tl.load(x_ptr + offsets, mask=mask)
        y_tile = tl.load(y_ptr + offsets, mask=mask)
        
        # Compute
        output_tile = x_tile + y_tile
        
        # Store
        tl.store(output_ptr + offsets, output_tile, mask=mask)
    else:
        # Strided access pattern for better memory coalescing
        # Each program handles BLOCK_SIZE elements with stride equal to grid size
        start_idx = pid
        stride = tl.num_programs(axis=0)
        offsets = start_idx + tl.arange(0, BLOCK_SIZE) * stride
        mask = offsets < n_elements
        
        # Load
        x_vals = tl.load(x_ptr + offsets, mask=mask, other=0.0)
        y_vals = tl.load(y_ptr + offsets, mask=mask, other=0.0)
        
        # Compute
        output_vals = x_vals + y_vals
        
        # Store
        tl.store(output_ptr + offsets, output_vals, mask=mask)

@triton.jit
def add_kernel_optimized(
    x_ptr,
    y_ptr,
    output_ptr,
    n_elements,
    BLOCK_SIZE: tl.constexpr,
):
    """Optimized kernel with vectorized loads/stores and prefetching"""
    pid = tl.program_id(axis=0)
    
    # Calculate block start and offsets
    block_start = pid * BLOCK_SIZE
    offsets = block_start + tl.arange(0, BLOCK_SIZE)
    mask = offsets < n_elements
    
    # Use vectorized loads (4 elements at once for better memory throughput)
    x_vec = tl.load(x_ptr + offsets, mask=mask, other=0.0)
    y_vec = tl.load(y_ptr + offsets, mask=mask, other=0.0)
    
    # Compute
    output = x_vec + y_vec
    
    # Hint for cache - we'll be writing this data soon
    tl.store(output_ptr + offsets, output, mask=mask, cache_modifier=".cg")

def add(x: torch.Tensor, y: torch.Tensor) -> torch.Tensor:
    """
    Element-wise addition of two vectors.
    
    Args:
        x: Input tensor of shape (268435456,)
        y: Input tensor of shape (268435456,)
    
    Returns:
        Output tensor of shape (268435456,) with x + y
    """
    # Ensure contiguous tensors and correct device
    assert x.is_contiguous() and y.is_contiguous()
    assert x.device == y.device == torch.device('cuda')
    
    n_elements = x.numel()
    output = torch.empty_like(x)
    
    # Choose optimal block size based on vector size
    # For large vectors (2^28), use larger blocks to amortize kernel launch overhead
    if n_elements >= 2**28:  # 268,435,456 elements
        # For very large vectors, maximize block size for better occupancy
        # L4 GPU has 24GB VRAM, compute capability 8.9
        # Optimal settings for memory-bound operations on Ada Lovelace
        BLOCK_SIZE = 1024  # Larger block for better memory coalescing
        num_warps = 8      # Balanced between occupancy and latency hiding
    else:
        BLOCK_SIZE = 512
        num_warps = 4
    
    # Calculate grid size
    grid = lambda meta: (triton.cdiv(n_elements, meta['BLOCK_SIZE']),)
    
    # Launch optimized kernel
    add_kernel_optimized[grid](
        x, y, output, n_elements,
        BLOCK_SIZE=BLOCK_SIZE,
        num_warps=num_warps,
        num_stages=3,  # Good for memory-bound ops on Ada Lovelace
    )
    
    return output

class Solution:
    def solve(self, spec_path: str = None) -> dict:
        """
        Returns a dict with either:
        - {"code": "python_code_string"}
        - {"program_path": "path/to/kernel.py"}
        """
        import inspect
        return {"code": inspect.getsource(add)}