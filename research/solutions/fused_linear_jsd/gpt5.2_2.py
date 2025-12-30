import textwrap

KERNEL_CODE = textwrap.dedent(
    r"""
import math
import torch
import triton
import triton.language as tl

_LOGITS_CACHE = {}

@triton.jit
def _fused_two_linear_kernel(
    X_ptr, W1_ptr, B1_ptr, W2_ptr, B2_ptr,
    Y1_ptr, Y2_ptr,
    M: tl.constexpr, N: tl.constexpr,
    K,  # runtime
    stride_xm, stride_xk,
    stride_wk, stride_wn,
    stride_ym, stride_yn,
    NUM_K_BLOCKS: tl.constexpr,
    BLOCK_M: tl.constexpr, BLOCK_N: tl.constexpr, BLOCK_K: tl.constexpr,
):
    pid_m = tl.program_id(0)
    pid_n = tl.program_id(1)

    offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
    offs_n = pid_n * BLOCK_N + tl.arange(0, BLOCK_N)
    offs_k = tl.arange(0, BLOCK_K)

    mask_m = offs_m < M
    mask_n = offs_n < N

    acc1 = tl.zeros((BLOCK_M, BLOCK_N), dtype=tl.float32)
    acc2 = tl.zeros((BLOCK_M, BLOCK_N), dtype=tl.float32)

    x_row_base = X_ptr + offs_m[:, None] * stride_xm
    w1_col_base = W1_ptr + offs_n[None, :] * stride_wn
    w2_col_base = W2_ptr + offs_n[None, :] * stride_wn

    for kb in range(0, NUM_K_BLOCKS):
        k0 = kb * BLOCK_K
        k = k0 + offs_k
        mask_k = k < K

        x = tl.load(
            x_row_base + k[None, :] * stride_xk,
            mask=mask_m[:, None] & mask_k[None, :],
            other=0.0,
        ).to(tl.float16)

        w1 = tl.load(
            w1_col_base + k[:, None] * stride_wk,
            mask=mask_k[:, None] & mask_n[None, :],
            other=0.0,
        ).to(tl.float16)

        w2 = tl.load(
            w2_col_base + k[:, None] * stride_wk,
            mask=mask_k[:, None] & mask_n[None, :],
            other=0.0,
        ).to(tl.float16)

        acc1 += tl.dot(x, w1, out_dtype=tl.float32)
        acc2 += tl.dot(x, w2, out_dtype=tl.float32)

    b1 = tl.load(B1_ptr + offs_n, mask=mask_n, other=0.0).to(tl.float32)
    b2 = tl.load(B2_ptr + offs_n, mask=mask_n, other=0.0).to(tl.float32)
    acc1 = acc1 + b1[None, :]
    acc2 = acc2 + b2[None, :]

    y1_ptrs = Y1_ptr + offs_m[:, None] * stride_ym + offs_n[None, :] * stride_yn
    y2_ptrs = Y2_ptr + offs_m[:, None] * stride_ym + offs_n[None, :] * stride_yn
    mask_mn = mask_m[:, None] & mask_n[None, :]

    tl.store(y1_ptrs, acc1.to(tl.float16), mask=mask_mn)
    tl.store(y2_ptrs, acc2.to(tl.float16), mask=mask_mn)


@triton.jit
def _jsd_from_logits_kernel(
    L1_ptr, L2_ptr, Out_ptr,
    M, N,
    stride_lm, stride_ln,
    stride_out,
    NUM_N_BLOCKS: tl.constexpr,
    BLOCK_N: tl.constexpr,
    EPS: tl.constexpr,
):
    pid = tl.program_id(0)
    m = pid
    if m >= M:
        return

    offs = tl.arange(0, BLOCK_N)
    row1 = L1_ptr + m * stride_lm
    row2 = L2_ptr + m * stride_lm

    max1 = tl.full((), -float("inf"), tl.float32)
    max2 = tl.full((), -float("inf"), tl.float32)

    for nb in range(0, NUM_N_BLOCKS):
        n0 = nb * BLOCK_N
        n = n0 + offs
        mask = n < N
        l1 = tl.load(row1 + n * stride_ln, mask=mask, other=-float("inf")).to(tl.float32)
        l2 = tl.load(row2 + n * stride_ln, mask=mask, other=-float("inf")).to(tl.float32)
        max1 = tl.maximum(max1, tl.max(l1, axis=0))
        max2 = tl.maximum(max2, tl.max(l2, axis=0))

    sum1 = tl.zeros((), dtype=tl.float32)
    sum2 = tl.zeros((), dtype=tl.float32)

    for nb in range(0, NUM_N_BLOCKS):
        n0 = nb * BLOCK_N
        n = n0 + offs
        mask = n < N
        l1 = tl.load(row1 + n * stride_ln, mask=mask, other=-float("inf")).to(tl.float32)
        l2 = tl.load(row2 + n * stride_ln, mask=mask, other=-float("inf")).to(tl.float32)
        sum1 += tl.sum(tl.exp(l1 - max1), axis=0)
        sum2 += tl.sum(tl.exp(l2 - max2), axis=0)

    lse1 = tl.log(sum1) + max1
    lse2 = tl.log(sum2) + max2

    klp = tl.zeros((), dtype=tl.float32)
    klq = tl.zeros((), dtype=tl.float32)

    for nb in range(0, NUM_N_BLOCKS):
        n0 = nb * BLOCK_N
        n = n0 + offs
        mask = n < N
        l1 = tl.load(row1 + n * stride_ln, mask=mask, other=-float("inf")).to(tl.float32)
        l2 = tl.load(row2 + n * stride_ln, mask=mask, other=-float("inf")).to(tl.float32)
        log_p = l1 - lse1
        log_q = l2 - lse2
        p = tl.exp(log_p)
        q = tl.exp(log_q)
        mprob = 0.5 * (p + q)
        mprob = tl.maximum(mprob, EPS)
        log_m = tl.log(mprob)
        klp += tl.sum(p * (log_p - log_m), axis=0)
        klq += tl.sum(q * (log_q - log_m), axis=0)

    jsd = 0.5 * (klp + klq)
    tl.store(Out_ptr + m * stride_out, jsd, mask=True)


def fused_linear_jsd(X: torch.Tensor, W1: torch.Tensor, B1: torch.Tensor, W2: torch.Tensor, B2: torch.Tensor) -> torch.Tensor:
    if not (X.is_cuda and W1.is_cuda and W2.is_cuda and B1.is_cuda and B2.is_cuda):
        logits1 = X @ W1 + B1
        logits2 = X @ W2 + B2
        p = torch.softmax(logits1, dim=-1)
        q = torch.softmax(logits2, dim=-1)
        m = 0.5 * (p + q)
        jsd = 0.5 * ((p * (p.log() - m.log())).sum(dim=-1) + (q * (q.log() - m.log())).sum(dim=-1))
        return jsd.to(torch.float32)

    assert X.dtype == torch.float16
    assert W1.dtype == torch.float16 and W2.dtype == torch.float16
    assert B1.dtype == torch.float32 and B2.dtype == torch.float32
    assert X.ndim == 2 and W1.ndim == 2 and W2.ndim == 2 and B1.ndim == 1 and B2.ndim == 1

    M, K = X.shape
    K1, N = W1.shape
    K2, N2 = W2.shape
    assert K1 == K and K2 == K and N2 == N
    assert B1.numel() == N and B2.numel() == N

    dev_index = X.device.index
    key = (dev_index, M, N)
    buf = _LOGITS_CACHE.get(key)
    if buf is None or buf.numel() != 2 * M * N or buf.dtype != torch.float16 or buf.device != X.device:
        buf = torch.empty((2, M, N), device=X.device, dtype=torch.float16)
        _LOGITS_CACHE[key] = buf

    L1 = buf[0]
    L2 = buf[1]

    stride_xm, stride_xk = X.stride()
    stride_wk, stride_wn = W1.stride()
    stride_ym, stride_yn = L1.stride()

    BLOCK_M = 64
    BLOCK_N = 128
    BLOCK_K = 32

    num_k_blocks = (K + BLOCK_K - 1) // BLOCK_K
    grid = (triton.cdiv(M, BLOCK_M), triton.cdiv(N, BLOCK_N))

    _fused_two_linear_kernel[grid](
        X, W1, B1, W2, B2,
        L1, L2,
        M=M, N=N,
        K=K,
        stride_xm=stride_xm, stride_xk=stride_xk,
        stride_wk=stride_wk, stride_wn=stride_wn,
        stride_ym=stride_ym, stride_yn=stride_yn,
        NUM_K_BLOCKS=num_k_blocks,
        BLOCK_M=BLOCK_M, BLOCK_N=BLOCK_N, BLOCK_K=BLOCK_K,
        num_warps=8,
        num_stages=4,
    )

    out = torch.empty((M,), device=X.device, dtype=torch.float32)

    JS_BLOCK_N = 1024
    num_n_blocks = (N + JS_BLOCK_N - 1) // JS_BLOCK_N

    _jsd_from_logits_kernel[(M,)](
        L1, L2, out,
        M, N,
        stride_lm=L1.stride(0), stride_ln=L1.stride(1),
        stride_out=out.stride(0),
        NUM_N_BLOCKS=num_n_blocks,
        BLOCK_N=JS_BLOCK_N,
        EPS=1e-20,
        num_warps=4,
        num_stages=2,
    )

    return out

__all__ = ["fused_linear_jsd"]
"""
).strip() + "\n"


class Solution:
    def solve(self, spec_path: str = None) -> dict:
        return {"code": KERNEL_CODE}