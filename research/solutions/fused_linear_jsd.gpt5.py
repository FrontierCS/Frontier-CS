import torch
import triton
import triton.language as tl


@triton.jit
def _jsd_from_logits_kernel(
    LOGITS1_PTR, LOGITS2_PTR, OUT_PTR,
    M, N,
    STRIDE_L1_M, STRIDE_L1_N,
    STRIDE_L2_M, STRIDE_L2_N,
    STRIDE_OUT,
    BLOCK_N: tl.constexpr
):
    pid_m = tl.program_id(axis=0)
    # Guard in case grid is larger than M
    if pid_m >= M:
        return

    # First pass: compute logsumexp for both logits rows
    max1 = tl.full((1,), -float("inf"), tl.float32)
    max2 = tl.full((1,), -float("inf"), tl.float32)
    sumexp1 = tl.zeros((1,), tl.float32)
    sumexp2 = tl.zeros((1,), tl.float32)

    offs_n = tl.arange(0, BLOCK_N)
    n0 = 0
    while n0 < N:
        n_idx = n0 + offs_n
        mask = n_idx < N

        l1 = tl.load(LOGITS1_PTR + pid_m * STRIDE_L1_M + n_idx * STRIDE_L1_N, mask=mask, other=-float("inf"))
        l2 = tl.load(LOGITS2_PTR + pid_m * STRIDE_L2_M + n_idx * STRIDE_L2_N, mask=mask, other=-float("inf"))

        tile_max1 = tl.max(l1, axis=0)
        tile_max2 = tl.max(l2, axis=0)

        new_max1 = tl.maximum(max1, tile_max1)
        new_max2 = tl.maximum(max2, tile_max2)

        sumexp1 = sumexp1 * tl.exp(max1 - new_max1) + tl.sum(tl.exp(l1 - new_max1), axis=0)
        sumexp2 = sumexp2 * tl.exp(max2 - new_max2) + tl.sum(tl.exp(l2 - new_max2), axis=0)

        max1 = new_max1
        max2 = new_max2

        n0 += BLOCK_N

    lse1 = max1 + tl.log(sumexp1)
    lse2 = max2 + tl.log(sumexp2)

    # Second pass: compute JSD
    acc = tl.zeros((1,), tl.float32)
    LOG_HALF = tl.log(tl.full((1,), 0.5, dtype=tl.float32))  # log(0.5)

    n0 = 0
    while n0 < N:
        n_idx = n0 + offs_n
        mask = n_idx < N

        l1 = tl.load(LOGITS1_PTR + pid_m * STRIDE_L1_M + n_idx * STRIDE_L1_N, mask=mask, other=-float("inf"))
        l2 = tl.load(LOGITS2_PTR + pid_m * STRIDE_L2_M + n_idx * STRIDE_L2_N, mask=mask, other=-float("inf"))

        logP = l1 - lse1
        logQ = l2 - lse2

        P = tl.exp(logP)
        Q = tl.exp(logQ)
        PQ = P + Q
        # logM = log(0.5 * (P+Q)) = log(P+Q) + log(0.5)
        # For numerical stability, PQ >= 0
        # mask to avoid log(0) when both P and Q ~ 0; use tl.log with masking
        # But when mask is False, l1/l2 are -inf so P/Q are 0, PQ is 0 -> set contribution to 0 by mask
        logM = tl.log(PQ + 1e-20) + LOG_HALF  # small epsilon to avoid log(0)

        term = 0.5 * (P * (logP - logM) + Q * (logQ - logM))
        term = tl.where(mask, term, 0.0)
        acc += tl.sum(term, axis=0)

        n0 += BLOCK_N

    tl.store(OUT_PTR + pid_m * STRIDE_OUT, acc)


def fused_linear_jsd(X: torch.Tensor, W1: torch.Tensor, B1: torch.Tensor, W2: torch.Tensor, B2: torch.Tensor) -> torch.Tensor:
    """
    Fused linear layers with Jensen-Shannon Divergence computation.
    """
    assert X.is_cuda and W1.is_cuda and W2.is_cuda and B1.is_cuda and B2.is_cuda, "All tensors must be on CUDA."
    assert X.dtype == torch.float16 and W1.dtype == torch.float16 and W2.dtype == torch.float16, "X, W1, W2 must be float16."
    assert B1.dtype == torch.float32 and B2.dtype == torch.float32, "B1, B2 must be float32."
    assert X.dim() == 2 and W1.dim() == 2 and W2.dim() == 2 and B1.dim() == 1 and B2.dim() == 1, "Invalid tensor ranks."

    M, K = X.shape
    K1, N = W1.shape
    K2, N2 = W2.shape
    assert K == K1 == K2, "K dims must match."
    assert N == N2 == B1.numel() == B2.numel(), "N dims must match."

    # Compute logits using highly-optimized cuBLAS via PyTorch
    # Matmul in fp16 then cast to fp32 for stability; add bias in fp32
    logits1 = torch.matmul(X, W1).to(torch.float32)
    logits2 = torch.matmul(X, W2).to(torch.float32)
    logits1.add_(B1)
    logits2.add_(B2)

    logits1 = logits1.contiguous()
    logits2 = logits2.contiguous()

    # Output buffer
    out = torch.empty((M,), dtype=torch.float32, device=X.device)

    BLOCK_N = 256
    grid = (triton.cdiv(M, 1),)

    _jsd_from_logits_kernel[grid](
        logits1, logits2, out,
        M, N,
        logits1.stride(0), logits1.stride(1),
        logits2.stride(0), logits2.stride(1),
        out.stride(0),
        BLOCK_N=BLOCK_N,
        num_warps=8,
        num_stages=2
    )
    return out


