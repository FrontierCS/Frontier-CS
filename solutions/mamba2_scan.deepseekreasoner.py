import torch
import triton
import triton.language as tl


@triton.jit
def chunk_scan_kernel(
    x_ptr, a_ptr, b_ptr, y_ptr,
    stride_x_l, stride_x_d,
    stride_a_l, stride_a_d,
    stride_b_l, stride_b_d,
    stride_y_l, stride_y_d,
    L, D,
    chunk_size, BD: tl.constexpr,
    BLOCK_L: tl.constexpr,
    BLOCK_D: tl.constexpr,
):
    # Parallelize over chunks and feature blocks
    pid_chunk = tl.program_id(0)
    pid_feature = tl.program_id(1)
    
    # Compute chunk boundaries
    chunk_start = pid_chunk * chunk_size
    chunk_end = tl.minimum(chunk_start + chunk_size, L)
    
    # Feature block boundaries
    d_offset = pid_feature * BLOCK_D
    d_start = d_offset
    d_end = tl.minimum(d_start + BLOCK_D, D)
    d_size = d_end - d_start
    
    # Pointers for this feature block
    x_ptr += d_start * stride_x_d
    a_ptr += d_start * stride_a_d
    b_ptr += d_start * stride_b_d
    y_ptr += d_start * stride_y_d
    
    # Load chunk data into registers
    rows = tl.arange(0, BLOCK_L)
    cols = tl.arange(0, BLOCK_D)
    
    # Initialize carry from previous chunk
    carry = tl.zeros((BLOCK_D,), dtype=tl.float32)
    
    # Process each timestep in the chunk
    for i in range(chunk_start, chunk_end, BLOCK_L):
        l_idx = i + rows
        mask = (l_idx < chunk_end) & (cols < d_size)
        
        # Load inputs
        x = tl.load(
            x_ptr + l_idx * stride_x_l,
            mask=mask,
            other=0.0
        )
        a = tl.load(
            a_ptr + l_idx * stride_a_l,
            mask=mask,
            other=0.0
        )
        b = tl.load(
            b_ptr + l_idx * stride_b_l,
            mask=mask,
            other=0.0
        )
        
        # Convert to float32 for stable accumulation
        x_f32 = x.to(tl.float32)
        a_f32 = a.to(tl.float32)
        b_f32 = b.to(tl.float32)
        
        # Sequential scan computation
        for j in range(BLOCK_L):
            # Broadcast carry to all rows
            carry_broadcast = tl.broadcast_to(carry, (BLOCK_D,))
            
            # Compute current output
            y_val = a_f32[j] * carry_broadcast + b_f32[j] * x_f32[j]
            
            # Store if within bounds
            row_mask = (rows == j) & mask
            if tl.any(row_mask):
                tl.store(
                    y_ptr + l_idx[j] * stride_y_l,
                    y_val.to(tl.float16),
                    mask=row_mask
                )
            
            # Update carry for next iteration
            carry = tl.where(
                (l_idx[j] < chunk_end) & (cols < d_size),
                y_val,
                carry
            )
        
        # Move pointers to next block
        l_idx += BLOCK_L


@triton.jit
def chunk_scan_kernel_optimized(
    x_ptr, a_ptr, b_ptr, y_ptr,
    stride_x_l, stride_x_d,
    stride_a_l, stride_a_d,
    stride_b_l, stride_b_d,
    stride_y_l, stride_y_d,
    L, D,
    chunk_size, BD: tl.constexpr,
    BLOCK_L: tl.constexpr,
    BLOCK_D: tl.constexpr,
):
    # Parallelize over chunks and feature blocks
    pid_chunk = tl.program_id(0)
    pid_feature = tl.program_id(1)
    
    # Compute chunk boundaries
    chunk_start = pid_chunk * chunk_size
    chunk_end = tl.minimum(chunk_start + chunk_size, L)
    
    # Feature block boundaries
    d_offset = pid_feature * BLOCK_D
    d_start = d_offset
    d_end = tl.minimum(d_start + BLOCK_D, D)
    
    # Pointers for this feature block
    x_ptr += d_start * stride_x_d
    a_ptr += d_start * stride_a_d
    b_ptr += d_start * stride_b_d
    y_ptr += d_start * stride_y_d
    
    # Initialize carry from previous chunk
    carry = tl.zeros((BLOCK_D,), dtype=tl.float32)
    
    # Process each timestep in the chunk
    for l in range(chunk_start, chunk_end):
        # Create mask for this timestep
        cols = tl.arange(0, BLOCK_D)
        mask = cols < (d_end - d_start)
        
        # Load inputs for this timestep
        x = tl.load(
            x_ptr + l * stride_x_l,
            mask=mask,
            other=0.0
        )
        a = tl.load(
            a_ptr + l * stride_a_l,
            mask=mask,
            other=0.0
        )
        b = tl.load(
            b_ptr + l * stride_b_l,
            mask=mask,
            other=0.0
        )
        
        # Convert to float32 for stable accumulation
        x_f32 = x.to(tl.float32)
        a_f32 = a.to(tl.float32)
        b_f32 = b.to(tl.float32)
        
        # Compute scan: y_t = a_t * y_{t-1} + b_t * x_t
        y_val = a_f32 * carry + b_f32 * x_f32
        
        # Store output
        tl.store(
            y_ptr + l * stride_y_l,
            y_val.to(tl.float16),
            mask=mask
        )
        
        # Update carry for next iteration
        carry = tl.where(mask, y_val, carry)


