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
def _forward_chunk_state_kernel(
    # Pointers to matrices
    X, A, B,
    Y_chunk_final, A_chunk_final,
    # Matrix dimensions
    L, D,
    # Strides
    X_L_STRIDE: tl.constexpr,
    STATE_L_STRIDE: tl.constexpr,
    # Kernel parameters
    BLOCK_L: tl.constexpr, BLOCK_D: tl.constexpr,
):
    # This program processes one chunk of size [BLOCK_L, BLOCK_D]
    pid_c = tl.program_id(0)  # Chunk ID
    pid_d = tl.program_id(1)  # Feature block ID

    # Offsets for the current program
    d_offset = pid_d * BLOCK_D
    l_offset = pid_c * BLOCK_L
    
    # Pointers to the start of the current block in the input tensors
    x_block_ptr = X + l_offset * X_L_STRIDE
    a_block_ptr = A + l_offset * X_L_STRIDE
    b_block_ptr = B + l_offset * X_L_STRIDE

    # Column indices for the feature block
    d_cols = d_offset + tl.arange(0, BLOCK_D)
    d_mask = d_cols < D

    # State accumulators, initialized to identity
    h = tl.zeros((BLOCK_D,), dtype=tl.float32)
    a_scan = tl.ones((BLOCK_D,), dtype=tl.float32)

    # Intra-chunk scan loop
    for t in range(BLOCK_L):
        # Pointers to the current row
        x_row_ptr = x_block_ptr + t * X_L_STRIDE
        a_row_ptr = a_block_ptr + t * X_L_STRIDE
        b_row_ptr = b_block_ptr + t * X_L_STRIDE
        
        # Load data for the current time step, converting to float32 for computation
        x = tl.load(x_row_ptr + d_cols, mask=d_mask, other=0.0).to(tl.float32)
        a = tl.load(a_row_ptr + d_cols, mask=d_mask, other=0.0).to(tl.float32)
        b = tl.load(b_row_ptr + d_cols, mask=d_mask, other=0.0).to(tl.float32)
        
        # The scan recurrence: y_t = a_t * y_{t-1} + b_t * x_t
        h = a * h + b * x
        # Cumulative product of A's
        a_scan = a * a_scan
        
    # Pointers to store the final state of the chunk
    y_final_ptr = Y_chunk_final + pid_c * STATE_L_STRIDE + d_cols
    a_final_ptr = A_chunk_final + pid_c * STATE_L_STRIDE + d_cols
    
    # Store the computed final states
    tl.store(y_final_ptr, h, mask=d_mask)
    tl.store(a_final_ptr, a_scan, mask=d_mask)


@triton.jit
def _scan_chunk_states_kernel(
    # Pointers to matrices
    Y_chunk_final, A_chunk_final, H_initial,
    # Matrix dimensions
    NUM_CHUNKS: tl.constexpr, D: tl.constexpr,
    # Strides
    STATE_L_STRIDE: tl.constexpr,
    # Kernel parameters
    BLOCK_D: tl.constexpr,
):
    # This program processes a vertical slice of features across all chunks
    pid_d = tl.program_id(0)  # Feature block ID
    
    d_offset = pid_d * BLOCK_D
    d_cols = d_offset + tl.arange(0, BLOCK_D)
    d_mask = d_cols < D

    # Initial state for the scan-of-scans
    h_carry = tl.zeros((BLOCK_D,), dtype=tl.float32)
    
    # Loop over chunks to perform the scan
    for c in range(NUM_CHUNKS):
        # Store the initial state for the current chunk c
        h_init_ptr = H_initial + c * STATE_L_STRIDE + d_cols
        tl.store(h_init_ptr, h_carry, mask=d_mask)
        
        # Load the final states from chunk c
        y_final_ptr = Y_chunk_final + c * STATE_L_STRIDE + d_cols
        a_final_ptr = A_chunk_final + c * STATE_L_STRIDE + d_cols
        
        y_c = tl.load(y_final_ptr, mask=d_mask, other=0.0)
        a_c = tl.load(a_final_ptr, mask=d_mask, other=0.0)
        
        # Update the carry for the next chunk
        h_carry = a_c * h_carry + y_c


