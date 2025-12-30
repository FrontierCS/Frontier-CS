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
def chunk_scan_kernel(
    x_ptr,
    a_ptr,
    b_ptr,
    y_ptr,
    state_ptr,
    stride_l,
    stride_d,
    stride_state,
    start,
    CHUNK,
    BD,
    D,
    BLOCK: tl.constexpr = 256,
):
    pid = tl.program_id(0)
    block_start = pid * BD
    offs = tl.arange(0, BLOCK)
    mask = (offs < BD) & (block_start + offs < D)
    state_offsets = state_ptr + (block_start + offs) * stride_state
    state = tl.load(state_offsets, mask=mask, other=0.0)
    k = 0
    while k < CHUNK:
        t = start + k
        t_offset = t * stride_l
        d_base = block_start * stride_d
        input_offsets = x_ptr + t_offset + d_base + offs * stride_d
        a_offsets = a_ptr + t_offset + d_base + offs * stride_d
        b_offsets = b_ptr + t_offset + d_base + offs * stride_d
        y_offsets = y_ptr + t_offset + d_base + offs * stride_d
        x_k = tl.load(input_offsets, mask=mask, other=0.0)
        a_k = tl.load(a_offsets, mask=mask, other=0.0)
        b_k = tl.load(b_offsets, mask=mask, other=0.0)
        y_k = a_k * state + b_k * x_k
        tl.store(y_offsets, y_k, mask=mask)
        state = y_k
        k += 1
    tl.store(state_offsets, state, mask=mask)


def chunk_scan(X: torch.Tensor, A: torch.Tensor, B: torch.Tensor, chunk: int = 128, BD: int = 128) -> torch.Tensor:
    L, D_ = X.shape
    y = torch.empty_like(X)
    state = torch.zeros(D_, dtype=X.dtype, device=X.device)
    stride_l = X.stride(0)
    stride_d = X.stride(1)
    stride_state = state.stride(0)
    num_blocks = (D_ + BD - 1) // BD
    for i in range(0, L, chunk):
        chunk_scan_kernel[num_blocks](
            X,
            A,
            B,
            y,
            state,
            stride_l,
            stride_d,
            stride_state,
            start=i,
            CHUNK=chunk,
            BD=BD,
            D=D_,
            BLOCK=256,
        )
    return y
"""
        return {"code": code}