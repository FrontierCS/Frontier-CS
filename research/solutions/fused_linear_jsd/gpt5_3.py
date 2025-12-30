import math
from typing import Dict, Optional


class Solution:
    def solve(self, spec_path: str = None) -> dict:
        code = '''
import math
import torch
import triton
import triton.language as tl


@triton.jit
def _jsd_rowwise_kernel(
    logits1_ptr, logits2_ptr, out_ptr,
    M, N,
    stride1_m, stride1_n,
    stride2_m, stride2_n,
    BLOCK_N: tl.constexpr,
):
    pid_m = tl.program_id(0)
    # Early return if row is out-of-bounds
    if pid_m >= M:
        return

    # Pointers to the start of the row
    row1_ptr = logits1_ptr + pid_m * stride1_m
    row2_ptr = logits2_ptr + pid_m * stride2_m

    # Pass 1a: compute row-wise maximums
    max1 = tl.full([], -float('inf'), dtype=tl.float32)
    max2 = tl.full([], -float('inf'), dtype=tl.float32)
    for start_n in range(0, N, BLOCK_N):
        offs_n = start_n + tl.arange(0, BLOCK_N)
        mask = offs_n < N
        l1 = tl.load(row1_ptr + offs_n * stride1_n, mask=mask, other=-float('inf'))
        l2 = tl.load(row2_ptr + offs_n * stride2_n, mask=mask, other=-float('inf'))
        max1 = tl.maximum(max1, tl.max(l1, axis=0))
        max2 = tl.maximum(max2, tl.max(l2, axis=0))

    # Pass 1b: compute row-wise log-sum-exp using the max
    s1 = tl.zeros([], dtype=tl.float32)
    s2 = tl.zeros([], dtype=tl.float32)
    for start_n in range(0, N, BLOCK_N):
        offs_n = start_n + tl.arange(0, BLOCK_N)
        mask = offs_n < N
        l1 = tl.load(row1_ptr + offs_n * stride1_n, mask=mask, other=-float('inf'))
        l2 = tl.load(row2_ptr + offs_n * stride2_n, mask=mask, other=-float('inf'))
        s1 += tl.sum(tl.exp(l1 - max1), axis=0)
        s2 += tl.sum(tl.exp(l2 - max2), axis=0)

    lse1 = tl.log(s1) + max1
    lse2 = tl.log(s2) + max2

    # Pass 2: accumulate JSD over classes
    jsd_sum = tl.zeros([], dtype=tl.float32)
    LOG_TWO = 0.6931471805599453
    for start_n in range(0, N, BLOCK_N):
        offs_n = start_n + tl.arange(0, BLOCK_N)
        mask = offs_n < N
        l1 = tl.load(row1_ptr + offs_n * stride1_n, mask=mask, other=-float('inf'))
        l2 = tl.load(row2_ptr + offs_n * stride2_n, mask=mask, other=-float('inf'))

        logp = l1 - lse1
        logq = l2 - lse2

        mx = tl.maximum(logp, logq)
        # log(p + q) in a stable way
        log_p_plus_q = mx + tl.log(tl.exp(logp - mx) + tl.exp(logq - mx))
        logm = log_p_plus_q - LOG_TWO

        p = tl.exp(logp)
        q = tl.exp(logq)

        contrib = 0.5 * (p * (logp - logm) + q * (logq - logm))
        jsd_sum += tl.sum(contrib, axis=0)

    tl.store(out_ptr + pid_m, jsd_sum)


def _jsd_from_logits_triton(logits1: torch.Tensor, logits2: torch.Tensor) -> torch.Tensor:
    # logits1/logits2: [M, N], float32, contiguous
    assert logits1.is_cuda and logits2.is_cuda
    assert logits1.dtype == torch.float32 and logits2.dtype == torch.float32
    assert logits1.shape == logits2.shape
    logits1 = logits1.contiguous()
    logits2 = logits2.contiguous()
    M, N = logits1.shape
    out = torch.empty((M,), device=logits1.device, dtype=torch.float32)

    # Choose BLOCK_N as power-of-two up to 1024
    max_block = 1024
    if N >= max_block:
        BLOCK_N = max_block
    else:
        # largest power-of-two <= N, at least 128
        p = 1
        while (p << 1) <= N:
            p <<= 1
        BLOCK_N = max(128, p)

    num_warps = 4 if BLOCK_N <= 1024 else 8

    grid = (triton.cdiv(M, 1),)

    _jsd_rowwise_kernel[grid](
        logits1, logits2, out,
        M, N,
        logits1.stride(0), logits1.stride(1),
        logits2.stride(0), logits2.stride(1),
        BLOCK_N=BLOCK_N,
        num_warps=num_warps,
        num_stages=1,
    )
    return out


def fused_linear_jsd(X: torch.Tensor, W1: torch.Tensor, B1: torch.Tensor, W2: torch.Tensor, B2: torch.Tensor) -> torch.Tensor:
    """
    Fused linear layers with Jensen-Shannon Divergence computation.
    Inputs:
      X:  (M, K) float16, CUDA
      W1: (K, N) float16, CUDA
      B1: (N,)   float32, CUDA
      W2: (K, N) float16, CUDA
      B2: (N,)   float32, CUDA
    Return:
      (M,) float32, CUDA
    """
    assert X.is_cuda and W1.is_cuda and W2.is_cuda and B1.is_cuda and B2.is_cuda
    assert X.dtype == torch.float16
    assert W1.dtype == torch.float16 and W2.dtype == torch.float16
    assert B1.dtype == torch.float32 and B2.dtype == torch.float32
    M, K = X.shape
    K1, N1 = W1.shape
    K2, N2 = W2.shape
    assert K1 == K2 == K
    assert N1 == N2
    N = N1
    assert B1.shape[0] == N and B2.shape[0] == N

    # Matmul using Tensor Cores (fp16) then accumulate bias in fp32
    # Use torch.matmul (or mm) and then cast to fp32 for numerics
    logits1 = torch.matmul(X, W1)  # fp16
    logits2 = torch.matmul(X, W2)  # fp16

    logits1 = logits1.to(torch.float32)
    logits2 = logits2.to(torch.float32)

    # Add biases (fp32)
    logits1 += B1
    logits2 += B2

    # Compute row-wise JSD via Triton
    out = _jsd_from_logits_triton(logits1, logits2)
    return out
'''
        return {"code": code}