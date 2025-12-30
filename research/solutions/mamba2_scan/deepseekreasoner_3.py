import torch
import triton
import triton.language as tl

@triton.jit
def chunk_scan_kernel(
    x_ptr,
    a_ptr,
    b_ptr,
    y_ptr,
    l,
    d,
    chunk,
    BD,
    stride_xl,
    stride_xd,
    stride_al,
    stride_ad,
    stride_bl,
    stride_bd,
    stride_yl,
    stride_yd,
    BLOCK_D: tl.constexpr,
    BLOCK_L: tl.constexpr,
):
    pid = tl.program_id(0)
    num_pid_d = tl.cdiv(d, BLOCK_D)
    pid_d = pid % num_pid_d
    pid_l = pid // num_pid_d
    
    start_d = pid_d * BLOCK_D
    start_l = pid_l * BLOCK_L
    
    d_offs = start_d + tl.arange(0, BLOCK_D)
    l_offs = start_l + tl.arange(0, BLOCK_L)
    
    mask_d = d_offs < d
    mask_l = l_offs < l
    full_mask = mask_d[:, None] & mask_l[None, :]
    
    x_ptrs = x_ptr + (l_offs[None, :] * stride_xl + d_offs[:, None] * stride_xd)
    a_ptrs = a_ptr + (l_offs[None, :] * stride_al + d_offs[:, None] * stride_ad)
    b_ptrs = b_ptr + (l_offs[None, :] * stride_bl + d_offs[:, None] * stride_bd)
    y_ptrs = y_ptr + (l_offs[None, :] * stride_yl + d_offs[:, None] * stride_yd)
    
    x = tl.load(x_ptrs, mask=full_mask, other=0.0)
    a = tl.load(a_ptrs, mask=full_mask, other=0.0)
    b = tl.load(b_ptrs, mask=full_mask, other=0.0)
    
    result = tl.zeros((BLOCK_D, BLOCK_L), dtype=tl.float16)
    state = tl.zeros((BLOCK_D,), dtype=tl.float16)
    
    for i in range(BLOCK_L):
        result[:, i] = a[:, i] * state + b[:, i] * x[:, i]
        state = result[:, i]
    
    tl.store(y_ptrs, result, mask=full_mask)

@triton.jit
def chunk_scan_state_propagation_kernel(
    y_ptr,
    state_ptr,
    l,
    d,
    chunk,
    stride_yl,
    stride_yd,
    stride_sl,
    stride_sd,
    BLOCK_D: tl.constexpr,
    BLOCK_L: tl.constexpr,
):
    pid = tl.program_id(0)
    num_pid_d = tl.cdiv(d, BLOCK_D)
    pid_d = pid % num_pid_d
    
    start_d = pid_d * BLOCK_D
    d_offs = start_d + tl.arange(0, BLOCK_D)
    mask_d = d_offs < d
    
    num_chunks = l // chunk
    
    for chunk_idx in range(1, num_chunks):
        state_prev_ptr = state_ptr + ((chunk_idx - 1) * stride_sl + d_offs[:, None] * stride_sd)
        state_prev = tl.load(state_prev_ptr, mask=mask_d[:, None], other=0.0)
        
        y_chunk_ptr = y_ptr + (chunk_idx * chunk * stride_yl + d_offs[:, None] * stride_yd)
        
        for i in range(chunk):
            y_cur_ptr = y_chunk_ptr + (i * stride_yl)
            y_cur = tl.load(y_cur_ptr, mask=mask_d[:, None], other=0.0)
            y_new = y_cur + state_prev
            tl.store(y_cur_ptr, y_new, mask=mask_d[:, None])
            
            if i == chunk - 1:
                state_cur_ptr = state_ptr + (chunk_idx * stride_sl + d_offs[:, None] * stride_sd)
                tl.store(state_cur_ptr, y_new, mask=mask_d[:, None])

def chunk_scan(
    X: torch.Tensor,
    A: torch.Tensor,
    B: torch.Tensor,
    chunk: int = 128,
    BD: int = 128,
) -> torch.Tensor:
    L, D = X.shape
    assert L % chunk == 0, f"L ({L}) must be divisible by chunk ({chunk})"
    assert X.dtype == torch.float16
    assert A.dtype == torch.float16
    assert B.dtype == torch.float16
    
    Y = torch.empty_like(X)
    
    num_chunks = L // chunk
    num_warps = 4 if chunk <= 64 else 8
    
    BLOCK_D = min(BD, 128)
    BLOCK_L = min(chunk, 128)
    
    grid = (num_chunks * triton.cdiv(D, BLOCK_D),)
    
    chunk_scan_kernel[grid](
        X,
        A,
        B,
        Y,
        L,
        D,
        chunk,
        BD,
        X.stride(0),
        X.stride(1),
        A.stride(0),
        A.stride(1),
        B.stride(0),
        B.stride(1),
        Y.stride(0),
        Y.stride(1),
        BLOCK_D=BLOCK_D,
        BLOCK_L=BLOCK_L,
        num_warps=num_warps,
    )
    
    if num_chunks > 1:
        state = torch.zeros((num_chunks, D), dtype=torch.float16, device=X.device)
        
        chunk_scan_state_propagation_kernel[(triton.cdiv(D, BLOCK_D),)](
            Y,
            state,
            L,
            D,
            chunk,
            Y.stride(0),
            Y.stride(1),
            state.stride(0),
            state.stride(1),
            BLOCK_D=BLOCK_D,
            BLOCK_L=BLOCK_L,
            num_warps=num_warps,
        )
    
    return Y

