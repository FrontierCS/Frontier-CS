import torch
import triton
import triton.language as tl


@triton.jit
def _kernel_partial_pass(
    X_ptr, W_ptr, B_ptr,
    targets_ptr, target_segs_ptr,
    partial_max_ptr, partial_sum_ptr, target_logits_ptr,
    M, N, K, S,
    stride_xm, stride_xk,
    stride_wk, stride_wn,
    stride_b,
    stride_pm_m, stride_pm_s,
    stride_ps_m, stride_ps_s,
    BLOCK_M: tl.constexpr, BLOCK_N: tl.constexpr, BLOCK_K: tl.constexpr
):
    pid_m = tl.program_id(axis=0)
    pid_s = tl.program_id(axis=1)

    offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
    offs_n = pid_s * BLOCK_N + tl.arange(0, BLOCK_N)

    m_mask = offs_m < M
    n_mask = offs_n < N

    # Accumulator for the tile
    acc = tl.zeros((BLOCK_M, BLOCK_N), dtype=tl.float32)

    # Iterate over K dimension
    for k0 in range(0, K, BLOCK_K):
        offs_k = k0 + tl.arange(0, BLOCK_K)
        k_mask = offs_k < K

        a_ptrs = X_ptr + (offs_m[:, None] * stride_xm + offs_k[None, :] * stride_xk)
        b_ptrs = W_ptr + (offs_k[:, None] * stride_wk + offs_n[None, :] * stride_wn)

        a = tl.load(a_ptrs, mask=m_mask[:, None] & k_mask[None, :], other=0.).to(tl.float16)
        b = tl.load(b_ptrs, mask=k_mask[:, None] & n_mask[None, :], other=0.).to(tl.float16)

        acc += tl.dot(a, b)

    # Add bias
    bias = tl.load(B_ptr + offs_n, mask=n_mask, other=0.).to(tl.float32)
    acc = acc + bias[None, :]

    # Mask columns beyond N to -inf for max/sumexp stability
    acc_masked = tl.where(n_mask[None, :], acc, tl.full_like(acc, -float("inf")))

    # Local row-wise max over this segment
    row_local_max = tl.max(acc_masked, axis=1)

    # Local sumexp over this segment using local max
    expv = tl.exp(acc_masked - row_local_max[:, None])
    sumexp_local = tl.sum(expv, axis=1)

    # Store partial results
    pm_ptrs = partial_max_ptr + (offs_m * stride_pm_m + pid_s * stride_pm_s)
    ps_ptrs = partial_sum_ptr + (offs_m * stride_ps_m + pid_s * stride_ps_s)
    tl.store(pm_ptrs, row_local_max, mask=m_mask)
    tl.store(ps_ptrs, sumexp_local, mask=m_mask)

    # Compute and store target logits for rows whose target falls in this segment
    # Each row's target segment: targets // BLOCK_N
    target_segs = tl.load(target_segs_ptr + offs_m, mask=m_mask, other=0).to(tl.int32)
    is_seg = target_segs == pid_s

    # Compute selection mask across BN per row to pick target column
    start_n = pid_s * BLOCK_N
    t_idx = tl.load(targets_ptr + offs_m, mask=m_mask, other=0).to(tl.int32)
    col_idx = t_idx - start_n  # may be negative if not this segment
    col_idx = tl.where(is_seg, col_idx, 0)

    offs_bn = tl.arange(0, BLOCK_N)[None, :]
    selector = (offs_bn == col_idx[:, None])
    selector = selector.to(acc.dtype)

    selected_vals = tl.sum(acc * selector, axis=1)

    # Only store for the matching segment
    tl.store(target_logits_ptr + offs_m, selected_vals, mask=m_mask & is_seg)


