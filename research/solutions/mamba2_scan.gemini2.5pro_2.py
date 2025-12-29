import torch
import triton
import triton.language as tl

class Solution:
    def solve(self, spec_path: str = None) -> dict:
        code = """
import torch
import triton
import triton.language as tl

@triton.jit
def _scan_kernel1(
    X_ptr, A_ptr, B_ptr, Y_ptr, A_carry_ptr, Y_carry_ptr,
    L, D,
    stride_x_l, stride_x_d,
    stride_a_l, stride_a_d,
    stride_b_l, stride_b_d,
    stride_y_l, stride_y_d,
    stride_ac_c, stride_ac_d,
    stride_yc_c, stride_yc_d,
    CHUNK: tl.constexpr, BD: tl.constexpr,
):
    \"\"\"
    Performs intra-chunk scan.
    For each chunk, computes the local scan result (assuming initial state is 0)
    and the carry-over values (cumulative product of A and final local state).
    Grid: (L/CHUNK, D/BD)
    \"\"\"
    pid_c = tl.program_id(0)
    pid_d = tl.program_id(1)

    d_offsets = pid_d * BD + tl.arange(0, BD)
    chunk_offsets = pid_c * CHUNK + tl.arange(0, CHUNK)

    X_ptrs = X_ptr + chunk_offsets[:, None] * stride_x_l + d_offsets[None, :] * stride_x_d
    A_ptrs = A_ptr + chunk_offsets[:, None] * stride_a_l + d_offsets[None, :] * stride_a_d
    B_ptrs = B_ptr + chunk_offsets[:, None] * stride_b_l + d_offsets[None, :] * stride_b_d
    Y_ptrs = Y_ptr + chunk_offsets[:, None] * stride_y_l + d_offsets[None, :] * stride_y_d

    y_state = tl.zeros((BD,), dtype=tl.float32)
    a_carry = tl.ones((BD,), dtype=tl.float32)

    for t in range(CHUNK):
        a_t_ptr = A_ptrs + t * stride_a_l
        b_t_ptr = B_ptrs + t * stride_b_l
        x_t_ptr = X_ptrs + t * stride_x_l
        y_t_ptr = Y_ptrs + t * stride_y_l

        a_t = tl.load(a_t_ptr).to(tl.float32)
        b_t = tl.load(b_t_ptr).to(tl.float32)
        x_t = tl.load(x_t_ptr).to(tl.float32)

        y_state = a_t * y_state + b_t * x_t
        tl.store(y_t_ptr, y_state.to(tl.float16))
        a_carry = a_carry * a_t

    A_carry_out_ptr = A_carry_ptr + pid_c * stride_ac_c + d_offsets * stride_ac_d
    Y_carry_out_ptr = Y_carry_ptr + pid_c * stride_yc_c + d_offsets * stride_yc_d
    
    tl.store(A_carry_out_ptr, a_carry)
    tl.store(Y_carry_out_ptr, y_state)


@triton.jit
def _scan_kernel2(
    A_carry_ptr, Y_carry_ptr, H_initial_ptr,
    NUM_CHUNKS, D,
    stride_ac_c, stride_ac_d,
    stride_yc_c, stride_yc_d,
    stride_h_c, stride_h_d,
    BD: tl.constexpr,
):
    \"\"\"
    Performs the inter-chunk scan (scan over the carry-overs).
    This is a sequential scan over the chunks, but parallel over the feature dimension.
    It computes the correct initial state for each chunk.
    Grid: (D/BD,)
    \"\"\"
    pid_d = tl.program_id(0)
    
    d_offsets = pid_d * BD + tl.arange(0, BD)
    
    A_carry_d_ptr = A_carry_ptr + d_offsets * stride_ac_d
    Y_carry_d_ptr = Y_carry_ptr + d_offsets * stride_yc_d
    H_initial_d_ptr = H_initial_ptr + d_offsets * stride_h_d

    h_state = tl.zeros((BD,), dtype=tl.float32)

    k = 0
    while k < NUM_CHUNKS:
        h_ptr = H_initial_d_ptr + k * stride_h_c
        tl.store(h_ptr, h_state)

        ac_ptr = A_carry_d_ptr + k * stride_ac_c
        yc_ptr = Y_carry_d_ptr + k * stride_yc_c
        
        a_carry_k = tl.load(ac_ptr)
        y_carry_k = tl.load(yc_ptr)
        
        h_state = a_carry_k * h_state + y_carry_k
        k += 1


@triton.jit
def _scan_kernel3(
    Y_ptr, A_ptr, H_initial_ptr,
    L, D,
    stride_y_l, stride_y_d,
    stride_a_l, stride_a_d,
    stride_h_c, stride_h_d,
    CHUNK: tl.constexpr, BD: tl.constexpr,
):
    \"\"\"
    Applies the correction to the local scan results based on the true initial states.
    It adds the propagated state from previous chunks to each element.
    Grid: (L/CHUNK, D/BD)
    \"\"\"
    pid_c = tl.program_id(0)
    pid_d = tl.program_id(1)

    if pid_c == 0:
        return

    d_offsets = pid_d * BD + tl.arange(0, BD)
    chunk_offsets = pid_c * CHUNK + tl.arange(0, CHUNK)
    
    Y_ptrs = Y_ptr + chunk_offsets[:, None] * stride_y_l + d_offsets[None, :] * stride_y_d
    A_ptrs = A_ptr + chunk_offsets[:, None] * stride_a_l + d_offsets[None, :] * stride_a_d

    h_ptr = H_initial_ptr + pid_c * stride_h_c + d_offsets * stride_h_d
    h_k = tl.load(h_ptr)

    correction_state = h_k

    for t in range(CHUNK):
        y_t_ptr = Y_ptrs + t * stride_y_l
        a_t_ptr = A_ptrs + t * stride_a_l
        
        y_local_t = tl.load(y_t_ptr).to(tl.float32)
        a_t = tl.load(a_t_ptr).to(tl.float32)
        
        correction_state = a_t * correction_state
        y_final_t = y_local_t + correction_state
        tl.store(y_t_ptr, y_final_t.to(tl.float16))


def chunk_scan(X: torch.Tensor, A: torch.Tensor, B: torch.Tensor, chunk: int = 128, BD: int = 128) -> torch.Tensor:
    \"\"\"
    Mamba2 chunked scan computation.
    
    Args:
        X: Input tensor of shape (L, D) - input sequence (float16)
        A: Input tensor of shape (L, D) - decay factors (float16)
        B: Input tensor of shape (L, D) - input weights (float16)
        chunk: Chunk size for parallel processing (default 128)
        BD: Block dimension for feature dimension tiling (default 128)
    
    Returns:
        Output tensor of shape (L, D) - scan output (float16)
    \"\"\"
    L, D = X.shape
    num_chunks = L // chunk
    
    Y = torch.empty_like(X)

    A_carry = torch.empty(num_chunks, D, device=X.device, dtype=torch.float32)
    Y_carry = torch.empty(num_chunks, D, device=X.device, dtype=torch.float32)
    H_initial = torch.empty(num_chunks, D, device=X.device, dtype=torch.float32)

    grid1 = (num_chunks, D // BD)
    _scan_kernel1[grid1](
        X, A, B, Y, A_carry, Y_carry,
        L, D,
        X.stride(0), X.stride(1),
        A.stride(0), A.stride(1),
        B.stride(0), B.stride(1),
        Y.stride(0), Y.stride(1),
        A_carry.stride(0), A_carry.stride(1),
        Y_carry.stride(0), Y_carry.stride(1),
        CHUNK=chunk, BD=BD
    )

    grid2 = (D // BD,)
    _scan_kernel2[grid2](
        A_carry, Y_carry, H_initial,
        num_chunks, D,
        A_carry.stride(0), A_carry.stride(1),
        Y_carry.stride(0), Y_carry.stride(1),
        H_initial.stride(0), H_initial.stride(1),
        BD=BD
    )
    
    grid3 = (num_chunks, D // BD)
    _scan_kernel3[grid3](
        Y, A, H_initial,
        L, D,
        Y.stride(0), Y.stride(1),
        A.stride(0), A.stride(1),
        H_initial.stride(0), H_initial.stride(1),
        CHUNK=chunk, BD=BD
    )

    return Y
"""
        return {"code": code}