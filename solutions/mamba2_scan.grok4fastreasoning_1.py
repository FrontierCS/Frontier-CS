class Solution:
    def solve(self, spec_path: str = None) -> dict:
        code = """
import torch
import triton
import triton.language as tl

@triton.autotune(
    configs=[
        triton.Config({'BLOCK': 64}),
        triton.Config({'BLOCK': 128}),
        triton.Config({'BLOCK': 256}),
        triton.Config({'BLOCK': 512}),
    ],
    key=['D'],
)
@triton.jit
def scan_chunk_kernel(
    x_ptr, a_ptr, b_ptr, y_ptr, state_ptr,
    chunk_size: tl.int32,
    D: tl.int32,
    BLOCK: tl.constexpr
):
    pid = tl.program_id(0)
    d_start = pid * BLOCK
    offsets = tl.arange(0, BLOCK)
    mask_d = d_start + offsets < D
    state = tl.load(state_ptr + d_start + offsets, mask=mask_d, other=tl.float16(0.0))
    x_block = tl.make_block_ptr(
        base=x_ptr,
        shape=(chunk_size, D),
        strides=(D, 1),
        offset=(0, 0),
        block_shape=(1, BLOCK),
        order=(0, 1)
    )
    a_block = tl.make_block_ptr(
        base=a_ptr,
        shape=(chunk_size, D),
        strides=(D, 1),
        offset=(0, 0),
        block_shape=(1, BLOCK),
        order=(0, 1)
    )
    b_block = tl.make_block_ptr(
        base=b_ptr,
        shape=(chunk_size, D),
        strides=(D, 1),
        offset=(0, 0),
        block_shape=(1, BLOCK),
        order=(0, 1)
    )
    y_block = tl.make_block_ptr(
        base=y_ptr,
        shape=(chunk_size, D),
        strides=(D, 1),
        offset=(0, 0),
        block_shape=(1, BLOCK),
        order=(0, 1)
    )
    for k in range(chunk_size):
        x_ptrs = x_block + (k, 0)
        a_ptrs = a_block + (k, 0)
        b_ptrs = b_block + (k, 0)
        y_ptrs = y_block + (k, 0)
        x_k = tl.load(x_ptrs, mask=mask_d[None, :], other=tl.float16(0.0))
        a_k = tl.load(a_ptrs, mask=mask_d[None, :], other=tl.float16(0.0))
        b_k = tl.load(b_ptrs, mask=mask_d[None, :], other=tl.float16(0.0))
        y_new = a_k * state + b_k * x_k
        tl.store(y_ptrs, y_new, mask=mask_d[None, :])
        state = y_new
    tl.store(state_ptr + d_start + offsets, state, mask=mask_d)

def chunk_scan(X: torch.Tensor, A: torch.Tensor, B: torch.Tensor, chunk: int = 128, BD: int = 128) -> torch.Tensor:
    L, D = X.shape
    if L % chunk != 0:
        raise ValueError("L must be divisible by chunk")
    output = torch.empty_like(X)
    state = torch.zeros(D, dtype=X.dtype, device=X.device)
    num_chunks = L // chunk
    for i in range(num_chunks):
        start = i * chunk
        x_c = X[start:start + chunk]
        a_c = A[start:start + chunk]
        b_c = B[start:start + chunk]
        y_c = output[start:start + chunk]
        grid = lambda meta: (triton.cdiv(D, meta['BLOCK']), )
        scan_chunk_kernel[grid](x_c, a_c, b_c, y_c, state, chunk, D)
    return output
"""
        return {"code": code}
