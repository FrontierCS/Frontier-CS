import torch
import triton
import triton.language as tl

@triton.jit
def _chunk_scan_kernel(
    X_ptr, A_ptr, B_ptr, Y_ptr, 
    L, D, chunk, stride_xl, stride_xd,
    stride_al, stride_ad, stride_bl, stride_bd,
    stride_yl, stride_yd, BD: tl.constexpr
):
    pid = tl.program_id(0)
    num_chunks = tl.cdiv(L, chunk)
    
    # Compute chunk index and feature block
    chunk_idx = pid // (D // BD)
    feature_block = pid % (D // BD)
    start_d = feature_block * BD
    
    # Check bounds
    if chunk_idx >= num_chunks:
        return
    
    # Allocate shared memory for state and accumulators
    state = tl.zeros((BD,), dtype=tl.float16)
    a_accum = tl.zeros((BD,), dtype=tl.float16)
    b_accum = tl.zeros((BD,), dtype=tl.float16)
    
    # Load first element of chunk
    t_start = chunk_idx * chunk
    t_end = tl.minimum(t_start + chunk, L)
    
    # Process chunk sequentially
    for t in range(t_start, t_end):
        # Load inputs for this timestep
        x_offsets = t * stride_xl + start_d * stride_xd
        a_offsets = t * stride_al + start_d * stride_ad
        b_offsets = t * stride_bl + start_d * stride_bd
        
        x = tl.load(X_ptr + x_offsets, mask=start_d + tl.arange(0, BD) < D, other=0.0)
        a = tl.load(A_ptr + a_offsets, mask=start_d + tl.arange(0, BD) < D, other=0.0)
        b = tl.load(B_ptr + b_offsets, mask=start_d + tl.arange(0, BD) < D, other=0.0)
        
        # Compute scan: y_t = a_t * y_{t-1} + b_t * x_t
        y = a * state + b * x
        
        # Store output
        y_offsets = t * stride_yl + start_d * stride_yd
        tl.store(Y_ptr + y_offsets, y, mask=start_d + tl.arange(0, BD) < D)
        
        # Update state for next timestep
        state = y

@triton.jit
def _parallel_chunk_scan_kernel(
    X_ptr, A_ptr, B_ptr, Y_ptr, State_ptr,
    L, D, chunk, stride_xl, stride_xd,
    stride_al, stride_ad, stride_bl, stride_bd,
    stride_yl, stride_yd, stride_sl, stride_sd,
    BD: tl.constexpr
):
    pid = tl.program_id(0)
    num_chunks = L // chunk
    
    # Compute chunk index and feature block
    chunk_idx = pid // (D // BD)
    feature_block = pid % (D // BD)
    start_d = feature_block * BD
    
    if chunk_idx >= num_chunks:
        return
    
    # Load initial state for this chunk
    if chunk_idx > 0:
        state_offsets = (chunk_idx - 1) * stride_sl + start_d * stride_sd
        state = tl.load(State_ptr + state_offsets, 
                       mask=start_d + tl.arange(0, BD) < D, other=0.0)
    else:
        state = tl.zeros((BD,), dtype=tl.float16)
    
    t_start = chunk_idx * chunk
    t_end = t_start + chunk
    
    # Process chunk
    for t in range(t_start, t_end):
        # Load inputs
        x_offsets = t * stride_xl + start_d * stride_xd
        a_offsets = t * stride_al + start_d * stride_ad
        b_offsets = t * stride_bl + start_d * stride_bd
        
        x = tl.load(X_ptr + x_offsets, mask=start_d + tl.arange(0, BD) < D, other=0.0)
        a = tl.load(A_ptr + a_offsets, mask=start_d + tl.arange(0, BD) < D, other=0.0)
        b = tl.load(B_ptr + b_offsets, mask=start_d + tl.arange(0, BD) < D, other=0.0)
        
        # Compute scan
        y = a * state + b * x
        
        # Store output
        y_offsets = t * stride_yl + start_d * stride_yd
        tl.store(Y_ptr + y_offsets, y, mask=start_d + tl.arange(0, BD) < D)
        
        # Update state
        state = y
    
    # Store final state of this chunk
    state_offsets = chunk_idx * stride_sl + start_d * stride_sd
    tl.store(State_ptr + state_offsets, state, mask=start_d + tl.arange(0, BD) < D)

def chunk_scan(
    X: torch.Tensor, 
    A: torch.Tensor, 
    B: torch.Tensor, 
    chunk: int = 128, 
    BD: int = 128
) -> torch.Tensor:
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
    device = X.device
    
    # Allocate output tensor
    Y = torch.empty_like(X)
    
    # Check divisibility
    assert L % chunk == 0, f"Sequence length {L} must be divisible by chunk size {chunk}"
    assert D % BD == 0, f"Feature dimension {D} must be divisible by block dimension {BD}"
    
    num_chunks = L // chunk
    
    # Two-pass approach for parallel chunk processing
    if num_chunks > 1:
        # First pass: compute chunk states independently
        num_blocks = num_chunks * (D // BD)
        
        # Temporary storage for chunk states
        chunk_states = torch.zeros((num_chunks, D), dtype=torch.float16, device=device)
        
        # Launch kernel for independent chunk processing
        grid = (num_blocks, 1, 1)
        
        _parallel_chunk_scan_kernel[grid](
            X, A, B, Y, chunk_states,
            L, D, chunk,
            X.stride(0), X.stride(1),
            A.stride(0), A.stride(1),
            B.stride(0), B.stride(1),
            Y.stride(0), Y.stride(1),
            chunk_states.stride(0), chunk_states.stride(1),
            BD=BD
        )
        
        # Second pass: propagate states between chunks
        # Compute prefix scan over chunk states
        chunk_state_prefix = torch.zeros((num_chunks, D), dtype=torch.float16, device=device)
        
        # Sequential prefix computation (small overhead)
        for i in range(1, num_chunks):
            # Load previous chunk's output at last position
            prev_last_y = Y[i * chunk - 1].unsqueeze(0)
            # Current chunk's initial state is previous chunk's final state
            chunk_state_prefix[i] = chunk_states[i-1]
        
        # Adjust outputs with prefix states
        for i in range(num_chunks):
            if i > 0:
                start_idx = i * chunk
                end_idx = (i + 1) * chunk
                # Add prefix state to all elements in chunk
                for t in range(start_idx, end_idx):
                    Y[t] += chunk_state_prefix[i]
    else:
        # Single chunk - simple sequential scan
        num_blocks = D // BD
        grid = (num_blocks, 1, 1)
        
        _chunk_scan_kernel[grid](
            X, A, B, Y,
            L, D, chunk,
            X.stride(0), X.stride(1),
            A.stride(0), A.stride(1),
            B.stride(0), B.stride(1),
            Y.stride(0), Y.stride(1),
            BD=BD
        )
    
    return Y

class Solution:
    def solve(self, spec_path: str = None) -> dict:
        code = '''import torch
import triton
import triton.language as tl

@triton.jit
def _chunk_scan_kernel(
    X_ptr, A_ptr, B_ptr, Y_ptr, 
    L, D, chunk, stride_xl, stride_xd,
    stride_al, stride_ad, stride_bl, stride_bd,
    stride_yl, stride_yd, BD: tl.constexpr
):
    pid = tl.program_id(0)
    num_chunks = tl.cdiv(L, chunk)
    
    # Compute chunk index and feature block
    chunk_idx = pid // (D // BD)
    feature_block = pid % (D // BD)
    start_d = feature_block * BD
    
    # Check bounds
    if chunk_idx >= num_chunks:
        return
    
    # Allocate shared memory for state and accumulators
    state = tl.zeros((BD,), dtype=tl.float16)
    a_accum = tl.zeros((BD,), dtype=tl.float16)
    b_accum = tl.zeros((BD,), dtype=tl.float16)
    
    # Load first element of chunk
    t_start = chunk_idx * chunk
    t_end = tl.minimum(t_start + chunk, L)
    
    # Process chunk sequentially
    for t in range(t_start, t_end):
        # Load inputs for this timestep
        x_offsets = t * stride_xl + start_d * stride_xd
        a_offsets = t * stride_al + start_d * stride_ad
        b_offsets = t * stride_bl + start_d * stride_bd
        
        x = tl.load(X_ptr + x_offsets, mask=start_d + tl.arange(0, BD) < D, other=0.0)
        a = tl.load(A_ptr + a_offsets, mask=start_d + tl.arange(0, BD) < D, other=0.0)
        b = tl.load(B_ptr + b_offsets, mask=start_d + tl.arange(0, BD) < D, other=0.0)
        
        # Compute scan: y_t = a_t * y_{t-1} + b_t * x_t
        y = a * state + b * x
        
        # Store output
        y_offsets = t * stride_yl + start_d * stride_yd
        tl.store(Y_ptr + y_offsets, y, mask=start_d + tl.arange(0, BD) < D)
        
        # Update state for next timestep
        state = y

@triton.jit
def _parallel_chunk_scan_kernel(
    X_ptr, A_ptr, B_ptr, Y_ptr, State_ptr,
    L, D, chunk, stride_xl, stride_xd,
    stride_al, stride_ad, stride_bl, stride_bd,
    stride_yl, stride_yd, stride_sl, stride_sd,
    BD: tl.constexpr
):
    pid = tl.program_id(0)
    num_chunks = L // chunk
    
    # Compute chunk index and feature block
    chunk_idx = pid // (D // BD)
    feature_block = pid % (D // BD)
    start_d = feature_block * BD
    
    if chunk_idx >= num_chunks:
        return
    
    # Load initial state for this chunk
    if chunk_idx > 0:
        state_offsets = (chunk_idx - 1) * stride_sl + start_d * stride_sd
        state = tl.load(State_ptr + state_offsets, 
                       mask=start_d + tl.arange(0, BD) < D, other=0.0)
    else:
        state = tl.zeros((BD,), dtype=tl.float16)
    
    t_start = chunk_idx * chunk
    t_end = t_start + chunk
    
    # Process chunk
    for t in range(t_start, t_end):
        # Load inputs
        x_offsets = t * stride_xl + start_d * stride_xd
        a_offsets = t * stride_al + start_d * stride_ad
        b_offsets = t * stride_bl + start_d * stride_bd
        
        x = tl.load(X_ptr + x_offsets, mask=start_d + tl.arange(0, BD) < D, other=0.0)
        a = tl.load(A_ptr + a_offsets, mask=start_d + tl.arange(0, BD) < D, other=0.0)
        b = tl.load(B_ptr + b_offsets, mask=start_d + tl.arange(0, BD) < D, other=0.0)
        
        # Compute scan
        y = a * state + b * x
        
        # Store output
        y_offsets = t * stride_yl + start_d * stride_yd
        tl.store(Y_ptr + y_offsets, y, mask=start_d + tl.arange(0, BD) < D)
        
        # Update state
        state = y
    
    # Store final state of this chunk
    state_offsets = chunk_idx * stride_sl + start_d * stride_sd
    tl.store(State_ptr + state_offsets, state, mask=start_d + tl.arange(0, BD) < D)

def chunk_scan(
    X: torch.Tensor, 
    A: torch.Tensor, 
    B: torch.Tensor, 
    chunk: int = 128, 
    BD: int = 128
) -> torch.Tensor:
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
    device = X.device
    
    # Allocate output tensor
    Y = torch.empty_like(X)
    
    # Check divisibility
    assert L % chunk == 0, f"Sequence length {L} must be divisible by chunk size {chunk}"
    assert D % BD == 0, f"Feature dimension {D} must be divisible by block dimension {BD}"
    
    num_chunks = L // chunk
    
    # Two-pass approach for parallel chunk processing
    if num_chunks > 1:
        # First pass: compute chunk states independently
        num_blocks = num_chunks * (D // BD)
        
        # Temporary storage for chunk states
        chunk_states = torch.zeros((num_chunks, D), dtype=torch.float16, device=device)
        
        # Launch kernel for independent chunk processing
        grid = (num_blocks, 1, 1)
        
        _parallel_chunk_scan_kernel[grid](
            X, A, B, Y, chunk_states,
            L, D, chunk,
            X.stride(0), X.stride(1),
            A.stride(0), A.stride(1),
            B.stride(0), B.stride(1),
            Y.stride(0), Y.stride(1),
            chunk_states.stride(0), chunk_states.stride(1),
            BD=BD
        )
        
        # Second pass: propagate states between chunks
        # Compute prefix scan over chunk states
        chunk_state_prefix = torch.zeros((num_chunks, D), dtype=torch.float16, device=device)
        
        # Sequential prefix computation (small overhead)
        for i in range(1, num_chunks):
            # Load previous chunk's output at last position
            prev_last_y = Y[i * chunk - 1].unsqueeze(0)
            # Current chunk's initial state is previous chunk's final state
            chunk_state_prefix[i] = chunk_states[i-1]
        
        # Adjust outputs with prefix states
        for i in range(num_chunks):
            if i > 0:
                start_idx = i * chunk
                end_idx = (i + 1) * chunk
                # Add prefix state to all elements in chunk
                for t in range(start_idx, end_idx):
                    Y[t] += chunk_state_prefix[i]
    else:
        # Single chunk - simple sequential scan
        num_blocks = D // BD
        grid = (num_blocks, 1, 1)
        
        _chunk_scan_kernel[grid](
            X, A, B, Y,
            L, D, chunk,
            X.stride(0), X.stride(1),
            A.stride(0), A.stride(1),
            B.stride(0), B.stride(1),
            Y.stride(0), Y.stride(1),
            BD=BD
        )
    
    return Y
'''
        return {"code": code}