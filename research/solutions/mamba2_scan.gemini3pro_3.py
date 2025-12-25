import torch
import triton
import triton.language as tl
import os

@triton.jit
def _scan_phase1_kernel(
    X_ptr, A_ptr, B_ptr,
    OutA_ptr, OutX_ptr,
    stride_L, stride_D,
    CHUNK_SIZE: tl.constexpr,
    BD: tl.constexpr
):
    pid_c = tl.program_id(0)
    pid_d = tl.program_id(1)
    
    # Offsets for D dimension
    offs_d = pid_d * BD + tl.arange(0, BD)
    
    # Base pointer for this chunk
    chunk_offset = pid_c * CHUNK_SIZE * stride_L
    base_ptr_X = X_ptr + chunk_offset + offs_d * stride_D
    base_ptr_A = A_ptr + chunk_offset + offs_d * stride_D
    base_ptr_B = B_ptr + chunk_offset + offs_d * stride_D
    
    # Accumulators
    # acc_a starts at 1.0 (identity for product)
    # acc_x starts at 0.0 (identity for sum)
    acc_a = tl.full([BD], 1.0, dtype=tl.float32)
    acc_x = tl.zeros([BD], dtype=tl.float32)
    
    for i in range(CHUNK_SIZE):
        offset = i * stride_L
        
        # Load inputs
        val_x = tl.load(base_ptr_X + offset).to(tl.float32)
        val_a = tl.load(base_ptr_A + offset).to(tl.float32)
        val_b = tl.load(base_ptr_B + offset).to(tl.float32)
        
        # Update state: y_t = a_t * y_{t-1} + b_t * x_t
        acc_x = val_a * acc_x + val_b * val_x
        acc_a = acc_a * val_a

    # Write output summaries
    out_offset = pid_c * stride_L + offs_d
    tl.store(OutA_ptr + out_offset, acc_a.to(tl.float16))
    tl.store(OutX_ptr + out_offset, acc_x.to(tl.float16))

@triton.jit
def _scan_phase2_kernel(
    InA_ptr, InX_ptr, OutState_ptr,
    num_chunks,
    stride_chunks,
    BD: tl.constexpr
):
    pid_d = tl.program_id(0)
    offs_d = pid_d * BD + tl.arange(0, BD)
    
    # Initialize state to 0 for the first chunk
    curr_state = tl.zeros([BD], dtype=tl.float32)
    
    # Store initial state for chunk 0
    tl.store(OutState_ptr + offs_d, curr_state.to(tl.float16))
    
    # Loop over chunks to propagate state
    # We propagate state[c] -> state[c+1]
    for c in range(num_chunks - 1):
        idx = c * stride_chunks + offs_d
        
        val_a = tl.load(InA_ptr + idx).to(tl.float32)
        val_x = tl.load(InX_ptr + idx).to(tl.float32)
        
        curr_state = val_a * curr_state + val_x
        
        target_idx = (c + 1) * stride_chunks + offs_d
        tl.store(OutState_ptr + target_idx, curr_state.to(tl.float16))

@triton.jit
def _scan_phase3_kernel(
    X_ptr, A_ptr, B_ptr, State_ptr, Y_ptr,
    stride_L, stride_D,
    CHUNK_SIZE: tl.constexpr,
    BD: tl.constexpr
):
    pid_c = tl.program_id(0)
    pid_d = tl.program_id(1)
    
    offs_d = pid_d * BD + tl.arange(0, BD)
    
    # Load initial state for this chunk
    state_idx = pid_c * stride_L + offs_d
    curr_y = tl.load(State_ptr + state_idx).to(tl.float32)
    
    # Base pointers
    chunk_offset = pid_c * CHUNK_SIZE * stride_L
    base_ptr_X = X_ptr + chunk_offset + offs_d * stride_D
    base_ptr_A = A_ptr + chunk_offset + offs_d * stride_D
    base_ptr_B = B_ptr + chunk_offset + offs_d * stride_D
    base_ptr_Y = Y_ptr + chunk_offset + offs_d * stride_D
    
    for i in range(CHUNK_SIZE):
        offset = i * stride_L
        
        val_x = tl.load(base_ptr_X + offset).to(tl.float32)
        val_a = tl.load(base_ptr_A + offset).to(tl.float32)
        val_b = tl.load(base_ptr_B + offset).to(tl.float32)
        
        curr_y = val_a * curr_y + val_b * val_x
        
        tl.store(base_ptr_Y + offset, curr_y.to(tl.float16))

def chunk_scan(X: torch.Tensor, A: torch.Tensor, B: torch.Tensor, chunk: int = 128, BD: int = 128) -> torch.Tensor:
    """
    Mamba2 chunked scan computation.
    """
    L, D = X.shape
    assert L % chunk == 0, "Sequence length must be divisible by chunk size"
    num_chunks = L // chunk
    
    # Outputs
    Y = torch.empty_like(X)
    
    # Intermediate buffers
    # Summaries and States: (num_chunks, D)
    # Using float16 for storage to match output/input dtype, though accumulation is float32 in kernel
    chunk_A = torch.empty((num_chunks, D), dtype=torch.float16, device=X.device)
    chunk_X = torch.empty((num_chunks, D), dtype=torch.float16, device=X.device)
    chunk_States = torch.empty((num_chunks, D), dtype=torch.float16, device=X.device)
    
    stride_L = X.stride(0)
    stride_D = X.stride(1)
    
    # Phase 1: Intra-chunk reduction
    grid_1 = (num_chunks, triton.cdiv(D, BD))
    _scan_phase1_kernel[grid_1](
        X, A, B,
        chunk_A, chunk_X,
        stride_L, stride_D,
        CHUNK_SIZE=chunk, BD=BD
    )
    
    # Phase 2: Inter-chunk propagation
    grid_2 = (triton.cdiv(D, BD), )
    _scan_phase2_kernel[grid_2](
        chunk_A, chunk_X, chunk_States,
        num_chunks,
        stride_L,  # stride of chunk dim in summaries is same as stride_L (D)
        BD=BD
    )
    
    # Phase 3: Final scan with initial states
    _scan_phase3_kernel[grid_1](
        X, A, B, chunk_States, Y,
        stride_L, stride_D,
        CHUNK_SIZE=chunk, BD=BD
    )
    
    return Y

class Solution:
    def solve(self, spec_path: str = None) -> dict:
        return {"program_path": __file__}
