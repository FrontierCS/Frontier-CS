class Solution:
    def solve(self, spec_path: str = None) -> dict:
        code = r'''
import torch
import triton
import triton.language as tl

configs = [
    triton.Config({"BLOCK_M": 128, "BLOCK_N": 128, "BLOCK_K": 64}, num_warps=8, num_stages=4),
    triton.Config({"BLOCK_M": 64, "BLOCK_N": 128, "BLOCK_K": 128}, num_warps=4, num_stages=3),
    triton.Config({"BLOCK_M": 128, "BLOCK_N": 64, "BLOCK_K": 128}, num_warps=8, num_stages=4),
]

@triton.autotune(
    configs=configs,
    key=["M", "N", "K"],
)
@triton.jit
def kernel(
    X_PTR,
    W_PTR,
    B_PTR,
    O_PTR,
    M: tl.int32,
    N: tl.int32,
    K: tl.int32,
    stride_xm: tl.int32,
    stride_xk: tl.int32,
    stride_wk: tl.int32,
    stride_wn: tl.int32,
    stride_b: tl.int32,
    stride_om: tl.int32,
    stride_on: tl.int32,
    BLOCK_M: tl.constexpr,
    BLOCK_N: tl.constexpr,
    BLOCK_K: tl.constexpr,
):
    pid_m = tl.program_id(0)
    pid_n = tl.program_id(1)
    offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
    offs_n = pid_n * BLOCK_N + tl.arange(0, BLOCK_N)
    acc = tl.zeros((BLOCK_M, BLOCK_N), dtype=tl.float32)
    for start_k in range(0, K, BLOCK_K):
        offs_k = start_k + tl.arange(0, BLOCK_K)
        x_ptrs = X_PTR + offs_m[:, None] * stride_xm + offs_k[None, :] * stride_xk
        x_mask = (offs_m[:, None] < M) & (offs_k[None, :] < K)
        x = tl.load(x_ptrs, mask=x_mask, other=0.0).to(tl.float32)
        w_ptrs = W_PTR + offs_k[:, None] * stride_wk + offs_n[None, :] * stride_wn
        w_mask = (offs_k[:, None] < K) & (offs_n[None, :] < N)
        w = tl.load(w_ptrs, mask=w_mask, other=0.0).to(tl.float32)
        acc += tl.dot(x, w)
    b_ptrs = B_PTR + offs_n * stride_b
    b_mask = offs_n < N
    b = tl.load(b_ptrs, mask=b_mask, other=0.0)
    acc += b[None, :]
    scale = 0.7071067811865476
    erf = tl.extra.cuda.libdevice.erf(acc * scale)
    gelu = acc * 0.5 * (1.0 + erf)
    o = gelu.to(tl.float16)
    o_ptrs = O_PTR + offs_m[:, None] * stride_om + offs_n[None, :] * stride_on
    o_mask = (offs_m[:, None] < M) & (offs_n[None, :] < N)
    tl.store(o_ptrs, o, mask=o_mask)

def linear_gelu(X: torch.Tensor, W: torch.Tensor, B: torch.Tensor) -> torch.Tensor:
    M, K = X.shape
    _, N = W.shape
    output = torch.empty((M, N), dtype=torch.float16, device=X.device)
    def grid(meta):
        return (
            triton.cdiv(M, meta["BLOCK_M"]),
            triton.cdiv(N, meta["BLOCK_N"]),
        )
    kernel[grid](
        X,
        W,
        B,
        output,
        M,
        N,
        K,
        X.stride(0),
        X.stride(1),
        W.stride(0),
        W.stride(1),
        B.stride(0),
        output.stride(0),
        output.stride(1),
    )
    return output
        '''
        return {"code": code}