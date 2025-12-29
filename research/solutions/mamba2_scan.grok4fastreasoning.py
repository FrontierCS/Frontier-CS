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
def chunk_kernel(
    X, A, B, Y, state,
    start: tl.int32,
    stride_l: tl.int32,
    D: tl.int32,
    chunk_size: tl.int32,
    BLOCK_D: tl.constexpr
):
    pid = tl.program_id(0)
    block_start = pid * BLOCK_D
    offsets = block_start + tl.arange(0, BLOCK_D)
    mask = offsets < D
    y_prev = tl.load(state + offsets, mask=mask, other=0.0)
    for t in range(chunk_size):
        offs_t = start + t
        offset = offs_t * stride_l + offsets
        x_slice = tl.load(X + offset, mask=mask, other=0.0)
        a_slice = tl.load(A + offset, mask=mask, other=0.0)
        b_slice = tl.load(B + offset, mask=mask, other=0.0)
        c = b_slice * x_slice
        y_curr = a_slice * y_prev + c
        tl.store(Y + offset, y_curr, mask=mask)
        y_prev = y_curr
    tl.store(state + offsets, y_prev, mask=mask)

def chunk_scan(X: torch.Tensor, A: torch.Tensor, B: torch.Tensor, chunk: int = 128, BD: int = 128) -> torch.Tensor:
    L, D_ = X.shape
    if L % chunk != 0:
        raise ValueError("L must be divisible by chunk")
    Y = torch.empty_like(X)
    state = torch.zeros(D_, dtype=X.dtype, device=X.device)
    N = L // chunk
    stride_l = D_
    for k in range(N):
        start = k * chunk
        n_blocks = (D_ + BD - 1) // BD
        grid = (n_blocks,)
        chunk_kernel[grid](
            X, A, B, Y, state,
            start, stride_l, D_, chunk,
            BLOCK_D=BD,
            num_stages=4
        )
    return Y
"""
        return {"code": code}