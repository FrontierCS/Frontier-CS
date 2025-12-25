import torch
import triton
import triton.language as tl

class Solution:
    def solve(self, spec_path: str = None) -> dict:
        code = """
import torch
import triton
import triton.language as tl

def chunk_scan(X: torch.Tensor, A: torch.Tensor, B: torch.Tensor, chunk: int = 128, BD: int = 128) -> torch.Tensor:
    L, D = X.shape
    if L % chunk != 0:
        raise ValueError("L must be divisible by chunk")
    Y = torch.empty((L, D), dtype=X.dtype, device=X.device)
    num_chunks = L // chunk
    num_tiles = (D + BD - 1) // BD
    grid = (num_tiles,)
    state = torch.zeros(D, dtype=torch.float32, device=X.device)
    stride_l = X.stride(0) * X.element_size()
    stride_d = X.stride(1) * X.element_size()
    stride_sd = state.element_size()

    @triton.jit
    def chunk_scan_kernel(
        X_PTR,
        A_PTR,
        B_PTR,
        Y_PTR,
        STATE_PTR,
        chunk_start: int,
        D: int,
        stride_xl: int,
        stride_xd: int,
        stride_al: int,
        stride_ad: int,
        stride_bl: int,
        stride_bd: int,
        stride_yl: int,
        stride_yd: int,
        stride_sd: int,
        BD: tl.constexpr,
        chunk_size: tl.constexpr,
    ):
        pid = tl.program_id(0)
        d_start = pid * BD
        offsets_d = d_start + tl.arange(0, BD)
        mask = offsets_d < D
        off_state = offsets_d * stride_sd
        y_prev = tl.load(STATE_PTR + off_state, mask=mask, other=0.0)
        for step in range(0, chunk_size):
            t = chunk_start + step
            off_x = t * stride_xl + offsets_d * stride_xd
            off_a = t * stride_al + offsets_d * stride_ad
            off_b = t * stride_bl + offsets_d * stride_bd
            off_y = t * stride_yl + offsets_d * stride_yd
            x = tl.load(X_PTR + off_x, mask=mask, other=0.0).to(tl.float32)
            a = tl.load(A_PTR + off_a, mask=mask, other=0.0).to(tl.float32)
            b = tl.load(B_PTR + off_b, mask=mask, other=0.0).to(tl.float32)
            y_curr = a * y_prev + b * x
            tl.store(Y_PTR + off_y, y_curr.to(tl.float16), mask=mask)
            y_prev = y_curr
        tl.store(STATE_PTR + off_state, y_prev, mask=mask)

    for c in range(num_chunks):
        chunk_start = c * chunk
        chunk_scan_kernel[grid](
            X,
            A,
            B,
            Y,
            state,
            chunk_start=chunk_start,
            D=D,
            stride_xl=stride_l,
            stride_xd=stride_d,
            stride_al=stride_l,
            stride_ad=stride_d,
            stride_bl=stride_l,
            stride_bd=stride_d,
            stride_yl=stride_l,
            stride_yd=stride_d,
            stride_sd=stride_sd,
            BD=BD,
            chunk_size=chunk,
        )
    return Y
"""
        return {"code": code}
