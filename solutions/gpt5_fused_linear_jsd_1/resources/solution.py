import torch
import triton
import triton.language as tl


@triton.jit
def _jsd_row_kernel(
    l1_ptr, l2_ptr, out_ptr,
    M, N,
    stride1_m, stride1_n,
    stride2_m, stride2_n,
    BLOCK_N: tl.constexpr
):
    pid = tl.program_id(0)
    row_mask = pid < M
    offs = tl.arange(0, BLOCK_N)

    m1 = tl.full([1], -float('inf'), dtype=tl.float32)
    s1 = tl.zeros([1], dtype=tl.float32)
    m2 = tl.full([1], -float('inf'), dtype=tl.float32)
    s2 = tl.zeros([1], dtype=tl.float32)

    n = 0
    while n < N:
        col = n + offs
        mask = (col < N) & row_mask
        l1 = tl.load(l1_ptr + pid * stride1_m + col * stride1_n, mask=mask, other=-float('inf'))
        l2 = tl.load(l2_ptr + pid * stride2_m + col * stride2_n, mask=mask, other=-float('inf'))
        tmax1 = tl.max(l1, axis=0)
        new_m1 = tl.maximum(m1, tmax1)
        s1 = s1 * tl.exp(m1 - new_m1) + tl.sum(tl.exp(l1 - new_m1), axis=0)
        m1 = new_m1

        tmax2 = tl.max(l2, axis=0)
        new_m2 = tl.maximum(m2, tmax2)
        s2 = s2 * tl.exp(m2 - new_m2) + tl.sum(tl.exp(l2 - new_m2), axis=0)
        m2 = new_m2

        n += BLOCK_N

    lse1 = m1 + tl.log(s1)
    lse2 = m2 + tl.log(s2)

    acc = tl.zeros([1], dtype=tl.float32)
    n = 0
    LN2 = 0.6931471805599453
    while n < N:
        col = n + offs
        mask = (col < N) & row_mask
        l1 = tl.load(l1_ptr + pid * stride1_m + col * stride1_n, mask=mask, other=0.0)
        l2 = tl.load(l2_ptr + pid * stride2_m + col * stride2_n, mask=mask, other=0.0)

        logp = l1 - lse1
        logq = l2 - lse2
        p = tl.exp(logp)
        q = tl.exp(logq)

        a = logp - LN2
        b = logq - LN2
        m_ab = tl.maximum(a, b)
        exp_a = tl.exp(a - m_ab)
        exp_b = tl.exp(b - m_ab)
        logm = m_ab + tl.log(exp_a + exp_b)

        term = 0.5 * (p * (logp - logm) + q * (logq - logm))
        term = tl.where(mask, term, 0.0)
        acc += tl.sum(term, axis=0)

        n += BLOCK_N

    tl.store(out_ptr + pid, acc, mask=row_mask)


def _compute_logits(X: torch.Tensor, W: torch.Tensor, B: torch.Tensor) -> torch.Tensor:
    logits = torch.matmul(X, W)  # (M, N), dtype = X.dtype (fp16)
    logits = logits.to(torch.float32)
    logits += B  # broadcast add (N,)
    return logits.contiguous()


