import torch
import triton
import triton.language as tl

class Solution:
    def solve(self, spec_path: str = None) -> dict:
        code = '''
import torch
import triton
import triton.language as tl

@triton.jit
def _scan_chunk_kernel(X_ptr, A_ptr, B_ptr, Y_ptr, State_ptr,
                       D,
                       START_L,
                       CHUNK: tl.constexpr,
                       BD: tl.constexpr):
    pid = tl.program_id(0)
    d_offsets = pid * BD + tl.arange(0, BD)
    mask = d_offsets < D

    # Base pointers for this chunk (row-major: (L, D))
    base = START_L * D + d_offsets
    px = X_ptr + base
    pa = A_ptr + base
    pb = B_ptr + base
    py = Y_ptr + base

    # Load initial state for this D tile in fp32 for stability
    y_prev = tl.load(State_ptr + d_offsets, mask=mask, other=0.0).to(tl.float32)

    for t in range(CHUNK):
        x = tl.load(px, mask=mask, other=0.0).to(tl.float32)
        a = tl.load(pa, mask=mask, other=0.0).to(tl.float32)
        b = tl.load(pb, mask=mask, other=0.0).to(tl.float32)
        y = a * y_prev + b * x
        tl.store(py, y.to(tl.float16), mask=mask)
        y_prev = y

        px += D
        pa += D
        pb += D
        py += D

    # Store final state for this D tile
    tl.store(State_ptr + d_offsets, y_prev, mask=mask)

def chunk_scan(X: torch.Tensor, A: torch.Tensor, B: torch.Tensor, chunk: int = 128, BD: int = 128) -> torch.Tensor:
    """
    Mamba2 chunked scan computation.
    
    Args:
        X: Input tensor of shape (L, D) - input sequence (float16)
        A: Input tensor of shape (L, D) - decay factors (float16)
        B: Input tensor of shape (L, D) - input weights (float16)
        chunk: Chunk size for parallel processing (default 128)
        BD: Block dimension for feature dimension tiling (default 128)
    
    Returns:
        Output tensor of shape (L, D) - scan output (float16)
    """
    if not (X.is_cuda and A.is_cuda and B.is_cuda):
        raise ValueError("All inputs must be CUDA tensors.")
    if X.dtype != torch.float16 or A.dtype != torch.float16 or B.dtype != torch.float16:
        raise ValueError("All inputs must be float16.")
    if X.ndim != 2 or A.shape != X.shape or B.shape != X.shape:
        raise ValueError("Inputs must have the same shape (L, D).")
    L, D = X.shape
    if L % chunk != 0:
        raise ValueError("L must be divisible by chunk.")
    # Ensure contiguous layout
    if not X.is_contiguous():
        X = X.contiguous()
    if not A.is_contiguous():
        A = A.contiguous()
    if not B.is_contiguous():
        B = B.contiguous()
    Y = torch.empty_like(X)

    # State buffer per feature in fp32 for numerical stability
    state = torch.zeros(D, device=X.device, dtype=torch.float32)

    grid = (triton.cdiv(D, BD),)

    # Heuristic for num_warps
    if BD >= 256:
        num_warps = 8
    elif BD >= 128:
        num_warps = 4
    elif BD >= 64:
        num_warps = 2
    else:
        num_warps = 1

    # Process each chunk sequentially; parallel over feature tiles
    for start in range(0, L, chunk):
        _scan_chunk_kernel[grid](
            X, A, B, Y, state,
            D,
            start,
            CHUNK=chunk,
            BD=BD,
            num_warps=num_warps,
            num_stages=2
        )
    return Y
'''
        return {"code": code}
