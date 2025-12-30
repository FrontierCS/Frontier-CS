import torch
import triton
import triton.language as tl
import inspect


@triton.jit
def _fused_linear_ce_stage1(
    X_ptr, W_ptr, B_ptr, targets_ptr,
    partial_max_ptr, partial_sumexp_ptr, partial_target_ptr,
    M, N, K,
    stride_xm, stride_xk,
    stride_wk, stride_wn,
    stride_b,
    stride_pm_m, stride_pm_n,
    stride_ps_m, stride_ps_n,
    stride_pt_m, stride_pt_n,
    BLOCK_M: tl.constexpr, BLOCK_N: tl.constexpr, BLOCK_K: tl.constexpr,
):
    pid_m = tl.program_id(0)
    pid_n = tl.program_id(1)

    row_offsets = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
    col_offsets = pid_n * BLOCK_N + tl.arange(0, BLOCK_N)

    mask_m = row_offsets < M
    mask_n = col_offsets < N

    # Load target indices for these rows
    targets = tl.load(targets_ptr + row_offsets, mask=mask_m, other=0).to(tl.int32)

    # Accumulator for logits tile
    acc = tl.zeros((BLOCK_M, BLOCK_N), dtype=tl.float32)

    for k_start in range(0, K, BLOCK_K):
        k_offsets = k_start + tl.arange(0, BLOCK_K)
        mask_k = k_offsets < K

        x_ptrs = X_ptr + row_offsets[:, None] * stride_xm + k_offsets[None, :] * stride_xk
        w_ptrs = W_ptr + k_offsets[:, None] * stride_wk + col_offsets[None, :] * stride_wn

        x = tl.load(x_ptrs, mask=mask_m[:, None] & mask_k[None, :], other=0.0).to(tl.float16)
        w = tl.load(w_ptrs, mask=mask_k[:, None] & mask_n[None, :], other=0.0).to(tl.float16)

        acc += tl.dot(x, w)

    # Add bias
    b = tl.load(B_ptr + col_offsets * stride_b, mask=mask_n, other=0.0).to(tl.float32)
    acc += b[None, :]

    minus_inf = -float("inf")
    # Mask invalid rows/cols for max/sumexp computation
    acc_masked = tl.where(mask_m[:, None] & mask_n[None, :], acc, minus_inf)

    # Local max over columns for each row
    tile_max = tl.max(acc_masked, axis=1)

    # Local sumexp with numerical stability
    exp_term = tl.exp(acc_masked - tile_max[:, None])
    tile_sumexp = tl.sum(exp_term, axis=1)
    tile_sumexp = tl.where(tile_max == minus_inf, 0.0, tile_sumexp)

    # Target logits contribution from this tile
    target_eq = (targets[:, None] == col_offsets[None, :]) & mask_n[None, :] & mask_m[:, None]
    target_contrib = tl.sum(tl.where(target_eq, acc, 0.0), axis=1)

    # Store partial results
    pm_ptrs = partial_max_ptr + row_offsets * stride_pm_m + pid_n * stride_pm_n
    ps_ptrs = partial_sumexp_ptr + row_offsets * stride_ps_m + pid_n * stride_ps_n
    pt_ptrs = partial_target_ptr + row_offsets * stride_pt_m + pid_n * stride_pt_n

    tl.store(pm_ptrs, tile_max, mask=mask_m)
    tl.store(ps_ptrs, tile_sumexp, mask=mask_m)
    tl.store(pt_ptrs, target_contrib, mask=mask_m)


