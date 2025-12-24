import torch
import triton
import triton.language as tl

class Solution:
    def solve(self, spec_path: str = None) -> dict:
        code = """
import torch
import triton
import triton.language as tl

@triton.jit(num_warps=8, num_stages=3)
def _compute_chunk_states_kernel(
    X_ptr, A_ptr, B_ptr, CHUNK_A_ptr, CHUNK_S_ptr,
    L, D,
    stride_lx, stride_la, stride_lb,
    stride_ca_c, stride_cs_c,
    chunk: tl.constexpr, BD: tl.constexpr,
):
    pid_c = tl.program_id(0)
    pid_d_block = tl.program_id(1)

    d_offsets = pid_d_block * BD + tl.arange(0, BD)
    d_mask = d_offsets < D

    x_ptr_base = X_ptr + (pid_c * chunk) * stride_lx
    a_ptr_base = A_ptr + (pid_c * chunk) * stride_la
    b_ptr_base = B_ptr + (pid_c * chunk) * stride_lb

    y_state = tl.zeros((BD,), dtype=tl.float32)
    a_prod_state = tl.ones((BD,), dtype=tl.float32)

    for t in range(chunk):
        x_ptr = x_ptr_base + t * stride_lx + d_offsets
        a_ptr = a_ptr_base + t * stride_la + d_offsets
        b_ptr = b_ptr_base + t * stride_lb + d_offsets
        
        x_t = tl.load(x_ptr, mask=d_mask, other=0.0).to(tl.float32)
        a_t = tl.load(a_ptr, mask=d_mask, other=0.0).to(tl.float32)
        b_t = tl.load(b_ptr, mask=d_mask, other=0.0).to(tl.float32)
        
        y_state = a_t * y_state + b_t * x_t
        a_prod_state = a_prod_state * a_t

    chunk_a_ptr = CHUNK_A_ptr + pid_c * stride_ca_c + d_offsets
    chunk_s_ptr = CHUNK_S_ptr + pid_c * stride_cs_c + d_offsets
    
    tl.store(chunk_a_ptr, a_prod_state.to(tl.float16), mask=d_mask)
    tl.store(chunk_s_ptr, y_state.to(tl.float16), mask=d_mask)

@triton.jit(num_warps=4)
def _scan_states_kernel(
    CHUNK_A_ptr, CHUNK_S_ptr, H_ptr,
    C, D,
    stride_ca_c, stride_cs_c, stride_h_c,
):
    pid_d = tl.program_id(0)

    chunk_a_ptr = CHUNK_A_ptr + pid_d
    chunk_s_ptr = CHUNK_S_ptr + pid_d
    h_ptr = H_ptr + pid_d

    h_state = tl.zeros((), dtype=tl.float32)
    
    for c in range(C):
        tl.store(h_ptr + c * stride_h_c, h_state.to(tl.float16))
        
        a_prod_c = tl.load(chunk_a_ptr + c * stride_ca_c).to(tl.float32)
        s_c = tl.load(chunk_s_ptr + c * stride_cs_c).to(tl.float32)
        
        h_state = a_prod_c * h_state + s_c

@triton.jit(num_warps=8, num_stages=3)
def _final_scan_kernel(
    X_ptr, A_ptr, B_ptr, H_ptr, Y_ptr,
    L, D,
    stride_lx, stride_la, stride_lb, stride_ly,
    stride_h_c,
    chunk: tl.constexpr, BD: tl.constexpr,
):
    pid_c = tl.program_id(0)
    pid_d_block = tl.program_id(1)

    d_offsets = pid_d_block * BD + tl.arange(0, BD)
    d_mask = d_offsets < D
    
    x_ptr_base = X_ptr + (pid_c * chunk) * stride_lx
    a_ptr_base = A_ptr + (pid_c * chunk) * stride_la
    b_ptr_base = B_ptr + (pid_c * chunk) * stride_lb
    y_ptr_base = Y_ptr + (pid_c * chunk) * stride_ly

    h_ptr = H_ptr + pid_c * stride_h_c + d_offsets
    y_state = tl.load(h_ptr, mask=d_mask, other=0.0).to(tl.float32)

    for t in range(chunk):
        x_ptr = x_ptr_base + t * stride_lx + d_offsets
        a_ptr = a_ptr_base + t * stride_la + d_offsets
        b_ptr = b_ptr_base + t * stride_lb + d_offsets
        
        x_t = tl.load(x_ptr, mask=d_mask, other=0.0).to(tl.float32)
        a_t = tl.load(a_ptr, mask=d_mask, other=0.0).to(tl.float32)
        b_t = tl.load(b_ptr, mask=d_mask, other=0.0).to(tl.float32)
        
        y_state = a_t * y_state + b_t * x_t
        
        y_ptr = y_ptr_base + t * stride_ly + d_offsets
        tl.store(y_ptr, y_state.to(tl.float16), mask=d_mask)

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
        raise ValueError("L must be divisible by chunk")

    X, A, B = X.contiguous(), A.contiguous(), B.contiguous()

    CHUNK_A = torch.empty((C, D), dtype=torch.float16, device=X.device)
    CHUNK_S = torch.empty((C, D), dtype=torch.float16, device=X.device)
    H = torch.empty((C, D), dtype=torch.float16, device=X.device)
    Y = torch.empty((L, D), dtype=torch.float16, device=X.device)

    grid_cd = (C, triton.cdiv(D, BD))
    
    _compute_chunk_states_kernel[grid_cd](
        X, A, B, CHUNK_A, CHUNK_S,
        L, D,
        X.stride(0), A.stride(0), B.stride(0),
        CHUNK_A.stride(0), CHUNK_S.stride(0),
        chunk=chunk, BD=BD,
    )
    
    grid_d = (D,)
    
    _scan_states_kernel[grid_d](
        CHUNK_A, CHUNK_S, H,
        C, D,
        CHUNK_A.stride(0), CHUNK_S.stride(0), H.stride(0),
    )
    
    _final_scan_kernel[grid_cd](
        X, A, B, H, Y,
        L, D,
        X.stride(0), A.stride(0), B.stride(0), Y.stride(0),
        H.stride(0),
        chunk=chunk, BD=BD,
    )

    return Y
"""
        return {"code": code}
