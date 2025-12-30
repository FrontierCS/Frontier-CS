import torch
import triton
import triton.language as tl

class Solution:
    def solve(self, spec_path: str = None) -> dict:
        code = """
import torch
import triton
import triton.language as tl

@triton.jit
def _forward_intra_scan(
    X, A, B, Y, A_carry, H_carry,
    L, D,
    stride_x_l, stride_x_d,
    stride_a_l, stride_a_d,
    stride_b_l, stride_b_d,
    stride_y_l, stride_y_d,
    stride_ac_c, stride_ac_d,
    stride_hc_c, stride_hc_d,
    CHUNK: tl.constexpr,
    BD: tl.constexpr
):
    pid_chunk = tl.program_id(0)
    pid_d_block = tl.program_id(1)

    d_offsets = pid_d_block * BD + tl.arange(0, BD)
    d_mask = d_offsets < D

    l_base = pid_chunk * CHUNK
    
    X_chunk_ptr = X + l_base * stride_x_l + d_offsets
    A_chunk_ptr = A + l_base * stride_a_l + d_offsets
    B_chunk_ptr = B + l_base * stride_b_l + d_offsets
    Y_chunk_ptr = Y + l_base * stride_y_l + d_offsets

    h = tl.zeros((BD,), dtype=tl.float32)
    a_carry_val = tl.ones((BD,), dtype=tl.float32)
    
    for i in range(CHUNK):
        a = tl.load(A_chunk_ptr + i * stride_a_l, mask=d_mask).to(tl.float32)
        b = tl.load(B_chunk_ptr + i * stride_b_l, mask=d_mask).to(tl.float32)
        x = tl.load(X_chunk_ptr + i * stride_x_l, mask=d_mask).to(tl.float32)

        h = a * h + b * x
        
        tl.store(Y_chunk_ptr + i * stride_y_l, h.to(tl.float16), mask=d_mask)
        
        a_carry_val = a_carry_val * a

    A_carry_chunk_ptr = A_carry + pid_chunk * stride_ac_c + d_offsets
    H_carry_chunk_ptr = H_carry + pid_chunk * stride_hc_c + d_offsets
    
    tl.store(A_carry_chunk_ptr, a_carry_val, mask=d_mask)
    tl.store(H_carry_chunk_ptr, h, mask=d_mask)


@triton.jit
def _forward_inter_scan(
    A_carry, H_carry, H_global,
    D,
    stride_ac_c, stride_ac_d,
    stride_hc_c, stride_hc_d,
    stride_hg_c, stride_hg_d,
    NUM_CHUNKS: tl.constexpr,
    BD: tl.constexpr
):
    pid_d_block = tl.program_id(0)

    d_offsets = pid_d_block * BD + tl.arange(0, BD)
    d_mask = d_offsets < D
    
    A_carry_col_ptr = A_carry + d_offsets
    H_carry_col_ptr = H_carry + d_offsets
    H_global_col_ptr = H_global + d_offsets

    h = tl.zeros((BD,), dtype=tl.float32)

    for i in range(NUM_CHUNKS):
        tl.store(H_global_col_ptr + i * stride_hg_c, h, mask=d_mask)
        
        a_c = tl.load(A_carry_col_ptr + i * stride_ac_c, mask=d_mask)
        h_c = tl.load(H_carry_col_ptr + i * stride_hc_c, mask=d_mask)
        
        h = a_c * h + h_c

@triton.jit
def _forward_final_update(
    Y, A, H_global,
    L, D,
    stride_y_l, stride_y_d,
    stride_a_l, stride_a_d,
    stride_hg_c, stride_hg_d,
    CHUNK: tl.constexpr,
    BD: tl.constexpr
):
    pid_chunk = tl.program_id(0)
    pid_d_block = tl.program_id(1)

    d_offsets = pid_d_block * BD + tl.arange(0, BD)
    d_mask = d_offsets < D

    H_global_chunk_ptr = H_global + pid_chunk * stride_hg_c + d_offsets
    h_init = tl.load(H_global_chunk_ptr, mask=d_mask)

    l_base = pid_chunk * CHUNK
    
    Y_chunk_ptr = Y + l_base * stride_y_l + d_offsets
    A_chunk_ptr = A + l_base * stride_a_l + d_offsets

    delta = h_init
    for i in range(CHUNK):
        y_ptr_i = Y_chunk_ptr + i * stride_y_l
        a_ptr_i = A_chunk_ptr + i * stride_a_l

        y_inter = tl.load(y_ptr_i, mask=d_mask).to(tl.float32)
        a = tl.load(a_ptr_i, mask=d_mask).to(tl.float32)
        
        delta = delta * a
        y_final = y_inter + delta
        
        tl.store(y_ptr_i, y_final.to(tl.float16), mask=d_mask)

def chunk_scan(X: torch.Tensor, A: torch.Tensor, B: torch.Tensor, chunk: int = 128, BD: int = 128) -> torch.Tensor:
    L, D = X.shape
    num_chunks = L // chunk
    
    Y = torch.empty_like(X)
    
    A_carry = torch.empty((num_chunks, D), device=X.device, dtype=torch.float32)
    H_carry = torch.empty((num_chunks, D), device=X.device, dtype=torch.float32)
    H_global = torch.empty((num_chunks, D), device=X.device, dtype=torch.float32)
    
    grid1 = (num_chunks, D // BD)
    _forward_intra_scan[grid1](
        X, A, B, Y, A_carry, H_carry,
        L, D,
        X.stride(0), X.stride(1),
        A.stride(0), A.stride(1),
        B.stride(0), B.stride(1),
        Y.stride(0), Y.stride(1),
        A_carry.stride(0), A_carry.stride(1),
        H_carry.stride(0), H_carry.stride(1),
        CHUNK=chunk, BD=BD
    )

    grid2 = (D // BD,)
    _forward_inter_scan[grid2](
        A_carry, H_carry, H_global,
        D,
        A_carry.stride(0), A_carry.stride(1),
        H_carry.stride(0), H_carry.stride(1),
        H_global.stride(0), H_global.stride(1),
        NUM_CHUNKS=num_chunks, BD=BD
    )

    grid3 = (num_chunks, D // BD)
    _forward_final_update[grid3](
        Y, A, H_global,
        L, D,
        Y.stride(0), Y.stride(1),
        A.stride(0), A.stride(1),
        H_global.stride(0), H_global.stride(1),
        CHUNK=chunk, BD=BD
    )
    
    return Y
"""
        # The split/join logic is to remove the initial newline and trailing whitespace
        return {"code": "\n".join(code.splitlines()[1:])}