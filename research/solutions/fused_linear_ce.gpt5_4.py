import torch
import triton
import triton.language as tl


class Solution:
    def solve(self, spec_path: str = None) -> dict:
        code = r'''
import torch
import triton
import triton.language as tl


@triton.autotune(
    configs=[
        triton.Config({'BLOCK_M': 32, 'BLOCK_N': 128, 'BLOCK_K': 32}, num_warps=4, num_stages=2),
        triton.Config({'BLOCK_M': 64, 'BLOCK_N': 128, 'BLOCK_K': 32}, num_warps=8, num_stages=2),
        triton.Config({'BLOCK_M': 64, 'BLOCK_N': 64,  'BLOCK_K': 32}, num_warps=4, num_stages=2),
        triton.Config({'BLOCK_M': 128,'BLOCK_N': 128, 'BLOCK_K': 32}, num_warps=8, num_stages=3),
        triton.Config({'BLOCK_M': 64, 'BLOCK_N': 256, 'BLOCK_K': 32}, num_warps=8, num_stages=3),
    ],
    key=['M', 'N', 'K']
)
@triton.jit
def _fused_linear_ce_kernel(
    X_ptr, W_ptr, B_ptr, T_ptr, Out_ptr,
    M: tl.int32, N: tl.int32, K: tl.int32,
    stride_xm: tl.int32, stride_xk: tl.int32,
    stride_wk: tl.int32, stride_wn: tl.int32,
    BLOCK_M: tl.constexpr, BLOCK_N: tl.constexpr, BLOCK_K: tl.constexpr,
):
    pid_m = tl.program_id(axis=0)
    offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
    m_mask = offs_m < M

    # Pass 1: compute row-wise max over logits
    row_max = tl.full((BLOCK_M,), -float('inf'), dtype=tl.float32)

    n = 0
    while n < N:
        offs_n = n + tl.arange(0, BLOCK_N)
        acc = tl.zeros((BLOCK_M, BLOCK_N), dtype=tl.float32)

        k = 0
        while k < K:
            offs_k = k + tl.arange(0, BLOCK_K)

            x_ptrs = X_ptr + (offs_m[:, None] * stride_xm + offs_k[None, :] * stride_xk)
            w_ptrs = W_ptr + (offs_k[:, None] * stride_wk + offs_n[None, :] * stride_wn)

            x_mask = (m_mask[:, None]) & (offs_k[None, :] < K)
            w_mask = (offs_k[:, None] < K) & (offs_n[None, :] < N)

            x = tl.load(x_ptrs, mask=x_mask, other=0.0)
            w = tl.load(w_ptrs, mask=w_mask, other=0.0)

            acc += tl.dot(x, w)
            k += BLOCK_K

        b = tl.load(B_ptr + offs_n, mask=offs_n < N, other=0.0)
        acc += b[None, :]

        tile_row_max = tl.max(acc, axis=1)
        row_max = tl.maximum(row_max, tile_row_max)

        n += BLOCK_N

    # Pass 2: compute sumexp and gather target logits
    sumexp = tl.zeros((BLOCK_M,), dtype=tl.float32)
    tgt_logit = tl.zeros((BLOCK_M,), dtype=tl.float32)

    t = tl.load(T_ptr + offs_m, mask=m_mask, other=0).to(tl.int32)

    n = 0
    while n < N:
        offs_n = n + tl.arange(0, BLOCK_N)
        acc = tl.zeros((BLOCK_M, BLOCK_N), dtype=tl.float32)

        k = 0
        while k < K:
            offs_k = k + tl.arange(0, BLOCK_K)

            x_ptrs = X_ptr + (offs_m[:, None] * stride_xm + offs_k[None, :] * stride_xk)
            w_ptrs = W_ptr + (offs_k[:, None] * stride_wk + offs_n[None, :] * stride_wn)

            x_mask = (m_mask[:, None]) & (offs_k[None, :] < K)
            w_mask = (offs_k[:, None] < K) & (offs_n[None, :] < N)

            x = tl.load(x_ptrs, mask=x_mask, other=0.0)
            w = tl.load(w_ptrs, mask=w_mask, other=0.0)

            acc += tl.dot(x, w)
            k += BLOCK_K

        b = tl.load(B_ptr + offs_n, mask=offs_n < N, other=0.0)
        acc += b[None, :]

        acc_shifted = acc - row_max[:, None]
        nmask = offs_n[None, :] < N
        exp_tile = tl.where(nmask, tl.exp(acc_shifted), 0.0)
        sumexp += tl.sum(exp_tile, axis=1)

        in_tile = (t >= n) & (t < n + BLOCK_N)
        col_index = t - n
        col_index = tl.where(in_tile, col_index, 0)
        one_hot = tl.arange(0, BLOCK_N)[None, :] == col_index[:, None]
        # Reconstruct original logits for gathered elements: acc_shifted + row_max[:, None]
        gathered_vals = tl.sum((acc_shifted + row_max[:, None]) * one_hot, axis=1)
        tgt_logit = tl.where(in_tile, gathered_vals, tgt_logit)

        n += BLOCK_N

    loss = tl.log(sumexp) + row_max - tgt_logit
    tl.store(Out_ptr + offs_m, loss, mask=m_mask)


def fused_linear_ce(X: torch.Tensor, W: torch.Tensor, B: torch.Tensor, targets: torch.Tensor) -> torch.Tensor:
    """
    Fused linear layer with cross entropy loss computation.

    Args:
        X: (M, K) float16
        W: (K, N) float16
        B: (N,) float32
        targets: (M,) int64

    Returns:
        (M,) float32 negative log-likelihood per row
    """
    assert X.is_cuda and W.is_cuda and B.is_cuda and targets.is_cuda, "All inputs must be CUDA tensors"
    assert X.dtype in (torch.float16, torch.bfloat16), "X must be float16 or bfloat16"
    assert W.dtype == X.dtype, "W must have same dtype as X"
    assert B.dtype == torch.float32, "B must be float32"
    assert targets.dtype in (torch.int64, torch.int32), "targets must be int64 or int32"
    assert X.shape[1] == W.shape[0], "K dimension mismatch"
    assert W.shape[1] == B.shape[0], "N dimension mismatch"
    assert X.shape[0] == targets.shape[0], "M dimension mismatch"

    M, K = X.shape
    K2, N = W.shape
    assert K2 == K

    Xc = X
    Wc = W
    Bc = B
    T = targets.to(torch.int64)

    out = torch.empty((M,), dtype=torch.float32, device=X.device)

    grid = lambda META: (triton.cdiv(M, META['BLOCK_M']),)

    _fused_linear_ce_kernel[grid](
        Xc, Wc, Bc, T, out,
        M, N, K,
        Xc.stride(0), Xc.stride(1),
        Wc.stride(0), Wc.stride(1),
        num_warps=8, num_stages=2
    )
    return out
'''
        return {"code": code}
