import torch
import triton
import triton.language as tl

@triton.jit
def _pass1_kernel(
    X, A, B,
    P, G,
    stride_x_l, stride_x_d,
    stride_a_l, stride_a_d,
    stride_b_l, stride_b_d,
    stride_p_c, stride_p_d,
    stride_g_c, stride_g_d,
    L, D,
    CHUNK: tl.constexpr,
    BD: tl.constexpr
):
    chunk_idx = tl.program_id(0)
    d_idx = tl.program_id(1)
    
    row_start = chunk_idx * CHUNK
    col_start = d_idx * BD
    
    offs_d = col_start + tl.arange(0, BD)
    mask_d = offs_d < D
    
    x_ptr = X + row_start * stride_x_l + offs_d * stride_x_d
    a_ptr = A + row_start * stride_a_l + offs_d * stride_a_d
    b_ptr = B + row_start * stride_b_l + offs_d * stride_b_d
    
    # Initialize accumulators
    p_acc = tl.zeros([BD], dtype=tl.float32) + 1.0
    g_acc = tl.zeros([BD], dtype=tl.float32)
    
    # Iterate over the chunk
    for i in range(CHUNK):
        x_val = tl.load(x_ptr, mask=mask_d, other=0.0).to(tl.float32)
        a_val = tl.load(a_ptr, mask=mask_d, other=0.0).to(tl.float32)
        b_val = tl.load(b_ptr, mask=mask_d, other=0.0).to(tl.float32)
        
        # p_acc: cumulative product of a
        # g_acc: cumulative sum of (b*x) * trailing_a_product
        p_acc = p_acc * a_val
        g_acc = g_acc * a_val + b_val * x_val
        
        x_ptr += stride_x_l
        a_ptr += stride_a_l
        b_ptr += stride_b_l
        
    # Store chunk aggregates
    p_out = P + chunk_idx * stride_p_c + offs_d * stride_p_d
    g_out = G + chunk_idx * stride_g_c + offs_d * stride_g_d
    
    tl.store(p_out, p_acc, mask=mask_d)
    tl.store(g_out, g_acc, mask=mask_d)

@triton.jit
def _pass2_kernel(
    P, G, State,
    stride_p_c, stride_p_d,
    stride_g_c, stride_g_d,
    stride_s_c, stride_s_d,
    NumChunks, D,
    BD: tl.constexpr
):
    d_idx = tl.program_id(0)
    col_start = d_idx * BD
    offs_d = col_start + tl.arange(0, BD)
    mask_d = offs_d < D
    
    p_ptr = P + offs_d * stride_p_d
    g_ptr = G + offs_d * stride_g_d
    s_ptr = State + offs_d * stride_s_d
    
    # Initial state for the first chunk is 0
    state = tl.zeros([BD], dtype=tl.float32)
    tl.store(s_ptr, state, mask=mask_d)
    
    # Scan over chunks
    # State[k+1] = State[k] * P[k] + G[k]
    for k in range(NumChunks - 1):
        p_val = tl.load(p_ptr, mask=mask_d, other=0.0).to(tl.float32)
        g_val = tl.load(g_ptr, mask=mask_d, other=0.0).to(tl.float32)
        
        state = state * p_val + g_val
        
        # Advance input pointers
        p_ptr += stride_p_c
        g_ptr += stride_g_c
        
        # Advance output pointer
        s_ptr += stride_s_c
        
        tl.store(s_ptr, state, mask=mask_d)

@triton.jit
def _pass3_kernel(
    X, A, B, State, Y,
    stride_x_l, stride_x_d,
    stride_a_l, stride_a_d,
    stride_b_l, stride_b_d,
    stride_s_c, stride_s_d,
    stride_y_l, stride_y_d,
    L, D,
    CHUNK: tl.constexpr,
    BD: tl.constexpr
):
    chunk_idx = tl.program_id(0)
    d_idx = tl.program_id(1)
    
    row_start = chunk_idx * CHUNK
    col_start = d_idx * BD
    
    offs_d = col_start + tl.arange(0, BD)
    mask_d = offs_d < D
    
    # Load initial state for this chunk
    s_ptr = State + chunk_idx * stride_s_c + offs_d * stride_s_d
    state = tl.load(s_ptr, mask=mask_d, other=0.0).to(tl.float32)
    
    x_ptr = X + row_start * stride_x_l + offs_d * stride_x_d
    a_ptr = A + row_start * stride_a_l + offs_d * stride_a_d
    b_ptr = B + row_start * stride_b_l + offs_d * stride_b_d
    y_ptr = Y + row_start * stride_y_l + offs_d * stride_y_d
    
    # Iterate over chunk and compute final output
    for i in range(CHUNK):
        x_val = tl.load(x_ptr, mask=mask_d, other=0.0).to(tl.float32)
        a_val = tl.load(a_ptr, mask=mask_d, other=0.0).to(tl.float32)
        b_val = tl.load(b_ptr, mask=mask_d, other=0.0).to(tl.float32)
        
        # y_t = a_t * y_{t-1} + b_t * x_t
        state = state * a_val + b_val * x_val
        
        tl.store(y_ptr, state.to(tl.float16), mask=mask_d)
        
        x_ptr += stride_x_l
        a_ptr += stride_a_l
        b_ptr += stride_b_l
        y_ptr += stride_y_l

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
    assert L % chunk == 0, "L must be divisible by chunk"
    num_chunks = L // chunk
    
    # Allocate intermediate buffers (float32 for precision)
    P = torch.empty((num_chunks, D), device=X.device, dtype=torch.float32)
    G = torch.empty((num_chunks, D), device=X.device, dtype=torch.float32)
    State = torch.empty((num_chunks, D), device=X.device, dtype=torch.float32)
    Y = torch.empty_like(X)
    
    # Grid configurations
    grid_pass1 = (num_chunks, (D + BD - 1) // BD)
    grid_pass2 = ((D + BD - 1) // BD, )
    grid_pass3 = (num_chunks, (D + BD - 1) // BD)
    
    # Pass 1: Compute per-chunk aggregates (P, G)
    _pass1_kernel[grid_pass1](
        X, A, B, P, G,
        X.stride(0), X.stride(1),
        A.stride(0), A.stride(1),
        B.stride(0), B.stride(1),
        P.stride(0), P.stride(1),
        G.stride(0), G.stride(1),
        L, D,
        CHUNK=chunk, BD=BD
    )
    
    # Pass 2: Scan aggregates to get initial state for each chunk
    _pass2_kernel[grid_pass2](
        P, G, State,
        P.stride(0), P.stride(1),
        G.stride(0), G.stride(1),
        State.stride(0), State.stride(1),
        num_chunks, D,
        BD=BD
    )
    
    # Pass 3: Compute final output using initial states
    _pass3_kernel[grid_pass3](
        X, A, B, State, Y,
        X.stride(0), X.stride(1),
        A.stride(0), A.stride(1),
        B.stride(0), B.stride(1),
        State.stride(0), State.stride(1),
        Y.stride(0), Y.stride(1),
        L, D,
        CHUNK=chunk, BD=BD
    )
    
    return Y

class Solution:
    def solve(self, spec_path: str = None) -> dict:
        """
        Returns a dict with either:
        - {"code": "python_code_string"}
        - {"program_path": "path/to/kernel.py"}
        """
        return {"program_path": __file__}