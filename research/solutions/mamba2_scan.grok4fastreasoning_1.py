import torch
import triton
import triton.language as tl

class Solution:
    def solve(self, spec_path: str = None) -> dict:
        code = r'''
import torch
import triton
import triton.language as tl

@triton.jit
def mamba_scan_chunk(
    X_ptr, A_ptr, B_ptr, Y_ptr, state_ptr,
    start_idx, D,
    chunk_size: tl.constexpr,
    BD: tl.constexpr
):
    ELEM_BYTES = 2  # float16
    d_stride = ELEM_BYTES
    l_stride = D * ELEM_BYTES

    pid = tl.program_id(0)
    block_start = pid * BD
    offs = tl.arange(0, BD)
    mask = (block_start + offs) < D
    offs_d = block_start + offs

    state_offs = offs_d * d_stride
    current = tl.load(state_ptr + state_offs, mask=mask, other=0.0)

    for tt in range(chunk_size):
        t = start_idx + tt
        row_offs = t * l_stride
        data_offs = row_offs + state_offs
        a = tl.load(A_ptr + data_offs, mask=mask, other=0.0)
        b = tl.load(B_ptr + data_offs, mask=mask, other=0.0)
        x = tl.load(X_ptr + data_offs, mask=mask, other=0.0)
        current = a * current + b * x
        tl.store(Y_ptr + data_offs, current, mask=mask)

    tl.store(state_ptr + state_offs, current, mask=mask)

def chunk_scan(X: torch.Tensor, A: torch.Tensor, B: torch.Tensor, chunk: int = 128, BD: int = 128) -> torch.Tensor:
    L, D_ = X.shape
    assert L % chunk == 0 and L > 0
    y = torch.empty_like(X)
    state = torch.zeros(D_, dtype=X.dtype, device=X.device)
    num_chunks = L // chunk
    for i in range(num_chunks):
        start = i * chunk
        num_blocks = (D_ + BD - 1) // BD
        mamba_scan_chunk[(num_blocks,)](
            X, A, B, y, state,
            start_idx=start,
            D=D_,
            chunk_size=chunk,
            BD=BD,
            num_stages=4,
        )
    return y
'''
        return {"code": code}