import torch
import triton
import triton.language as tl

_MAMBA2_CHUNK_SCAN_CODE = """
import torch
import triton
import triton.language as tl

@triton.jit
def _forward_kernel_pass1(
    X, A, B, Y, Chunk_A, Chunk_Y, A_cumprod,
    L, D,
    CHUNK_SIZE: tl.constexpr,
    BLOCK_D: tl.constexpr,
):
    # Each program instance handles one chunk (pid_l) for a block of features (pid_d)
    pid_l = tl.program_id(0)
    pid_d = tl.program_id(1)

    # Offsets for the current block
    l_offsets = pid_l * CHUNK_SIZE + tl.arange(0, CHUNK_SIZE)
    d_offsets = pid_d * BLOCK_D + tl.arange(0, BLOCK_D)

    # Pointers to the input and output tensors
    X_ptrs = X + l_offsets[:, None] * D + d_offsets[None, :]
    A_ptrs = A + l_offsets[:, None] * D + d_offsets[None, :]
    B_ptrs = B + l_offsets[:, None] * D + d_offsets[None, :]
    Y_ptrs = Y + l_offsets[:, None] * D + d_offsets[None, :]
    A_cumprod_ptrs = A_cumprod + l_offsets[:, None] * D + d_offsets[None, :]

    # Load input blocks from global memory
    # Use float32 for high-precision accumulation
    x_chunk = tl.load(X_ptrs).to(tl.float32)
    a_chunk = tl.load(A_ptrs).to(tl.float32)
    b_chunk = tl.load(B_ptrs).to(tl.float32)

    z_chunk = x_chunk * b_chunk

    # Initialize states for the scan
    h_state = tl.zeros([BLOCK_D], dtype=tl.float32)
    a_cp_state = tl.ones([BLOCK_D], dtype=tl.float32)

    # Intra-chunk scan loop
    for t in range(CHUNK_SIZE):
        a_t = a_chunk[t, :]
        z_t = z_chunk[t, :]
        
        h_state = a_t * h_state + z_t
        a_cp_state = a_t * a_cp_state

        # Store intermediate results (Y_partial and A_cumprod)
        tl.store(Y_ptrs + t * D, h_state.to(tl.float16))
        tl.store(A_cumprod_ptrs + t * D, a_cp_state)

    # Store the final state of the chunk for the next pass
    chunk_a_ptr = Chunk_A + pid_l * D + d_offsets
    chunk_y_ptr = Chunk_Y + pid_l * D + d_offsets
    
    tl.store(chunk_a_ptr, a_cp_state)
    tl.store(chunk_y_ptr, h_state)


@triton.jit
def _forward_kernel_pass2(
    Chunk_A, Chunk_Y, H_initial,
    NUM_CHUNKS, D,
    BLOCK_D: tl.constexpr,
):
    # Each program instance handles a block of features for all chunks
    pid_d = tl.program_id(0)

    d_offsets = pid_d * BLOCK_D + tl.arange(0, BLOCK_D)
    
    # Initialize the hidden state for the inter-chunk scan
    h_state = tl.zeros([BLOCK_D], dtype=tl.float32)

    # Inter-chunk scan loop
    for c in range(NUM_CHUNKS):
        # Store the initial state for the current chunk
        H_initial_ptr = H_initial + c * D + d_offsets
        tl.store(H_initial_ptr, h_state)

        # Load the transformation parameters for the current chunk
        a_chunk_ptr = Chunk_A + c * D + d_offsets
        y_chunk_ptr = Chunk_Y + c * D + d_offsets
        a_chunk = tl.load(a_chunk_ptr)
        y_chunk = tl.load(y_chunk_ptr)

        # Apply the transformation to update the state
        h_state = a_chunk * h_state + y_chunk


@triton.jit
def _forward_kernel_pass3(
    Y, A_cumprod, H_initial,
    L, D,
    CHUNK_SIZE: tl.constexpr,
    BLOCK_D: tl.constexpr,
):
    # Each program instance handles one chunk (pid_l) for a block of features (pid_d)
    pid_l = tl.program_id(0)
    pid_d = tl.program_id(1)

    # Chunk 0 is already correct, so we skip it
    if pid_l == 0:
        return

    # Offsets for the current block
    l_offsets = pid_l * CHUNK_SIZE + tl.arange(0, CHUNK_SIZE)
    d_offsets = pid_d * BLOCK_D + tl.arange(0, BLOCK_D)

    Y_ptrs = Y + l_offsets[:, None] * D + d_offsets[None, :]
    A_cumprod_ptrs = A_cumprod + l_offsets[:, None] * D + d_offsets[None, :]

    # Load the initial state for the current chunk from the result of pass 2
    h_initial_ptr = H_initial + pid_l * D + d_offsets
    h_initial = tl.load(h_initial_ptr)

    # Load the intermediate results from pass 1
    y_partial_chunk = tl.load(Y_ptrs).to(tl.float32)
    a_cumprod_chunk = tl.load(A_cumprod_ptrs) # This is already float32

    # Apply the correction factor
    correction = a_cumprod_chunk * h_initial[None, :]
    y_final_chunk = y_partial_chunk + correction

    # Store the final corrected result back to global memory
    tl.store(Y_ptrs, y_final_chunk.to(tl.float16))


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
    assert L % chunk == 0, "Sequence length L must be divisible by chunk size"
    assert D % BD == 0, "Feature dimension D must be divisible by block dimension BD"
    
    num_chunks = L // chunk

    # Allocate output and intermediate tensors
    # Y will store partial results from pass 1 and be corrected in pass 3
    Y = torch.empty_like(X)
    
    # Use float32 for intermediate states to maintain precision during accumulation
    Chunk_A = torch.empty((num_chunks, D), device=X.device, dtype=torch.float32)
    Chunk_Y = torch.empty((num_chunks, D), device=X.device, dtype=torch.float32)
    H_initial = torch.empty((num_chunks, D), device=X.device, dtype=torch.float32)
    A_cumprod = torch.empty((L, D), device=X.device, dtype=torch.float32)

    # Define grid dimensions for Triton kernels
    grid_p1_p3 = (num_chunks, D // BD)
    grid_p2 = (D // BD,)

    # Pass 1: Perform intra-chunk scans in parallel
    _forward_kernel_pass1[grid_p1_p3](
        X, A, B, Y, Chunk_A, Chunk_Y, A_cumprod,
        L, D,
        CHUNK_SIZE=chunk,
        BLOCK_D=BD,
    )

    # Pass 2: Perform inter-chunk scan to compute the correct initial states for each chunk
    _forward_kernel_pass2[grid_p2](
        Chunk_A, Chunk_Y, H_initial,
        num_chunks, D,
        BLOCK_D=BD,
    )

    # Pass 3: Apply corrections to the results from pass 1 using the initial states from pass 2
    _forward_kernel_pass3[grid_p1_p3](
        Y, A_cumprod, H_initial,
        L, D,
        CHUNK_SIZE=chunk,
        BLOCK_D=BD,
    )

    return Y
"""

class Solution:
    def solve(self, spec_path: str = None) -> dict:
        """
        Returns a dict with either:
        - {"code": "python_code_string"}
        - {"program_path": "path/to/kernel.py"}
        """
        return {"code": _MAMBA2_CHUNK_SCAN_CODE}