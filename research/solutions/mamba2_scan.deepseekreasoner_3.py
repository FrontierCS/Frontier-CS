import torch
import triton
import triton.language as tl

@triton.jit
def chunk_scan_kernel(
    # Pointers to tensors
    x_ptr, a_ptr, b_ptr, output_ptr,
    # Chunk state tensors
    chunk_out_ptr, chunk_alpha_ptr,
    # Dimensions
    L, D,
    # Chunk parameters
    chunk_size, BD,
    # Strides
    stride_x_l, stride_x_d,
    stride_a_l, stride_a_d,
    stride_b_l, stride_b_d,
    stride_out_l, stride_out_d,
    # Meta-parameters
    BLOCK_L: tl.constexpr, BLOCK_D: tl.constexpr,
    NUM_CHUNKS: tl.constexpr,
):
    # Program ID
    pid_chunk = tl.program_id(0)
    pid_feature = tl.program_id(1)
    
    # Feature dimension range for this block
    d_start = pid_feature * BLOCK_D
    d_offsets = d_start + tl.arange(0, BLOCK_D)
    d_mask = d_offsets < D
    
    # Chunk range
    chunk_start = pid_chunk * chunk_size
    chunk_end = min(chunk_start + chunk_size, L)
    chunk_len = chunk_end - chunk_start
    
    # Initialize state for this chunk (y_{t-1})
    state = tl.zeros([BLOCK_D], dtype=tl.float32)
    
    # Loop over timesteps in this chunk
    for t in range(chunk_len):
        l_idx = chunk_start + t
        
        # Load x_t, a_t, b_t for this timestep
        x_ptrs = x_ptr + l_idx * stride_x_l + d_offsets * stride_x_d
        a_ptrs = a_ptr + l_idx * stride_a_l + d_offsets * stride_a_d
        b_ptrs = b_ptr + l_idx * stride_b_l + d_offsets * stride_b_d
        
        x_t = tl.load(x_ptrs, mask=d_mask, other=0.0).to(tl.float32)
        a_t = tl.load(a_ptrs, mask=d_mask, other=0.0).to(tl.float32)
        b_t = tl.load(b_ptrs, mask=d_mask, other=0.0).to(tl.float32)
        
        # Compute y_t = a_t * y_{t-1} + b_t * x_t
        y_t = a_t * state + b_t * x_t
        
        # Store output
        out_ptrs = output_ptr + l_idx * stride_out_l + d_offsets * stride_out_d
        tl.store(out_ptrs, y_t.to(tl.float16), mask=d_mask)
        
        # Update state for next timestep
        state = y_t
    
    # Store final state and cumulative alpha for this chunk
    if chunk_len > 0:
        # Store final state of this chunk
        chunk_out_ptrs = chunk_out_ptr + pid_chunk * D + d_offsets
        tl.store(chunk_out_ptrs, state.to(tl.float16), mask=d_mask)
        
        # For alpha propagation, we need cumulative product of a_t
        # But we only need the final alpha multiplier for the chunk
        alpha = tl.ones([BLOCK_D], dtype=tl.float32)
        for t in range(chunk_len):
            l_idx = chunk_start + t
            a_ptrs = a_ptr + l_idx * stride_a_l + d_offsets * stride_a_d
            a_t = tl.load(a_ptrs, mask=d_mask, other=0.0).to(tl.float32)
            alpha = alpha * a_t
        
        chunk_alpha_ptrs = chunk_alpha_ptr + pid_chunk * D + d_offsets
        tl.store(chunk_alpha_ptrs, alpha.to(tl.float16), mask=d_mask)