@triton.jit
def _kernel_reduce_rows(
    partial_max_ptr, partial_sum_ptr, target_logits_ptr, loss_ptr,
    M, S,
    stride_pm_m, stride_pm_s,
    stride_ps_m, stride_ps_s,
    BLOCK_M: tl.constexpr
):
    pid_m = tl.program_id(axis=0)
    offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
    m_mask = offs_m < M

    # Initialize running max/sum for each row
    m_val = tl.full((BLOCK_M,), -float("inf"), dtype=tl.float32)
    s_val = tl.zeros((BLOCK_M,), dtype=tl.float32)

    for s in range(0, S):
        pm_ptrs = partial_max_ptr + (offs_m * stride_pm_m + s * stride_pm_s)
        ps_ptrs = partial_sum_ptr + (offs_m * stride_ps_m + s * stride_ps_s)

        m2 = tl.load(pm_ptrs, mask=m_mask, other=-float("inf"))
        s2 = tl.load(ps_ptrs, mask=m_mask, other=0.0)

        m_new = tl.maximum(m_val, m2)
        s_val = s_val * tl.exp(m_val - m_new) + s2 * tl.exp(m2 - m_new)
        m_val = m_new

    tgt = tl.load(target_logits_ptr + offs_m, mask=m_mask, other=0.0)
    loss = tl.log(s_val) + m_val - tgt
    tl.store(loss_ptr + offs_m, loss, mask=m_mask)


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
    assert X.dtype == torch.float16 and W.dtype == torch.float16, "X and W must be float16"
    assert B.dtype == torch.float32, "B must be float32"
    assert targets.dtype == torch.long, "targets must be int64 (long)"
    M, K = X.shape
    KW, N = W.shape
    assert K == KW, "Incompatible shapes for matmul"
    assert B.shape[0] == N, "Bias dimension mismatch"
    assert targets.shape[0] == M, "Targets length mismatch"

    # Tunable block sizes
    BLOCK_M = 32
    BLOCK_N = 128
    BLOCK_K = 32

    # Number of column segments
    S = (N + BLOCK_N - 1) // BLOCK_N

    # Allocate partial buffers
    partial_max = torch.empty((M, S), dtype=torch.float32, device=X.device)
    partial_sum = torch.empty((M, S), dtype=torch.float32, device=X.device)

    # Precompute target segments to avoid atomics
    target_segs = (targets // BLOCK_N).to(torch.int32)

    # Allocate target logits and output loss
    target_logits = torch.empty((M,), dtype=torch.float32, device=X.device)
    loss = torch.empty((M,), dtype=torch.float32, device=X.device)

    # Strides in elements
    stride_xm, stride_xk = X.stride()
    stride_wk, stride_wn = W.stride()
    stride_b = B.stride()[0]
    stride_pm_m, stride_pm_s = partial_max.stride()
    stride_ps_m, stride_ps_s = partial_sum.stride()

    # Grid for partial pass
    grid0 = (triton.cdiv(M, BLOCK_M), S)

    _kernel_partial_pass[grid0](
        X, W, B,
        targets, target_segs,
        partial_max, partial_sum, target_logits,
        M, N, K, S,
        stride_xm, stride_xk,
        stride_wk, stride_wn,
        stride_b,
        stride_pm_m, stride_pm_s,
        stride_ps_m, stride_ps_s,
        BLOCK_M=BLOCK_M, BLOCK_N=BLOCK_N, BLOCK_K=BLOCK_K,
        num_warps=8, num_stages=3
    )

    # Grid for reduction pass
    RED_BM = 128
    grid1 = (triton.cdiv(M, RED_BM),)
    _kernel_reduce_rows[grid1](
        partial_max, partial_sum, target_logits, loss,
        M, S,
        stride_pm_m, stride_pm_s,
        stride_ps_m, stride_ps_s,
        BLOCK_M=RED_BM,
        num_warps=4, num_stages=2
    )

    return loss


class Solution:
    def solve(self, spec_path: str = None) -> dict:
        kernel_code = '''
import torch
import triton
import triton.language as tl


@triton.jit
def _kernel_partial_pass(
    X_ptr, W_ptr, B_ptr,
    targets_ptr, target_segs_ptr,
    partial_max_ptr, partial_sum_ptr, target_logits_ptr,
    M, N, K, S,
    stride_xm, stride_xk,
    stride_wk, stride_wn,
    stride_b,
    stride_pm_m, stride_pm_s,
    stride_ps_m, stride_ps_s,
    BLOCK_M: tl.constexpr, BLOCK_N: tl.constexpr, BLOCK_K: tl.constexpr
):
    pid_m = tl.program_id(axis=0)
    pid_s = tl.program_id(axis=1)

    offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
    offs_n = pid_s * BLOCK_N + tl.arange(0, BLOCK_N)

    m_mask = offs_m < M
    n_mask = offs_n < N

    acc = tl.zeros((BLOCK_M, BLOCK_N), dtype=tl.float32)

    for k0 in range(0, K, BLOCK_K):
        offs_k = k0 + tl.arange(0, BLOCK_K)
        k_mask = offs_k < K

        a_ptrs = X_ptr + (offs_m[:, None] * stride_xm + offs_k[None, :] * stride_xk)
        b_ptrs = W_ptr + (offs_k[:, None] * stride_wk + offs_n[None, :] * stride_wn)

        a = tl.load(a_ptrs, mask=m_mask[:, None] & k_mask[None, :], other=0.).to(tl.float16)
        b = tl.load(b_ptrs, mask=k_mask[:, None] & n_mask[None, :], other=0.).to(tl.float16)

        acc += tl.dot(a, b)

    bias = tl.load(B_ptr + offs_n, mask=n_mask, other=0.).to(tl.float32)
    acc = acc + bias[None, :]

    acc_masked = tl.where(n_mask[None, :], acc, tl.full_like(acc, -float("inf")))

    row_local_max = tl.max(acc_masked, axis=1)
    expv = tl.exp(acc_masked - row_local_max[:, None])
    sumexp_local = tl.sum(expv, axis=1)

    pm_ptrs = partial_max_ptr + (offs_m * stride_pm_m + pid_s * stride_pm_s)
    ps_ptrs = partial_sum_ptr + (offs_m * stride_ps_m + pid_s * stride_ps_s)
    tl.store(pm_ptrs, row_local_max, mask=m_mask)
    tl.store(ps_ptrs, sumexp_local, mask=m_mask)

    target_segs = tl.load(target_segs_ptr + offs_m, mask=m_mask, other=0).to(tl.int32)
    is_seg = target_segs == pid_s

    start_n = pid_s * BLOCK_N
    t_idx = tl.load(targets_ptr + offs_m, mask=m_mask, other=0).to(tl.int32)
    col_idx = t_idx - start_n
    col_idx = tl.where(is_seg, col_idx, 0)

    offs_bn = tl.arange(0, BLOCK_N)[None, :]
    selector = (offs_bn == col_idx[:, None]).to(acc.dtype)
    selected_vals = tl.sum(acc * selector, axis=1)

    tl.store(target_logits_ptr + offs_m, selected_vals, mask=m_mask & is_seg)


@triton.jit
def _kernel_reduce_rows(
    partial_max_ptr, partial_sum_ptr, target_logits_ptr, loss_ptr,
    M, S,
    stride_pm_m, stride_pm_s,
    stride_ps_m, stride_ps_s,
    BLOCK_M: tl.constexpr
):
    pid_m = tl.program_id(axis=0)
    offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
    m_mask = offs_m < M

    m_val = tl.full((BLOCK_M,), -float("inf"), dtype=tl.float32)
    s_val = tl.zeros((BLOCK_M,), dtype=tl.float32)

    for s in range(0, S):
        pm_ptrs = partial_max_ptr + (offs_m * stride_pm_m + s * stride_pm_s)
        ps_ptrs = partial_sum_ptr + (offs_m * stride_ps_m + s * stride_ps_s)

        m2 = tl.load(pm_ptrs, mask=m_mask, other=-float("inf"))
        s2 = tl.load(ps_ptrs, mask=m_mask, other=0.0)

        m_new = tl.maximum(m_val, m2)
        s_val = s_val * tl.exp(m_val - m_new) + s2 * tl.exp(m2 - m_new)
        m_val = m_new

    tgt = tl.load(target_logits_ptr + offs_m, mask=m_mask, other=0.0)
    loss = tl.log(s_val) + m_val - tgt
    tl.store(loss_ptr + offs_m, loss, mask=m_mask)


def fused_linear_ce(X: torch.Tensor, W: torch.Tensor, B: torch.Tensor, targets: torch.Tensor) -> torch.Tensor:
    assert X.is_cuda and W.is_cuda and B.is_cuda and targets.is_cuda, "All inputs must be on CUDA"
    assert X.dtype == torch.float16 and W.dtype == torch.float16, "X and W must be float16"
    assert B.dtype == torch.float32, "B must be float32"
    assert targets.dtype == torch.long, "targets must be int64 (long)"
    M, K = X.shape
    KW, N = W.shape
    assert K == KW, "Incompatible shapes for matmul"
    assert B.shape[0] == N, "Bias dimension mismatch"
    assert targets.shape[0] == M, "Targets length mismatch"

    BLOCK_M = 32
    BLOCK_N = 128
    BLOCK_K = 32

    S = (N + BLOCK_N - 1) // BLOCK_N

    partial_max = torch.empty((M, S), dtype=torch.float32, device=X.device)
    partial_sum = torch.empty((M, S), dtype=torch.float32, device=X.device)

    target_segs = (targets // BLOCK_N).to(torch.int32)

    target_logits = torch.empty((M,), dtype=torch.float32, device=X.device)
    loss = torch.empty((M,), dtype=torch.float32, device=X.device)

    stride_xm, stride_xk = X.stride()
    stride_wk, stride_wn = W.stride()
    stride_b = B.stride()[0]
    stride_pm_m, stride_pm_s = partial_max.stride()
    stride_ps_m, stride_ps_s = partial_sum.stride()

    grid0 = (triton.cdiv(M, BLOCK_M), S)
    _kernel_partial_pass[grid0](
        X, W, B,
        targets, target_segs,
        partial_max, partial_sum, target_logits,
        M, N, K, S,
        stride_xm, stride_xk,
        stride_wk, stride_wn,
        stride_b,
        stride_pm_m, stride_pm_s,
        stride_ps_m, stride_ps_s,
        BLOCK_M=BLOCK_M, BLOCK_N=BLOCK_N, BLOCK_K=BLOCK_K,
        num_warps=8, num_stages=3
    )

    RED_BM = 128
    grid1 = (triton.cdiv(M, RED_BM),)
    _kernel_reduce_rows[grid1](
        partial_max, partial_sum, target_logits, loss,
        M, S,
        stride_pm_m, stride_pm_s,
        stride_ps_m, stride_ps_s,
        BLOCK_M=RED_BM,
        num_warps=4, num_stages=2
    )

    return loss
'''
        return {"code": kernel_code}
