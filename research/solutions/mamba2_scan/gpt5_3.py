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
def _chunk_summary_kernel(X_ptr, A_ptr, B_ptr, P_ptr, S_ptr, 
                          L, D, stride_xL, stride_xD, stride_aL, stride_aD, stride_bL, stride_bD,
                          stride_pL, stride_pD, stride_sL, stride_sD,
                          CHUNK: tl.constexpr, BD: tl.constexpr):
    pid_c = tl.program_id(0)
    pid_d = tl.program_id(1)
    offs_d = pid_d * BD + tl.arange(0, BD)
    mask_d = offs_d < D
    start = pid_c * CHUNK
    P = tl.full([BD], 1.0, dtype=tl.float32)
    S = tl.zeros([BD], dtype=tl.float32)
    for i in range(CHUNK):
        row = start + i
        a = tl.load(A_ptr + row * stride_aL + offs_d * stride_aD, mask=mask_d, other=0.).to(tl.float32)
        b = tl.load(B_ptr + row * stride_bL + offs_d * stride_bD, mask=mask_d, other=0.).to(tl.float32)
        x = tl.load(X_ptr + row * stride_xL + offs_d * stride_xD, mask=mask_d, other=0.).to(tl.float32)
        S = a * S + b * x
        P = P * a
    tl.store(P_ptr + pid_c * stride_pL + offs_d * stride_pD, P, mask=mask_d)
    tl.store(S_ptr + pid_c * stride_sL + offs_d * stride_sD, S, mask=mask_d)

@triton.jit
def _chunk_prefix_kernel(P_ptr, S_ptr, Yinit_ptr, D, stride_pL, stride_pD, stride_sL, stride_sD, stride_yL, stride_yD,
                         NUM_CHUNKS: tl.constexpr, BD: tl.constexpr):
    pid_d = tl.program_id(0)
    offs_d = pid_d * BD + tl.arange(0, BD)
    mask_d = offs_d < D
    y = tl.zeros([BD], dtype=tl.float32)
    for c in range(NUM_CHUNKS):
        tl.store(Yinit_ptr + c * stride_yL + offs_d * stride_yD, y, mask=mask_d)
        p = tl.load(P_ptr + c * stride_pL + offs_d * stride_pD, mask=mask_d, other=1.).to(tl.float32)
        s = tl.load(S_ptr + c * stride_sL + offs_d * stride_sD, mask=mask_d, other=0.).to(tl.float32)
        y = p * y + s

@triton.jit
def _chunk_apply_kernel(X_ptr, A_ptr, B_ptr, Y_ptr, Yinit_ptr, 
                        L, D,
                        stride_xL, stride_xD, stride_aL, stride_aD, stride_bL, stride_bD,
                        stride_yL, stride_yD, stride_yiL, stride_yiD,
                        CHUNK: tl.constexpr, BD: tl.constexpr):
    pid_c = tl.program_id(0)
    pid_d = tl.program_id(1)
    offs_d = pid_d * BD + tl.arange(0, BD)
    mask_d = offs_d < D
    start = pid_c * CHUNK
    y = tl.load(Yinit_ptr + pid_c * stride_yiL + offs_d * stride_yiD, mask=mask_d, other=0.).to(tl.float32)
    for i in range(CHUNK):
        row = start + i
        a = tl.load(A_ptr + row * stride_aL + offs_d * stride_aD, mask=mask_d, other=0.).to(tl.float32)
        b = tl.load(B_ptr + row * stride_bL + offs_d * stride_bD, mask=mask_d, other=0.).to(tl.float32)
        x = tl.load(X_ptr + row * stride_xL + offs_d * stride_xD, mask=mask_d, other=0.).to(tl.float32)
        y = a * y + b * x
        tl.store(Y_ptr + row * stride_yL + offs_d * stride_yD, y.to(tl.float16), mask=mask_d)

def chunk_scan(X: torch.Tensor, A: torch.Tensor, B: torch.Tensor, chunk: int = 128, BD: int = 128) -> torch.Tensor:
    if X.device.type != "cuda":
        raise RuntimeError("X must be on CUDA")
    if not (X.is_contiguous() and A.is_contiguous() and B.is_contiguous()):
        X = X.contiguous()
        A = A.contiguous()
        B = B.contiguous()
    assert X.dtype == torch.float16 and A.dtype == torch.float16 and B.dtype == torch.float16
    L, D = X.shape
    assert A.shape == (L, D) and B.shape == (L, D)
    assert L % chunk == 0, "L must be divisible by chunk"
    C = L // chunk
    Y = torch.empty((L, D), device=X.device, dtype=torch.float16)
    # Allocate chunk summaries and initial states in fp32 for stability
    P_chunks = torch.empty((C, D), device=X.device, dtype=torch.float32)
    S_chunks = torch.empty((C, D), device=X.device, dtype=torch.float32)
    Y_init = torch.empty((C, D), device=X.device, dtype=torch.float32)
    grid_summary = (C, triton.cdiv(D, BD))
    _chunk_summary_kernel[grid_summary](
        X, A, B, P_chunks, S_chunks,
        L, D,
        X.stride(0), X.stride(1), A.stride(0), A.stride(1), B.stride(0), B.stride(1),
        P_chunks.stride(0), P_chunks.stride(1),
        S_chunks.stride(0), S_chunks.stride(1),
        CHUNK=chunk, BD=BD, num_warps=4, num_stages=2
    )
    grid_prefix = (triton.cdiv(D, BD),)
    _chunk_prefix_kernel[grid_prefix](
        P_chunks, S_chunks, Y_init, D,
        P_chunks.stride(0), P_chunks.stride(1),
        S_chunks.stride(0), S_chunks.stride(1),
        Y_init.stride(0), Y_init.stride(1),
        NUM_CHUNKS=C, BD=BD, num_warps=4, num_stages=2
    )
    grid_apply = (C, triton.cdiv(D, BD))
    _chunk_apply_kernel[grid_apply](
        X, A, B, Y, Y_init,
        L, D,
        X.stride(0), X.stride(1), A.stride(0), A.stride(1), B.stride(0), B.stride(1),
        Y.stride(0), Y.stride(1), Y_init.stride(0), Y_init.stride(1),
        CHUNK=chunk, BD=BD, num_warps=4, num_stages=2
    )
    return Y
'''
        return {"code": code}