@triton.jit
def propagate_state_kernel(
    # Pointers
    output_ptr, chunk_out_ptr, chunk_alpha_ptr,
    # Dimensions
    L, D,
    # Chunk parameters
    chunk_size, BD,
    # Strides
    stride_out_l, stride_out_d,
    # Meta-parameters
    BLOCK_L: tl.constexpr, BLOCK_D: tl.constexpr,
    NUM_CHUNKS: tl.constexpr,
):
    # Program ID
    pid_chunk = tl.program_id(0)
    pid_feature = tl.program_id(1)
    
    # Skip first chunk (already correct)
    if pid_chunk == 0:
        return
    
    # Feature dimension range for this block
    d_start = pid_feature * BLOCK_D
    d_offsets = d_start + tl.arange(0, BLOCK_D)
    d_mask = d_offsets < D
    
    # Chunk range
    chunk_start = pid_chunk * chunk_size
    chunk_end = min(chunk_start + chunk_size, L)
    chunk_len = chunk_end - chunk_start
    
    # Load accumulated state from all previous chunks
    accumulated_state = tl.zeros([BLOCK_D], dtype=tl.float32)
    
    # Compute: state = sum_{k=0}^{pid_chunk-1} (chunk_out_k * prod_{j=k+1}^{pid_chunk-1} chunk_alpha_j)
    for k in range(pid_chunk):
        # Load chunk_out_k
        chunk_out_ptrs = chunk_out_ptr + k * D + d_offsets
        chunk_out = tl.load(chunk_out_ptrs, mask=d_mask, other=0.0).to(tl.float32)
        
        # Multiply by product of alphas from k+1 to pid_chunk-1
        prod_alpha = tl.ones([BLOCK_D], dtype=tl.float32)
        for j in range(k + 1, pid_chunk):
            alpha_ptrs = chunk_alpha_ptr + j * D + d_offsets
            alpha = tl.load(alpha_ptrs, mask=d_mask, other=0.0).to(tl.float32)
            prod_alpha = prod_alpha * alpha
        
        accumulated_state = accumulated_state + chunk_out * prod_alpha
    
    # Now add accumulated_state to every element in this chunk
    for t in range(chunk_len):
        l_idx = chunk_start + t
        
        # Load current value
        out_ptrs = output_ptr + l_idx * stride_out_l + d_offsets * stride_out_d
        current = tl.load(out_ptrs, mask=d_mask, other=0.0).to(tl.float32)
        
        # Compute cumulative alpha up to this position in chunk
        cum_alpha = tl.ones([BLOCK_D], dtype=tl.float32)
        for tt in range(t + 1):
            tt_idx = chunk_start + tt
            a_ptrs = output_ptr + tt_idx * stride_out_l + d_offsets * stride_out_d + (L * D * 2)  # Hack: using extra memory
            # Actually we need to reload a_t values
            # For simplicity, we'll recompute the cumulative product
        
        # Actually, we need a different approach
        
        # Load a_t for this position and all previous in chunk
        local_alpha = tl.ones([BLOCK_D], dtype=tl.float32)
        for tt in range(t + 1):
            tt_idx = chunk_start + tt
            # We need access to A tensor again, but we don't have the pointer
            # Instead, we'll compute the correction factor differently
        
        # Better: Update output using the recurrence:
        # y_t = y_t + accumulated_state * (prod_{s=chunk_start}^{t} a_s)
        
        # We'll accumulate the alpha product as we go through the chunk
        if t == 0:
            alpha_ptr = chunk_alpha_ptr + pid_chunk * D + d_offsets
            # Actually we need per-position alpha, not chunk alpha
            
        # For now, use a simpler but less accurate approach:
        # Just add accumulated_state to every element (this assumes a_t ~= 1 for correction)
        updated = current + accumulated_state
        tl.store(out_ptrs, updated.to(tl.float16), mask=d_mask)

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
    assert X.dtype == torch.float16
    assert A.dtype == torch.float16
    assert B.dtype == torch.float16
    
    L, D = X.shape
    
    # Output tensor
    Y = torch.empty_like(X)
    
    # Number of chunks
    num_chunks = (L + chunk - 1) // chunk
    
    # Tensors for chunk states
    chunk_out = torch.zeros((num_chunks, D), dtype=torch.float16, device=X.device)
    chunk_alpha = torch.zeros((num_chunks, D), dtype=torch.float16, device=X.device)
    
    # Grid dimensions
    grid = (num_chunks, triton.cdiv(D, BD))
    
    # Launch first kernel to compute chunk-wise scans
    chunk_scan_kernel[grid](
        X, A, B, Y,
        chunk_out, chunk_alpha,
        L, D,
        chunk, BD,
        X.stride(0), X.stride(1),
        A.stride(0), A.stride(1),
        B.stride(0), B.stride(1),
        Y.stride(0), Y.stride(1),
        BLOCK_L=chunk, BLOCK_D=BD,
        NUM_CHUNKS=num_chunks,
    )
    
    # Correct for inter-chunk dependencies using CPU (small num_chunks)
    if num_chunks > 1:
        # Move chunk states to CPU for sequential processing
        chunk_out_cpu = chunk_out.cpu().float()
        chunk_alpha_cpu = chunk_alpha.cpu().float()
        
        # State propagation between chunks
        for c in range(1, num_chunks):
            # Compute correction factor for chunk c
            correction = torch.zeros(D, dtype=torch.float32)
            
            # For each previous chunk k, add its contribution
            for k in range(c):
                # Contribution from chunk k: chunk_out[k] * product of alphas from k+1 to c-1
                contribution = chunk_out_cpu[k].clone()
                for j in range(k + 1, c):
                    contribution = contribution * chunk_alpha_cpu[j]
                correction = correction + contribution
            
            # Apply correction to each element in chunk c
            chunk_start = c * chunk
            chunk_end = min(chunk_start + chunk, L)
            chunk_len = chunk_end - chunk_start
            
            if chunk_len > 0:
                # Compute cumulative alpha within the chunk
                cum_alpha = torch.ones(D, dtype=torch.float32)
                for t in range(chunk_len):
                    l_idx = chunk_start + t
                    # Load a_t for this position
                    a_t = A[l_idx].float().cpu()
                    # Update output
                    Y[l_idx] = (Y[l_idx].float().cpu() + correction * cum_alpha).half()
                    # Update cumulative alpha for next position
                    cum_alpha = cum_alpha * a_t
    
    return Y

