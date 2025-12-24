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
def scan_op(elem1, elem2):
    a1, y1 = elem1
    a2, y2 = elem2
    return a2 * a1, a2 * y1 + y2

@triton.jit
def _mamba_scan_kernel(
    X, A, B, Y,
    L, D,
    stride_Xl, stride_Xd,
    stride_Al, stride_Ad,
    stride_Bl, stride_Bd,
    stride_Yl, stride_Yd,
    chunk: tl.constexpr,
    BD: tl.constexpr,
):
    pid_d = tl.program_id(0)
    num_chunks = L // chunk

    d_offsets = pid_d * BD + tl.arange(0, BD)
    d_mask = d_offsets < D

    X_ptr = X + d_offsets
    A_ptr = A + d_offsets
    B_ptr = B + d_offsets
    Y_ptr = Y + d_offsets

    h = tl.zeros((BD,), dtype=tl.float32)

    for i in range(num_chunks):
        l_offsets = i * chunk + tl.arange(0, chunk)

        X_chunk_ptr = X_ptr + l_offsets[:, None] * stride_Xl
        A_chunk_ptr = A_ptr + l_offsets[:, None] * stride_Al
        B_chunk_ptr = B_ptr + l_offsets[:, None] * stride_Bl
        Y_chunk_ptr = Y_ptr + l_offsets[:, None] * stride_Yl

        x = tl.load(X_chunk_ptr, mask=d_mask[None, :], other=0.0)
        a = tl.load(A_chunk_ptr, mask=d_mask[None, :], other=0.0)
        b = tl.load(B_chunk_ptr, mask=d_mask[None, :], other=0.0)
        
        a_fp32 = a.to(tl.float32)
        b_fp32 = b.to(tl.float32)
        x_fp32 = x.to(tl.float32)
        c_fp32 = b_fp32 * x_fp32

        a_scan, y_scan = tl.associative_scan((a_fp32, c_fp32), axis=0, op=scan_op)

        y_corrected = y_scan + a_scan * h[None, :]

        tl.store(Y_chunk_ptr, y_corrected.to(tl.float16), mask=d_mask[None, :])

        mask_last = (tl.arange(0, chunk) == chunk - 1)
        a_total_chunk = tl.sum(a_scan * mask_last[:, None], axis=0)
        y_total_chunk = tl.sum(y_scan * mask_last[:, None], axis=0)
        
        h = y_total_chunk + a_total_chunk * h

def chunk_scan(X: torch.Tensor, A: torch.Tensor, B: torch.Tensor, chunk: int = 128, BD: int = 128) -> torch.Tensor:
    L, D = X.shape
    if L % chunk != 0:
        raise ValueError("Sequence length L must be divisible by chunk size.")
    
    Y = torch.empty_like(X, dtype=torch.float16)
    
    grid = (triton.cdiv(D, BD),)
    
    _mamba_scan_kernel[grid](
        X, A, B, Y,
        L, D,
        X.stride(0), X.stride(1),
        A.stride(0), A.stride(1),
        B.stride(0), B.stride(1),
        Y.stride(0), Y.stride(1),
        chunk=chunk,
        BD=BD,
        num_warps=4,
        num_stages=4,
    )
    return Y
"""
        return {"code": code}
