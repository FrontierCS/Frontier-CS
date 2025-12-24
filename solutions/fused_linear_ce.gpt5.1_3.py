import torch
import triton
import triton.language as tl


class Solution:
    def solve(self, spec_path: str = None) -> dict:
        kernel_code = '''
import torch
import triton
import triton.language as tl


@triton.jit
def _fused_linear_ce_kernel(
    X_ptr, W_ptr, B_ptr, Tgt_ptr, Loss_ptr,
    M, K, N,
    stride_xm, stride_xk,
    stride_wk, stride_wn,
    BLOCK_N: tl.constexpr, BLOCK_K: tl.constexpr,
):
    row_idx = tl.program_id(0)
    if row_idx >= M:
        return

    target = tl.load(Tgt_ptr + row_idx)
    target = target.to(tl.int32)

    row_max = -float("inf")
    row_sumexp = 0.0
    target_logit = 0.0

    n_start = 0
    while n_start < N:
        offs_n = n_start + tl.arange(0, BLOCK_N)
        mask_n = offs_n < N

        acc = tl.zeros((BLOCK_N,), dtype=tl.float32)

        k_start = 0
        while k_start < K:
            offs_k = k_start + tl.arange(0, BLOCK_K)
            mask_k = offs_k < K

            x = tl.load(
                X_ptr + row_idx * stride_xm + offs_k * stride_xk,
                mask=mask_k,
                other=0.0,
            )
            x = x.to(tl.float32)

            w_ptrs = W_ptr + offs_k[:, None] * stride_wk + offs_n[None, :] * stride_wn
            w = tl.load(
                w_ptrs,
                mask=mask_k[:, None] & mask_n[None, :],
                other=0.0,
            )
            w = w.to(tl.float32)

            acc += tl.sum(w * x[:, None], axis=0)

            k_start += BLOCK_K

        b = tl.load(B_ptr + offs_n, mask=mask_n, other=0.0)
        raw_logits = acc + b
        logits = tl.where(mask_n, raw_logits, -float("inf"))

        block_max = tl.max(logits, axis=0)
        new_row_max = tl.maximum(row_max, block_max)

        exp_scale_old = tl.exp(row_max - new_row_max)
        exp_vals = tl.exp(logits - new_row_max)
        exp_vals = tl.where(mask_n, exp_vals, 0.0)

        row_sumexp = row_sumexp * exp_scale_old + tl.sum(exp_vals, axis=0)
        row_max = new_row_max

        mask_tgt = offs_n == target
        target_logit += tl.sum(tl.where(mask_tgt, raw_logits, 0.0), axis=0)

        n_start += BLOCK_N

    log_sum_exp = row_max + tl.log(row_sumexp)
    nll = log_sum_exp - target_logit
    tl.store(Loss_ptr + row_idx, nll)


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
    assert X.is_cuda and W.is_cuda and B.is_cuda and targets.is_cuda, "All inputs must be on CUDA"
    assert X.dtype == torch.float16, "X must be float16"
    assert W.dtype == torch.float16, "W must be float16"
    assert B.dtype == torch.float32, "B must be float32"
    assert targets.dtype == torch.int64, "targets must be int64"

    M, K = X.shape
    K_w, N = W.shape
    assert K_w == K, "Incompatible shapes between X and W"
    assert B.shape[0] == N, "Bias dimension must match number of classes"
    assert targets.shape[0] == M, "Targets must have same batch size as X"

    X_contig = X
    W_contig = W
    B_contig = B
    targets_contig = targets

    out = torch.empty((M,), device=X.device, dtype=torch.float32)

    BLOCK_N = 128
    BLOCK_K = 32

    grid = (M,)

    _fused_linear_ce_kernel[grid](
        X_contig, W_contig, B_contig, targets_contig, out,
        M, K, N,
        X_contig.stride(0), X_contig.stride(1),
        W_contig.stride(0), W_contig.stride(1),
        BLOCK_N=BLOCK_N,
        BLOCK_K=BLOCK_K,
        num_warps=4,
        num_stages=2,
    )

    return out
'''
        return {"code": kernel_code}
