class Solution:
    def solve(self, spec_path: str = None) -> dict:
        return {
            "code": r"""
import torch
import triton
import triton.language as tl

@triton.jit
def max_kernel(
    x_ptr, w_ptr, b_ptr, row_max_ptr,
    stride_xm, stride_xk, stride_wk, stride_wn, stride_b, stride_rm,
    M: tl.int32, K: tl.int32, n_start: tl.int32, N: tl.int32,
    BLOCK_M: tl.constexpr, BLOCK_N: tl.constexpr, BLOCK_K: tl.constexpr
):
    pid_m = tl.program_id(0)
    m_start = pid_m * BLOCK_M
    offs_m = m_start + tl.arange(0, BLOCK_M)
    m_mask = offs_m < M
    row_max_cur = tl.load(row_max_ptr + offs_m * stride_rm, mask=m_mask, other=tl.float32("-inf"))
    offs_n = n_start + tl.arange(0, BLOCK_N)
    lo = tl.zeros((BLOCK_M, BLOCK_N), dtype=tl.float32)
    for k_off in range(0, K, BLOCK_K):
        offs_x_m = (m_start + tl.arange(0, BLOCK_M))[:, None]
        offs_x_k = (k_off + tl.arange(0, BLOCK_K))[None, :]
        x_offsets = offs_x_m * stride_xm + offs_x_k * stride_xk
        x_mask = (offs_x_m < M)[:, None] & (offs_x_k < K)[None, :]
        x = tl.load(x_ptr + x_offsets, mask=x_mask, other=0.0).to(tl.float32)
        offs_w_k = (k_off + tl.arange(0, BLOCK_K))[:, None]
        offs_w_n = (n_start + tl.arange(0, BLOCK_N))[None, :]
        w_offsets = offs_w_k * stride_wk + offs_w_n * stride_wn
        w_mask = (offs_w_k < K)[:, None] & (offs_w_n < N)[None, :]
        w = tl.load(w_ptr + w_offsets, mask=w_mask, other=0.0).to(tl.float32)
        lo += tl.dot(x, w)
    offs_b = n_start + tl.arange(0, BLOCK_N)
    b_mask = offs_b < N
    b = tl.load(b_ptr + offs_b * stride_b, mask=b_mask, other=0.0)[None, :]
    lo += b
    n_invalid = offs_n >= N
    lo = tl.where(n_invalid[None, :], tl.float32("-inf"), lo)
    sub_max = tl.max(lo, axis=1)
    row_max_cur = tl.maximum(row_max_cur, sub_max)
    tl.store(row_max_ptr + offs_m * stride_rm, row_max_cur, mask=m_mask)

@triton.jit
def se_kernel(
    x_ptr, w_ptr, b_ptr, row_max_ptr, sum_exp_ptr,
    stride_xm, stride_xk, stride_wk, stride_wn, stride_b, stride_rm, stride_se,
    M: tl.int32, K: tl.int32, n_start: tl.int32, N: tl.int32,
    BLOCK_M: tl.constexpr, BLOCK_N: tl.constexpr, BLOCK_K: tl.constexpr
):
    pid_m = tl.program_id(0)
    m_start = pid_m * BLOCK_M
    offs_m = m_start + tl.arange(0, BLOCK_M)
    m_mask = offs_m < M
    row_max_block = tl.load(row_max_ptr + offs_m * stride_rm, mask=m_mask, other=0.0)
    se_cur = tl.load(sum_exp_ptr + offs_m * stride_se, mask=m_mask, other=0.0)
    offs_n = n_start + tl.arange(0, BLOCK_N)
    lo = tl.zeros((BLOCK_M, BLOCK_N), dtype=tl.float32)
    for k_off in range(0, K, BLOCK_K):
        offs_x_m = (m_start + tl.arange(0, BLOCK_M))[:, None]
        offs_x_k = (k_off + tl.arange(0, BLOCK_K))[None, :]
        x_offsets = offs_x_m * stride_xm + offs_x_k * stride_xk
        x_mask = (offs_x_m < M)[:, None] & (offs_x_k < K)[None, :]
        x = tl.load(x_ptr + x_offsets, mask=x_mask, other=0.0).to(tl.float32)
        offs_w_k = (k_off + tl.arange(0, BLOCK_K))[:, None]
        offs_w_n = (n_start + tl.arange(0, BLOCK_N))[None, :]
        w_offsets = offs_w_k * stride_wk + offs_w_n * stride_wn
        w_mask = (offs_w_k < K)[:, None] & (offs_w_n < N)[None, :]
        w = tl.load(w_ptr + w_offsets, mask=w_mask, other=0.0).to(tl.float32)
        lo += tl.dot(x, w)
    offs_b = n_start + tl.arange(0, BLOCK_N)
    b_mask = offs_b < N
    b = tl.load(b_ptr + offs_b * stride_b, mask=b_mask, other=0.0)[None, :]
    lo += b
    n_invalid = offs_n >= N
    shifted = lo - row_max_block[:, None]
    shifted = tl.where(n_invalid[None, :], tl.float32("-30.0"), shifted)
    exps = tl.exp(shifted)
    partial_se = tl.sum(exps, axis=1)
    se_cur += partial_se
    tl.store(sum_exp_ptr + offs_m * stride_se, se_cur, mask=m_mask)

@triton.jit
def target_kernel(
    x_ptr, w_ptr, b_ptr, targets_ptr, out_ptr,
    stride_xm, stride_xk, stride_wk, stride_wn, stride_b, stride_targets, stride_out,
    M: tl.int32, K: tl.int32, N: tl.int32,
    BLOCK_K: tl.constexpr
):
    m = tl.program_id(0)
    if m >= M:
        return
    t = tl.load(targets_ptr + m * stride_targets)
    acc = tl.float32(0.0)
    for k_off in range(0, K, BLOCK_K):
        offs_k = k_off + tl.arange(0, BLOCK_K)
        k_mask = offs_k < K
        x = tl.load(x_ptr + m * stride_xm + offs_k * stride_xk, mask=k_mask, other=0.0).to(tl.float32)
        offs_wk = k_off + tl.arange(0, BLOCK_K)
        w_offsets = offs_wk * stride_wk + t * stride_wn
        w_mask = offs_wk < K
        w = tl.load(w_ptr + w_offsets, mask=w_mask, other=0.0).to(tl.float32)
        acc += tl.sum(x * w)
    b_val = tl.load(b_ptr + t * stride_b)
    acc += b_val
    tl.store(out_ptr + m * stride_out, acc)

def fused_linear_ce(X: torch.Tensor, W: torch.Tensor, B: torch.Tensor, targets: torch.Tensor) -> torch.Tensor:
    M, K = X.shape
    _, N = W.shape
    device = X.device
    BLOCK_M = 128
    BLOCK_N = 128
    BLOCK_K = 64
    row_max = torch.full((M,), float("-inf"), dtype=torch.float32, device=device)
    for ns in range(0, N, BLOCK_N):
        grid = (triton.cdiv(M, BLOCK_M), )
        max_kernel[grid](
            x_ptr=X, w_ptr=W, b_ptr=B, row_max_ptr=row_max,
            stride_xm=X.stride(0), stride_xk=X.stride(1),
            stride_wk=W.stride(0), stride_wn=W.stride(1),
            stride_b=B.stride(0), stride_rm=row_max.stride(0),
            M=M, K=K, n_start=ns, N=N,
            BLOCK_M=BLOCK_M, BLOCK_N=BLOCK_N, BLOCK_K=BLOCK_K,
            num_warps=8
        )
    sum_exp = torch.zeros((M,), dtype=torch.float32, device=device)
    for ns in range(0, N, BLOCK_N):
        grid = (triton.cdiv(M, BLOCK_M), )
        se_kernel[grid](
            x_ptr=X, w_ptr=W, b_ptr=B, row_max_ptr=row_max, sum_exp_ptr=sum_exp,
            stride_xm=X.stride(0), stride_xk=X.stride(1),
            stride_wk=W.stride(0), stride_wn=W.stride(1),
            stride_b=B.stride(0), stride_rm=row_max.stride(0), stride_se=sum_exp.stride(0),
            M=M, K=K, n_start=ns, N=N,
            BLOCK_M=BLOCK_M, BLOCK_N=BLOCK_N, BLOCK_K=BLOCK_K,
            num_warps=8
        )
    target_logit = torch.empty((M,), dtype=torch.float32, device=device)
    grid = (M, )
    target_kernel[grid](
        x_ptr=X, w_ptr=W, b_ptr=B, targets_ptr=targets, out_ptr=target_logit,
        stride_xm=X.stride(0), stride_xk=X.stride(1),
        stride_wk=W.stride(0), stride_wn=W.stride(1),
        stride_b=B.stride(0), stride_targets=targets.stride(0), stride_out=target_logit.stride(0),
        M=M, K=K, N=N,
        BLOCK_K=64,
        num_warps=4
    )
    sum_exp.clamp_(min=1e-8)
    logsumexp = row_max + torch.log(sum_exp)
    loss = -(target_logit - logsumexp)
    return loss
            """
        }