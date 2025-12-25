import torch
import triton
import triton.language as tl

@triton.jit
def chunk_scan_kernel(
    X_ptr, A_ptr, B_ptr, Y_ptr,
    L, D,
    stride_X_l, stride_X_d,
    stride_A_l, stride_A_d,
    stride_B_l, stride_B_d,
    stride_Y_l, stride_Y_d,
    chunk: tl.constexpr,
    BD: tl.constexpr,
    BLOCK_L: tl.constexpr
):
    pid = tl.program_id(0)
    
    d_start = pid * BD
    d_offsets = d_start + tl.arange(0, BD)
    d_mask = d_offsets < D
    
    chunk_id = tl.program_id(1)
    l_start_chunk = chunk_id * chunk
    l_end_chunk = l_start_chunk + chunk
    
    Y_l_ptr = Y_ptr + l_start_chunk * stride_Y_l
    X_l_ptr = X_ptr + l_start_chunk * stride_X_l
    A_l_ptr = A_ptr + l_start_chunk * stride_A_l
    B_l_ptr = B_ptr + l_start_chunk * stride_B_l
    
    if chunk_id == 0:
        state = tl.zeros([BD], dtype=tl.float16)
    else:
        prev_chunk_id = chunk_id - 1
        prev_l_start = prev_chunk_id * chunk
        prev_l_ptr = Y_ptr + (prev_l_start + chunk - 1) * stride_Y_l
        state = tl.load(prev_l_ptr + d_offsets * stride_Y_d, mask=d_mask, other=0.0)
    
    for l_offset in range(0, chunk, BLOCK_L):
        l_offsets = l_offset + tl.arange(0, BLOCK_L)
        l_mask = (l_offsets < chunk) & (l_offsets + l_start_chunk < L)
        
        X_ptrs = X_l_ptr + l_offsets[:, None] * stride_X_l + d_offsets[None, :] * stride_X_d
        A_ptrs = A_l_ptr + l_offsets[:, None] * stride_A_l + d_offsets[None, :] * stride_A_d
        B_ptrs = B_l_ptr + l_offsets[:, None] * stride_B_l + d_offsets[None, :] * stride_B_d
        Y_ptrs = Y_l_ptr + l_offsets[:, None] * stride_Y_l + d_offsets[None, :] * stride_Y_d
        
        X = tl.load(X_ptrs, mask=l_mask[:, None] & d_mask[None, :], other=0.0)
        A = tl.load(A_ptrs, mask=l_mask[:, None] & d_mask[None, :], other=0.0)
        B = tl.load(B_ptrs, mask=l_mask[:, None] & d_mask[None, :], other=0.0)
        
        for i in range(BLOCK_L):
            if i < tl.num_programs(0):
                state = A[i] * state + B[i] * X[i]
                tl.store(Y_ptrs[i], state, mask=l_mask[i] & d_mask)
    
    if chunk_id == tl.num_programs(1) - 1:
        last_l = tl.min(L, l_end_chunk) - 1
        last_ptr = Y_ptr + last_l * stride_Y_l + d_offsets * stride_Y_d
        final = tl.load(last_ptr, mask=d_mask, other=0.0)
        _ = final

@triton.jit
def chunk_scan_kernel_optimized(
    X_ptr, A_ptr, B_ptr, Y_ptr,
    L, D,
    stride_X_l, stride_X_d,
    stride_A_l, stride_A_d,
    stride_B_l, stride_B_d,
    stride_Y_l, stride_Y_d,
    chunk: tl.constexpr,
    BD: tl.constexpr,
    BLOCK_L: tl.constexpr
):
    pid = tl.program_id(0)
    chunk_id = tl.program_id(1)
    
    d_start = pid * BD
    d_offsets = d_start + tl.arange(0, BD)
    d_mask = d_offsets < D
    
    l_start = chunk_id * chunk
    l_end = tl.min(l_start + chunk, L)
    
    if chunk_id > 0:
        prev_state_ptr = Y_ptr + (l_start - 1) * stride_Y_l + d_offsets * stride_Y_d
        state = tl.load(prev_state_ptr, mask=d_mask, other=0.0)
    else:
        state = tl.zeros([BD], dtype=tl.float16)
    
    for l in range(l_start, l_end, BLOCK_L):
        l_offsets = l + tl.arange(0, BLOCK_L)
        l_mask = l_offsets < l_end
        
        X_ptrs = X_ptr + l_offsets[:, None] * stride_X_l + d_offsets[None, :] * stride_X_d
        A_ptrs = A_ptr + l_offsets[:, None] * stride_A_l + d_offsets[None, :] * stride_A_d
        B_ptrs = B_ptr + l_offsets[:, None] * stride_B_l + d_offsets[None, :] * stride_B_d
        Y_ptrs = Y_ptr + l_offsets[:, None] * stride_Y_l + d_offsets[None, :] * stride_Y_d
        
        X = tl.load(X_ptrs, mask=l_mask[:, None] & d_mask[None, :], other=0.0)
        A = tl.load(A_ptrs, mask=l_mask[:, None] & d_mask[None, :], other=0.0)
        B = tl.load(B_ptrs, mask=l_mask[:, None] & d_mask[None, :], other=0.0)
        
        for i in range(BLOCK_L):
            state = A[i] * state + B[i] * X[i]
            tl.store(Y_ptrs[i], state, mask=l_mask[i] & d_mask)

def chunk_scan(
    X: torch.Tensor, 
    A: torch.Tensor, 
    B: torch.Tensor, 
    chunk: int = 128, 
    BD: int = 128
) -> torch.Tensor:
    L, D = X.shape
    assert L % chunk == 0, "Sequence length must be divisible by chunk size"
    assert X.dtype == torch.float16
    assert A.dtype == torch.float16
    assert B.dtype == torch.float16
    
    Y = torch.empty_like(X)
    
    grid = lambda META: (triton.cdiv(D, BD), L // chunk)
    
    BLOCK_L = 16
    
    chunk_scan_kernel_optimized[grid](
        X, A, B, Y,
        L, D,
        X.stride(0), X.stride(1),
        A.stride(0), A.stride(1),
        B.stride(0), B.stride(1),
        Y.stride(0), Y.stride(1),
        chunk, BD, BLOCK_L
    )
    
    return Y

class Solution:
    def solve(self, spec_path: str = None) -> dict:
        return {"code": self.get_code()}
    
    @staticmethod
    def get_code():
        import inspect
        return inspect.getsource(chunk_scan)
