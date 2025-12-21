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
    x_ptr, a_ptr, b_ptr, y_ptr, state_ptr,
    start: tl.int32,
    chunk_size: tl.int32,
    BLOCK_D: tl.constexpr,
    D: tl.int32,
    stride_xl: tl.int64,
    stride_xd: tl.int64,
    stride_al: tl.int64,
    stride_ad: tl.int64,
    stride_bl: tl.int64,
    stride_bd: tl.int64,
    stride_yl: tl.int64,
    stride_yd: tl.int64,
    state_stride: tl.int64,
):
    pid = tl.program_id(0)
    block_start = pid * BLOCK_D
    offsets = block_start + tl.arange(0, BLOCK_D)
    mask = offsets < D
    state = tl.load(state_ptr + offsets * state_stride, mask=mask, other=0.0)
    for t in range(chunk_size):
        pos = start + t
        x_off = pos * stride_xl + offsets * stride_xd
        x = tl.load(x_ptr + x_off, mask=mask, other=0.0).to(tl.float32)
        a_off = pos * stride_al + offsets * stride_ad
        a = tl.load(a_ptr + a_off, mask=mask, other=0.0).to(tl.float32)
        b_off = pos * stride_bl + offsets * stride_bd
        b = tl.load(b_ptr + b_off, mask=mask, other=0.0).to(tl.float32)
        state = a * state + b * x
        y_off = pos * stride_yl + offsets * stride_yd
        tl.store(y_ptr + y_off, state.to(tl.float16), mask=mask)

def chunk_scan(X: torch.Tensor, A: torch.Tensor, B: torch.Tensor, chunk: int = 128, BD: int = 128) -> torch.Tensor:
    L, D = X.shape
    Y = torch.empty_like(X)
    state = torch.zeros(D, dtype=torch.float32, device=X.device)
    N = L // chunk
    for i in range(N):
        start = i * chunk
        num_blocks = (D + BD - 1) // BD
        chunk_kernel[num_blocks,](
            X.data_ptr(), A.data_ptr(), B.data_ptr(), Y.data_ptr(), state.data_ptr(),
            start=start,
            chunk_size=chunk,
            BLOCK_D=BD,
            D=D,
            stride_xl=X.stride(0) * X.element_size(),
            stride_xd=X.stride(1) * X.element_size(),
            stride_al=A.stride(0) * A.element_size(),
            stride_ad=A.stride(1) * A.element_size(),
            stride_bl=B.stride(0) * B.element_size(),
            stride_bd=B.stride(1) * B.element_size(),
            stride_yl=Y.stride(0) * Y.element_size(),
            stride_yd=Y.stride(1) * Y.element_size(),
            state_stride=state.stride(0) * state.element_size(),
        )
        state.copy_(Y[start + chunk - 1].float())
    return Y
"""
        return {"code": code}
