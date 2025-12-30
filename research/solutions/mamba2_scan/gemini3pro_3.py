import torch
import triton
import triton.language as tl
import sys

@triton.jit
def scan_pre_kernel(
    X_ptr, A_ptr, B_ptr,
    Inter_A_ptr, Inter_U_ptr,
    stride_x0, stride_x1,
    stride_i0, stride_i1,
    D,
    CHUNK_SIZE: tl.constexpr,
    BLOCK_D: tl.constexpr
):
    pid_c = tl.program_id(0)
    pid_d = tl.program_id(1)
    
    offs_d = pid_d * BLOCK_D + tl.arange(0, BLOCK_D)
    mask = offs_d < D
    
    # Offsets for this chunk
    row_start = pid_c * CHUNK_SIZE
    
    # Input pointers
    # Assuming X, A, B have same strides and shapes
    off_base = row_start * stride_x0 + offs_d * stride_x1
    x_ptrs = X_ptr + off_base
    a_ptrs = A_ptr + off_base
    b_ptrs = B_ptr + off_base
    
    # Accumulators (FP32)
    acc_a = tl.full([BLOCK_D], 1.0, dtype=tl.float32)
    acc_u = tl.full([BLOCK_D], 0.0, dtype=tl.float32)
    
    for i in range(CHUNK_SIZE):
        a = tl.load(a_ptrs, mask=mask, other=0.0).to(tl.float32)
        b = tl.load(b_ptrs, mask=mask, other=0.0).to(tl.float32)
        x = tl.load(x_ptrs, mask=mask, other=0.0).to(tl.float32)
        
        # y_t = a_t * y_{t-1} + b_t * x_t
        # Update accumulators
        u = b * x
        acc_u = a * acc_u + u
        acc_a = a * acc_a
        
        x_ptrs += stride_x0
        a_ptrs += stride_x0
        b_ptrs += stride_x0
        
    # Output pointers
    out_off = pid_c * stride_i0 + offs_d * stride_i1
    tl.store(Inter_A_ptr + out_off, acc_a.to(tl.float16), mask=mask)
    tl.store(Inter_U_ptr + out_off, acc_u.to(tl.float16), mask=mask)

@triton.jit
def scan_inter_kernel(
    Inter_A_ptr, Inter_U_ptr,
    Start_State_ptr,
    stride_i0, stride_i1,
    D,
    NUM_CHUNKS: tl.constexpr,
    BLOCK_D: tl.constexpr
):
    # This kernel processes one feature block across all chunks
    pid_d = tl.program_id(0)
    offs_d = pid_d * BLOCK_D + tl.arange(0, BLOCK_D)
    mask = offs_d < D
    
    # State accumulator
    state = tl.zeros([BLOCK_D], dtype=tl.float32)
    
    # Store state for chunk 0 (always 0)
    # Start_State_ptr offset for chunk 0
    start_off = 0 * stride_i0 + offs_d * stride_i1
    tl.store(Start_State_ptr + start_off, state.to(tl.float16), mask=mask)
    
    # Pointers
    ia_ptrs = Inter_A_ptr + offs_d * stride_i1
    iu_ptrs = Inter_U_ptr + offs_d * stride_i1
    # We output to Start_State starting from chunk 1
    out_ptrs = Start_State_ptr + stride_i0 + offs_d * stride_i1
    
    for c in range(NUM_CHUNKS - 1):
        ia = tl.load(ia_ptrs, mask=mask, other=0.0).to(tl.float32)
        iu = tl.load(iu_ptrs, mask=mask, other=0.0).to(tl.float32)
        
        state = ia * state + iu
        
        tl.store(out_ptrs, state.to(tl.float16), mask=mask)
        
        ia_ptrs += stride_i0
        iu_ptrs += stride_i0
        out_ptrs += stride_i0

@triton.jit
def scan_post_kernel(
    X_ptr, A_ptr, B_ptr,
    Start_State_ptr,
    Y_ptr,
    stride_x0, stride_x1,
    stride_s0, stride_s1,
    stride_y0, stride_y1,
    D,
    CHUNK_SIZE: tl.constexpr,
    BLOCK_D: tl.constexpr
):
    pid_c = tl.program_id(0)
    pid_d = tl.program_id(1)
    
    offs_d = pid_d * BLOCK_D + tl.arange(0, BLOCK_D)
    mask = offs_d < D
    
    # Load initial state for this chunk
    state_off = pid_c * stride_s0 + offs_d * stride_s1
    state = tl.load(Start_State_ptr + state_off, mask=mask, other=0.0).to(tl.float32)
    
    row_start = pid_c * CHUNK_SIZE
    off_base_x = row_start * stride_x0 + offs_d * stride_x1
    off_base_y = row_start * stride_y0 + offs_d * stride_y1
    
    x_ptrs = X_ptr + off_base_x
    a_ptrs = A_ptr + off_base_x
    b_ptrs = B_ptr + off_base_x
    y_ptrs = Y_ptr + off_base_y
    
    for i in range(CHUNK_SIZE):
        a = tl.load(a_ptrs, mask=mask, other=0.0).to(tl.float32)
        b = tl.load(b_ptrs, mask=mask, other=0.0).to(tl.float32)
        x = tl.load(x_ptrs, mask=mask, other=0.0).to(tl.float32)
        
        u = b * x
        state = a * state + u
        
        tl.store(y_ptrs, state.to(tl.float16), mask=mask)
        
        x_ptrs += stride_x0
        a_ptrs += stride_x0
        b_ptrs += stride_x0
        y_ptrs += stride_y0

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
    assert L % chunk == 0, "L must be divisible by chunk"
    num_chunks = L // chunk
    
    # Intermediate buffers for chunk summaries
    Inter_A = torch.empty((num_chunks, D), dtype=torch.float16, device=X.device)
    Inter_U = torch.empty((num_chunks, D), dtype=torch.float16, device=X.device)
    # Buffer for chunk start states
    Start_State = torch.empty((num_chunks, D), dtype=torch.float16, device=X.device)
    # Output
    Y = torch.empty_like(X)
    
    # 1. Chunk Accumulation (Parallel over chunks and features)
    grid_pre = (num_chunks, (D + BD - 1) // BD)
    scan_pre_kernel[grid_pre](
        X, A, B, Inter_A, Inter_U,
        X.stride(0), X.stride(1),
        Inter_A.stride(0), Inter_A.stride(1),
        D,
        CHUNK_SIZE=chunk, BLOCK_D=BD
    )
    
    # 2. Inter-chunk Scan (Parallel over features, Serial over chunks)
    grid_inter = ((D + BD - 1) // BD,)
    scan_inter_kernel[grid_inter](
        Inter_A, Inter_U, Start_State,
        Inter_A.stride(0), Inter_A.stride(1),
        D,
        NUM_CHUNKS=num_chunks, BLOCK_D=BD
    )
    
    # 3. Final Generation (Parallel over chunks and features)
    grid_post = (num_chunks, (D + BD - 1) // BD)
    scan_post_kernel[grid_post](
        X, A, B, Start_State, Y,
        X.stride(0), X.stride(1),
        Start_State.stride(0), Start_State.stride(1),
        Y.stride(0), Y.stride(1),
        D,
        CHUNK_SIZE=chunk, BLOCK_D=BD
    )
    
    return Y

class Solution:
    def solve(self, spec_path: str = None) -> dict:
        """
        Returns a dict with either:
        - {"code": "python_code_string"}
        - {"program_path": "path/to/kernel.py"}
        """
        return {"program_path": __file__}