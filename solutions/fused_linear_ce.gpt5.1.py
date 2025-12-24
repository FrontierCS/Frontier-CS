import textwrap


class Solution:
    def solve(self, spec_path: str = None) -> dict:
        code = r"""
import torch
import triton
import triton.language as tl


@triton.jit
def _fused_ce_kernel(
    logits_ptr,   # float16*
    bias_ptr,     # float32*
    targets_ptr,  # int64*
    output_ptr,   # float32*
    M, N,
    stride_m, stride_n,
    BLOCK_N: tl.constexpr,
    MAX_COLS: tl.constexpr,
):
    row_idx = tl.program_id(0)
    if row_idx >= M:
        return

    row_logits_ptr = logits_ptr + row_idx * stride_m
    target = tl.load(targets_ptr + row_idx)
    target = target.to(tl.int32)

    offsets = tl.arange(0, BLOCK_N)
    running_max = tl.full((), -1e9, tl.float32)
    running_sum = tl.zeros((), tl.float32)
    target_logit = tl.zeros((), tl.float32)

    for start_n in tl.static_range(0, MAX_COLS, BLOCK_N):
        cols = start_n + offsets
        mask = cols < N

        logits_fp16 = tl.load(row_logits_ptr + cols * stride_n, mask=mask, other=0.0)
        logits = logits_fp16.to(tl.float32)
        bias = tl.load(bias_ptr + cols, mask=mask, other=0.0)
        logits = logits + bias
        logits = tl.where(mask, logits, -1e9)

        block_max = tl.max(logits, axis=0)
        new_max = tl.maximum(running_max, block_max)
        exp_old = tl.exp(running_max - new_max) * running_sum
        exp_curr = tl.sum(tl.exp(logits - new_max), axis=0)
        running_sum = exp_old + exp_curr
        running_max = new_max

        mask_target = cols == target
        target_logit += tl.sum(tl.where(mask_target, logits, 0.0), axis=0)

    logsumexp = running_max + tl.log(running_sum)
    loss = logsumexp - target_logit
    tl.store(output_ptr + row_idx, loss)


def fused_linear_ce(X: torch.Tensor, W: torch.Tensor, B: torch.Tensor, targets: torch.Tensor) -> torch.Tensor:
    """
    Fused linear layer (via PyTorch matmul) with Triton cross-entropy kernel.

    Args:
        X: (M, K) float16 CUDA
        W: (K, N) float16 CUDA
        B: (N,)  float32 CUDA
        targets: (M,) int64 CUDA

    Returns:
        (M,) float32 CUDA negative log-likelihood per sample
    """
    assert X.is_cuda and W.is_cuda and B.is_cuda and targets.is_cuda
    assert X.dtype == torch.float16
    assert W.dtype == torch.float16
    assert B.dtype == torch.float32
    assert targets.dtype == torch.int64

    M, K = X.shape
    K2, N = W.shape
    assert K == K2
    assert B.shape[0] == N
    assert targets.shape[0] == M

    # Linear layer: X @ W -> float16 logits
    logits_half = torch.matmul(X, W).contiguous()

    out = torch.empty(M, device=X.device, dtype=torch.float32)

    stride_m, stride_n = logits_half.stride()
    BLOCK_N = 128
    MAX_COLS = triton.cdiv(N, BLOCK_N) * BLOCK_N

    grid = (M,)

    _fused_ce_kernel[grid](
        logits_half,
        B,
        targets,
        out,
        M,
        N,
        stride_m,
        stride_n,
        BLOCK_N=BLOCK_N,
        MAX_COLS=MAX_COLS,
        num_warps=4,
        num_stages=2,
    )

    return out
"""
        return {"code": textwrap.dedent(code)}
