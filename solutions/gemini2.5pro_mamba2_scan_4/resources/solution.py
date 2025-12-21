import torch
import triton
import triton.language as tl

class Solution:
    def solve(self, spec_path: str = None) -> dict:
        kernel_code = """
import torch
import triton
import triton.language as tl

@triton.jit
def _scan_kernel(
    X_ptr, A_ptr, B_ptr, Y_ptr, H_ends_ptr, A_prods_ptr,
    L, D,
    stride_x_l, stride_x_d,
    stride_a_l, stride_a_d,
    stride_b_l, stride_b_d,
    stride_y_l, stride_y_d,
    stride_h_c, stride_h_d,
    stride_ap_c, stride_ap_d,
    CHUNK_SIZE: tl.constexpr,
    BLOCK_D: tl.constexpr,
):
    \"\"\"
    Pass 1: Intra-chunk scan.
    Processes each chunk in parallel assuming an initial state of 0.
    Writes intermediate scan results to Y, and saves the final state (h_end)
    and total decay factor (a_prod) for each chunk to be used in Pass 2.
    \"\"\"
    pid_c = tl.program_id(0)
    pid_d = tl.program_id(1)

    d_offsets = pid_d * BLOCK_D + tl.arange(0, BLOCK_D)
    d_mask = d_offsets < D

    chunk_start_offset_l = pid_c * CHUNK_SIZE

    # Pointers to the start of the current chunk for this feature block
    x_chunk_ptr = X_ptr + chunk_start_offset_l * stride_x_l + d_offsets
    a_chunk_ptr = A_ptr + chunk_start_offset_l * stride_a_l + d_offsets
    b_chunk_ptr = B_ptr + chunk_start_offset_l * stride_b_l + d_offsets
    y_chunk_ptr = Y_ptr + chunk_start_offset_l * stride_y_l + d_offsets
    
    # Initialize state (h) and accumulated decay (a_prod)
    h = tl.zeros([BLOCK_D], dtype=tl.float32)
    a_prod = tl.ones([BLOCK_D], dtype=tl.float32)

    # Iterate over the time dimension of the chunk
    for t in range(CHUNK_SIZE):
        x_t = tl.load(x_chunk_ptr + t * stride_x_l, mask=d_mask, other=0.0).to(tl.float32)
        a_t = tl.load(a_chunk_ptr + t * stride_a_l, mask=d_mask, other=0.0).to(tl.float32)
        b_t = tl.load(b_chunk_ptr + t * stride_b_l, mask=d_mask, other=0.0).to(tl.float32)

        # Mamba recurrence: h_t = a_t * h_{t-1} + b_t * x_t
        h = a_t * h + b_t * x_t
        a_prod = a_prod * a_t
        
        # Store intermediate result (Y_intra)
        tl.store(y_chunk_ptr + t * stride_y_l, h.to(tl.float16), mask=d_mask)

    # Store final state and A_prod for this chunk
    h_ends_c_ptr = H_ends_ptr + pid_c * stride_h_c + d_offsets
    a_prods_c_ptr = A_prods_ptr + pid_c * stride_ap_c + d_offsets
    
    tl.store(h_ends_c_ptr, h, mask=d_mask)
    tl.store(a_prods_c_ptr, a_prod, mask=d_mask)


@triton.jit
def _correction_kernel(
    Y_ptr, A_ptr, H_ends_ptr, A_prods_ptr,
    L, D, NUM_CHUNKS,
    stride_y_l, stride_y_d,
    stride_a_l, stride_a_d,
    stride_h_c, stride_h_d,
    stride_ap_c, stride_ap_d,
    CHUNK_SIZE: tl.constexpr,
    BLOCK_D: tl.constexpr,
):
    \"\"\"
    Pass 2: State propagation and correction.
    This kernel has two stages, both performed by the same thread block.
    1. Sequentially compute the true final states for all chunks by scanning over
       the intermediate results from Pass 1.
    2. Iterate through chunks again to apply a correction based on the propagated
       initial state from the previous chunk.
    \"\"\"
    pid_d = tl.program_id(0)

    d_offsets = pid_d * BLOCK_D + tl.arange(0, BLOCK_D)
    d_mask = d_offsets < D

    # --- Stage 1: Compute true chunk-end states sequentially ---
    s_prev = tl.zeros([BLOCK_D], dtype=tl.float32)
    for c in range(NUM_CHUNKS):
        h_end_ptr = H_ends_ptr + c * stride_h_c + d_offsets
        a_prod_ptr = A_prods_ptr + c * stride_ap_c + d_offsets
        
        h_end = tl.load(h_end_ptr, mask=d_mask, other=0.0)
        a_prod = tl.load(a_prod_ptr, mask=d_mask, other=0.0)
        
        # S_c = A_prod_c * S_{c-1} + H_intra_end_c
        s_current = a_prod * s_prev + h_end
        
        # Overwrite H_ends with the true final state S_c
        tl.store(h_end_ptr, s_current, mask=d_mask)
        s_prev = s_current

    # --- Stage 2: Propagate states and correct Y ---
    s_initial = tl.zeros([BLOCK_D], dtype=tl.float32)
    for c in range(NUM_CHUNKS):
        if c > 0:
            # Load S_{c-1}, now stored in H_ends[c-1]
            s_initial_ptr = H_ends_ptr + (c - 1) * stride_h_c + d_offsets
            s_initial = tl.load(s_initial_ptr, mask=d_mask, other=0.0)

        chunk_start_l = c * CHUNK_SIZE
        a_chunk_ptr = A_ptr + chunk_start_l * stride_a_l + d_offsets
        y_chunk_ptr = Y_ptr + chunk_start_l * stride_y_l + d_offsets
        
        a_prefix_prod_t = tl.ones([BLOCK_D], dtype=tl.float32)
        for t in range(CHUNK_SIZE):
            a_t_ptr = a_chunk_ptr + t * stride_a_l
            y_t_ptr = y_chunk_ptr + t * stride_y_l
            
            a_t = tl.load(a_t_ptr, mask=d_mask, other=0.0).to(tl.float32)
            
            # Update prefix product: (a_t * ... * a_0)
            a_prefix_prod_t = a_prefix_prod_t * a_t
            
            y_intra_t = tl.load(y_t_ptr, mask=d_mask, other=0.0).to(tl.float32)
            
            # Correction term: (a_t * ... * a_0) * s_initial
            correction = a_prefix_prod_t * s_initial
            y_final_t = y_intra_t + correction
            
            tl.store(y_t_ptr, y_final_t.to(tl.float16), mask=d_mask)


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
    C = L // chunk
    if L % chunk != 0:
        raise ValueError("L must be divisible by chunk size")

    Y = torch.empty_like(X)
    H_ends = torch.empty((C, D), device=X.device, dtype=torch.float32)
    A_prods = torch.empty((C, D), device=X.device, dtype=torch.float32)

    grid1 = (C, triton.cdiv(D, BD))
    _scan_kernel[grid1](
        X, A, B, Y, H_ends, A_prods,
        L, D,
        X.stride(0), X.stride(1),
        A.stride(0), A.stride(1),
        B.stride(0), B.stride(1),
        Y.stride(0), Y.stride(1),
        H_ends.stride(0), H_ends.stride(1),
        A_prods.stride(0), A_prods.stride(1),
        CHUNK_SIZE=chunk,
        BLOCK_D=BD,
    )
    
    grid2 = (triton.cdiv(D, BD),)
    _correction_kernel[grid2](
        Y, A, H_ends, A_prods,
        L, D, C,
        Y.stride(0), Y.stride(1),
        A.stride(0), A.stride(1),
        H_ends.stride(0), H_ends.stride(1),
        A_prods.stride(0), A_prods.stride(1),
        CHUNK_SIZE=chunk,
        BLOCK_D=BD,
    )

    return Y
"""
        return {"code": kernel_code}
