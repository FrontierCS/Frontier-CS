import os
import torch
import triton
import triton.language as tl


@triton.autotune(
    configs=[
        triton.Config(
            {'BLOCK_M': 8, 'BLOCK_N': 128, 'BLOCK_K': 32},
            num_warps=4,
            num_stages=3,
        ),
        triton.Config(
            {'BLOCK_M': 16, 'BLOCK_N': 128, 'BLOCK_K': 32},
            num_warps=4,
            num_stages=3,
        ),
        triton.Config(
            {'BLOCK_M': 8, 'BLOCK_N': 64, 'BLOCK_K': 64},
            num_warps=4,
            num_stages=3,
        ),
        triton.Config(
            {'BLOCK_M': 16, 'BLOCK_N': 64, 'BLOCK_K': 64},
            num_warps=4,
            num_stages=3,
        ),
    ],
    key=['M', 'N', 'K'],
)
@triton.jit
def fused_linear_ce_kernel(
    X_ptr,  # float16[M, K]
    W_ptr,  # float16[K, N]
    B_ptr,  # float32[N]
    targets_ptr,  # int64[M]
    out_ptr,  # float32[M]
    M: tl.int32,
    N: tl.int32,
    K: tl.int32,
    stride_xm: tl.int32,
    stride_xk: tl.int32,
    stride_wk: tl.int32,
    stride_wn: tl.int32,
    BLOCK_M: tl.constexpr,
    BLOCK_N: tl.constexpr,
    BLOCK_K: tl.constexpr,
):
    pid_m = tl.program_id(axis=0)
    m_start = pid_m * BLOCK_M
    if m_start >= M:
        return

    offs_m = m_start + tl.arange(0, BLOCK_M)
    mask_m = offs_m < M

    # Load targets for this block
    targets = tl.load(targets_ptr + offs_m, mask=mask_m, other=0).to(tl.int32)

    # Initialize per-row statistics
    neg_inf = -float('inf')
    row_max = tl.full((BLOCK_M,), neg_inf, dtype=tl.float32)
    row_sumexp = tl.zeros((BLOCK_M,), dtype=tl.float32)
    target_logit = tl.zeros((BLOCK_M,), dtype=tl.float32)

    rows_idx = tl.arange(0, BLOCK_M)

    n_block = 0
    while n_block < N:
        offs_n = n_block + tl.arange(0, BLOCK_N)
        mask_n = offs_n < N

        # Accumulator for logits tile: [BLOCK_M, BLOCK_N]
        acc = tl.zeros((BLOCK_M, BLOCK_N), dtype=tl.float32)

        k_block = 0
        while k_block < K:
            offs_k = k_block + tl.arange(0, BLOCK_K)
            mask_k = offs_k < K

            # X tile: [BLOCK_M, BLOCK_K]
            x_ptrs = X_ptr + (
                offs_m[:, None] * stride_xm
                + offs_k[None, :] * stride_xk
            )
            x = tl.load(
                x_ptrs,
                mask=mask_m[:, None] & mask_k[None, :],
                other=0.0,
            ).to(tl.float16)

            # W tile: [BLOCK_K, BLOCK_N]
            w_ptrs = W_ptr + (
                offs_k[:, None] * stride_wk
                + offs_n[None, :] * stride_wn
            )
            w = tl.load(
                w_ptrs,
                mask=mask_k[:, None] & mask_n[None, :],
                other=0.0,
            ).to(tl.float16)

            acc += tl.dot(x, w, out_dtype=tl.float32)

            k_block += BLOCK_K

        # Add bias
        b = tl.load(B_ptr + offs_n, mask=mask_n, other=0.0).to(tl.float32)
        logits = acc + b[None, :]

        # Mask out-of-range rows/cols before reductions
        cur_mask = mask_m[:, None] & mask_n[None, :]
        logits = tl.where(cur_mask, logits, neg_inf)

        # Local max over N-block
        local_max = tl.max(logits, axis=1)

        # Update running max and sumexp in a numerically stable way
        row_max_new = tl.maximum(row_max, local_max)
        # scale_old = exp(row_max - row_max_new)
        scale_old = tl.exp(row_max - row_max_new)

        logits_shifted = logits - row_max_new[:, None]
        exp_block = tl.exp(logits_shifted)
        sumexp_block = tl.sum(exp_block, axis=1)

        row_sumexp = row_sumexp * scale_old + sumexp_block
        row_max = row_max_new

        # Gather target logits for rows whose target is in this N-block
        target_in_block = (targets >= n_block) & (targets < n_block + BLOCK_N)
        mask_t = mask_m & target_in_block

        rel_target = (targets - n_block).to(tl.int32)
        # For rows not in this block, set index to 0 (ignored by mask_t)
        rel_target = tl.where(mask_t, rel_target, 0)

        gathered = logits[rows_idx, rel_target]
        target_logit_block = tl.where(mask_t, gathered, 0.0)
        target_logit += target_logit_block

        n_block += BLOCK_N

    # Final NLL = logsumexp - target_logit
    logsumexp = tl.log(row_sumexp) + row_max
    nll = logsumexp - target_logit

    tl.store(out_ptr + offs_m, nll, mask=mask_m)


def fused_linear_ce(X: torch.Tensor, W: torch.Tensor, B: torch.Tensor, targets: torch.Tensor) -> torch.Tensor:
    """
    Fused linear layer with cross entropy loss computation.
    """
    assert X.is_cuda and W.is_cuda and B.is_cuda and targets.is_cuda
    assert X.dtype == torch.float16
    assert W.dtype == torch.float16
    assert B.dtype == torch.float32
    assert targets.dtype == torch.long

    M, K = X.shape
    KW, N = W.shape
    assert KW == K
    assert B.shape[0] == N
    assert targets.shape[0] == M

    # Ensure contiguous tensors for predictable strides
    if not X.is_contiguous():
        X = X.contiguous()
    if not W.is_contiguous():
        W = W.contiguous()
    if not B.is_contiguous():
        B = B.contiguous()
    if not targets.is_contiguous():
        targets = targets.contiguous()

    out = torch.empty((M,), device=X.device, dtype=torch.float32)

    grid = lambda META: (triton.cdiv(M, META['BLOCK_M']),)

    fused_linear_ce_kernel[grid](
        X,
        W,
        B,
        targets,
        out,
        M,
        N,
        K,
        X.stride(0),
        X.stride(1),
        W.stride(0),
        W.stride(1),
    )

    return out


class Solution:
    def solve(self, spec_path: str = None) -> dict:
        return {"program_path": os.path.abspath(__file__)}