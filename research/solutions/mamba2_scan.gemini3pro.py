import torch
import triton
import triton.language as tl

class Solution:
    def solve(self, spec_path: str = None) -> dict:
        return {
            "code": r"""
import torch
import triton
import triton.language as tl

@triton.jit
def _scan_reduce_kernel(
    X_ptr, A_ptr, B_ptr,
    State_ptr,
    stride_L, stride_D,
    stride_State_K, stride_State_D,
    CHUNK_SIZE: tl.constexpr,
    BLOCK_D: tl.constexpr
):
    pid_c = tl.program_id(0)
    pid_d = tl.program_id(1)

    offs_d = pid_d * BLOCK_D + tl.arange(0, BLOCK_D)
    
    base_idx = pid_c * CHUNK_SIZE
    
    # Initialize accumulation state (Prod, Sum)
    # y_out = Prod * y_in + Sum
    # Initial state (Identity): Prod=1, Sum=0
    r_prod = tl.zeros([BLOCK_D], dtype=tl.float32) + 1.0
    r_acc = tl.zeros([BLOCK_D], dtype=tl.float32)

    off_base = base_idx * stride_L + offs_d * stride_D
    x_ptrs = X_ptr + off_base
    a_ptrs = A_ptr + off_base
    b_ptrs = B_ptr + off_base

    for i in range(CHUNK_SIZE):
        a = tl.load(a_ptrs).to(tl.float32)
        b = tl.load(b_ptrs).to(tl.float32)
        x = tl.load(x_ptrs).to(tl.float32)

        # Update transition function
        # Old: y_i-1 = P * y_in + S
        # New: y_i = a * y_i-1 + b * x
        #          = a * (P * y_in + S) + b * x
        #          = (a * P) * y_in + (a * S + b * x)
        r_acc = a * r_acc + b * x
        r_prod = a * r_prod

        x_ptrs += stride_L
        a_ptrs += stride_L
        b_ptrs += stride_L

    off_state = pid_c * stride_State_K + offs_d * stride_State_D
    
    tl.store(State_ptr + off_state, r_prod.to(tl.float16))
    tl.store(State_ptr + off_state + 1, r_acc.to(tl.float16))

@triton.jit
def _scan_distribute_kernel(
    State_ptr,
    Prefix_ptr,
    stride_K, stride_D,
    K,
    BLOCK_D: tl.constexpr
):
    pid_d = tl.program_id(0)
    offs_d = pid_d * BLOCK_D + tl.arange(0, BLOCK_D)

    acc_prod = tl.zeros([BLOCK_D], dtype=tl.float32) + 1.0
    acc_sum = tl.zeros([BLOCK_D], dtype=tl.float32)

    # Store initial prefix (Identity) for first chunk
    off_out = 0 * stride_K + offs_d * stride_D
    tl.store(Prefix_ptr + off_out, acc_prod.to(tl.float16))
    tl.store(Prefix_ptr + off_out + 1, acc_sum.to(tl.float16))

    for k in range(K - 1):
        off_in = k * stride_K + offs_d * stride_D
        v_prod = tl.load(State_ptr + off_in).to(tl.float32)
        v_sum = tl.load(State_ptr + off_in + 1).to(tl.float32)

        # Compose transitions
        # Transition K: y_next = v_prod * y_curr + v_sum
        # Accumulated: y_curr = acc_prod * y_start + acc_sum
        # Combined: y_next = v_prod * (acc_prod * y_start + acc_sum) + v_sum
        #                  = (v_prod * acc_prod) * y_start + (v_prod * acc_sum + v_sum)
        n_prod = v_prod * acc_prod
        n_sum = v_prod * acc_sum + v_sum
        
        acc_prod = n_prod
        acc_sum = n_sum

        off_out = (k + 1) * stride_K + offs_d * stride_D
        tl.store(Prefix_ptr + off_out, acc_prod.to(tl.float16))
        tl.store(Prefix_ptr + off_out + 1, acc_sum.to(tl.float16))

@triton.jit
def _scan_final_kernel(
    X_ptr, A_ptr, B_ptr, Y_ptr,
    Prefix_ptr,
    stride_L, stride_D,
    stride_Prefix_K, stride_Prefix_D,
    CHUNK_SIZE: tl.constexpr,
    BLOCK_D: tl.constexpr
):
    pid_c = tl.program_id(0)
    pid_d = tl.program_id(1)

    offs_d = pid_d * BLOCK_D + tl.arange(0, BLOCK_D)
    
    # Load starting value for this chunk
    # The Prefix contains the accumulated transition from start to chunk_start.
    # y_start = Prefix_Prod * y_initial + Prefix_Sum
    # Since y_initial = 0, y_start = Prefix_Sum
    off_prefix = pid_c * stride_Prefix_K + offs_d * stride_Prefix_D + 1
    current_y = tl.load(Prefix_ptr + off_prefix).to(tl.float32)

    base_idx = pid_c * CHUNK_SIZE
    off_base = base_idx * stride_L + offs_d * stride_D
    
    x_ptrs = X_ptr + off_base
    a_ptrs = A_ptr + off_base
    b_ptrs = B_ptr + off_base
    y_ptrs = Y_ptr + off_base

    for i in range(CHUNK_SIZE):
        a = tl.load(a_ptrs).to(tl.float32)
        b = tl.load(b_ptrs).to(tl.float32)
        x = tl.load(x_ptrs).to(tl.float32)

        current_y = a * current_y + b * x
        
        tl.store(y_ptrs, current_y.to(tl.float16))

        x_ptrs += stride_L
        a_ptrs += stride_L
        b_ptrs += stride_L
        y_ptrs += stride_L

def chunk_scan(X: torch.Tensor, A: torch.Tensor, B: torch.Tensor, chunk: int = 128, BD: int = 128) -> torch.Tensor:
    L, D = X.shape
    assert L % chunk == 0, "L must be divisible by chunk size"
    
    K = L // chunk
    
    # Allocate intermediate buffers
    # Shape (K, D, 2)
    chunk_states = torch.empty((K, D, 2), device=X.device, dtype=torch.float16)
    chunk_prefixes = torch.empty((K, D, 2), device=X.device, dtype=torch.float16)
    Y = torch.empty_like(X)

    # 1. Reduce Kernel
    grid_reduce = (K, triton.cdiv(D, BD))
    _scan_reduce_kernel[grid_reduce](
        X, A, B,
        chunk_states,
        X.stride(0), X.stride(1),
        chunk_states.stride(0), chunk_states.stride(1),
        CHUNK_SIZE=chunk, BLOCK_D=BD,
        num_warps=4
    )

    # 2. Distribute Kernel
    grid_dist = (triton.cdiv(D, BD),)
    _scan_distribute_kernel[grid_dist](
        chunk_states,
        chunk_prefixes,
        chunk_states.stride(0), chunk_states.stride(1),
        K,
        BLOCK_D=BD,
        num_warps=4
    )

    # 3. Final Kernel
    grid_final = (K, triton.cdiv(D, BD))
    _scan_final_kernel[grid_final](
        X, A, B, Y,
        chunk_prefixes,
        X.stride(0), X.stride(1),
        chunk_prefixes.stride(0), chunk_prefixes.stride(1),
        CHUNK_SIZE=chunk, BLOCK_D=BD,
        num_warps=4
    )

    return Y
"""
        }
