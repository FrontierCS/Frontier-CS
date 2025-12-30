import torch
import triton
import triton.language as tl
import os

@triton.jit
def _chunk_scan_pass1_kernel(
    X_ptr, A_ptr, B_ptr,
    Chunk_A_ptr, Chunk_Y_ptr,
    stride_L, stride_D,
    L, D, chunk_size,
    BLOCK_D: tl.constexpr
):
    # Pass 1: Local Scan & Reduction within each chunk
    # Calculates the total product of A (decay) and the local accumulated sum Y for the chunk
    
    pid_c = tl.program_id(0)
    pid_d = tl.program_id(1)
    
    offs_d = pid_d * BLOCK_D + tl.arange(0, BLOCK_D)
    mask_d = offs_d < D
    
    start_l = pid_c * chunk_size
    
    # Initialize accumulators
    # acc_a: product of a's (multiplicative identity = 1.0)
    # acc_y: local scan result assuming 0 initial state (additive identity = 0.0)
    acc_a = tl.zeros([BLOCK_D], dtype=tl.float32) + 1.0
    acc_y = tl.zeros([BLOCK_D], dtype=tl.float32)
    
    # Iterate over the chunk
    for i in range(chunk_size):
        idx_l = start_l + i
        offs = idx_l * stride_L + offs_d
        
        # Load inputs with masking
        a = tl.load(A_ptr + offs, mask=mask_d, other=0.0).to(tl.float32)
        b = tl.load(B_ptr + offs, mask=mask_d, other=0.0).to(tl.float32)
        x = tl.load(X_ptr + offs, mask=mask_d, other=0.0).to(tl.float32)
        
        # Update accumulators
        # y_t = a_t * y_{t-1} + b_t * x_t
        acc_y = a * acc_y + b * x
        acc_a = a * acc_a
        
    # Store chunk summaries
    out_idx = pid_c * D + offs_d
    tl.store(Chunk_A_ptr + out_idx, acc_a.to(tl.float16), mask=mask_d)
    tl.store(Chunk_Y_ptr + out_idx, acc_y.to(tl.float16), mask=mask_d)

@triton.jit
def _chunk_scan_pass2_kernel(
    Chunk_A_ptr, Chunk_Y_ptr,
    Chunk_State_ptr,
    num_chunks, D,
    BLOCK_D: tl.constexpr
):
    # Pass 2: Sequential Scan over Chunk Summaries
    # Computes the state at the end of each chunk by propagating across chunks
    
    pid_d = tl.program_id(0)
    offs_d = pid_d * BLOCK_D + tl.arange(0, BLOCK_D)
    mask_d = offs_d < D
    
    # Running state initialization
    h = tl.zeros([BLOCK_D], dtype=tl.float32)
    
    for i in range(num_chunks):
        idx = i * D + offs_d
        
        c_a = tl.load(Chunk_A_ptr + idx, mask=mask_d, other=0.0).to(tl.float32)
        c_y = tl.load(Chunk_Y_ptr + idx, mask=mask_d, other=0.0).to(tl.float32)
        
        # Update global state: H_k = A_chunk * H_{k-1} + Y_chunk
        h = c_a * h + c_y
        
        # Store state at END of chunk i
        tl.store(Chunk_State_ptr + idx, h.to(tl.float16), mask=mask_d)

@triton.jit
def _chunk_scan_pass3_kernel(
    X_ptr, A_ptr, B_ptr,
    Chunk_State_ptr,
    Y_ptr,
    stride_L, stride_D,
    L, D, chunk_size,
    BLOCK_D: tl.constexpr
):
    # Pass 3: Final Scan / Downsweep
    # Computes final outputs using initial states from Pass 2
    
    pid_c = tl.program_id(0)
    pid_d = tl.program_id(1)
    
    offs_d = pid_d * BLOCK_D + tl.arange(0, BLOCK_D)
    mask_d = offs_d < D
    
    # Load initial state for this chunk
    h = tl.zeros([BLOCK_D], dtype=tl.float32)
    if pid_c > 0:
        # State at end of previous chunk is start state for this chunk
        prev_idx = (pid_c - 1) * D + offs_d
        h = tl.load(Chunk_State_ptr + prev_idx, mask=mask_d, other=0.0).to(tl.float32)
        
    start_l = pid_c * chunk_size
    
    for i in range(chunk_size):
        idx_l = start_l + i
        offs = idx_l * stride_L + offs_d
        
        a = tl.load(A_ptr + offs, mask=mask_d, other=0.0).to(tl.float32)
        b = tl.load(B_ptr + offs, mask=mask_d, other=0.0).to(tl.float32)
        x = tl.load(X_ptr + offs, mask=mask_d, other=0.0).to(tl.float32)
        
        h = a * h + b * x
        
        tl.store(Y_ptr + offs, h.to(tl.float16), mask=mask_d)

def chunk_scan(X: torch.Tensor, A: torch.Tensor, B: torch.Tensor, chunk: int = 128, BD: int = 128) -> torch.Tensor:
    """
    Mamba2 chunked scan computation using Triton.
    Algorithm: 3-pass parallel scan
    1. Local Reduce: Compute chunk summaries (prod_a, sum_y)
    2. Global Scan: Scan the summaries to get initial state for each chunk
    3. Final Scan: Compute final results using propagated states
    """
    assert X.is_cuda and A.is_cuda and B.is_cuda
    L, D = X.shape
    
    # Check constraints
    assert L % chunk == 0, f"L ({L}) must be divisible by chunk ({chunk})"
    
    num_chunks = L // chunk
    
    # Allocate temporary buffers for chunk summaries and states
    # chunk_a: product of A in each chunk
    chunk_a = torch.empty((num_chunks, D), device=X.device, dtype=torch.float16)
    # chunk_y: local scan sum in each chunk
    chunk_y = torch.empty((num_chunks, D), device=X.device, dtype=torch.float16)
    # chunk_state: state at the end of each chunk after global scan
    chunk_state = torch.empty((num_chunks, D), device=X.device, dtype=torch.float16)
    
    # Allocate output tensor
    Y = torch.empty_like(X)
    
    # Grid dimensions
    # Pass 1 & 3: Parallel across chunks and feature blocks
    grid_parallel = (num_chunks, triton.cdiv(D, BD))
    # Pass 2: Parallel across feature blocks only (sequential over chunks)
    grid_scan = (triton.cdiv(D, BD), )
    
    # Execute Pass 1
    _chunk_scan_pass1_kernel[grid_parallel](
        X, A, B,
        chunk_a, chunk_y,
        X.stride(0), X.stride(1),
        L, D, chunk,
        BLOCK_D=BD
    )
    
    # Execute Pass 2
    _chunk_scan_pass2_kernel[grid_scan](
        chunk_a, chunk_y,
        chunk_state,
        num_chunks, D,
        BLOCK_D=BD
    )
    
    # Execute Pass 3
    _chunk_scan_pass3_kernel[grid_parallel](
        X, A, B,
        chunk_state,
        Y,
        X.stride(0), X.stride(1),
        L, D, chunk,
        BLOCK_D=BD
    )
    
    return Y

class Solution:
    def solve(self, spec_path: str = None) -> dict:
        return {"program_path": os.path.abspath(__file__)}