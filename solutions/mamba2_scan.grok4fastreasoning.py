class Solution:
    def solve(self, spec_path: str = None) -> dict:
        code = """
import torch
import triton
import triton.language as tl

def chunk_scan(X: torch.Tensor, A: torch.Tensor, B: torch.Tensor, chunk: int = 128, BD: int = 128) -> torch.Tensor:
    L, D = X.shape
    y = torch.empty((L, D), dtype=X.dtype, device=X.device)
    state = torch.zeros(D, dtype=X.dtype, device=X.device)
    MAX_BD = 128

    @triton.jit
    def kernel(
        X_ptr, A_ptr, B_ptr, Y_ptr, state_ptr,
        start: tl.int32,
        C: tl.int32,
        L: tl.int32,
        D: tl.int32,
        BD: tl.int32,
        MAX_BD: tl.constexpr
    ):
        pid = tl.program_id(0)
        block_start = pid * BD
        offs = tl.arange(0, MAX_BD)
        mask = offs < BD
        offs_d = block_start + offs
        mask_d = mask & (offs_d < D)

        state = tl.load(state_ptr + offs_d, mask=mask_d, other=0.0)

        for k in range(C):
            t = start + k
            row_start = t * D + block_start
            x = tl.load(X_ptr + row_start + offs, mask=mask_d, other=0.0)
            a = tl.load(A_ptr + row_start + offs, mask=mask_d, other=0.0)
            b = tl.load(B_ptr + row_start + offs, mask=mask_d, other=0.0)
            state = a * state + b * x
            tl.store(Y_ptr + row_start + offs, state, mask=mask_d)

        tl.store(state_ptr + offs_d, state, mask=mask_d)

    grid = lambda meta: (triton.cdiv(D, BD), )

    num_chunks = L // chunk
    for i in range(num_chunks):
        start_pos = i * chunk
        kernel[grid](
            X, A, B, y, state,
            start_pos, chunk, L, D, BD,
            MAX_BD=MAX_BD,
            num_stages=1
        )

    return y
        """
        return {"code": code}