@triton.jit
def _fused_linear_ce_stage2(
    partial_max_ptr, partial_sumexp_ptr, partial_target_ptr,
    loss_ptr,
    M,
    stride_pm_m, stride_pm_n,
    stride_ps_m, stride_ps_n,
    stride_pt_m, stride_pt_n,
    BLOCK_M: tl.constexpr,
    NUM_TILES_N: tl.constexpr,
):
    pid_m = tl.program_id(0)
    row_offsets = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
    mask_m = row_offsets < M

    minus_inf = -float("inf")
    row_max = tl.full((BLOCK_M,), minus_inf, dtype=tl.float32)
    row_sumexp = tl.zeros((BLOCK_M,), dtype=tl.float32)
    target_logit = tl.zeros((BLOCK_M,), dtype=tl.float32)

    for tile_id in range(0, NUM_TILES_N):
        pm_ptrs = partial_max_ptr + row_offsets * stride_pm_m + tile_id * stride_pm_n
        ps_ptrs = partial_sumexp_ptr + row_offsets * stride_ps_m + tile_id * stride_ps_n
        pt_ptrs = partial_target_ptr + row_offsets * stride_pt_m + tile_id * stride_pt_n

        tile_max = tl.load(pm_ptrs, mask=mask_m, other=minus_inf)
        tile_sumexp = tl.load(ps_ptrs, mask=mask_m, other=0.0)
        tile_target = tl.load(pt_ptrs, mask=mask_m, other=0.0)

        new_max = tl.maximum(row_max, tile_max)
        factor_prev = tl.exp(row_max - new_max)
        factor_tile = tl.exp(tile_max - new_max)
        row_sumexp = row_sumexp * factor_prev + tile_sumexp * factor_tile
        row_max = new_max

        target_logit += tile_target

    logsumexp = tl.log(row_sumexp) + row_max
    loss = logsumexp - target_logit

    tl.store(loss_ptr + row_offsets, loss, mask=mask_m)


def fused_linear_ce(X: torch.Tensor, W: torch.Tensor, B: torch.Tensor, targets: torch.Tensor) -> torch.Tensor:
    """
    Fused linear layer with cross entropy loss computation.

    Args:
        X: (M, K) float16
        W: (K, N) float16
        B: (N,) float32
        targets: (M,) int64

    Returns:
        (M,) float32 loss per sample
    """
    assert X.is_cuda and W.is_cuda and B.is_cuda and targets.is_cuda
    assert X.dtype == torch.float16
    assert W.dtype == torch.float16
    assert B.dtype == torch.float32
    assert targets.dtype == torch.long

    X_ = X.contiguous()
    W_ = W.contiguous()
    B_ = B.contiguous()
    targets_ = targets.contiguous()

    M, K = X_.shape
    K2, N = W_.shape
    if K != K2:
        raise ValueError("Incompatible dimensions: X.shape[1] must equal W.shape[0]")

    BLOCK_M = 32
    BLOCK_N = 128
    BLOCK_K = 64

    grid_m = triton.cdiv(M, BLOCK_M)
    num_tiles_n = triton.cdiv(N, BLOCK_N)

    partial_max = torch.empty((M, num_tiles_n), dtype=torch.float32, device=X_.device)
    partial_sumexp = torch.empty_like(partial_max)
    partial_target = torch.zeros_like(partial_max)

    grid1 = (grid_m, num_tiles_n)

    _fused_linear_ce_stage1[grid1](
        X_, W_, B_, targets_,
        partial_max, partial_sumexp, partial_target,
        M, N, K,
        X_.stride(0), X_.stride(1),
        W_.stride(0), W_.stride(1),
        B_.stride(0),
        partial_max.stride(0), partial_max.stride(1),
        partial_sumexp.stride(0), partial_sumexp.stride(1),
        partial_target.stride(0), partial_target.stride(1),
        BLOCK_M=BLOCK_M,
        BLOCK_N=BLOCK_N,
        BLOCK_K=BLOCK_K,
        num_warps=4,
        num_stages=2,
    )

    loss = torch.empty((M,), dtype=torch.float32, device=X_.device)

    grid2 = (grid_m,)

    _fused_linear_ce_stage2[grid2](
        partial_max, partial_sumexp, partial_target,
        loss,
        M,
        partial_max.stride(0), partial_max.stride(1),
        partial_sumexp.stride(0), partial_sumexp.stride(1),
        partial_target.stride(0), partial_target.stride(1),
        BLOCK_M=BLOCK_M,
        NUM_TILES_N=num_tiles_n,
        num_warps=4,
        num_stages=2,
    )

    return loss


class Solution:
    def solve(self, spec_path: str = None) -> dict:
        parts = [
            "import torch",
            "import triton",
            "import triton.language as tl",
            inspect.getsource(_fused_linear_ce_stage1),
            inspect.getsource(_fused_linear_ce_stage2),
            inspect.getsource(fused_linear_ce),
        ]
        code = "\n\n".join(parts)
        return {"code": code}