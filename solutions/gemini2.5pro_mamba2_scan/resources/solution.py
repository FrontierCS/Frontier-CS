import torch

class Solution:
    def solve(self, spec_path: str = None) -> dict:
        code = r'''
import torch
import triton
import triton.language as tl

@triton.jit
def _kernel1_intra_scan(
    # Pointers to tensors
    X, A, B, Y,
    A_chunks, H_chunks,
    # Dimensions
    L, D,
    # Compile-time constants
    chunk: tl.constexpr,
    BD: tl.constexpr,
):
    """
    Kernel 1: Intra-chunk Scan.
    For each chunk, performs a sequential scan independently.
    y'_t = a_t * y'_{t-1} + b_t * x_t, with y'_{-1} = 0.
    Also calculates the chunk's total decay (product of A's) and final state.
    These are stored for the next phase.
    Grid: (D/BD, L/chunk)
    """
    # Program IDs
    pid_d_block = tl.program_id(0)
    pid_l_chunk = tl.program_id(1)

    # Offsets for feature dimension
    offs_d = pid_d_block * BD + tl.arange(0, BD)
    
    # Base pointers for the current chunk
    chunk_base_ptr_offset = pid_l_chunk * chunk * D
    curr_X_ptr = X + chunk_base_ptr_offset + offs_d
    curr_A_ptr = A + chunk_base_ptr_offset + offs_d
    curr_B_ptr = B + chunk_base_ptr_offset + offs_d
    curr_Y_ptr = Y + chunk_base_ptr_offset + offs_d

    # Initialize states for intra-chunk scan
    h_state = tl.zeros([BD], dtype=tl.float32)
    a_prefix = tl.ones([BD], dtype=tl.float32)

    # Sequential scan within the chunk
    for i in range(chunk):
        a_i = tl.load(curr_A_ptr).to(tl.float32)
        b_i = tl.load(curr_B_ptr).to(tl.float32)
        x_i = tl.load(curr_X_ptr).to(tl.float32)
        
        # Scan update: h_t = a_t * h_{t-1} + b_t * x_t
        h_state = h_state * a_i + b_i * x_i
        
        # Store the partial result (intra-chunk scan)
        tl.store(curr_Y_ptr, h_state.to(tl.float16))

        # Update the prefix product of A's for the chunk state
        a_prefix = a_prefix * a_i
        
        # Increment pointers to the next row
        curr_X_ptr += D
        curr_A_ptr += D
        curr_B_ptr += D
        curr_Y_ptr += D

    # Store the final state and prefix product for this chunk
    # These will be used in the inter-chunk scan
    A_chunks_ptr = A_chunks + pid_l_chunk * D + offs_d
    H_chunks_ptr = H_chunks + pid_l_chunk * D + offs_d
    tl.store(A_chunks_ptr, a_prefix.to(tl.float16))
    tl.store(H_chunks_ptr, h_state.to(tl.float16))


@triton.jit
def _kernel2_inter_scan(
    # Pointers to tensors
    A_chunks, H_chunks,
    # Dimensions
    D, num_chunks,
    # Compile-time constants
    BD: tl.constexpr
):
    """
    Kernel 2: Inter-chunk Scan (State Propagation).
    Performs a sequential scan over the chunk-end states from Kernel 1.
    This correctly propagates the hidden state across chunk boundaries.
    Grid: (D/BD,)
    """
    pid_d_block = tl.program_id(0)
    offs_d = pid_d_block * BD + tl.arange(0, BD)

    h_carry = tl.zeros([BD], dtype=tl.float32)

    # Pointers to the start of the columns
    curr_A_chunk_ptr = A_chunks + offs_d
    curr_H_chunk_ptr = H_chunks + offs_d

    for i in range(num_chunks):
        a_i = tl.load(curr_A_chunk_ptr).to(tl.float32)
        h_i = tl.load(curr_H_chunk_ptr).to(tl.float32)

        # Apply the associative combine operation
        # h_new = a_i * h_carry_{i-1} + h_i
        h_new = h_carry * a_i + h_i
        
        # Store the updated (propagated) state back
        tl.store(curr_H_chunk_ptr, h_new.to(tl.float16))
        
        # Update carry for the next iteration
        h_carry = h_new
        
        # Increment pointers to the next chunk's state
        curr_A_chunk_ptr += D
        curr_H_chunk_ptr += D


@triton.jit
def _kernel3_correction(
    # Pointers to tensors
    Y, A, H_chunks,
    # Dimensions
    L, D,
    # Compile-time constants
    chunk: tl.constexpr,
    BD: tl.constexpr,
):
    """
    Kernel 3: Correction.
    Corrects the intra-chunk scan results using the propagated states.
    y_corrected = y_intra + (prefix_prod(A) * h_prev_chunk_state)
    The prefix product of A is recomputed to save memory bandwidth.
    Grid: (D/BD, L/chunk - 1)
    """
    pid_d_block = tl.program_id(0)
    pid_l_chunk = tl.program_id(1) + 1 # Correct chunks from index 1 onwards

    offs_d = pid_d_block * BD + tl.arange(0, BD)
    
    # Load the correctly propagated state from the *previous* chunk
    h_prev_ptr = H_chunks + (pid_l_chunk - 1) * D + offs_d
    h_prev = tl.load(h_prev_ptr).to(tl.float32)

    # Base pointers for the current chunk
    chunk_base_ptr_offset = pid_l_chunk * chunk * D
    curr_Y_ptr = Y + chunk_base_ptr_offset + offs_d
    curr_A_ptr = A + chunk_base_ptr_offset + offs_d
    
    a_prefix = tl.ones([BD], dtype=tl.float32)
    for i in range(chunk):
        y_intra = tl.load(curr_Y_ptr).to(tl.float32)
        a_i = tl.load(curr_A_ptr).to(tl.float32)
        
        # Update prefix product
        a_prefix = a_prefix * a_i

        # Apply correction: y_corrected = y_intra + (prefix_prod(A) * h_prev)
        y_corrected = y_intra + a_prefix * h_prev
        
        # Store corrected value back
        tl.store(curr_Y_ptr, y_corrected.to(tl.float16))
        
        # Increment pointers
        curr_Y_ptr += D
        curr_A_ptr += D


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
    
    # The benchmark guarantees that L is divisible by chunk and D by BD.
    # No need for a fallback path for this problem.
    num_chunks = L // chunk
    
    # Allocate output and intermediate tensors
    Y = torch.empty_like(X)
    # Tensors to store the state at the end of each chunk
    A_chunks = torch.empty(num_chunks, D, device=X.device, dtype=X.dtype)
    H_chunks = torch.empty(num_chunks, D, device=X.device, dtype=X.dtype)

    # --- Kernel 1: Intra-chunk Scan ---
    # Each block processes one chunk for a BD-slice of the D dimension.
    grid1 = (D // BD, num_chunks)
    _kernel1_intra_scan[grid1](
        X, A, B, Y,
        A_chunks, H_chunks,
        L, D,
        chunk=chunk,
        BD=BD,
    )

    # If there is only one chunk, no inter-chunk communication is needed.
    if num_chunks > 1:
        # --- Kernel 2: Inter-chunk Scan ---
        # Scan over the chunk states to propagate the values correctly.
        # Each block handles a BD-slice of D for all chunks.
        grid2 = (D // BD,)
        _kernel2_inter_scan[grid2](
            A_chunks, H_chunks,
            D, num_chunks,
            BD=BD
        )

        # --- Kernel 3: Correction ---
        # Apply the propagated states to correct the intra-chunk results.
        # This is not needed for the first chunk, so the grid is smaller.
        grid3 = (D // BD, num_chunks - 1)
        _kernel3_correction[grid3](
            Y, A, H_chunks,
            L, D, 
            chunk=chunk,
            BD=BD
        )
    
    return Y
'''
        return {"code": code}
