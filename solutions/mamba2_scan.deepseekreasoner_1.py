import torch
import triton
import triton.language as tl


@triton.jit
def chunk_scan_kernel(
    x_ptr,
    a_ptr,
    b_ptr,
    y_ptr,
    chunk_size,
    l,
    d,
    stride_xl,
    stride_xd,
    stride_al,
    stride_ad,
    stride_bl,
    stride_bd,
    stride_yl,
    stride_yd,
    bd: tl.constexpr,
):
    """
    Triton kernel for chunked scan computation.
    
    Each program processes a block of features (bd) for a specific chunk.
    """
    pid = tl.program_id(0)
    num_chunks = tl.cdiv(l, chunk_size)
    
    # Compute chunk and feature block indices
    chunk_idx = pid // tl.cdiv(d, bd)
    feature_block = pid % tl.cdiv(d, bd)
    
    # Check bounds
    if chunk_idx >= num_chunks:
        return
    
    # Compute feature range for this block
    feature_start = feature_block * bd
    feature_end = min(feature_start + bd, d)
    num_features = feature_end - feature_start
    
    # Initialize state to zero for this chunk
    state = tl.zeros([bd], dtype=tl.float16)
    
    # Compute chunk boundaries
    chunk_start = chunk_idx * chunk_size
    chunk_end = min(chunk_start + chunk_size, l)
    
    # Main computation loop over the chunk
    for pos in range(chunk_start, chunk_end):
        # Load inputs for this position
        x_offset = pos * stride_xl + feature_start * stride_xd
        a_offset = pos * stride_al + feature_start * stride_ad
        b_offset = pos * stride_bl + feature_start * stride_bd
        
        x = tl.load(x_ptr + x_offset, mask=tl.arange(0, bd) < num_features, other=0.0)
        a = tl.load(a_ptr + a_offset, mask=tl.arange(0, bd) < num_features, other=0.0)
        b = tl.load(b_ptr + b_offset, mask=tl.arange(0, bd) < num_features, other=0.0)
        
        # Compute: y_t = a_t * y_{t-1} + b_t * x_t
        state = a * state + b * x
        
        # Store output
        y_offset = pos * stride_yl + feature_start * stride_yd
        tl.store(y_ptr + y_offset, state, mask=tl.arange(0, bd) < num_features)


@triton.jit
def chunk_scan_kernel_with_state(
    x_ptr,
    a_ptr,
    b_ptr,
    y_ptr,
    chunk_state_ptr,
    chunk_size,
    l,
    d,
    stride_xl,
    stride_xd,
    stride_al,
    stride_ad,
    stride_bl,
    stride_bd,
    stride_yl,
    stride_yd,
    stride_cs_chunk,
    stride_cs_feat,
    bd: tl.constexpr,
):
    """
    Triton kernel for chunked scan with pre-computed chunk states.
    
    Each program processes a block of features (bd) for a specific chunk,
    using the chunk's starting state.
    """
    pid = tl.program_id(0)
    num_chunks = tl.cdiv(l, chunk_size)
    
    # Compute chunk and feature block indices
    chunk_idx = pid // tl.cdiv(d, bd)
    feature_block = pid % tl.cdiv(d, bd)
    
    # Check bounds
    if chunk_idx >= num_chunks:
        return
    
    # Compute feature range for this block
    feature_start = feature_block * bd
    feature_end = min(feature_start + bd, d)
    num_features = feature_end - feature_start
    
    # Load starting state for this chunk
    state_offset = chunk_idx * stride_cs_chunk + feature_start * stride_cs_feat
    state = tl.load(chunk_state_ptr + state_offset, mask=tl.arange(0, bd) < num_features, other=0.0)
    
    # Compute chunk boundaries
    chunk_start = chunk_idx * chunk_size
    chunk_end = min(chunk_start + chunk_size, l)
    
    # Main computation loop over the chunk
    for pos in range(chunk_start, chunk_end):
        # Load inputs for this position
        x_offset = pos * stride_xl + feature_start * stride_xd
        a_offset = pos * stride_al + feature_start * stride_ad
        b_offset = pos * stride_bl + feature_start * stride_bd
        
        x = tl.load(x_ptr + x_offset, mask=tl.arange(0, bd) < num_features, other=0.0)
        a = tl.load(a_ptr + a_offset, mask=tl.arange(0, bd) < num_features, other=0.0)
        b = tl.load(b_ptr + b_offset, mask=tl.arange(0, bd) < num_features, other=0.0)
        
        # Compute: y_t = a_t * y_{t-1} + b_t * x_t
        state = a * state + b * x
        
        # Store output
        y_offset = pos * stride_yl + feature_start * stride_yd
        tl.store(y_ptr + y_offset, state, mask=tl.arange(0, bd) < num_features)


