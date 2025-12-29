import torch
import triton
import triton.language as tl

@triton.jit
def chunk_scan_kernel(
    x_ptr, a_ptr, b_ptr, y_ptr,
    l, d,
    stride_xl, stride_xd,
    stride_al, stride_ad,
    stride_bl, stride_bd,
    stride_yl, stride_yd,
    chunk_size: tl.constexpr,
    bd: tl.constexpr,
):
    pid = tl.program_id(0)
    
    # Process multiple chunks per program to reduce kernel launch overhead
    chunks_per_program = 4
    chunk_start = pid * chunks_per_program
    chunk_end = min(chunk_start + chunks_per_program, tl.cdiv(l, chunk_size))
    
    for chunk_idx in range(chunk_start, chunk_end):
        # Chunk boundaries
        chunk_l_start = chunk_idx * chunk_size
        chunk_l_end = min(chunk_l_start + chunk_size, l)
        
        # Process BD features per program
        for d_start in range(0, d, bd):
            d_end = min(d_start + bd, d)
            
            # Initialize state for this chunk
            if chunk_idx == 0:
                state = tl.zeros([bd], dtype=tl.float16)
            else:
                # Load state from previous chunk
                state_ptr = y_ptr + (chunk_l_start - 1) * stride_yl + d_start * stride_yd
                state = tl.load(state_ptr + tl.arange(0, bd), mask=tl.arange(0, bd) < (d_end - d_start))
            
            # Process chunk elements sequentially
            for l_pos in range(chunk_l_start, chunk_l_end):
                # Calculate offsets
                x_offset = l_pos * stride_xl + d_start * stride_xd
                a_offset = l_pos * stride_al + d_start * stride_ad
                b_offset = l_pos * stride_bl + d_start * stride_bd
                y_offset = l_pos * stride_yl + d_start * stride_yd
                
                # Load data
                x_mask = tl.arange(0, bd) < (d_end - d_start)
                x = tl.load(x_ptr + x_offset + tl.arange(0, bd), mask=x_mask, other=0)
                a = tl.load(a_ptr + a_offset + tl.arange(0, bd), mask=x_mask, other=0)
                b = tl.load(b_ptr + b_offset + tl.arange(0, bd), mask=x_mask, other=0)
                
                # Compute scan: y_t = a_t * y_{t-1} + b_t * x_t
                y = a * state + b * x
                state = y
                
                # Store result
                tl.store(y_ptr + y_offset + tl.arange(0, bd), y, mask=x_mask)

def chunk_scan(X: torch.Tensor, A: torch.Tensor, B: torch.Tensor, chunk: int = 128, BD: int = 128) -> torch.Tensor:
    """
    Mamba2 chunked scan computation.
    
    Args:
        X: Input tensor of shape (L, D) - input sequence (float16)
        A: Input tensor of shape (L, D) - decay factors (float16)
        B: Input tensor of shape (L, D) - input weights (float16)
        chunk: Chunk size for parallel processing (default 128)
        BD: Block dimension for feature dimension tiling (default 128)
    
    Returns:
        Output tensor of shape (L, D) - scan output (float16)
    """
    L, D = X.shape
    Y = torch.empty_like(X)
    
    # Validate input constraints
    assert L % chunk == 0, f"Sequence length {L} must be divisible by chunk size {chunk}"
    assert X.dtype == torch.float16, "Input tensors must be float16"
    
    # Calculate optimal grid size
    num_chunks = L // chunk
    programs_per_chunk = (D + BD - 1) // BD
    total_programs = (num_chunks * programs_per_chunk + 3) // 4
    
    # Launch kernel
    chunk_scan_kernel[(total_programs,)](
        X, A, B, Y,
        L, D,
        X.stride(0), X.stride(1),
        A.stride(0), A.stride(1),
        B.stride(0), B.stride(1),
        Y.stride(0), Y.stride(1),
        chunk_size=chunk,
        bd=BD,
    )
    
    return Y

class Solution:
    def solve(self, spec_path: str = None) -> dict:
        return {"code": __import__("inspect").getsource(chunk_scan)}