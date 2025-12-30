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
def _fused_linear_ce_kernel(
    X_ptr, W_ptr, B_ptr, T_ptr, O_ptr,
    M: tl.constexpr, N: tl.constexpr, K: tl.constexpr,
    stride_xm, stride_xk,
    stride_wk, stride_wn,
    stride_b,
    stride_tm,
    stride_om,
    BLOCK_M: tl.constexpr, BLOCK_N: tl.constexpr, BLOCK_K: tl.constexpr
):
    pid_m = tl.program_id(0)
    offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
    mask_m = offs_m < M

    # Load targets for this block of rows
    t_idx = tl.load(T_ptr + offs_m * stride_tm, mask=mask_m, other=0).to(tl.int32)

    # Initialize streaming logsumexp state
    row_max = tl.full((BLOCK_M,), -1.0e30, dtype=tl.float32)
    row_sum = tl.zeros((BLOCK_M,), dtype=tl.float32)
    t_val = tl.zeros((BLOCK_M,), dtype=tl.float32)

    arange_n = tl.arange(0, BLOCK_N)

    n = 0
    while n < N:
        offs_n = n + arange_n
        n_mask = offs_n < N

        # Accumulator for the BMxBN tile
        acc = tl.zeros((BLOCK_M, BLOCK_N), dtype=tl.float32)

        k = 0
        while k < K:
            offs_k = k + tl.arange(0, BLOCK_K)

            x_ptrs = X_ptr + offs_m[:, None] * stride_xm + offs_k[None, :] * stride_xk
            w_ptrs = W_ptr + offs_k[:, None] * stride_wk + offs_n[None, :] * stride_wn

            x_mask = (mask_m[:, None]) & (offs_k[None, :] < K)
            w_mask = (offs_k[:, None] < K) & (n_mask[None, :])

            x = tl.load(x_ptrs, mask=x_mask, other=0.0).to(tl.float16)
            w = tl.load(w_ptrs, mask=w_mask, other=0.0).to(tl.float16)

            acc += tl.dot(x, w)

            k += BLOCK_K

        # Add bias
        b = tl.load(B_ptr + offs_n * stride_b, mask=n_mask, other=0.0).to(tl.float32)
        acc += b[None, :]

        # Streaming logsumexp update
        tile_max = tl.max(acc, axis=1)
        new_max = tl.maximum(row_max, tile_max)
        # Scale previous sum to new_max
        scale_prev = tl.exp(row_max - new_max)
        # Add current tile contribution
        cur_sum = tl.sum(tl.exp(acc - new_max[:, None]), axis=1)

        row_sum = row_sum * scale_prev + cur_sum
        row_max = new_max

        # Gather target logits from this tile
        rel = t_idx - n
        eq = (arange_n[None, :].to(tl.int32) == rel[:, None])
        sel = tl.sum(acc * eq, axis=1)
        t_val += sel

        n += BLOCK_N

    # Final loss: logsumexp - target_logit
    loss = tl.log(row_sum) + row_max - t_val
    tl.store(O_ptr + offs_m * stride_om, loss, mask=mask_m)


def fused_linear_ce(X: torch.Tensor, W: torch.Tensor, B: torch.Tensor, targets: torch.Tensor) -> torch.Tensor:
    """
    Fused linear layer with cross entropy loss computation.
    Args:
        X: (M, K) float16 CUDA
        W: (K, N) float16 CUDA
        B: (N,) float32 CUDA
        targets: (M,) int64 CUDA
    Returns:
        (M,) float32 CUDA losses
    """
    assert X.is_cuda and W.is_cuda and B.is_cuda and targets.is_cuda, "All tensors must be on CUDA"
    assert X.dtype == torch.float16 and W.dtype == torch.float16, "X and W must be float16"
    assert B.dtype == torch.float32, "B must be float32"
    assert targets.dtype in (torch.int64, torch.long), "targets must be int64"
    assert X.shape[1] == W.shape[0], "Incompatible shapes"
    assert W.shape[1] == B.shape[0], "Incompatible shapes"
    M, K = X.shape
    K2, N = W.shape
    assert K2 == K
    assert targets.numel() == M

    # Heuristic block sizes
    if N >= 8192:
        BLOCK_N = 128
    elif N >= 4096:
        BLOCK_N = 128
    elif N >= 2048:
        BLOCK_N = 64
    else:
        BLOCK_N = 64

    if K >= 4096:
        BLOCK_K = 64
    elif K >= 2048:
        BLOCK_K = 64
    else:
        BLOCK_K = 32

    if M >= 256:
        BLOCK_M = 64
    else:
        BLOCK_M = 64

    # num_warps heuristic
    num_warps = 8 if BLOCK_N >= 128 else 4
    num_stages = 2 if BLOCK_K >= 64 else 3

    O = torch.empty((M,), device=X.device, dtype=torch.float32)

    grid = (triton.cdiv(M, BLOCK_M),)
    _fused_linear_ce_kernel[grid](
        X, W, B, targets, O,
        M, N, K,
        X.stride(0), X.stride(1),
        W.stride(0), W.stride(1),
        B.stride(0),
        targets.stride(0),
        O.stride(0),
        BLOCK_M=BLOCK_M, BLOCK_N=BLOCK_N, BLOCK_K=BLOCK_K,
        num_warps=num_warps, num_stages=num_stages
    )
    return O
'''
        return {"code": code}