import torch
import triton
import triton.language as tl
import sys

# Define combine function for associative scan
@triton.jit
def scan_combine_fn(a, b):
    # a and b are tuples (decay, input)
    # state_new = decay_new * state_old + input_new
    # Combined state represents applying the sequence of operations
    # (a_left, u_left) followed by (a_right, u_right)
    # The decay for the combined range is product of decays: a_right * a_left
    # The input contribution is: a_right * u_left + u_right
    a_a, a_u = a
    b_a, b_u = b
    return (b_a * a_a, b_a * a_u + b_u)

@triton.jit
def _scan_kernel(
    X_ptr, A_ptr, B_ptr, Y_ptr,
    stride_x_l, stride_x_d,
    stride_a_l, stride_a_d,
    stride_b_l, stride_b_d,
    stride_y_l, stride_y_d,
    L, D,
    CHUNK_SIZE: tl.constexpr,
    BLOCK_D: tl.constexpr
):
    pid = tl.program_id(0)
    # Calculate feature columns handled by this block
    cols = pid * BLOCK_D + tl.arange(0, BLOCK_D)
    mask_d = cols < D

    # Initialize running state (accumulated y from previous chunk) to zeros
    # Shape: (BLOCK_D,)
    running_y = tl.zeros([BLOCK_D], dtype=tl.float32)

    # Iterate over the sequence length L in chunks
    for start_idx in range(0, L, CHUNK_SIZE):
        offs_l = start_idx + tl.arange(0, CHUNK_SIZE)
        
        # Calculate pointers for the current chunk
        # Broadcast offsets to (CHUNK_SIZE, BLOCK_D)
        # ptr = base + row_idx * stride_l + col_idx * stride_d
        ptr_x = X_ptr + offs_l[:, None] * stride_x_l + cols[None, :] * stride_x_d
        ptr_a = A_ptr + offs_l[:, None] * stride_a_l + cols[None, :] * stride_a_d
        ptr_b = B_ptr + offs_l[:, None] * stride_b_l + cols[None, :] * stride_b_d
        ptr_y = Y_ptr + offs_l[:, None] * stride_y_l + cols[None, :] * stride_y_d
        
        # Load inputs (float16 -> float32 for precision)
        # We only need to mask columns since L is divisible by CHUNK_SIZE
        a = tl.load(ptr_a, mask=mask_d[None, :], other=0.0).to(tl.float32)
        b = tl.load(ptr_b, mask=mask_d[None, :], other=0.0).to(tl.float32)
        x = tl.load(ptr_x, mask=mask_d[None, :], other=0.0).to(tl.float32)
        
        # Calculate local input term u_t = b_t * x_t
        u = b * x
        
        # Perform parallel associative scan on the chunk
        # axis=0 corresponds to the time dimension (CHUNK_SIZE)
        # This computes the cumulative effect within the chunk
        scan_a, scan_u = tl.associative_scan((a, u), axis=0, combine_fn=scan_combine_fn)
        
        # Propagate state from previous chunk
        # y_t = scan_u_t + scan_a_t * y_{prev}
        y = scan_u + scan_a * running_y[None, :]
        
        # Store result (convert back to float16)
        tl.store(ptr_y, y.to(tl.float16), mask=mask_d[None, :])
        
        # Update running_y for the next chunk
        # The state entering the next chunk is the last value of the current chunk
        # We extract the last row using a mask and sum reduction
        mask_last = (tl.arange(0, CHUNK_SIZE) == (CHUNK_SIZE - 1)).to(tl.float32)
        # Summing y * mask along axis 0 selects the last row
        running_y = tl.sum(y * mask_last[:, None], axis=0)

def chunk_scan(X: torch.Tensor, A: torch.Tensor, B: torch.Tensor, chunk: int = 128, BD: int = 128) -> torch.Tensor:
    """
    Mamba2 chunked scan computation using Triton.
    """
    assert X.is_cuda and A.is_cuda and B.is_cuda
    L, D = X.shape
    assert A.shape == (L, D)
    assert B.shape == (L, D)
    assert L % chunk == 0, "Length L must be divisible by chunk size"
    
    Y = torch.empty_like(X)
    
    # Grid size covers the feature dimension D
    grid = (triton.cdiv(D, BD),)
    
    _scan_kernel[grid](
        X, A, B, Y,
        X.stride(0), X.stride(1),
        A.stride(0), A.stride(1),
        B.stride(0), B.stride(1),
        Y.stride(0), Y.stride(1),
        L, D,
        CHUNK_SIZE=chunk,
        BLOCK_D=BD,
        num_warps=4
    )
    
    return Y

class Solution:
    def solve(self, spec_path: str = None) -> dict:
        """
        Returns the solution code.
        """
        return {"code": open(__file__).read()}
