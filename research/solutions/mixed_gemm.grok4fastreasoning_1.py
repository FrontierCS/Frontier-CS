import torch
import triton
import triton.language as tl

class Solution:
    def solve(self, spec_path: str = None) -> dict:
        code = """
import torch
import triton
import triton.language as tl

def linear_gelu(X: torch.Tensor, W: torch.Tensor, B: torch.Tensor) -> torch.Tensor:
    M, K = X.shape
    _, N = W.shape
    Y = torch.empty((M, N), dtype=torch.float16, device=X.device, memory_format=torch.contiguous_format)

    @triton.autotune(
        configs=[
            triton.Config({'BLOCK_M': 128, 'BLOCK_N': 128, 'BLOCK_K': 64}),
            triton.Config({'BLOCK_M': 64, 'BLOCK_N': 128, 'BLOCK_K': 64}),
            triton.Config({'BLOCK_M': 128, 'BLOCK_N': 64, 'BLOCK_K': 64}),
            triton.Config({'BLOCK_M': 128, 'BLOCK_N': 256, 'BLOCK_K': 64}),
        ],
        key=['M', 'N', 'K'],
    )
    @triton.jit
    def kernel(
        X_ptr, W_ptr, B_ptr, Y_ptr,
        M, N, K,
        stride_xm, stride_xk,
        stride_wk, stride_wn,
        stride_b,
        stride_ym, stride_yn,
        BLOCK_M: tl.constexpr,
        BLOCK_N: tl.constexpr,
        BLOCK_K: tl.constexpr,
    ):
        num_blocks_n = (N + BLOCK_N - 1) // BLOCK_N
        pid = tl.program_id(0)
        block_m = pid // num_blocks_n
        block_n = pid % num_blocks_n
        offs_m = block_m * BLOCK_M + tl.arange(0, BLOCK_M)
        offs_n = block_n * BLOCK_N + tl.arange(0, BLOCK_N)
        acc = tl.zeros((BLOCK_M, BLOCK_N), dtype=tl.float32)
        b_ptrs = B_ptr + offs_n * stride_b
        b_mask = offs_n < N
        b = tl.load(b_ptrs, mask=b_mask, other=0.0)
        lo = 0
        while lo < K:
            offs_k = lo + tl.arange(0, BLOCK_K)
            k_mask = offs_k < K
            x_ptrs = X_ptr + offs_m[:, None] * stride_xm + offs_k[None, :] * stride_xk
            x_mask = (offs_m[:, None] < M) & (k_mask[None, :])
            x = tl.load(x_ptrs, mask=x_mask, other=0.0).to(tl.float32)
            w_ptrs = W_ptr + offs_k[:, None] * stride_wk + offs_n[None, :] * stride_wn
            w_mask = (k_mask[:, None]) & (offs_n[None, :] < N)
            w = tl.load(w_ptrs, mask=w_mask, other=0.0, eviction_policy='evict_last').to(tl.float32)
            acc += tl.dot(x, w)
            lo += BLOCK_K
        acc += b[None, :]
        scale = 0.7071067811865476
        gelu = acc * 0.5 * (1.0 + tl.libdevice.erf(acc * scale))
        y = gelu.to(tl.float16)
        y_ptrs = Y_ptr + offs_m[:, None] * stride_ym + offs_n[None, :] * stride_yn
        y_mask = (offs_m[:, None] < M) & (offs_n[None, :] < N)
        tl.store(y_ptrs, y, mask=y_mask)

    grid = lambda meta: (triton.cdiv(M, meta['BLOCK_M']) * triton.cdiv(N, meta['BLOCK_N']), )
    kernel[grid](
        X, W, B, Y,
        M, N, K,
        X.stride(0), X.stride(1),
        W.stride(0), W.stride(1),
        B.stride(0),
        Y.stride(0), Y.stride(1),
    )
    return Y
"""
        return {"code": code}