@triton.jit
def chunk_scan_kernel_final(
    x_ptr, a_ptr, b_ptr, y_ptr,
    stride_x_l, stride_x_d,
    stride_a_l, stride_a_d,
    stride_b_l, stride_b_d,
    stride_y_l, stride_y_d,
    L, D,
    chunk_size: tl.constexpr,
    BD: tl.constexpr,
    BLOCK_L: tl.constexpr,
    BLOCK_D: tl.constexpr,
):
    # Parallelize over chunks and feature dimension blocks
    pid_chunk = tl.program_id(0)
    pid_feature = tl.program_id(1)
    
    # Compute chunk boundaries
    chunk_start = pid_chunk * chunk_size
    chunk_end = tl.minimum(chunk_start + chunk_size, L)
    
    # Compute feature block boundaries
    d_start = pid_feature * BLOCK_D
    d_end = tl.minimum(d_start + BLOCK_D, D)
    
    # Create masks
    l_offsets = tl.arange(0, BLOCK_L) + chunk_start
    d_offsets = tl.arange(0, BLOCK_D)
    
    l_mask = l_offsets < chunk_end
    d_mask = d_offsets < (d_end - d_start)
    mask = l_mask[:, None] & d_mask[None, :]
    
    # Compute pointer offsets
    x_offsets = l_offsets[:, None] * stride_x_l + (d_start + d_offsets[None, :]) * stride_x_d
    a_offsets = l_offsets[:, None] * stride_a_l + (d_start + d_offsets[None, :]) * stride_a_d
    b_offsets = l_offsets[:, None] * stride_b_l + (d_start + d_offsets[None, :]) * stride_b_d
    y_offsets = l_offsets[:, None] * stride_y_l + (d_start + d_offsets[None, :]) * stride_y_d
    
    # Load data for the entire chunk block
    x = tl.load(x_ptr + x_offsets, mask=mask, other=0.0)
    a = tl.load(a_ptr + a_offsets, mask=mask, other=0.0)
    b = tl.load(b_ptr + b_offsets, mask=mask, other=0.0)
    
    # Convert to float32 for stable computation
    x_f32 = x.to(tl.float32)
    a_f32 = a.to(tl.float32)
    b_f32 = b.to(tl.float32)
    
    # Initialize output array
    y = tl.zeros((BLOCK_L, BLOCK_D), dtype=tl.float32)
    
    # Sequential scan within the block
    carry = tl.zeros((BLOCK_D,), dtype=tl.float32)
    
    for i in range(BLOCK_L):
        # Get current row
        a_row = tl.where(l_mask[i], a_f32[i], 0.0)
        b_row = tl.where(l_mask[i], b_f32[i], 0.0)
        x_row = tl.where(l_mask[i], x_f32[i], 0.0)
        
        # Compute: y_t = a_t * y_{t-1} + b_t * x_t
        y_row = a_row * carry + b_row * x_row
        
        # Update carry for next iteration
        carry = tl.where(d_mask, y_row, carry)
        
        # Store row in output array
        y = tl.where(
            tl.broadcast_to((tl.arange(0, BLOCK_L) == i)[:, None], (BLOCK_L, BLOCK_D)),
            tl.broadcast_to(y_row[None, :], (BLOCK_L, BLOCK_D)),
            y
        )
    
    # Store output
    tl.store(y_ptr + y_offsets, y.to(tl.float16), mask=mask)


def chunk_scan(X: torch.Tensor, A: torch.Tensor, B: torch.Tensor, chunk: int = 128, BD: int = 128) -> torch.Tensor:
    """
    Mamba2 chunked scan computation.
    """
    L, D = X.shape
    
    # Validate inputs
    assert L % chunk == 0, f"Sequence length {L} must be divisible by chunk size {chunk}"
    assert X.dtype == torch.float16, f"Expected float16, got {X.dtype}"
    assert A.dtype == torch.float16, f"Expected float16, got {A.dtype}"
    assert B.dtype == torch.float16, f"Expected float16, got {B.dtype}"
    
    # Allocate output
    Y = torch.empty_like(X)
    
    # Choose kernel configuration
    num_chunks = L // chunk
    num_feature_blocks = triton.cdiv(D, BD)
    
    # Grid and block sizes
    grid = (num_chunks, num_feature_blocks)
    
    # Launch kernel
    chunk_scan_kernel_final[grid](
        X, A, B, Y,
        X.stride(0), X.stride(1),
        A.stride(0), A.stride(1),
        B.stride(0), B.stride(1),
        Y.stride(0), Y.stride(1),
        L, D,
        chunk,
        BD,
        BLOCK_L=chunk,
        BLOCK_D=BD,
    )
    
    return Y


class Solution:
    def solve(self, spec_path: str = None) -> dict:
        return {"code": self.get_code()}
    
    @staticmethod
    def get_code() -> str:
        import inspect
        return inspect.getsource(chunk_scan)
