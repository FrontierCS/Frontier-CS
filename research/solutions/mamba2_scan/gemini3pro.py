import torch
import triton
import triton.language as tl
import os

def cdiv(x, y):
    return (x + y - 1) // y

@triton.jit
def _scan_reduce_kernel(
    X_ptr, A_ptr, B_ptr,
    StateP_ptr, StateS_ptr,
    stride_L, stride_D,
    stride_State_C, stride_State_D,
    CHUNK_SIZE: tl.constexpr,
    BLOCK_D: tl.constexpr
):
    pid_c = tl.program_id(0)
    pid_d = tl.program_id(1)
    
    offs_d = pid_d * BLOCK_D + tl.arange(0, BLOCK_D)
    
    # Calculate starting offset for this chunk
    chunk_start_row = pid_c * CHUNK_SIZE
    off_base = chunk_start_row * stride_L + offs_d * stride_D
    
    x_ptrs = X_ptr + off_base
    a_ptrs = A_ptr + off_base
    b_ptrs = B_ptr + off_base
    
    acc_p = tl.full([BLOCK_D], 1.0, dtype=tl.float32)
    acc_s = tl.full([BLOCK_D], 0.0, dtype=tl.float32)
    
    for _ in range(CHUNK_SIZE):
        a = tl.load(a_ptrs).to(tl.float32)
        b = tl.load(b_ptrs).to(tl.float32)
        x = tl.load(x_ptrs).to(tl.float32)
        
        # y_t = a_t * y_{t-1} + b_t * x_t
        # State updates:
        # P accumulates product of a
        # S accumulates contributions: S_new = S_old * a + b * x
        acc_s = acc_s * a + b * x
        acc_p = acc_p * a
        
        a_ptrs += stride_L
        b_ptrs += stride_L
        x_ptrs += stride_L
        
    state_offset = pid_c * stride_State_C + offs_d * stride_State_D
    tl.store(StateP_ptr + state_offset, acc_p)
    tl.store(StateS_ptr + state_offset, acc_s)

@triton.jit
def _scan_update_kernel(
    X_ptr, A_ptr, B_ptr, Y_ptr,
    StateP_ptr, StateS_ptr,
    stride_L, stride_D,
    stride_State_C, stride_State_D,
    CHUNK_SIZE: tl.constexpr,
    BLOCK_D: tl.constexpr
):
    pid_c = tl.program_id(0)
    pid_d = tl.program_id(1)
    
    offs_d = pid_d * BLOCK_D + tl.arange(0, BLOCK_D)
    
    # Calculate initial state for this chunk by accumulating previous chunk states
    running_y = tl.full([BLOCK_D], 0.0, dtype=tl.float32)
    
    state_p_ptrs = StateP_ptr + offs_d * stride_State_D
    state_s_ptrs = StateS_ptr + offs_d * stride_State_D
    
    # Scan over previous blocks to get initial state
    for c in range(pid_c):
        p = tl.load(state_p_ptrs + c * stride_State_C)
        s = tl.load(state_s_ptrs + c * stride_State_C)
        running_y = running_y * p + s
        
    # Process current chunk
    chunk_start_row = pid_c * CHUNK_SIZE
    off_base = chunk_start_row * stride_L + offs_d * stride_D
    
    x_ptrs = X_ptr + off_base
    a_ptrs = A_ptr + off_base
    b_ptrs = B_ptr + off_base
    y_ptrs = Y_ptr + off_base
    
    for _ in range(CHUNK_SIZE):
        a = tl.load(a_ptrs).to(tl.float32)
        b = tl.load(b_ptrs).to(tl.float32)
        x = tl.load(x_ptrs).to(tl.float32)
        
        running_y = running_y * a + b * x
        
        tl.store(y_ptrs, running_y.to(tl.float16))
        
        a_ptrs += stride_L
        b_ptrs += stride_L
        x_ptrs += stride_L
        y_ptrs += stride_L

def chunk_scan(X: torch.Tensor, A: torch.Tensor, B: torch.Tensor, chunk: int = 128, BD: int = 128) -> torch.Tensor:
    L, D = X.shape
    
    # Input validation
    assert L % chunk == 0, "Sequence length L must be divisible by chunk size"
    
    num_chunks = L // chunk
    
    # Allocate intermediate states (Float32 for precision)
    StateP = torch.empty((num_chunks, D), device=X.device, dtype=torch.float32)
    StateS = torch.empty((num_chunks, D), device=X.device, dtype=torch.float32)
    Y = torch.empty_like(X)
    
    # Grid: (chunks, blocks_of_features)
    grid = (num_chunks, cdiv(D, BD))
    
    # 1. Reduce Phase: Compute chunk-level P and S
    _scan_reduce_kernel[grid](
        X, A, B,
        StateP, StateS,
        X.stride(0), X.stride(1),
        StateP.stride(0), StateP.stride(1),
        CHUNK_SIZE=chunk,
        BLOCK_D=BD
    )
    
    # 2. Update Phase: Compute inter-chunk scan and generate final Y
    _scan_update_kernel[grid](
        X, A, B, Y,
        StateP, StateS,
        X.stride(0), X.stride(1),
        StateP.stride(0), StateP.stride(1),
        CHUNK_SIZE=chunk,
        BLOCK_D=BD
    )
    
    return Y

class Solution:
    def solve(self, spec_path=None) -> dict:
        return {"program_path": __file__}