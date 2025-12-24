import torch
import triton
import triton.language as tl

_mamba2_scan_code = """
import torch
import triton
import triton.language as tl

@triton.jit
def _intra_chunk_scan_kernel(
    X_ptr, A_ptr, B_ptr, Y_ptr, A_reduced_ptr, Z_reduced_ptr,
    L, D, C,
    stride_x_l, stride_a_l, stride_b_l, stride_y_l,
    stride_ar_c, stride_zr_c,
    BLOCK_SIZE_C: tl.constexpr,
    BLOCK_SIZE_D: tl.constexpr,
):
    pid_c = tl.program_id(0)
    pid_d = tl.program_id(1)

    d_offsets = pid_d * BLOCK_SIZE_D + tl.arange(0, BLOCK_SIZE_D)
    d_mask = d_offsets < D

    c_start = pid_c * BLOCK_SIZE_C
    
    h = tl.zeros((BLOCK_SIZE_D,), dtype=tl.float32)
    a_total = tl.ones((BLOCK_SIZE_D,), dtype=tl.float32)

    for t in range(0, BLOCK_SIZE_C):
        l_idx = c_start + t
        
        a = tl.load(A_ptr + l_idx * stride_a_l + d_offsets, mask=d_mask).to(tl.float32)
        b = tl.load(B_ptr + l_idx * stride_b_l + d_offsets, mask=d_mask).to(tl.float32)
        x = tl.load(X_ptr + l_idx * stride_x_l + d_offsets, mask=d_mask).to(tl.float32)
        
        z = b * x
        h = a * h + z
        
        tl.store(Y_ptr + l_idx * stride_y_l + d_offsets, h.to(tl.float16), mask=d_mask)
        
        a_total = a_total * a
        
    tl.store(A_reduced_ptr + pid_c * stride_ar_c + d_offsets, a_total, mask=d_mask)
    tl.store(Z_reduced_ptr + pid_c * stride_zr_c + d_offsets, h.to(tl.float16), mask=d_mask)


@triton.jit
def _inter_chunk_propagate_kernel(
    Y_ptr, A_ptr, A_reduced_ptr, Z_reduced_ptr,
    L, D, C, num_chunks,
    stride_y_l, stride_a_l,
    stride_ar_c, stride_zr_c,
    BLOCK_SIZE_D: tl.constexpr,
):
    pid_d = tl.program_id(1)
    
    d_offsets = pid_d * BLOCK_SIZE_D + tl.arange(0, BLOCK_SIZE_D)
    d_mask = d_offsets < D
    
    h_carry = tl.zeros((BLOCK_SIZE_D,), dtype=tl.float32)
    
    for c_idx in range(1, num_chunks):
        prev_c_idx = c_idx - 1
        
        a_red_prev = tl.load(A_reduced_ptr + prev_c_idx * stride_ar_c + d_offsets, mask=d_mask)
        z_red_prev = tl.load(Z_reduced_ptr + prev_c_idx * stride_zr_c + d_offsets, mask=d_mask).to(tl.float32)
        
        h_carry = a_red_prev * h_carry + z_red_prev
        
        c_start = c_idx * C
        a_prod_acc = tl.ones((BLOCK_SIZE_D,), dtype=tl.float32)
        
        for t in range(0, C):
            l_idx = c_start + t
            
            y_intra = tl.load(Y_ptr + l_idx * stride_y_l + d_offsets, mask=d_mask).to(tl.float32)
            a_t = tl.load(A_ptr + l_idx * stride_a_l + d_offsets, mask=d_mask).to(tl.float32)
            
            a_prod_acc = a_prod_acc * a_t
            
            y_new = y_intra + a_prod_acc * h_carry
            
            tl.store(Y_ptr + l_idx * stride_y_l + d_offsets, y_new.to(tl.float16), mask=d_mask)

def chunk_scan(X: torch.Tensor, A: torch.Tensor, B: torch.Tensor, chunk: int = 128, BD: int = 128) -> torch.Tensor:
    L, D = X.shape
    num_chunks = L // chunk
    
    Y = torch.empty_like(X)
    
    A_reduced = torch.empty(num_chunks, D, device=X.device, dtype=torch.float32)
    Z_reduced = torch.empty(num_chunks, D, device=X.device, dtype=X.dtype)
    
    grid1 = (num_chunks, triton.cdiv(D, BD))
    
    _intra_chunk_scan_kernel[grid1](
        X, A, B, Y, A_reduced, Z_reduced,
        L, D, chunk,
        X.stride(0), A.stride(0), B.stride(0), Y.stride(0),
        A_reduced.stride(0), Z_reduced.stride(0),
        BLOCK_SIZE_C=chunk,
        BLOCK_SIZE_D=BD,
        num_warps=4,
    )
    
    grid2 = (1, triton.cdiv(D, BD))
    
    _inter_chunk_propagate_kernel[grid2](
        Y, A, A_reduced, Z_reduced,
        L, D, chunk, num_chunks,
        Y.stride(0), A.stride(0),
        A_reduced.stride(0), Z_reduced.stride(0),
        BLOCK_SIZE_D=BD,
        num_warps=4,
    )
    
    return Y
"""

class Solution:
    def solve(self, spec_path: str = None) -> dict:
        """
        Returns a dict with either:
        - {"code": "python_code_string"}
        - {"program_path": "path/to/kernel.py"}
        """
        return {"code": _mamba2_scan_code}
