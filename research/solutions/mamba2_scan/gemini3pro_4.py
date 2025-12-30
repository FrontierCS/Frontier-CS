import torch
import triton
import triton.language as tl

class Solution:
    def solve(self, spec_path: str = None) -> dict:
        return {
            "code": """
import torch
import triton
import triton.language as tl

@triton.jit
def _chunk_reduce_kernel(
    X_ptr, A_ptr, B_ptr,
    State_ptr,
    stride_L, stride_D,
    stride_state_c, stride_state_dim, stride_state_d,
    D,
    CHUNK_SIZE: tl.constexpr,
    BLOCK_D: tl.constexpr
):
    pid_c = tl.program_id(0)
    pid_d = tl.program_id(1)
    
    offs_d = pid_d * BLOCK_D + tl.arange(0, BLOCK_D)
    mask = offs_d < D
    
    chunk_start = pid_c * CHUNK_SIZE
    
    # Initialize accumulator state (P=1, S=0)
    acc_p = tl.zeros([BLOCK_D], dtype=tl.float32) + 1.0
    acc_s = tl.zeros([BLOCK_D], dtype=tl.float32)
    
    for t in range(CHUNK_SIZE):
        idx = chunk_start + t
        offset = idx * stride_L + offs_d * stride_D
        
        a = tl.load(A_ptr + offset, mask=mask, other=0.0).to(tl.float32)
        b = tl.load(B_ptr + offset, mask=mask, other=0.0).to(tl.float32)
        x = tl.load(X_ptr + offset, mask=mask, other=0.0).to(tl.float32)
        
        acc_p = a * acc_p
        acc_s = a * acc_s + b * x
        
    # Store state to (num_chunks, 2, D)
    state_p_ptr = State_ptr + pid_c * stride_state_c + 0 * stride_state_dim + offs_d * stride_state_d
    state_s_ptr = State_ptr + pid_c * stride_state_c + 1 * stride_state_dim + offs_d * stride_state_d
    
    tl.store(state_p_ptr, acc_p, mask=mask)
    tl.store(state_s_ptr, acc_s, mask=mask)

@triton.jit
def _chunk_scan_state_kernel(
    State_ptr,
    Carried_ptr,
    stride_state_c, stride_state_dim, stride_state_d,
    stride_carried_c, stride_carried_d,
    D,
    NUM_CHUNKS: tl.constexpr,
    BLOCK_D: tl.constexpr
):
    pid_d = tl.program_id(0)
    offs_d = pid_d * BLOCK_D + tl.arange(0, BLOCK_D)
    mask = offs_d < D
    
    curr_val = tl.zeros([BLOCK_D], dtype=tl.float32)
    
    for c in range(NUM_CHUNKS):
        # Store current accumulated bias as the starting state for chunk c
        carried_ptr_loc = Carried_ptr + c * stride_carried_c + offs_d * stride_carried_d
        tl.store(carried_ptr_loc, curr_val, mask=mask)
        
        # Load aggregate for chunk c
        state_p_ptr = State_ptr + c * stride_state_c + 0 * stride_state_dim + offs_d * stride_state_d
        state_s_ptr = State_ptr + c * stride_state_c + 1 * stride_state_dim + offs_d * stride_state_d
        
        p = tl.load(state_p_ptr, mask=mask, other=1.0)
        s = tl.load(state_s_ptr, mask=mask, other=0.0)
        
        # Update state: val_new = p * val + s
        curr_val = p * curr_val + s

@triton.jit
def _chunk_update_kernel(
    X_ptr, A_ptr, B_ptr, Y_ptr,
    Carried_ptr,
    stride_L, stride_D,
    stride_carried_c, stride_carried_d,
    D,
    CHUNK_SIZE: tl.constexpr,
    BLOCK_D: tl.constexpr
):
    pid_c = tl.program_id(0)
    pid_d = tl.program_id(1)
    
    offs_d = pid_d * BLOCK_D + tl.arange(0, BLOCK_D)
    mask = offs_d < D
    
    # Load initial state for this chunk
    carried_ptr_loc = Carried_ptr + pid_c * stride_carried_c + offs_d * stride_carried_d
    curr_y = tl.load(carried_ptr_loc, mask=mask, other=0.0).to(tl.float32)
    
    chunk_start = pid_c * CHUNK_SIZE
    
    for t in range(CHUNK_SIZE):
        idx = chunk_start + t
        offset = idx * stride_L + offs_d * stride_D
        
        a = tl.load(A_ptr + offset, mask=mask, other=0.0).to(tl.float32)
        b = tl.load(B_ptr + offset, mask=mask, other=0.0).to(tl.float32)
        x = tl.load(X_ptr + offset, mask=mask, other=0.0).to(tl.float32)
        
        curr_y = a * curr_y + b * x
        
        tl.store(Y_ptr + offset, curr_y.to(tl.float16), mask=mask)

def chunk_scan(X: torch.Tensor, A: torch.Tensor, B: torch.Tensor, chunk: int = 128, BD: int = 128) -> torch.Tensor:
    L, D = X.shape
    assert L % chunk == 0, "Length must be divisible by chunk size"
    
    num_chunks = L // chunk
    
    Y = torch.empty_like(X)
    
    # Intermediate tensors
    # States: (num_chunks, 2, D) - stores (P, S) aggregates for each chunk
    States = torch.empty((num_chunks, 2, D), device=X.device, dtype=torch.float32)
    # Carried: (num_chunks, D) - stores starting y-value for each chunk
    Carried = torch.empty((num_chunks, D), device=X.device, dtype=torch.float32)
    
    # Pass 1: Compute local aggregates for each chunk
    grid1 = (num_chunks, (D + BD - 1) // BD)
    _chunk_reduce_kernel[grid1](
        X, A, B, States,
        X.stride(0), X.stride(1),
        States.stride(0), States.stride(1), States.stride(2),
        D,
        CHUNK_SIZE=chunk, BLOCK_D=BD
    )
    
    # Pass 2: Scan the aggregates to compute starting states
    grid2 = ((D + BD - 1) // BD, )
    _chunk_scan_state_kernel[grid2](
        States, Carried,
        States.stride(0), States.stride(1), States.stride(2),
        Carried.stride(0), Carried.stride(1),
        D,
        NUM_CHUNKS=num_chunks, BLOCK_D=BD
    )
    
    # Pass 3: Compute final outputs using starting states
    grid3 = (num_chunks, (D + BD - 1) // BD)
    _chunk_update_kernel[grid3](
        X, A, B, Y, Carried,
        X.stride(0), X.stride(1),
        Carried.stride(0), Carried.stride(1),
        D,
        CHUNK_SIZE=chunk, BLOCK_D=BD
    )
    
    return Y
"""
        }