class Solution:
    def solve(self, spec_path: str = None) -> dict:
        return {"code": """
import torch
import triton
import triton.language as tl

@triton.jit
def chunk_scan_kernel(
    x_ptr, a_ptr, b_ptr, output_ptr,
    chunk_out_ptr, chunk_alpha_ptr,
    L, D,
    chunk_size, BD,
    stride_x_l, stride_x_d,
    stride_a_l, stride_a_d,
    stride_b_l, stride_b_d,
    stride_out_l, stride_out_d,
    BLOCK_L: tl.constexpr, BLOCK_D: tl.constexpr,
    NUM_CHUNKS: tl.constexpr,
):
    pid_chunk = tl.program_id(0)
    pid_feature = tl.program_id(1)
    
    d_start = pid_feature * BLOCK_D
    d_offsets = d_start + tl.arange(0, BLOCK_D)
    d_mask = d_offsets < D
    
    chunk_start = pid_chunk * chunk_size
    chunk_end = min(chunk_start + chunk_size, L)
    chunk_len = chunk_end - chunk_start
    
    state = tl.zeros([BLOCK_D], dtype=tl.float32)
    alpha = tl.ones([BLOCK_D], dtype=tl.float32)
    
    for t in range(chunk_len):
        l_idx = chunk_start + t
        
        x_ptrs = x_ptr + l_idx * stride_x_l + d_offsets * stride_x_d
        a_ptrs = a_ptr + l_idx * stride_a_l + d_offsets * stride_a_d
        b_ptrs = b_ptr + l_idx * stride_b_l + d_offsets * stride_b_d
        
        x_t = tl.load(x_ptrs, mask=d_mask, other=0.0).to(tl.float32)
        a_t = tl.load(a_ptrs, mask=d_mask, other=0.0).to(tl.float32)
        b_t = tl.load(b_ptrs, mask=d_mask, other=0.0).to(tl.float32)
        
        y_t = a_t * state + b_t * x_t
        
        out_ptrs = output_ptr + l_idx * stride_out_l + d_offsets * stride_out_d
        tl.store(out_ptrs, y_t.to(tl.float16), mask=d_mask)
        
        state = y_t
        alpha = alpha * a_t
    
    if chunk_len > 0:
        chunk_out_ptrs = chunk_out_ptr + pid_chunk * D + d_offsets
        tl.store(chunk_out_ptrs, state.to(tl.float16), mask=d_mask)
        
        chunk_alpha_ptrs = chunk_alpha_ptr + pid_chunk * D + d_offsets
        tl.store(chunk_alpha_ptrs, alpha.to(tl.float16), mask=d_mask)

def chunk_scan(X: torch.Tensor, A: torch.Tensor, B: torch.Tensor, chunk: int = 128, BD: int = 128) -> torch.Tensor:
    assert X.dtype == torch.float16
    assert A.dtype == torch.float16
    assert B.dtype == torch.float16
    
    L, D = X.shape
    Y = torch.empty_like(X)
    
    num_chunks = (L + chunk - 1) // chunk
    
    chunk_out = torch.zeros((num_chunks, D), dtype=torch.float16, device=X.device)
    chunk_alpha = torch.zeros((num_chunks, D), dtype=torch.float16, device=X.device)
    
    grid = (num_chunks, triton.cdiv(D, BD))
    
    chunk_scan_kernel[grid](
        X, A, B, Y,
        chunk_out, chunk_alpha,
        L, D,
        chunk, BD,
        X.stride(0), X.stride(1),
        A.stride(0), A.stride(1),
        B.stride(0), B.stride(1),
        Y.stride(0), Y.stride(1),
        BLOCK_L=chunk, BLOCK_D=BD,
        NUM_CHUNKS=num_chunks,
    )
    
    if num_chunks > 1:
        chunk_out_cpu = chunk_out.cpu().float()
        chunk_alpha_cpu = chunk_alpha.cpu().float()
        
        for c in range(1, num_chunks):
            correction = torch.zeros(D, dtype=torch.float32)
            
            for k in range(c):
                contribution = chunk_out_cpu[k].clone()
                for j in range(k + 1, c):
                    contribution = contribution * chunk_alpha_cpu[j]
                correction = correction + contribution
            
            chunk_start = c * chunk
            chunk_end = min(chunk_start + chunk, L)
            chunk_len = chunk_end - chunk_start
            
            if chunk_len > 0:
                cum_alpha = torch.ones(D, dtype=torch.float32)
                for t in range(chunk_len):
                    l_idx = chunk_start + t
                    a_t = A[l_idx].float().cpu()
                    Y[l_idx] = (Y[l_idx].float().cpu() + correction * cum_alpha).half()
                    cum_alpha = cum_alpha * a_t
    
    return Y
"""}
