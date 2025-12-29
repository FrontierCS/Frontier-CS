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
    X_PTR, A_PTR, B_PTR, Y_PTR, STATE_PTR,
    STRIDE_L, STRIDE_D,
    START_T, CHUNK_SIZE, DIM_D,
    BLOCK_D: tl.constexpr
):
    pid = tl.program_id(0)
    block_start = pid * BLOCK_D
    offsets_d = block_start + tl.arange(0, BLOCK_D)
    mask = offsets_d < DIM_D
    
    state_offsets = STATE_PTR + offsets_d
    acc = tl.load(state_offsets, mask=mask, other=0.0)
    
    for k in range(CHUNK_SIZE):
        t = START_T + k
        x_offsets = X_PTR + t * STRIDE_L + offsets_d * STRIDE_D
        x = tl.load(x_offsets, mask=mask, other=0.0).to(tl.float32)
        a_offsets = A_PTR + t * STRIDE_L + offsets_d * STRIDE_D
        a = tl.load(a_offsets, mask=mask, other=0.0).to(tl.float32)
        b_offsets = B_PTR + t * STRIDE_L + offsets_d * STRIDE_D
        b = tl.load(b_offsets, mask=mask, other=0.0).to(tl.float32)
        acc = a * acc + b * x
        y_offsets = Y_PTR + t * STRIDE_L + offsets_d * STRIDE_D
        tl.store(y_offsets, acc.to(tl.float16), mask=mask)
    
    tl.store(state_offsets, acc, mask=mask)

def chunk_scan(X: torch.Tensor, A: torch.Tensor, B: torch.Tensor, chunk: int = 128, BD: int = 128) -> torch.Tensor:
    L, D = X.shape
    assert L % chunk == 0
    y = torch.empty_like(X)
    state = torch.zeros(D, dtype=torch.float32, device=X.device)
    stride_l = X.stride(0)
    stride_d = X.stride(1)
    # Assume all tensors are contiguous with matching strides
    grid = lambda meta: (triton.cdiv(D, meta['BD']),)
    
    @triton.jit
    def kernel_wrapper(
        X_PTR, A_PTR, B_PTR, Y_PTR, STATE_PTR,
        STRIDE_L, STRIDE_D,
        START_T, CHUNK_SIZE, DIM_D,
        BLOCK_D: tl.constexpr = 128
    ):
        chunk_kernel(X_PTR, A_PTR, B_PTR, Y_PTR, STATE_PTR,
                     STRIDE_L, STRIDE_D,
                     START_T, CHUNK_SIZE, DIM_D,
                     BLOCK_D=BLOCK_D)
    
    for i in range(0, L, chunk):
        kernel_wrapper[grid](X.data_ptr(), A.data_ptr(), B.data_ptr(), y.data_ptr(), state.data_ptr(),
                             stride_l, stride_d, i, chunk, D, BLOCK_D=128)
    return y
"""
        return {"code": code}