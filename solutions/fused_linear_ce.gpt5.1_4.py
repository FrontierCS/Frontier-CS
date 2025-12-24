import textwrap


class Solution:
    def solve(self, spec_path: str = None) -> dict:
        code = textwrap.dedent(
            '''\
import torch
import triton
import triton.language as tl


@triton.jit
def _fused_linear_ce_kernel(
    X_ptr, W_ptr, B_ptr, targets_ptr, out_ptr,
    M,
    stride_xm, stride_xk,
    stride_wk, stride_wn,
    K: tl.constexpr, N: tl.constexpr,
    BLOCK_N: tl.constexpr, BLOCK_K: tl.constexpr,
):
    row = tl.program_id(0)
    if row >= M:
        return

    # Load target index for this row
    t = tl.load(targets_ptr + row).to(tl.int32)

    # Streaming log-sum-exp state: log(sum(exp(logits))) = log(s) + m
    m = tl.full((), -1e9, dtype=tl.float32)
    s = tl.zeros((), dtype=tl.float32)
    target_logit = tl.zeros((), dtype=tl.float32)

    for n0 in range(0, N, BLOCK_N):
        offs_n = n0 + tl.arange(0, BLOCK_N)
        mask_n = offs_n < N

        # Accumulator for logits of this tile
        acc = tl.zeros([BLOCK_N], dtype=tl.float32)

        for k0 in range(0, K, BLOCK_K):
            offs_k = k0 + tl.arange(0, BLOCK_K)
            mask_k = offs_k < K

            # Load X[row, k] chunk
            x = tl.load(
                X_ptr + row * stride_xm + offs_k * stride_xk,
                mask=mask_k,
                other=0.0,
            ).to(tl.float32)

            # Load W[k, n] tile
            w = tl.load(
                W_ptr + offs_k[:, None] * stride_wk + offs_n[None, :] * stride_wn,
                mask=mask_k[:, None] & mask_n[None, :],
                other=0.0,
            ).to(tl.float32)

            # Dot product over K-block, unrolled for performance
            for kk in tl.static_range(0, BLOCK_K):
                acc += x[kk] * w[kk, :]

        # Add bias
        b = tl.load(B_ptr + offs_n, mask=mask_n, other=0.0).to(tl.float32)
        acc += b

        # Mask out columns beyond N so they don't affect reductions
        acc = tl.where(mask_n, acc, -1e30)

        # Update running log-sum-exp state
        tile_max = tl.max(acc, axis=0)
        new_m = tl.maximum(m, tile_max)
        s = s * tl.exp(m - new_m) + tl.sum(tl.exp(acc - new_m), axis=0)
        m = new_m

        # Accumulate target logit from this tile (only one position matches)
        mask_t = (offs_n == t) & mask_n
        target_logit += tl.sum(acc * mask_t.to(tl.float32), axis=0)

    logsumexp = tl.log(s) + m
    loss = -target_logit + logsumexp
    tl.store(out_ptr + row, loss)


def fused_linear_ce(X: torch.Tensor, W: torch.Tensor, B: torch.Tensor, targets: torch.Tensor) -> torch.Tensor:
    """
    Fused linear layer with cross entropy loss computation.

    Args:
        X: Input tensor of shape (M, K) - input features (float16)
        W: Weight tensor of shape (K, N) - weight matrix (float16)
        B: Bias tensor of shape (N,) - bias vector (float32)
        targets: Target tensor of shape (M,) - target class indices (int64)

    Returns:
        Output tensor of shape (M,) - negative log-likelihood loss per sample (float32)
    """
    assert X.is_cuda and W.is_cuda and B.is_cuda and targets.is_cuda, "All tensors must be on CUDA device"

    assert X.dtype == torch.float16, "X must be float16"
    assert W.dtype == torch.float16, "W must be float16"
    assert B.dtype == torch.float32, "B must be float32"
    assert targets.dtype in (torch.int64, torch.long), "targets must be int64"

    M, K = X.shape
    K_w, N = W.shape
    assert K_w == K, "Incompatible shapes for X and W"
    assert B.shape[0] == N, "Bias shape mismatch"
    assert targets.shape[0] == M, "targets shape mismatch"

    # Ensure contiguous memory layouts for predictable strides
    X_ = X.contiguous()
    W_ = W.contiguous()
    B_ = B.contiguous()
    targets_ = targets.contiguous()

    out = torch.empty(M, dtype=torch.float32, device=X.device)

    BLOCK_N = 128
    BLOCK_K = 32

    grid = (M,)

    _fused_linear_ce_kernel[grid](
        X_ptr=X_,
        W_ptr=W_,
        B_ptr=B_,
        targets_ptr=targets_,
        out_ptr=out,
        M=M,
        stride_xm=X_.stride(0),
        stride_xk=X_.stride(1),
        stride_wk=W_.stride(0),
        stride_wn=W_.stride(1),
        K=K,
        N=N,
        BLOCK_N=BLOCK_N,
        BLOCK_K=BLOCK_K,
        num_warps=4,
        num_stages=2,
    )

    return out
'''
        )
        return {"code": code}