@triton.jit
def _recompute_and_correct_kernel(
    # Pointers to matrices
    X, A, B, H_initial, Y,
    # Matrix dimensions
    L, D,
    # Strides
    X_L_STRIDE: tl.constexpr,
    STATE_L_STRIDE: tl.constexpr,
    # Kernel parameters
    BLOCK_L: tl.constexpr, BLOCK_D: tl.constexpr,
):
    # This program processes one chunk, same as the first kernel
    pid_c = tl.program_id(0)  # Chunk ID
    pid_d = tl.program_id(1)  # Feature block ID

    d_offset = pid_d * BLOCK_D
    l_offset = pid_c * BLOCK_L
    
    d_cols = d_offset + tl.arange(0, BLOCK_D)
    d_mask = d_cols < D

    # Load the corrected initial state for this chunk
    h_init_ptr = H_initial + pid_c * STATE_L_STRIDE + d_cols
    h = tl.load(h_init_ptr, mask=d_mask, other=0.0)

    # Pointers to the start of the current block
    x_block_ptr = X + l_offset * X_L_STRIDE
    a_block_ptr = A + l_offset * X_L_STRIDE
    b_block_ptr = B + l_offset * X_L_STRIDE
    y_block_ptr = Y + l_offset * X_L_STRIDE

    # Recompute the scan within the chunk using the correct initial state
    for t in range(BLOCK_L):
        x_row_ptr = x_block_ptr + t * X_L_STRIDE
        a_row_ptr = a_block_ptr + t * X_L_STRIDE
        b_row_ptr = b_block_ptr + t * X_L_STRIDE
        
        x = tl.load(x_row_ptr + d_cols, mask=d_mask, other=0.0).to(tl.float32)
        a = tl.load(a_row_ptr + d_cols, mask=d_mask, other=0.0).to(tl.float32)
        b = tl.load(b_row_ptr + d_cols, mask=d_mask, other=0.0).to(tl.float32)
        
        # Apply the scan recurrence
        h = a * h + b * x
        
        # Store the final result, casting back to float16
        y_row_ptr = y_block_ptr + t * X_L_STRIDE
        tl.store(y_row_ptr + d_cols, h.to(tl.float16), mask=d_mask)


def chunk_scan(X: torch.Tensor, A: torch.Tensor, B: torch.Tensor, chunk: int = 128, BD: int = 128) -> torch.Tensor:
    L, D = X.shape
    if L % chunk != 0:
        raise ValueError("Sequence length L must be divisible by chunk size")
    
    num_chunks = L // chunk
    
    # Allocate intermediate tensors for storing chunk-wise states.
    # Use float32 for better precision in inter-chunk computations.
    Y_chunk_final = torch.empty((num_chunks, D), device=X.device, dtype=torch.float32)
    A_chunk_final = torch.empty((num_chunks, D), device=X.device, dtype=torch.float32)
    H_initial = torch.empty((num_chunks, D), device=X.device, dtype=torch.float32)
    # Final output tensor.
    Y = torch.empty_like(X, dtype=torch.float16)

    # --- Kernel 1: Parallel intra-chunk scan ---
    # Each program computes the final state of one chunk.
    grid1 = (num_chunks, triton.cdiv(D, BD))
    _forward_chunk_state_kernel[grid1](
        X, A, B, Y_chunk_final, A_chunk_final,
        L, D,
        X_L_STRIDE=X.stride(0),
        STATE_L_STRIDE=Y_chunk_final.stride(0),
        BLOCK_L=chunk, BLOCK_D=BD,
        num_warps=4,
        num_stages=2
    )

    # --- Kernel 2: Scan-of-scans ---
    # A small sequential scan over the chunk final states to find the correct
    # initial state for each chunk. Parallelism is only over the feature dimension.
    grid2 = (triton.cdiv(D, BD),)
    _scan_chunk_states_kernel[grid2](
        Y_chunk_final, A_chunk_final, H_initial,
        NUM_CHUNKS=num_chunks, D=D,
        STATE_L_STRIDE=Y_chunk_final.stride(0),
        BLOCK_D=BD,
        num_warps=4
    )
    
    # --- Kernel 3: Recompute and correct ---
    # Recompute the intra-chunk scan, but this time starting with the correct
    # initial state. This pass is highly parallel.
    grid3 = (num_chunks, triton.cdiv(D, BD))
    _recompute_and_correct_kernel[grid3](
        X, A, B, H_initial, Y,
        L, D,
        X_L_STRIDE=X.stride(0),
        STATE_L_STRIDE=H_initial.stride(0),
        BLOCK_L=chunk, BLOCK_D=BD,
        num_warps=4,
        num_stages=2
    )

    return Y
"""
        return {"code": code}