class Solution:
    def solve(self, spec_path: str = None) -> dict:
        code = '''
import torch
import triton
import triton.language as tl

@triton.jit
def chunk_scan_kernel(
    x_ptr,
    a_ptr,
    b_ptr,
    y_ptr,
    l,
    d,
    chunk,
    BD,
    stride_xl,
    stride_xd,
    stride_al,
    stride_ad,
    stride_bl,
    stride_bd,
    stride_yl,
    stride_yd,
    BLOCK_D: tl.constexpr,
    BLOCK_L: tl.constexpr,
):
    pid = tl.program_id(0)
    num_pid_d = tl.cdiv(d, BLOCK_D)
    pid_d = pid % num_pid_d
    pid_l = pid // num_pid_d
    
    start_d = pid_d * BLOCK_D
    start_l = pid_l * BLOCK_L
    
    d_offs = start_d + tl.arange(0, BLOCK_D)
    l_offs = start_l + tl.arange(0, BLOCK_L)
    
    mask_d = d_offs < d
    mask_l = l_offs < l
    full_mask = mask_d[:, None] & mask_l[None, :]
    
    x_ptrs = x_ptr + (l_offs[None, :] * stride_xl + d_offs[:, None] * stride_xd)
    a_ptrs = a_ptr + (l_offs[None, :] * stride_al + d_offs[:, None] * stride_ad)
    b_ptrs = b_ptr + (l_offs[None, :] * stride_bl + d_offs[:, None] * stride_bd)
    y_ptrs = y_ptr + (l_offs[None, :] * stride_yl + d_offs[:, None] * stride_yd)
    
    x = tl.load(x_ptrs, mask=full_mask, other=0.0)
    a = tl.load(a_ptrs, mask=full_mask, other=0.0)
    b = tl.load(b_ptrs, mask=full_mask, other=0.0)
    
    result = tl.zeros((BLOCK_D, BLOCK_L), dtype=tl.float16)
    state = tl.zeros((BLOCK_D,), dtype=tl.float16)
    
    for i in range(BLOCK_L):
        result[:, i] = a[:, i] * state + b[:, i] * x[:, i]
        state = result[:, i]
    
    tl.store(y_ptrs, result, mask=full_mask)

@triton.jit
def chunk_scan_state_propagation_kernel(
    y_ptr,
    state_ptr,
    l,
    d,
    chunk,
    stride_yl,
    stride_yd,
    stride_sl,
    stride_sd,
    BLOCK_D: tl.constexpr,
    BLOCK_L: tl.constexpr,
):
    pid = tl.program_id(0)
    num_pid_d = tl.cdiv(d, BLOCK_D)
    pid_d = pid % num_pid_d
    
    start_d = pid_d * BLOCK_D
    d_offs = start_d + tl.arange(0, BLOCK_D)
    mask_d = d_offs < d
    
    num_chunks = l // chunk
    
    for chunk_idx in range(1, num_chunks):
        state_prev_ptr = state_ptr + ((chunk_idx - 1) * stride_sl + d_offs[:, None] * stride_sd)
        state_prev = tl.load(state_prev_ptr, mask=mask_d[:, None], other=0.0)
        
        y_chunk_ptr = y_ptr + (chunk_idx * chunk * stride_yl + d_offs[:, None] * stride_yd)
        
        for i in range(chunk):
            y_cur_ptr = y_chunk_ptr + (i * stride_yl)
            y_cur = tl.load(y_cur_ptr, mask=mask_d[:, None], other=0.0)
            y_new = y_cur + state_prev
            tl.store(y_cur_ptr, y_new, mask=mask_d[:, None])
            
            if i == chunk - 1:
                state_cur_ptr = state_ptr + (chunk_idx * stride_sl + d_offs[:, None] * stride_sd)
                tl.store(state_cur_ptr, y_new, mask=mask_d[:, None])

def chunk_scan(
    X: torch.Tensor,
    A: torch.Tensor,
    B: torch.Tensor,
    chunk: int = 128,
    BD: int = 128,
) -> torch.Tensor:
    L, D = X.shape
    assert L % chunk == 0, f"L ({L}) must be divisible by chunk ({chunk})"
    assert X.dtype == torch.float16
    assert A.dtype == torch.float16
    assert B.dtype == torch.float16
    
    Y = torch.empty_like(X)
    
    num_chunks = L // chunk
    num_warps = 4 if chunk <= 64 else 8
    
    BLOCK_D = min(BD, 128)
    BLOCK_L = min(chunk, 128)
    
    grid = (num_chunks * triton.cdiv(D, BLOCK_D),)
    
    chunk_scan_kernel[grid](
        X,
        A,
        B,
        Y,
        L,
        D,
        chunk,
        BD,
        X.stride(0),
        X.stride(1),
        A.stride(0),
        A.stride(1),
        B.stride(0),
        B.stride(1),
        Y.stride(0),
        Y.stride(1),
        BLOCK_D=BLOCK_D,
        BLOCK_L=BLOCK_L,
        num_warps=num_warps,
    )
    
    if num_chunks > 1:
        state = torch.zeros((num_chunks, D), dtype=torch.float16, device=X.device)
        
        chunk_scan_state_propagation_kernel[(triton.cdiv(D, BLOCK_D),)](
            Y,
            state,
            L,
            D,
            chunk,
            Y.stride(0),
            Y.stride(1),
            state.stride(0),
            state.stride(1),
            BLOCK_D=BLOCK_D,
            BLOCK_L=BLOCK_L,
            num_warps=num_warps,
        )
    
    return Y
'''
        return {"code": code}