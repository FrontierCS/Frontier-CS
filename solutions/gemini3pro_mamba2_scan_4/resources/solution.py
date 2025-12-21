import torch
import triton
import triton.language as tl

class Solution:
    def solve(self, spec_path: str = None) -> dict:
        code = r"""
import torch
import triton
import triton.language as tl

@triton.jit
def _chunk_scan_pass1_kernel(
    X_ptr, A_ptr, B_ptr, State_ptr,
    stride_row, stride_d,
    stride_state_c, stride_state_d, stride_state_val,
    D,
    BLOCK_D: tl.constexpr, CHUNK_SIZE: tl.constexpr
):
    pid_c = tl.program_id(0)
    pid_d = tl.program_id(1)
    
    offs_d = pid_d * BLOCK_D + tl.arange(0, BLOCK_D)
    mask_d = offs_d < D
    
    row_start = pid_c * CHUNK_SIZE
    off_base = row_start * stride_row + offs_d * stride_d
    
    # Initialize accumulators
    # acc_a: Product of 'a' factors
    # acc_u: Accumulation of updates
    acc_a = tl.zeros([BLOCK_D], dtype=tl.float32) + 1.0
    acc_u = tl.zeros([BLOCK_D], dtype=tl.float32)
    
    x_ptrs = X_ptr + off_base
    a_ptrs = A_ptr + off_base
    b_ptrs = B_ptr + off_base
    
    for i in range(CHUNK_SIZE):
        a = tl.load(a_ptrs, mask=mask_d, other=0.0).to(tl.float32)
        b = tl.load(b_ptrs, mask=mask_d, other=0.0).to(tl.float32)
        x = tl.load(x_ptrs, mask=mask_d, other=0.0).to(tl.float32)
        
        # Update state:
        # y_new = a * y_old + b * x
        # If y_old = acc_a * y_start + acc_u
        # y_new = a * (acc_a * y_start + acc_u) + b * x
        #       = (a * acc_a) * y_start + (a * acc_u + b * x)
        
        acc_u = a * acc_u + b * x
        acc_a = a * acc_a
        
        x_ptrs += stride_row
        a_ptrs += stride_row
        b_ptrs += stride_row

    # Store state (coefficients for the chunk)
    state_ptr_a = State_ptr + pid_c * stride_state_c + offs_d * stride_state_d + 0 * stride_state_val
    state_ptr_u = State_ptr + pid_c * stride_state_c + offs_d * stride_state_d + 1 * stride_state_val
    
    tl.store(state_ptr_a, acc_a, mask=mask_d)
    tl.store(state_ptr_u, acc_u, mask=mask_d)

@triton.jit
def _chunk_scan_pass2_kernel(
    State_ptr, Scan_ptr,
    stride_state_c, stride_state_d, stride_state_val,
    stride_scan_c, stride_scan_d,
    NumChunks, D,
    BLOCK_D: tl.constexpr
):
    pid_d = tl.program_id(0)
    offs_d = pid_d * BLOCK_D + tl.arange(0, BLOCK_D)
    mask_d = offs_d < D
    
    # running_y represents the state y at the END of the previous chunk
    running_y = tl.zeros([BLOCK_D], dtype=tl.float32)
    
    # Sequential scan over chunks for each feature
    for c in range(NumChunks):
        state_ptr_a = State_ptr + c * stride_state_c + offs_d * stride_state_d + 0 * stride_state_val
        state_ptr_u = State_ptr + c * stride_state_c + offs_d * stride_state_d + 1 * stride_state_val
        
        a = tl.load(state_ptr_a, mask=mask_d, other=1.0)
        u = tl.load(state_ptr_u, mask=mask_d, other=0.0)
        
        # Apply chunk transformation
        running_y = a * running_y + u
        
        # Store y at end of chunk c
        scan_ptr = Scan_ptr + c * stride_scan_c + offs_d * stride_scan_d
        tl.store(scan_ptr, running_y, mask=mask_d)

@triton.jit
def _chunk_scan_pass3_kernel(
    X_ptr, A_ptr, B_ptr, Scan_ptr, Y_ptr,
    stride_row, stride_d,
    stride_scan_c, stride_scan_d,
    D,
    BLOCK_D: tl.constexpr, CHUNK_SIZE: tl.constexpr
):
    pid_c = tl.program_id(0)
    pid_d = tl.program_id(1)
    
    offs_d = pid_d * BLOCK_D + tl.arange(0, BLOCK_D)
    mask_d = offs_d < D
    
    row_start = pid_c * CHUNK_SIZE
    off_base = row_start * stride_row + offs_d * stride_d
    
    # Initialize prev_y with state from end of previous chunk
    prev_y = tl.zeros([BLOCK_D], dtype=tl.float32)
    if pid_c > 0:
        scan_ptr = Scan_ptr + (pid_c - 1) * stride_scan_c + offs_d * stride_scan_d
        prev_y = tl.load(scan_ptr, mask=mask_d, other=0.0)
    
    x_ptrs = X_ptr + off_base
    a_ptrs = A_ptr + off_base
    b_ptrs = B_ptr + off_base
    y_ptrs = Y_ptr + off_base
    
    for i in range(CHUNK_SIZE):
        a = tl.load(a_ptrs, mask=mask_d, other=0.0).to(tl.float32)
        b = tl.load(b_ptrs, mask=mask_d, other=0.0).to(tl.float32)
        x = tl.load(x_ptrs, mask=mask_d, other=0.0).to(tl.float32)
        
        curr_y = a * prev_y + b * x
        
        tl.store(y_ptrs, curr_y.to(tl.float16), mask=mask_d)
        
        prev_y = curr_y
        
        x_ptrs += stride_row
        a_ptrs += stride_row
        b_ptrs += stride_row
        y_ptrs += stride_row

def chunk_scan(X: torch.Tensor, A: torch.Tensor, B: torch.Tensor, chunk: int = 128, BD: int = 128) -> torch.Tensor:
    L, D = X.shape
    assert L % chunk == 0, "L must be divisible by chunk"
    num_chunks = L // chunk
    
    # Intermediate buffers (float32 for numerical stability)
    # State: Stores chunk coefficients (A_cum, U_cum)
    State = torch.empty((num_chunks, D, 2), device=X.device, dtype=torch.float32)
    # Scan: Stores y values at the end of each chunk
    Scan = torch.empty((num_chunks, D), device=X.device, dtype=torch.float32)
    # Output Y
    Y = torch.empty_like(X)
    
    # Pass 1: Compute Chunk Aggregates
    grid1 = (num_chunks, triton.cdiv(D, BD))
    _chunk_scan_pass1_kernel[grid1](
        X, A, B, State,
        X.stride(0), X.stride(1),
        State.stride(0), State.stride(1), State.stride(2),
        D,
        BLOCK_D=BD, CHUNK_SIZE=chunk
    )
    
    # Pass 2: Scan Chunk Aggregates
    grid2 = (triton.cdiv(D, BD), )
    _chunk_scan_pass2_kernel[grid2](
        State, Scan,
        State.stride(0), State.stride(1), State.stride(2),
        Scan.stride(0), Scan.stride(1),
        num_chunks, D,
        BLOCK_D=BD
    )
    
    # Pass 3: Generate Final Output
    grid3 = (num_chunks, triton.cdiv(D, BD))
    _chunk_scan_pass3_kernel[grid3](
        X, A, B, Scan, Y,
        X.stride(0), X.stride(1),
        Scan.stride(0), Scan.stride(1),
        D,
        BLOCK_D=BD, CHUNK_SIZE=chunk
    )
    
    return Y
"""
        return {"code": code}