def fused_linear_jsd(X: torch.Tensor, W1: torch.Tensor, B1: torch.Tensor, W2: torch.Tensor, B2: torch.Tensor) -> torch.Tensor:
    assert X.is_cuda and W1.is_cuda and W2.is_cuda and B1.is_cuda and B2.is_cuda
    assert X.dtype in (torch.float16, torch.bfloat16), "X must be float16 or bfloat16"
    assert W1.dtype == X.dtype and W2.dtype == X.dtype, "Weights must match X dtype"
    assert B1.dtype == torch.float32 and B2.dtype == torch.float32, "Biases must be float32"
    M, K = X.shape
    K1, N = W1.shape
    K2, N2 = W2.shape
    assert K == K1 == K2 and N == N2
    assert B1.shape == (N,) and B2.shape == (N,)

    logits1 = _compute_logits(X, W1, B1)
    logits2 = _compute_logits(X, W2, B2)

    out = torch.empty((M,), dtype=torch.float32, device=X.device)

    BLOCK_N = 256
    grid = (triton.cdiv(M, 1),)
    _jsd_row_kernel[grid](
        logits1, logits2, out,
        M, N,
        logits1.stride(0), logits1.stride(1),
        logits2.stride(0), logits2.stride(1),
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
def _jsd_row_kernel(
    l1_ptr, l2_ptr, out_ptr,
    M, N,
    stride1_m, stride1_n,
    stride2_m, stride2_n,
    BLOCK_N: tl.constexpr
):
    pid = tl.program_id(0)
    row_mask = pid < M
    offs = tl.arange(0, BLOCK_N)

    m1 = tl.full([1], -float('inf'), dtype=tl.float32)
    s1 = tl.zeros([1], dtype=tl.float32)
    m2 = tl.full([1], -float('inf'), dtype=tl.float32)
    s2 = tl.zeros([1], dtype=tl.float32)

    n = 0
    while n < N:
        col = n + offs
        mask = (col < N) & row_mask
        l1 = tl.load(l1_ptr + pid * stride1_m + col * stride1_n, mask=mask, other=-float('inf'))
        l2 = tl.load(l2_ptr + pid * stride2_m + col * stride2_n, mask=mask, other=-float('inf'))
        tmax1 = tl.max(l1, axis=0)
        new_m1 = tl.maximum(m1, tmax1)
        s1 = s1 * tl.exp(m1 - new_m1) + tl.sum(tl.exp(l1 - new_m1), axis=0)
        m1 = new_m1

        tmax2 = tl.max(l2, axis=0)
        new_m2 = tl.maximum(m2, tmax2)
        s2 = s2 * tl.exp(m2 - new_m2) + tl.sum(tl.exp(l2 - new_m2), axis=0)
        m2 = new_m2

        n += BLOCK_N

    lse1 = m1 + tl.log(s1)
    lse2 = m2 + tl.log(s2)

    acc = tl.zeros([1], dtype=tl.float32)
    n = 0
    LN2 = 0.6931471805599453
    while n < N:
        col = n + offs
        mask = (col < N) & row_mask
        l1 = tl.load(l1_ptr + pid * stride1_m + col * stride1_n, mask=mask, other=0.0)
        l2 = tl.load(l2_ptr + pid * stride2_m + col * stride2_n, mask=mask, other=0.0)

        logp = l1 - lse1
        logq = l2 - lse2
        p = tl.exp(logp)
        q = tl.exp(logq)

        a = logp - LN2
        b = logq - LN2
        m_ab = tl.maximum(a, b)
        exp_a = tl.exp(a - m_ab)
        exp_b = tl.exp(b - m_ab)
        logm = m_ab + tl.log(exp_a + exp_b)

        term = 0.5 * (p * (logp - logm) + q * (logq - logm))
        term = tl.where(mask, term, 0.0)
        acc += tl.sum(term, axis=0)

        n += BLOCK_N

    tl.store(out_ptr + pid, acc, mask=row_mask)


def _compute_logits(X: torch.Tensor, W: torch.Tensor, B: torch.Tensor) -> torch.Tensor:
    logits = torch.matmul(X, W)
    logits = logits.to(torch.float32)
    logits += B
    return logits.contiguous()


def fused_linear_jsd(X: torch.Tensor, W1: torch.Tensor, B1: torch.Tensor, W2: torch.Tensor, B2: torch.Tensor) -> torch.Tensor:
    assert X.is_cuda and W1.is_cuda and W2.is_cuda and B1.is_cuda and B2.is_cuda
    assert X.dtype in (torch.float16, torch.bfloat16), "X must be float16 or bfloat16"
    assert W1.dtype == X.dtype and W2.dtype == X.dtype, "Weights must match X dtype"
    assert B1.dtype == torch.float32 and B2.dtype == torch.float32, "Biases must be float32"
    M, K = X.shape
    K1, N = W1.shape
    K2, N2 = W2.shape
    assert K == K1 == K2 and N == N2
    assert B1.shape == (N,) and B2.shape == (N,)

    logits1 = _compute_logits(X, W1, B1)
    logits2 = _compute_logits(X, W2, B2)

    out = torch.empty((M,), dtype=torch.float32, device=X.device)

    BLOCK_N = 256
    grid = (triton.cdiv(M, 1),)
    _jsd_row_kernel[grid](
        logits1, logits2, out,
        M, N,
        logits1.stride(0), logits1.stride(1),
        logits2.stride(0), logits2.stride(1),
        BLOCK_N=BLOCK_N,
        num_warps=8,
        num_stages=2
    )
    return out
"""
        return {"code": code}
