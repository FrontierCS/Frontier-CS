import torch
import triton
import triton.language as tl

class Solution:
    def solve(self, spec_path: str = None) -> dict:
        solution_code = """
import torch
import triton
import triton.language as tl

@triton.jit
def _reduce_scan_kernel(
    X_ptr, A_ptr, B_ptr, H_ptr,
    L, D,
    stride_lx, stride_dx,
    stride_la, stride_da,
    stride_lb, stride_db,
    stride_h_op, stride_h_nch, stride_h_d,
    NUM_CHUNKS: tl.constexpr,
    CHUNK_SIZE: tl.constexpr,
    BLOCK_D: tl.constexpr,
):
    chunk_idx = tl.program_id(0)
    d_block_idx = tl.program_id(1)

    d_offsets = d_block_idx * BLOCK_D + tl.arange(0, BLOCK_D)
    d_mask = d_offsets < D

    a_prod_acc = tl.ones((BLOCK_D,), dtype=tl.float32)
    y_acc = tl.zeros((BLOCK_D,), dtype=tl.float32)

    l_start = chunk_idx * CHUNK_SIZE
    for t_offset in range(CHUNK_SIZE):
        l_idx = l_start + t_offset
        
        x_ptr = X_ptr + l_idx * stride_lx + d_offsets
        a_ptr = A_ptr + l_idx * stride_la + d_offsets
        b_ptr = B_ptr + l_idx * stride_lb + d_offsets
        
        x = tl.load(x_ptr, mask=d_mask, other=0.0).to(tl.float32)
        a = tl.load(a_ptr, mask=d_mask, other=0.0).to(tl.float32)
        b = tl.load(b_ptr, mask=d_mask, other=0.0).to(tl.float32)

        x_prime = b * x
        
        y_acc = a * y_acc + x_prime
        a_prod_acc = a * a_prod_acc

    a_prod_ptr = H_ptr + 0 * stride_h_op + chunk_idx * stride_h_nch + d_offsets
    y_final_ptr = H_ptr + 1 * stride_h_op + chunk_idx * stride_h_nch + d_offsets
    
    tl.store(a_prod_ptr, a_prod_acc.to(tl.float16), mask=d_mask)
    tl.store(y_final_ptr, y_acc.to(tl.float16), mask=d_mask)

@triton.jit
def _inter_scan_kernel(
    H_ptr, H_final_ptr,
    D,
    stride_h_op, stride_h_nch, stride_h_d,
    stride_hf_nch, stride_hf_d,
    NUM_CHUNKS: tl.constexpr,
    BLOCK_D: tl.constexpr,
):
    d_block_idx = tl.program_id(0)

    d_offsets = d_block_idx * BLOCK_D + tl.arange(0, BLOCK_D)
    d_mask = d_offsets < D
    
    h_state = tl.zeros((BLOCK_D,), dtype=tl.float32)

    for chunk_idx in range(NUM_CHUNKS):
        a_prod_ptr = H_ptr + 0 * stride_h_op + chunk_idx * stride_h_nch + d_offsets
        y_local_ptr = H_ptr + 1 * stride_h_op + chunk_idx * stride_h_nch + d_offsets
        
        a_prod = tl.load(a_prod_ptr, mask=d_mask, other=0.0).to(tl.float32)
        y_local = tl.load(y_local_ptr, mask=d_mask, other=0.0).to(tl.float32)

        h_c = y_local + a_prod * h_state
        
        h_final_ptr_c = H_final_ptr + chunk_idx * stride_hf_nch + d_offsets
        tl.store(h_final_ptr_c, h_c.to(tl.float16), mask=d_mask)

        h_state = h_c

@triton.jit
def _final_scan_kernel(
    X_ptr, A_ptr, B_ptr, Y_ptr, H_final_ptr,
    L, D,
    stride_lx, stride_dx,
    stride_la, stride_da,
    stride_lb, stride_db,
    stride_ly, stride_dy,
    stride_hf_nch, stride_hf_d,
    NUM_CHUNKS: tl.constexpr,
    CHUNK_SIZE: tl.constexpr,
    BLOCK_D: tl.constexpr,
):
    chunk_idx = tl.program_id(0)
    d_block_idx = tl.program_id(1)

    d_offsets = d_block_idx * BLOCK_D + tl.arange(0, BLOCK_D)
    d_mask = d_offsets < D

    state = tl.zeros((BLOCK_D,), dtype=tl.float32)
    if chunk_idx > 0:
        h_ptr = H_final_ptr + (chunk_idx - 1) * stride_hf_nch + d_offsets
        state = tl.load(h_ptr, mask=d_mask, other=0.0).to(tl.float32)
        
    l_start = chunk_idx * CHUNK_SIZE
    for t_offset in range(CHUNK_SIZE):
        l_idx = l_start + t_offset
        
        x_ptr = X_ptr + l_idx * stride_lx + d_offsets
        a_ptr = A_ptr + l_idx * stride_la + d_offsets
        b_ptr = B_ptr + l_idx * stride_lb + d_offsets
        y_ptr = Y_ptr + l_idx * stride_ly + d_offsets
        
        x = tl.load(x_ptr, mask=d_mask, other=0.0).to(tl.float32)
        a = tl.load(a_ptr, mask=d_mask, other=0.0).to(tl.float32)
        b = tl.load(b_ptr, mask=d_mask, other=0.0).to(tl.float32)
        
        x_prime = b * x
        y_t = a * state + x_prime
        
        state = y_t
        
        tl.store(y_ptr, y_t.to(tl.float16), mask=d_mask)

def chunk_scan(X: torch.Tensor, A: torch.Tensor, B: torch.Tensor, chunk: int = 128, BD: int = 128) -> torch.Tensor:
    L, D = X.shape
    if L % chunk != 0:
        raise ValueError("Sequence length L must be divisible by chunk size.")
    
    num_chunks = L // chunk
    
    Y = torch.empty_like(X)
    H = torch.empty(2, num_chunks, D, device=X.device, dtype=torch.float16)
    H_final = torch.empty(num_chunks, D, device=X.device, dtype=torch.float16)

    grid_chunkwise = (num_chunks, triton.cdiv(D, BD))
    
    _reduce_scan_kernel[grid_chunkwise](
        X, A, B, H,
        L, D,
        X.stride(0), X.stride(1),
        A.stride(0), A.stride(1),
        B.stride(0), B.stride(1),
        H.stride(0), H.stride(1), H.stride(2),
        NUM_CHUNKS=num_chunks, CHUNK_SIZE=chunk, BLOCK_D=BD,
    )
    
    grid_inter = (triton.cdiv(D, BD),)
    _inter_scan_kernel[grid_inter](
        H, H_final,
        D,
        H.stride(0), H.stride(1), H.stride(2),
        H_final.stride(0), H_final.stride(1),
        NUM_CHUNKS=num_chunks, BLOCK_D=BD,
    )

    _final_scan_kernel[grid_chunkwise](
        X, A, B, Y, H_final,
        L, D,
        X.stride(0), X.stride(1),
        A.stride(0), A.stride(1),
        B.stride(0), B.stride(1),
        Y.stride(0), Y.stride(1),
        H_final.stride(0), H_final.stride(1),
        NUM_CHUNKS=num_chunks, CHUNK_SIZE=chunk, BLOCK_D=BD,
    )
    
    return Y
"""
        return {"code": solution_code}