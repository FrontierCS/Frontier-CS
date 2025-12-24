import torch
import triton
import triton.language as tl
import inspect

KERNEL_CODE = r"""
import torch
import triton
import triton.language as tl

@triton.jit
def _chunk_reduce_kernel(
    X_ptr, A_ptr, B_ptr,
    S_ptr, P_ptr,
    stride_L, stride_D,
    L, D,
    CHUNK_SIZE: tl.constexpr,
    BLOCK_D: tl.constexpr
):
    pid_c = tl.program_id(0)
    pid_d = tl.program_id(1)
    
    offs_d = pid_d * BLOCK_D + tl.arange(0, BLOCK_D)
    mask_d = offs_d < D
    
    # Initialize accumulators
    acc_s = tl.zeros([BLOCK_D], dtype=tl.float32)
    acc_p = tl.ones([BLOCK_D], dtype=tl.float32)
    
    chunk_start = pid_c * CHUNK_SIZE
    
    # Base pointers
    base_offset = chunk_start * stride_L + offs_d
    x_ptrs = X_ptr + base_offset
    a_ptrs = A_ptr + base_offset
    b_ptrs = B_ptr + base_offset
    
    for t in range(CHUNK_SIZE):
        x = tl.load(x_ptrs, mask=mask_d, other=0.0).to(tl.float32)
        a = tl.load(a_ptrs, mask=mask_d, other=0.0).to(tl.float32)
        b = tl.load(b_ptrs, mask=mask_d, other=0.0).to(tl.float32)
        
        acc_s = a * acc_s + b * x
        acc_p = a * acc_p
        
        x_ptrs += stride_L
        a_ptrs += stride_L
        b_ptrs += stride_L
        
    out_offset = pid_c * D + offs_d
    tl.store(S_ptr + out_offset, acc_s, mask=mask_d)
    tl.store(P_ptr + out_offset, acc_p, mask=mask_d)

@triton.jit
def _chunk_scan_state_kernel(
    S_ptr, P_ptr,
    States_ptr,
    num_chunks, D,
    BLOCK_D: tl.constexpr
):
    pid_d = tl.program_id(0)
    offs_d = pid_d * BLOCK_D + tl.arange(0, BLOCK_D)
    mask_d = offs_d < D
    
    running_state = tl.zeros([BLOCK_D], dtype=tl.float32)
    
    s_ptr = S_ptr + offs_d
    p_ptr = P_ptr + offs_d
    states_ptr = States_ptr + offs_d
    
    stride = D
    
    for k in range(num_chunks):
        tl.store(states_ptr, running_state, mask=mask_d)
        
        s = tl.load(s_ptr, mask=mask_d).to(tl.float32)
        p = tl.load(p_ptr, mask=mask_d).to(tl.float32)
        
        running_state = running_state * p + s
        
        s_ptr += stride
        p_ptr += stride
        states_ptr += stride

@triton.jit
def _final_update_kernel(
    X_ptr, A_ptr, B_ptr,
    States_ptr,
    Y_ptr,
    stride_L, stride_D,
    L, D,
    CHUNK_SIZE: tl.constexpr,
    BLOCK_D: tl.constexpr
):
    pid_c = tl.program_id(0)
    pid_d = tl.program_id(1)
    
    offs_d = pid_d * BLOCK_D + tl.arange(0, BLOCK_D)
    mask_d = offs_d < D
    
    state_offset = pid_c * D + offs_d
    current_y = tl.load(States_ptr + state_offset, mask=mask_d).to(tl.float32)
    
    chunk_start = pid_c * CHUNK_SIZE
    base_offset = chunk_start * stride_L + offs_d
    
    x_ptrs = X_ptr + base_offset
    a_ptrs = A_ptr + base_offset
    b_ptrs = B_ptr + base_offset
    y_ptrs = Y_ptr + base_offset
    
    for t in range(CHUNK_SIZE):
        x = tl.load(x_ptrs, mask=mask_d, other=0.0).to(tl.float32)
        a = tl.load(a_ptrs, mask=mask_d, other=0.0).to(tl.float32)
        b = tl.load(b_ptrs, mask=mask_d, other=0.0).to(tl.float32)
        
        current_y = a * current_y + b * x
        
        tl.store(y_ptrs, current_y.to(tl.float16), mask=mask_d)
        
        x_ptrs += stride_L
        a_ptrs += stride_L
        b_ptrs += stride_L
        y_ptrs += stride_L

def chunk_scan(X: torch.Tensor, A: torch.Tensor, B: torch.Tensor, chunk: int = 128, BD: int = 128) -> torch.Tensor:
    L, D = X.shape
    assert L % chunk == 0, "L must be divisible by chunk"
    
    num_chunks = L // chunk
    
    # Allocate intermediate buffers
    S = torch.empty((num_chunks, D), device=X.device, dtype=torch.float32)
    P = torch.empty((num_chunks, D), device=X.device, dtype=torch.float32)
    States = torch.empty((num_chunks, D), device=X.device, dtype=torch.float32)
    Y = torch.empty_like(X)
    
    grid_reduce = (num_chunks, triton.cdiv(D, BD))
    grid_scan = (triton.cdiv(D, BD),)
    
    # 1. Reduce chunks to compute P and S
    _chunk_reduce_kernel[grid_reduce](
        X, A, B,
        S, P,
        X.stride(0), X.stride(1),
        L, D,
        CHUNK_SIZE=chunk,
        BLOCK_D=BD
    )
    
    # 2. Scan chunk summaries to get initial states
    _chunk_scan_state_kernel[grid_scan](
        S, P,
        States,
        num_chunks, D,
        BLOCK_D=BD
    )
    
    # 3. Final update
    _final_update_kernel[grid_reduce](
        X, A, B,
        States,
        Y,
        X.stride(0), X.stride(1),
        L, D,
        CHUNK_SIZE=chunk,
        BLOCK_D=BD
    )
    
    return Y
"""

class Solution:
    def solve(self, spec_path: str = None) -> dict:
        return {"code": KERNEL_CODE}
