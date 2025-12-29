import torch
import triton
import triton.language as tl
from typing import Optional


@triton.jit
def chunk_scan_forward_kernel(
    x_ptr,
    a_ptr,
    b_ptr,
    y_ptr,
    state_ptr,
    l,
    d,
    chunk,
    stride_x_l,
    stride_x_d,
    stride_a_l,
    stride_a_d,
    stride_b_l,
    stride_b_d,
    stride_y_l,
    stride_y_d,
    stride_state_d,
    bd: tl.constexpr,
):
    """
    Forward pass kernel for chunked scan.
    Each program processes one chunk and multiple features.
    """
    pid = tl.program_id(0)
    num_chunks = tl.cdiv(l, chunk)
    chunk_idx = pid // tl.cdiv(d, bd)
    block_idx = pid % tl.cdiv(d, bd)
    
    # Feature block offset
    d_offset = block_idx * bd
    d_indices = d_offset + tl.arange(0, bd)
    d_mask = d_indices < d
    
    # Chunk offset
    chunk_start = chunk_idx * chunk
    chunk_end = tl.min(chunk_start + chunk, l)
    actual_chunk = chunk_end - chunk_start
    
    # Initialize state from previous chunk
    if chunk_idx == 0:
        state = tl.zeros((bd,), dtype=tl.float16)
    else:
        state = tl.load(
            state_ptr + d_indices * stride_state_d,
            mask=d_mask,
            other=0.0
        )
    
    # Process chunk
    for t in range(actual_chunk):
        l_idx = chunk_start + t
        
        # Load inputs
        x = tl.load(
            x_ptr + l_idx * stride_x_l + d_indices * stride_x_d,
            mask=d_mask,
            other=0.0
        )
        a = tl.load(
            a_ptr + l_idx * stride_a_l + d_indices * stride_a_d,
            mask=d_mask,
            other=0.0
        )
        b = tl.load(
            b_ptr + l_idx * stride_b_l + d_indices * stride_b_d,
            mask=d_mask,
            other=0.0
        )
        
        # Compute scan: y_t = a_t * y_{t-1} + b_t * x_t
        state = a * state + b * x
        
        # Store output
        tl.store(
            y_ptr + l_idx * stride_y_l + d_indices * stride_y_d,
            state,
            mask=d_mask
        )
    
    # Store final state for next chunk
    if chunk_idx < num_chunks - 1:
        tl.store(
            state_ptr + d_indices * stride_state_d,
            state,
            mask=d_mask
        )


@triton.jit
def chunk_scan_backward_kernel(
    x_ptr,
    a_ptr,
    b_ptr,
    y_ptr,
    state_ptr,
    l,
    d,
    chunk,
    stride_x_l,
    stride_x_d,
    stride_a_l,
    stride_a_d,
    stride_b_l,
    stride_b_d,
    stride_y_l,
    stride_y_d,
    stride_state_d,
    bd: tl.constexpr,
):
    """
    Backward pass to compute state from previous chunks.
    This kernel runs after forward pass to propagate states between chunks.
    """
    pid = tl.program_id(0)
    num_chunks = tl.cdiv(l, chunk)
    chunk_idx = pid // tl.cdiv(d, bd)
    block_idx = pid % tl.cdiv(d, bd)
    
    # Feature block offset
    d_offset = block_idx * bd
    d_indices = d_offset + tl.arange(0, bd)
    d_mask = d_indices < d
    
    # Only process chunks that need state adjustment
    if chunk_idx == 0:
        return
    
    # Load state from previous chunk
    prev_state = tl.load(
        state_ptr + d_indices * stride_state_d,
        mask=d_mask,
        other=0.0
    )
    
    # Chunk offset
    chunk_start = chunk_idx * chunk
    chunk_end = tl.min(chunk_start + chunk, l)
    actual_chunk = chunk_end - chunk_start
    
    # Process chunk with previous state
    state = prev_state
    for t in range(actual_chunk):
        l_idx = chunk_start + t
        
        # Load inputs
        x = tl.load(
            x_ptr + l_idx * stride_x_l + d_indices * stride_x_d,
            mask=d_mask,
            other=0.0
        )
        a = tl.load(
            a_ptr + l_idx * stride_a_l + d_indices * stride_a_d,
            mask=d_mask,
            other=0.0
        )
        b = tl.load(
            b_ptr + l_idx * stride_b_l + d_indices * stride_b_d,
            mask=d_mask,
            other=0.0
        )
        
        # Compute scan with propagated state
        state = a * state + b * x
        
        # Store updated output
        tl.store(
            y_ptr + l_idx * stride_y_l + d_indices * stride_y_d,
            state,
            mask=d_mask
        )
    
    # Store final state for next chunk
    if chunk_idx < num_chunks - 1:
        tl.store(
            state_ptr + d_indices * stride_state_d,
            state,
            mask=d_mask
        )


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
    
    # Validate inputs
    assert X.shape == A.shape == B.shape
    assert X.dtype == A.dtype == B.dtype == torch.float16
    assert L % chunk == 0, "Sequence length must be divisible by chunk size"
    
    # Allocate output and state buffer
    Y = torch.empty_like(X)
    state = torch.zeros((D,), dtype=torch.float16, device=X.device)
    
    # Compute grid size
    num_chunks = L // chunk
    num_blocks_per_chunk = triton.cdiv(D, BD)
    grid = (num_chunks * num_blocks_per_chunk,)
    
    # Launch forward kernel (process chunks in parallel with zero initial state)
    chunk_scan_forward_kernel[grid](
        X,
        A,
        B,
        Y,
        state,
        L,
        D,
        chunk,
        X.stride(0),
        X.stride(1),
        A.stride(0),
        A.stride(1),
        B.stride(0),
        B.stride(1),
        Y.stride(0),
        Y.stride(1),
        1,  # state stride
        BD=BD,
    )
    
    # Launch backward kernel to propagate states between chunks
    if num_chunks > 1:
        chunk_scan_backward_kernel[grid](
            X,
            A,
            B,
            Y,
            state,
            L,
            D,
            chunk,
            X.stride(0),
            X.stride(1),
            A.stride(0),
            A.stride(1),
            B.stride(0),
            B.stride(1),
            Y.stride(0),
            Y.stride(1),
            1,  # state stride
            BD=BD,
        )
    
    return Y


class Solution:
    def solve(self, spec_path: str = None) -> dict:
        return {"code": self._get_code()}
    
    @staticmethod
    def _get_code() -> str:
        """
        Returns the complete implementation code as a string.
        """
        import inspect
        return inspect.getsource(chunk_scan) + "\n" + inspect.getsource(Solution)