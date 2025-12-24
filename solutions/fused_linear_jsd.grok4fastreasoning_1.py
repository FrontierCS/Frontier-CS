import torch
import triton
import triton.language as tl

class Solution:
    def solve(self, spec_path: str = None) -> dict:
        code = """
import torch
import triton
import triton.language as tl

@triton.jit
def linear_kernel(X_ptr, W_ptr, B_ptr, out_ptr, M, N, K, stride_xm, stride_xk, stride_wk, stride_wn, stride_b, stride_om, stride_on, BLOCK_M: tl.constexpr, BLOCK_N: tl.constexpr, BLOCK_K: tl.constexpr):
    pid_m = tl.program_id(0)
    pid_n = tl.program_id(1)
    rm = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
    rn = pid_n * BLOCK_N + tl.arange(0, BLOCK_N)
    acc = tl.zeros((BLOCK_M, BLOCK_N), dtype=tl.float32)
    for k in range(0, K, BLOCK_K):
        rk = k + tl.arange(0, BLOCK_K)
        x_mask = (rm[:, None] < M, rk[None, :] < K)
        w_mask = (rk[:, None] < K, rn[None, :] < N)
        x_ptrs = X_ptr + rm[:, None] * stride_xm + rk[None, :] * stride_xk
        w_ptrs = W_ptr + rk[:, None] * stride_wk + rn[None, :] * stride_wn
        x = tl.load(x_ptrs, mask=x_mask, other=0.0)
        w = tl.load(w_ptrs, mask=w_mask, other=0.0)
        acc += tl.dot(x, w)
    b_ptrs = B_ptr + rn * stride_b
    b = tl.load(b_ptrs, mask=(rn < N), other=0.0)
    acc += b[None, :]
    out_ptrs = out_ptr + rm[:, None] * stride_om + rn[None, :] * stride_on
    out_mask = (rm[:, None] < M, rn[None, :] < N)
    tl.store(out_ptrs, acc, mask=out_mask)

@triton.jit
def softmax_lse_kernel(LOGITS_PTR, LSE_PTR, M, N, stride_row, stride_n, stride_lse, BLOCK_SIZE: tl.constexpr):
    rid = tl.program_id(0)
    if rid >= M:
        return
    row_max = tl.float32('-inf')
    row_sum = tl.float32(0.0)
    row_ptr = LOGITS_PTR + rid * stride_row
    for offset in range(0, N, BLOCK_SIZE):
        offs = tl.arange(0, BLOCK_SIZE)
        mask = (offset + offs) < N
        l_ptrs = row_ptr + (offset + offs) * stride_n
        lblock = tl.load(l_ptrs, mask=mask, other=0.0)
        valid_l = tl.where(mask, lblock, tl.float32('-inf'))
        bmax = tl.max(valid_l)
        sum_exp_bmax = tl.sum(tl.where(mask, tl.exp(lblock - bmax), 0.0))
        sum_exp_rmax = tl.sum(tl.where(mask, tl.exp(lblock - row_max), 0.0))
        is_update = bmax > row_max
        row_sum = tl.where(is_update, row_sum * tl.exp(row_max - bmax) + sum_exp_bmax, row_sum + sum_exp_rmax)
        row_max = tl.where(is_update, bmax, row_max)
    lse = row_max + tl.log(row_sum)
    tl.store(LSE_PTR + rid * stride_lse, lse)

@triton.jit
def softmax_kernel(LOGITS_PTR, LSE_PTR, OUTPUT_PTR, M, N, stride_l_row, stride_l_n, stride_o_row, stride_o_n, stride_lse, BLOCK_SIZE: tl.constexpr):
    rid = tl.program_id(0)
    if rid >= M:
        return
    rlse = tl.load(LSE_PTR + rid * stride_lse)
    r_l_ptr = LOGITS_PTR + rid * stride_l_row
    r_o_ptr = OUTPUT_PTR + rid * stride_o_row
    for offset in range(0, N, BLOCK_SIZE):
        offs = tl.arange(0, BLOCK_SIZE)
        mask = (offset + offs) < N
        l_ptrs = r_l_ptr + (offset + offs) * stride_l_n
        o_ptrs = r_o_ptr + (offset + offs) * stride_o_n
        lblock = tl.load(l_ptrs, mask=mask, other=0.0)
        oblock = tl.exp(lblock - rlse)
        tl.store(o_ptrs, oblock, mask=mask)

@triton.jit
def jsd_kernel(P_PTR, Q_PTR, OUT_PTR, M, N, sp_row, sp_n, sq_row, sq_n, so, BLOCK_SIZE: tl.constexpr):
    rid = tl.program_id(0)
    if rid >= M:
        return
    klp = tl.float32(0.0)
    klq = tl.float32(0.0)
    log05 = tl.log(tl.float32(0.5))
    rp = P_PTR + rid * sp_row
    rq = Q_PTR + rid * sq_row
    for offset in range(0, N, BLOCK_SIZE):
        offs = tl.arange(0, BLOCK_SIZE)
        mask = (offset + offs) < N
        pptrs = rp + (offset + offs) * sp_n
        qptrs = rq + (offset + offs) * sq_n
        pblk = tl.load(pptrs, mask=mask, other=0.0)
        qblk = tl.load(qptrs, mask=mask, other=0.0)
        mblk = tl.float32(0.5) * (pblk + qblk)
        logm = log05 + tl.log(mblk)
        plogp = tl.where(pblk > 0.0, pblk * tl.log(pblk), 0.0)
        plogm = tl.where(pblk > 0.0, pblk * logm, 0.0)
        klp += tl.sum(plogp - plogm)
        qlogq = tl.where(qblk > 0.0, qblk * tl.log(qblk), 0.0)
        qlogm = tl.where(qblk > 0.0, qblk * logm, 0.0)
        klq += tl.sum(qlogq - qlogm)
    jsd = tl.float32(0.5) * (klp + klq)
    tl.store(OUT_PTR + rid * so, jsd)

def fused_linear_jsd(X: torch.Tensor, W1: torch.Tensor, B1: torch.Tensor, W2: torch.Tensor, B2: torch.Tensor) -> torch.Tensor:
    M, K = X.shape
    N = W1.shape[1]
    device = X.device
    out_dtype = torch.float32
    logits1 = torch.empty((M, N), dtype=out_dtype, device=device)
    logits2 = torch.empty((M, N), dtype=out_dtype, device=device)
    lse1 = torch.empty((M,), dtype=out_dtype, device=device)
    P = torch.empty((M, N), dtype=out_dtype, device=device)
    lse2 = torch.empty((M,), dtype=out_dtype, device=device)
    Q = torch.empty((M, N), dtype=out_dtype, device=device)
    output = torch.empty((M,), dtype=out_dtype, device=device)
    BM = 128
    BN = 128
    BK = 128
    BS = 1024
    def matmul_grid(meta):
        return (
            triton.cdiv(M, meta['BLOCK_M']),
            triton.cdiv(N, meta['BLOCK_N'])
        )
    linear_kernel[matmul_grid](
        X, W1, B1, logits1, M, N, K,
        X.stride(0), X.stride(1),
        W1.stride(0), W1.stride(1),
        B1.stride(0),
        logits1.stride(0), logits1.stride(1),
        BLOCK_M=BM, BLOCK_N=BN, BLOCK_K=BK
    )
    def softmax_grid(meta):
        return (M,)
    softmax_lse_kernel[softmax_grid](
        logits1, lse1, M, N,
        logits1.stride(0), logits1.stride(1),
        lse1.stride(0), BLOCK_SIZE=BS
    )
    softmax_kernel[softmax_grid](
        logits1, lse1, P, M, N,
        logits1.stride(0), logits1.stride(1),
        P.stride(0), P.stride(1),
        lse1.stride(0), BLOCK_SIZE=BS
    )
    linear_kernel[matmul_grid](
        X, W2, B2, logits2, M, N, K,
        X.stride(0), X.stride(1),
        W2.stride(0), W2.stride(1),
        B2.stride(0),
        logits2.stride(0), logits2.stride(1),
        BLOCK_M=BM, BLOCK_N=BN, BLOCK_K=BK
    )
    softmax_lse_kernel[softmax_grid](
        logits2, lse2, M, N,
        logits2.stride(0), logits2.stride(1),
        lse2.stride(0), BLOCK_SIZE=BS
    )
    softmax_kernel[softmax_grid](
        logits2, lse2, Q, M, N,
        logits2.stride(0), logits2.stride(1),
        Q.stride(0), Q.stride(1),
        lse2.stride(0), BLOCK_SIZE=BS
    )
    jsd_kernel[softmax_grid](
        P, Q, output, M, N,
        P.stride(0), P.stride(1),
        Q.stride(0), Q.stride(1),
        output.stride(0), BLOCK_SIZE=BS
    )
    return output
"""
        return {"code": code}
