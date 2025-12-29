import torch
import triton
import triton.language as tl
import math

class Solution:
    def solve(self, spec_path: str = None) -> dict:
        code = """
import torch
import triton
import triton.language as tl
import math

@triton.jit
def max_pass_kernel(
    X_PTR, W_PTR, B_PTR, PARTIAL_PTR,
    M: tl.constexpr, K: tl.constexpr, N: tl.constexpr,
    stride_xm: tl.constexpr, stride_xk: tl.constexpr,
    stride_wk: tl.constexpr, stride_wn: tl.constexpr,
    stride_bn: tl.constexpr,
    stride_pm: tl.constexpr, stride_pnt: tl.constexpr,
    BLOCK_M: tl.constexpr, BLOCK_N: tl.constexpr, BLOCK_K: tl.constexpr
):
    pid_m = tl.program_id(0)
    pid_n = tl.program_id(1)
    m_start = pid_m * BLOCK_M
    n_start = pid_n * BLOCK_N
    offs_m = m_start + tl.arange(0, BLOCK_M)
    offs_n = n_start + tl.arange(0, BLOCK_N)
    m_mask = offs_m < M
    n_mask = offs_n < N
    acc = tl.zeros((BLOCK_M, BLOCK_N), dtype=tl.float32)
    lo = 0
    while lo < K:
        offs_k = lo + tl.arange(0, BLOCK_K)
        k_mask_m = m_mask[:, None] & (offs_k[None, :] < K)
        x_ptrs = X_PTR + (offs_m[:, None] * stride_xm + offs_k[None, :] * stride_xk)
        x = tl.load(x_ptrs, mask=k_mask_m, other=0.0, dtype=tl.float16)
        k_mask_n = (offs_k[:, None] < K) & n_mask[None, :]
        w_ptrs = W_PTR + (offs_k[:, None] * stride_wk + offs_n[None, :] * stride_wn)
        w = tl.load(w_ptrs, mask=k_mask_n, other=0.0, dtype=tl.float16)
        acc += tl.dot(x, w)
        lo += BLOCK_K
    b_ptrs = B_PTR + offs_n * stride_bn
    b_mask = n_mask
    b = tl.load(b_ptrs, mask=b_mask, other=0.0, dtype=tl.float32)
    b = b[None, :]
    logits = acc + b
    valid_mask = n_mask[None, :]
    masked_logits = tl.where(valid_mask, logits, tl.float32(-1e20))
    local_maxes = tl.max(masked_logits, axis=1)
    p_ptrs = PARTIAL_PTR + (m_start + tl.arange(0, BLOCK_M)) * stride_pm + pid_n * stride_pnt
    tl.store(p_ptrs, local_maxes, mask=m_mask)

@triton.jit
def sumexp_pass_kernel(
    X_PTR, W_PTR, B_PTR, ROW_MAX_PTR, PARTIAL_PTR,
    M: tl.constexpr, K: tl.constexpr, N: tl.constexpr,
    stride_xm: tl.constexpr, stride_xk: tl.constexpr,
    stride_wk: tl.constexpr, stride_wn: tl.constexpr,
    stride_bn: tl.constexpr,
    stride_rm: tl.constexpr,
    stride_pm: tl.constexpr, stride_pnt: tl.constexpr,
    BLOCK_M: tl.constexpr, BLOCK_N: tl.constexpr, BLOCK_K: tl.constexpr
):
    pid_m = tl.program_id(0)
    pid_n = tl.program_id(1)
    m_start = pid_m * BLOCK_M
    n_start = pid_n * BLOCK_N
    offs_m = m_start + tl.arange(0, BLOCK_M)
    offs_n = n_start + tl.arange(0, BLOCK_N)
    m_mask = offs_m < M
    n_mask = offs_n < N
    acc = tl.zeros((BLOCK_M, BLOCK_N), dtype=tl.float32)
    lo = 0
    while lo < K:
        offs_k = lo + tl.arange(0, BLOCK_K)
        k_mask_m = m_mask[:, None] & (offs_k[None, :] < K)
        x_ptrs = X_PTR + (offs_m[:, None] * stride_xm + offs_k[None, :] * stride_xk)
        x = tl.load(x_ptrs, mask=k_mask_m, other=0.0, dtype=tl.float16)
        k_mask_n = (offs_k[:, None] < K) & n_mask[None, :]
        w_ptrs = W_PTR + (offs_k[:, None] * stride_wk + offs_n[None, :] * stride_wn)
        w = tl.load(w_ptrs, mask=k_mask_n, other=0.0, dtype=tl.float16)
        acc += tl.dot(x, w)
        lo += BLOCK_K
    b_ptrs = B_PTR + offs_n * stride_bn
    b_mask = n_mask
    b = tl.load(b_ptrs, mask=b_mask, other=0.0, dtype=tl.float32)
    b = b[None, :]
    logits = acc + b
    r_ptrs = ROW_MAX_PTR + offs_m * stride_rm
    row_maxes = tl.load(r_ptrs, mask=m_mask, other=0.0, dtype=tl.float32)
    row_maxes = row_maxes[:, None]
    sub = logits - row_maxes
    exps = tl.exp(sub)
    valid_mask = n_mask[None, :]
    valid_exps = tl.where(valid_mask, exps, 0.0)
    local_sums = tl.sum(valid_exps, axis=1)
    p_ptrs = PARTIAL_PTR + (m_start + tl.arange(0, BLOCK_M)) * stride_pm + pid_n * stride_pnt
    tl.store(p_ptrs, local_sums, mask=m_mask)

@triton.jit
def reduce_max_kernel(
    PARTIAL_PTR, OUTPUT_PTR,
    M: tl.constexpr, num_nt: tl.constexpr,
    stride_pm: tl.constexpr, stride_pnt: tl.constexpr,
    stride_o: tl.constexpr,
    BLOCK_M: tl.constexpr
):
    pid = tl.program_id(0)
    m_start = pid * BLOCK_M
    offs_m = m_start + tl.arange(0, BLOCK_M)
    m_mask = offs_m < M
    offs_nt = tl.arange(0, num_nt)
    p_ptrs = PARTIAL_PTR + offs_m[:, None] * stride_pm + offs_nt[None, :] * stride_pnt
    partials = tl.load(p_ptrs, mask=m_mask[:, None], other=tl.float32(-1e20))
    row_maxes = tl.max(partials, axis=1)
    o_ptrs = OUTPUT_PTR + offs_m * stride_o
    tl.store(o_ptrs, row_maxes, mask=m_mask)

@triton.jit
def reduce_sum_kernel(
    PARTIAL_PTR, OUTPUT_PTR,
    M: tl.constexpr, num_nt: tl.constexpr,
    stride_pm: tl.constexpr, stride_pnt: tl.constexpr,
    stride_o: tl.constexpr,
    BLOCK_M: tl.constexpr
):
    pid = tl.program_id(0)
    m_start = pid * BLOCK_M
    offs_m = m_start + tl.arange(0, BLOCK_M)
    m_mask = offs_m < M
    offs_nt = tl.arange(0, num_nt)
    p_ptrs = PARTIAL_PTR + offs_m[:, None] * stride_pm + offs_nt[None, :] * stride_pnt
    partials = tl.load(p_ptrs, mask=m_mask[:, None], other=0.0)
    row_sums = tl.sum(partials, axis=1)
    o_ptrs = OUTPUT_PTR + offs_m * stride_o
    tl.store(o_ptrs, row_sums, mask=m_mask)

@triton.jit
def target_kernel(
    X_PTR, W_PTR, B_PTR, TARGETS_PTR, OUTPUT_PTR,
    M: tl.constexpr, K: tl.constexpr,
    stride_xm: tl.constexpr, stride_xk: tl.constexpr,
    stride_wk: tl.constexpr, stride_wn: tl.constexpr,
    stride_bn: tl.constexpr, stride_t: tl.constexpr, stride_o: tl.constexpr,
    BLOCK_K: tl.constexpr
):
    pid = tl.program_id(0)
    if pid >= M:
        return
    n = tl.load(TARGETS_PTR + pid * stride_t, dtype=tl.int32)
    acc = tl.float32(0.0)
    lo = 0
    while lo < K:
        offs_k = lo + tl.arange(0, BLOCK_K)
        k_mask = offs_k < K
        x_ptrs = X_PTR + pid * stride_xm + offs_k * stride_xk
        x = tl.load(x_ptrs, mask=k_mask, other=0.0, dtype=tl.float16)
        w_ptrs = W_PTR + offs_k * stride_wk + n * stride_wn
        w = tl.load(w_ptrs, mask=k_mask, other=0.0, dtype=tl.float16)
        acc += tl.sum(x.to(tl.float32) * w.to(tl.float32))
        lo += BLOCK_K
    b = tl.load(B_PTR + n * stride_bn, dtype=tl.float32)
    acc += b
    tl.store(OUTPUT_PTR + pid * stride_o, acc)

def fused_linear_ce(X: torch.Tensor, W: torch.Tensor, B: torch.Tensor, targets: torch.Tensor) -> torch.Tensor:
    M, K = X.shape
    N = W.shape[1]
    device = X.device
    BLOCK_M = 128
    BLOCK_N = 128
    BLOCK_K = 64
    TARGET_BLOCK_K = 64
    REDUCE_BLOCK_M = 128
    m_tiles = math.ceil(M / BLOCK_M)
    n_tiles = math.ceil(N / BLOCK_N)
    partial_max = torch.empty((M, n_tiles), dtype=torch.float32, device=device)
    partial_max_ptr = partial_max.data_ptr()
    stride_pm = partial_max.stride(0) * partial_max.element_size()
    stride_pnt = partial_max.stride(1) * partial_max.element_size()
    stride_xm = X.stride(0) * X.element_size()
    stride_xk = X.stride(1) * X.element_size()
    stride_wk = W.stride(0) * W.element_size()
    stride_wn = W.stride(1) * W.element_size()
    stride_bn = B.stride(0) * B.element_size()
    max_pass_kernel[(m_tiles, n_tiles)](
        X.data_ptr(), W.data_ptr(), B.data_ptr(), partial_max_ptr,
        M, K, N,
        stride_xm, stride_xk,
        stride_wk, stride_wn,
        stride_bn,
        stride_pm, stride_pnt,
        BLOCK_M=BLOCK_M, BLOCK_N=BLOCK_N, BLOCK_K=BLOCK_K,
        num_stages=1
    )
    row_max = torch.empty(M, dtype=torch.float32, device=device)
    stride_rm = row_max.stride(0) * row_max.element_size()
    reduce_max_kernel[(math.ceil(M / REDUCE_BLOCK_M))](
        partial_max_ptr, row_max.data_ptr(),
        M, n_tiles,
        stride_pm, stride_pnt,
        stride_rm,
        BLOCK_M=REDUCE_BLOCK_M
    )
    partial_sumexp = torch.empty((M, n_tiles), dtype=torch.float32, device=device)
    partial_sumexp_ptr = partial_sumexp.data_ptr()
    stride_psm = partial_sumexp.stride(0) * partial_sumexp.element_size()
    stride_psnt = partial_sumexp.stride(1) * partial_sumexp.element_size()
    sumexp_pass_kernel[(m_tiles, n_tiles)](
        X.data_ptr(), W.data_ptr(), B.data_ptr(), row_max.data_ptr(), partial_sumexp_ptr,
        M, K, N,
        stride_xm, stride_xk,
        stride_wk, stride_wn,
        stride_bn,
        stride_rm,
        stride_psm, stride_psnt,
        BLOCK_M=BLOCK_M, BLOCK_N=BLOCK_N, BLOCK_K=BLOCK_K,
        num_stages=1
    )
    total_sumexp = torch.empty(M, dtype=torch.float32, device=device)
    stride_ts = total_sumexp.stride(0) * total_sumexp.element_size()
    reduce_sum_kernel[(math.ceil(M / REDUCE_BLOCK_M))](
        partial_sumexp_ptr, total_sumexp.data_ptr(),
        M, n_tiles,
        stride_psm, stride_psnt,
        stride_ts,
        BLOCK_M=REDUCE_BLOCK_M
    )
    target_logits = torch.empty(M, dtype=torch.float32, device=device)
    stride_to = target_logits.stride(0) * target_logits.element_size()
    stride_t = targets.stride(0) * targets.element_size()
    target_kernel[M](
        X.data_ptr(), W.data_ptr(), B.data_ptr(), targets.data_ptr(), target_logits.data_ptr(),
        M, K,
        stride_xm, stride_xk,
        stride_wk, stride_wn,
        stride_bn, stride_t, stride_to,
        BLOCK_K=TARGET_BLOCK_K,
        num_stages=1
    )
    log_sum_exp = torch.log(total_sumexp) + row_max
    losses = -(target_logits - log_sum_exp)
    return losses

"""
        return {"code": code}