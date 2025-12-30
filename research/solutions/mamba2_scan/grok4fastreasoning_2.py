import torch
import triton
import triton.language as tl

class Solution:
    def solve(self, spec_path: str = None) -> dict:
        code = r"""
import torch
import triton
import triton.language as tl

@triton.jit
def chunk_kernel(
    x_ptr, a_ptr, b_ptr, y_ptr, state_ptr,
    start: tl.int32,
    chksz: tl.int32,
    D: tl.int32,
    BLOCK_D: tl.constexpr
):
    pid = tl.program_id(0)
    block_id = pid * BLOCK_D + tl.arange(0, BLOCK_D)
    mask = block_id < D
    y = tl.load(state_ptr + block_id, mask=mask)
    for local_t in range(chksz):
        t = start + local_t
        offset = t * D + block_id
        x_t = tl.load(x_ptr + offset, mask=mask, other=0.0).to(tl.float32)
        a_t = tl.load(a_ptr + offset, mask=mask, other=0.0).to(tl.float32)
        b_t = tl.load(b_ptr + offset, mask=mask, other=0.0).to(tl.float32)
        y = a_t * y + b_t * x_t
        tl.store(y_ptr + offset, y.to(tl.float16), mask=mask)
    tl.store(state_ptr + block_id, y, mask=mask)

def chunk_scan(X: torch.Tensor, A: torch.Tensor, B: torch.Tensor, chunk: int = 128, BD: int = 128) -> torch.Tensor:
    L, D = X.shape
    Y = torch.empty((L, D), dtype=X.dtype, device=X.device)
    state = torch.zeros(D, dtype=torch.float32, device=X.device)
    num_chunks = L // chunk
    grid = lambda: ((D + BD - 1) // BD,)
    for i in range(num_chunks):
        start_t = i * chunk
        chunk_kernel[grid()](X, A, B, Y, state, start_t, chunk, D, BLOCK_D=BD)
    return Y
"""
        return {"code": code}