@triton.jit
def compute_chunk_state_kernel(
    x_ptr,
    a_ptr,
    b_ptr,
    chunk_state_ptr,
    chunk_size,
    l,
    d,
    stride_xl,
    stride_xd,
    stride_al,
    stride_ad,
    stride_bl,
    stride_bd,
    stride_cs_chunk,
    stride_cs_feat,
    bd: tl.constexpr,
):
    """
    Compute the state at the end of each chunk (starting from zero).
    """
    pid = tl.program_id(0)
    num_chunks = tl.cdiv(l, chunk_size)
    
    # Compute chunk and feature block indices
    chunk_idx = pid // tl.cdiv(d, bd)
    feature_block = pid % tl.cdiv(d, bd)
    
    # Check bounds
    if chunk_idx >= num_chunks:
        return
    
    # Compute feature range for this block
    feature_start = feature_block * bd
    feature_end = min(feature_start + bd, d)
    num_features = feature_end - feature_start
    
    # Initialize state to zero for this chunk
    state = tl.zeros([bd], dtype=tl.float16)
    
    # Compute chunk boundaries
    chunk_start = chunk_idx * chunk_size
    chunk_end = min(chunk_start + chunk_size, l)
    
    # Compute state for this chunk
    for pos in range(chunk_start, chunk_end):
        x_offset = pos * stride_xl + feature_start * stride_xd
        a_offset = pos * stride_al + feature_start * stride_ad
        b_offset = pos * stride_bl + feature_start * stride_bd
        
        x = tl.load(x_ptr + x_offset, mask=tl.arange(0, bd) < num_features, other=0.0)
        a = tl.load(a_ptr + a_offset, mask=tl.arange(0, bd) < num_features, other=0.0)
        b = tl.load(b_ptr + b_offset, mask=tl.arange(0, bd) < num_features, other=0.0)
        
        state = a * state + b * x
    
    # Store the final state of this chunk
    state_offset = chunk_idx * stride_cs_chunk + feature_start * stride_cs_feat
    tl.store(chunk_state_ptr + state_offset, state, mask=tl.arange(0, bd) < num_features)


@triton.jit
def propagate_chunk_states_kernel(
    chunk_state_ptr,
    num_chunks,
    d,
    stride_cs_chunk,
    stride_cs_feat,
    bd: tl.constexpr,
):
    """
    Propagate chunk states to compute starting states for each chunk.
    
    This kernel performs a sequential scan over chunks for each feature block.
    """
    pid = tl.program_id(0)
    
    # Each program handles a block of features
    feature_block = pid
    feature_start = feature_block * bd
    feature_end = min(feature_start + bd, d)
    num_features = feature_end - feature_start
    
    if feature_start >= d:
        return
    
    # Load all chunk states for this feature block
    chunk_states = tl.zeros([num_chunks, bd], dtype=tl.float16)
    
    for chunk_idx in range(num_chunks):
        offset = chunk_idx * stride_cs_chunk + feature_start * stride_cs_feat
        state = tl.load(chunk_state_ptr + offset, mask=tl.arange(0, bd) < num_features, other=0.0)
        chunk_states = tl.where(
            tl.arange(0, bd)[None, :] < num_features,
            chunk_states.at[chunk_idx, :].set(state),
            chunk_states
        )
    
    # Sequential scan over chunks
    for chunk_idx in range(1, num_chunks):
        prev_state = chunk_states[chunk_idx - 1, :]
        chunk_states = tl.where(
            tl.arange(0, bd)[None, :] < num_features,
            chunk_states.at[chunk_idx, :].add(prev_state),
            chunk_states
        )
    
    # Store back the propagated states
    for chunk_idx in range(num_chunks):
        offset = chunk_idx * stride_cs_chunk + feature_start * stride_cs_feat
        state = chunk_states[chunk_idx, :]
        tl.store(chunk_state_ptr + offset, state, mask=tl.arange(0, bd) < num_features)


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
    L, D = X.shape
    device = X.device
    
    # Validate inputs
    assert X.dtype == torch.float16
    assert A.dtype == torch.float16
    assert B.dtype == torch.float16
    assert X.shape == A.shape == B.shape
    assert L % chunk == 0, "L must be divisible by chunk"
    
    # Allocate output tensor
    Y = torch.empty_like(X)
    
    # Compute number of chunks
    num_chunks = L // chunk
    
    # Optimize for small sequences: use single kernel approach
    if num_chunks <= 4 or D <= BD:
        # Launch a single kernel that handles everything sequentially within blocks
        grid = (num_chunks * triton.cdiv(D, BD),)
        chunk_scan_kernel[grid](
            X, A, B, Y,
            chunk, L, D,
            X.stride(0), X.stride(1),
            A.stride(0), A.stride(1),
            B.stride(0), B.stride(1),
            Y.stride(0), Y.stride(1),
            BD,
        )
        return Y
    
    # For larger sequences: use two-pass approach with state propagation
    # First pass: compute chunk states starting from zero
    chunk_states = torch.zeros(num_chunks, D, dtype=torch.float16, device=device)
    
    # Compute chunk states kernel
    grid1 = (num_chunks * triton.cdiv(D, BD),)
    compute_chunk_state_kernel[grid1](
        X, A, B, chunk_states,
        chunk, L, D,
        X.stride(0), X.stride(1),
        A.stride(0), A.stride(1),
        B.stride(0), B.stride(1),
        chunk_states.stride(0), chunk_states.stride(1),
        BD,
    )
    
    # Propagate chunk states to get starting states for each chunk
    grid2 = (triton.cdiv(D, BD),)
    propagate_chunk_states_kernel[grid2](
        chunk_states,
        num_chunks, D,
        chunk_states.stride(0), chunk_states.stride(1),
        BD,
    )
    
    # Second pass: compute final output using chunk starting states
    grid3 = (num_chunks * triton.cdiv(D, BD),)
    chunk_scan_kernel_with_state[grid3](
        X, A, B, Y, chunk_states,
        chunk, L, D,
        X.stride(0), X.stride(1),
        A.stride(0), A.stride(1),
        B.stride(0), B.stride(1),
        Y.stride(0), Y.stride(1),
        chunk_states.stride(0), chunk_states.stride(1),
        BD,
    )
    
    return Y


class Solution:
    def solve(self, spec_path: str = None) -> dict:
        """
        Returns a dict with either:
        - {"code": "python_code_string"}
        - {"program_path": "path/to/kernel.py"}
        """
        # Return the complete implementation as a code string
        import inspect
        code = inspect.getsource(__main__) if '__main__' in globals() else inspect.getsource(sys.modules[__name__])
        return {"code": code}
