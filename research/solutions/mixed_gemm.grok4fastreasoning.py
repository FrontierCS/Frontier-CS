class Solution:
    def solve(self, spec_path: str = None) -> dict:
        code = """
import torch
import triton
import triton.language as tl

@triton.autotune(
    configs=[
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 128, 'BLOCK_K': 64, 'num_stages': 4}, num_warps=8),
        triton.Config({'BLOCK_M': 64, 'BLOCK_N': 64, 'BLOCK_K': 128, 'num_stages': 4}, num_warps=4),
        triton.Config({'BLOCK_M': 256, 'BLOCK_N': 128, 'BLOCK_K': 64, 'num_stages': 4}, num_warps=8),
    ],
    key=['M', 'N', 'K'],
)
@triton.jit
def fused_linear_gelu_kernel(
    X_ptr, W_ptr, B_ptr, Y_ptr,
    M, N, K,
    stride_xm, stride_xk,
    stride_wk, stride_wn,
    stride_b,
    stride_ym, stride_yn,
    BLOCK_M: tl.constexpr,
    BLOCK_N: tl.constexpr,
    BLOCK_K: tl.constexpr,
    num_stages: tl.constexpr,
):
    pid_m = tl.program_id(0)
    pid_n = tl.program_id(1)

    offs_am = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
    offs_an = pid_n * BLOCK_N + tl.arange(0, BLOCK_N)
    offs_k = tl.arange(0, BLOCK_K)

    acc = tl.zeros((BLOCK_M, BLOCK_N), dtype=tl.float32)

    for start_k in range(0, K, BLOCK_K):
        offs_k_cur = start_k + offs_k

        x_ptrs = X_ptr + (offs_am[:, None] * stride_xm + offs_k_cur[None, :] * stride_xk)
        x_mask = (offs_am[:, None] < M) & (offs_k_cur[None, :] < K)
        x = tl.load(x_ptrs, mask=x_mask, other=0.0, num_stages=num_stages).to(tl.float32)

        w_ptrs = W_ptr + (offs_k_cur[:, None] * stride_wk + offs_an[None, :] * stride_wn)
        w_mask = (offs_k_cur[:, None] < K) & (offs_an[None, :] < N)
        w = tl.load(w_ptrs, mask=w_mask, other=0.0, num_stages=num_stages).to(tl.float32)

        acc += tl.dot(x, w)

    b_ptrs = B_ptr + offs_an * stride_b
    b_mask = offs_an < N
    b = tl.load(b_ptrs, mask=b_mask, other=0.0)

    row_mask = offs_am < M
    bias_tile = tl.where(row_mask[:, None], b[None, :], 0.0)
    acc += bias_tile

    scale = 0.7071067811865476
    arg = acc * scale
    erf_val = tl.libdevice.erf(arg)
    gelu = acc * 0.5 * (1.0 + erf_val)
    y = gelu.to(tl.float16)

    y_ptrs = Y_ptr + (offs_am[:, None] * stride_ym + offs_an[None, :] * stride_yn)
    y_mask = (offs_am[:, None] < M) & (offs_an[None, :] < N)
    tl.store(y_ptrs, y, mask=y_mask)

def linear_gelu(X: torch.Tensor, W: torch.Tensor, B: torch.Tensor) -> torch.Tensor:
    M, K = X.shape
    N = W.shape[1]
    Y = torch.empty((M, N), dtype=torch.float16, device=X.device)
    grid = lambda meta: (
        triton.cdiv(M, meta['BLOCK_M']),
        triton.cdiv(N, meta['BLOCK_N']),
    )
    fused_linear_gelu_kernel[grid](
        X, W, B, Y,
        M, N, K,
        stride_xm=X.stride(0),
        stride_xk=X.stride(1),
        stride_wk=W.stride(0),
        stride_wn=W.stride(1),
        stride_b=B.stride(0),
        stride_ym=Y.stride(0),
        stride_yn=Y.stride(1),
    )
    return Y
"""
        return {"code": code}