class Solution:
    def solve(self, spec_path: str = None) -> dict:
        code = """
import torch
import triton
import triton.language as tl


@triton.jit
def _jsd_from_logits_kernel(
    LOGITS1_PTR, LOGITS2_PTR, OUT_PTR,
    M, N,
    STRIDE_L1_M, STRIDE_L1_N,
    STRIDE_L2_M, STRIDE_L2_N,
    STRIDE_OUT,
    BLOCK_N: tl.constexpr
):
    pid_m = tl.program_id(axis=0)
    if pid_m >= M:
        return

    max1 = tl.full((1,), -float("inf"), tl.float32)
    max2 = tl.full((1,), -float("inf"), tl.float32)
    sumexp1 = tl.zeros((1,), tl.float32)
    sumexp2 = tl.zeros((1,), tl.float32)

    offs_n = tl.arange(0, BLOCK_N)
    n0 = 0
    while n0 < N:
        n_idx = n0 + offs_n
        mask = n_idx < N

        l1 = tl.load(LOGITS1_PTR + pid_m * STRIDE_L1_M + n_idx * STRIDE_L1_N, mask=mask, other=-float("inf"))
        l2 = tl.load(LOGITS2_PTR + pid_m * STRIDE_L2_M + n_idx * STRIDE_L2_N, mask=mask, other=-float("inf"))

        tile_max1 = tl.max(l1, axis=0)
        tile_max2 = tl.max(l2, axis=0)

        new_max1 = tl.maximum(max1, tile_max1)
        new_max2 = tl.maximum(max2, tile_max2)

        sumexp1 = sumexp1 * tl.exp(max1 - new_max1) + tl.sum(tl.exp(l1 - new_max1), axis=0)
        sumexp2 = sumexp2 * tl.exp(max2 - new_max2) + tl.sum(tl.exp(l2 - new_max2), axis=0)

        max1 = new_max1
        max2 = new_max2

        n0 += BLOCK_N

    lse1 = max1 + tl.log(sumexp1)
    lse2 = max2 + tl.log(sumexp2)

    acc = tl.zeros((1,), tl.float32)
    LOG_HALF = tl.log(tl.full((1,), 0.5, dtype=tl.float32))

    n0 = 0
    while n0 < N:
        n_idx = n0 + offs_n
        mask = n_idx < N

        l1 = tl.load(LOGITS1_PTR + pid_m * STRIDE_L1_M + n_idx * STRIDE_L1_N, mask=mask, other=-float("inf"))
        l2 = tl.load(LOGITS2_PTR + pid_m * STRIDE_L2_M + n_idx * STRIDE_L2_N, mask=mask, other=-float("inf"))

        logP = l1 - lse1
        logQ = l2 - lse2

        P = tl.exp(logP)
        Q = tl.exp(logQ)
        PQ = P + Q
        logM = tl.log(PQ + 1e-20) + LOG_HALF

        term = 0.5 * (P * (logP - logM) + Q * (logQ - logM))
        term = tl.where(mask, term, 0.0)
        acc += tl.sum(term, axis=0)

        n0 += BLOCK_N

    tl.store(OUT_PTR + pid_m * STRIDE_OUT, acc)


def fused_linear_jsd(X: torch.Tensor, W1: torch.Tensor, B1: torch.Tensor, W2: torch.Tensor, B2: torch.Tensor) -> torch.Tensor:
    assert X.is_cuda and W1.is_cuda and W2.is_cuda and B1.is_cuda and B2.is_cuda, "All tensors must be on CUDA."
    assert X.dtype == torch.float16 and W1.dtype == torch.float16 and W2.dtype == torch.float16, "X, W1, W2 must be float16."
    assert B1.dtype == torch.float32 and B2.dtype == torch.float32, "B1, B2 must be float32."
    assert X.dim() == 2 and W1.dim() == 2 and W2.dim() == 2 and B1.dim() == 1 and B2.dim() == 1, "Invalid tensor ranks."

    M, K = X.shape
    K1, N = W1.shape
    K2, N2 = W2.shape
    assert K == K1 == K2, "K dims must match."
    assert N == N2 == B1.numel() == B2.numel(), "N dims must match."

    logits1 = torch.matmul(X, W1).to(torch.float32)
    logits2 = torch.matmul(X, W2).to(torch.float32)
    logits1.add_(B1)
    logits2.add_(B2)

    logits1 = logits1.contiguous()
    logits2 = logits2.contiguous()

    out = torch.empty((M,), dtype=torch.float32, device=X.device)

    BLOCK_N = 256
    grid = (triton.cdiv(M, 1),)

    _jsd_from_logits_kernel[grid](
        logits1, logits2, out,
        M, N,
        logits1.stride(0), logits1.stride(1),
        logits2.stride(0), logits2.stride(1),
        out.stride(0),
        BLOCK_N=BLOCK_N,
        num_warps=8,
        num_stages=2
    )
    return out
"""
        return {"code": code}