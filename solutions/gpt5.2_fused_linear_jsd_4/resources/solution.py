import torch
import triton
import triton.language as tl
from collections import OrderedDict

_LOG2 = 0.6931471805599453
_EPS = 1.0e-20

_WCAT_CACHE = OrderedDict()
_WCAT_CACHE_MAX = 4


def _get_wcat(W1: torch.Tensor, W2: torch.Tensor) -> torch.Tensor:
    if not W1.is_cuda or not W2.is_cuda:
        raise ValueError("W1/W2 must be CUDA tensors")
    if W1.dtype != torch.float16 or W2.dtype != torch.float16:
        W1 = W1.to(torch.float16)
        W2 = W2.to(torch.float16)
    if not W1.is_contiguous():
        W1 = W1.contiguous()
    if not W2.is_contiguous():
        W2 = W2.contiguous()

    key = (W1.data_ptr(), W2.data_ptr(), W1._version, W2._version, tuple(W1.shape), tuple(W2.shape), W1.device)
    v = _WCAT_CACHE.get(key, None)
    if v is not None:
        _WCAT_CACHE.move_to_end(key)
        return v

    Wcat = torch.cat((W1, W2), dim=1).contiguous()
    _WCAT_CACHE[key] = Wcat
    if len(_WCAT_CACHE) > _WCAT_CACHE_MAX:
        _WCAT_CACHE.popitem(last=False)
    return Wcat


@triton.jit
def _block_stats_kernel(
    logits_ptr,
    b1_ptr,
    b2_ptr,
    max1_ptr,
    sum1_ptr,
    max2_ptr,
    sum2_ptr,
    stride_l0: tl.constexpr,
    stride_l1: tl.constexpr,
    stride_o0: tl.constexpr,
    stride_o1: tl.constexpr,
    M: tl.constexpr,
    N: tl.constexpr,
    BLOCK_M: tl.constexpr,
    BLOCK_N: tl.constexpr,
):
    pid_m = tl.program_id(0)
    pid_bn = tl.program_id(1)

    m_offsets = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
    n_offsets = pid_bn * BLOCK_N + tl.arange(0, BLOCK_N)

    mask_m = m_offsets < M
    mask_n = n_offsets < N
    mask = mask_m[:, None] & mask_n[None, :]

    offs1 = m_offsets[:, None] * stride_l0 + n_offsets[None, :] * stride_l1
    offs2 = m_offsets[:, None] * stride_l0 + (n_offsets[None, :] + N) * stride_l1

    x1 = tl.load(logits_ptr + offs1, mask=mask, other=-float("inf")).to(tl.float32)
    x2 = tl.load(logits_ptr + offs2, mask=mask, other=-float("inf")).to(tl.float32)

    b1 = tl.load(b1_ptr + n_offsets, mask=mask_n, other=0.0).to(tl.float32)
    b2 = tl.load(b2_ptr + n_offsets, mask=mask_n, other=0.0).to(tl.float32)

    x1 = x1 + b1[None, :]
    x2 = x2 + b2[None, :]

    m1 = tl.max(x1, axis=1)
    m2 = tl.max(x2, axis=1)

    e1 = tl.exp(x1 - m1[:, None])
    e2 = tl.exp(x2 - m2[:, None])

    s1 = tl.sum(e1, axis=1)
    s2 = tl.sum(e2, axis=1)

    out_offs = m_offsets * stride_o0 + pid_bn * stride_o1
    tl.store(max1_ptr + out_offs, m1, mask=mask_m)
    tl.store(sum1_ptr + out_offs, s1, mask=mask_m)
    tl.store(max2_ptr + out_offs, m2, mask=mask_m)
    tl.store(sum2_ptr + out_offs, s2, mask=mask_m)


@triton.jit
def _reduce_lse_kernel(
    max1_ptr,
    sum1_ptr,
    max2_ptr,
    sum2_ptr,
    lse1_ptr,
    lse2_ptr,
    stride_in0: tl.constexpr,
    stride_in1: tl.constexpr,
    M: tl.constexpr,
    NBLOCKS: tl.constexpr,
    BLOCK_M: tl.constexpr,
):
    pid_m = tl.program_id(0)
    m_offsets = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
    mask_m = m_offsets < M

    b = tl.arange(0, NBLOCKS)

    offs = m_offsets[:, None] * stride_in0 + b[None, :] * stride_in1

    m1b = tl.load(max1_ptr + offs, mask=mask_m[:, None], other=-float("inf")).to(tl.float32)
    s1b = tl.load(sum1_ptr + offs, mask=mask_m[:, None], other=0.0).to(tl.float32)
    m2b = tl.load(max2_ptr + offs, mask=mask_m[:, None], other=-float("inf")).to(tl.float32)
    s2b = tl.load(sum2_ptr + offs, mask=mask_m[:, None], other=0.0).to(tl.float32)

    m1 = tl.max(m1b, axis=1)
    m2 = tl.max(m2b, axis=1)

    w1 = tl.exp(m1b - m1[:, None])
    w2 = tl.exp(m2b - m2[:, None])

    ss1 = tl.sum(s1b * w1, axis=1)
    ss2 = tl.sum(s2b * w2, axis=1)

    ss1 = tl.where(mask_m, ss1, 0.0)
    ss2 = tl.where(mask_m, ss2, 0.0)

    lse1 = m1 + tl.log(ss1 + _EPS)
    lse2 = m2 + tl.log(ss2 + _EPS)

    tl.store(lse1_ptr + m_offsets, lse1, mask=mask_m)
    tl.store(lse2_ptr + m_offsets, lse2, mask=mask_m)


@triton.jit
def _jsd_kernel(
    logits_ptr,
    b1_ptr,
    b2_ptr,
    lse1_ptr,
    lse2_ptr,
    out_ptr,
    stride_l0: tl.constexpr,
    stride_l1: tl.constexpr,
    M: tl.constexpr,
    N: tl.constexpr,
    BLOCK_M: tl.constexpr,
    BLOCK_N: tl.constexpr,
):
    pid_m = tl.program_id(0)
    pid_bn = tl.program_id(1)

    m_offsets = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
    n_offsets = pid_bn * BLOCK_N + tl.arange(0, BLOCK_N)

    mask_m = m_offsets < M
    mask_n = n_offsets < N
    mask = mask_m[:, None] & mask_n[None, :]

    lse1 = tl.load(lse1_ptr + m_offsets, mask=mask_m, other=0.0).to(tl.float32)
    lse2 = tl.load(lse2_ptr + m_offsets, mask=mask_m, other=0.0).to(tl.float32)

    offs1 = m_offsets[:, None] * stride_l0 + n_offsets[None, :] * stride_l1
    offs2 = m_offsets[:, None] * stride_l0 + (n_offsets[None, :] + N) * stride_l1

    x1 = tl.load(logits_ptr + offs1, mask=mask, other=-float("inf")).to(tl.float32)
    x2 = tl.load(logits_ptr + offs2, mask=mask, other=-float("inf")).to(tl.float32)

    b1 = tl.load(b1_ptr + n_offsets, mask=mask_n, other=0.0).to(tl.float32)
    b2 = tl.load(b2_ptr + n_offsets, mask=mask_n, other=0.0).to(tl.float32)

    x1 = x1 + b1[None, :]
    x2 = x2 + b2[None, :]

    logP_raw = x1 - lse1[:, None]
    logQ_raw = x2 - lse2[:, None]

    P = tl.exp(logP_raw)
    Q = tl.exp(logQ_raw)

    P = tl.where(mask, P, 0.0)
    Q = tl.where(mask, Q, 0.0)

    logP = tl.where(P > 0.0, logP_raw, 0.0)
    logQ = tl.where(Q > 0.0, logQ_raw, 0.0)

    s = P + Q
    logM = tl.log(s + _EPS) - _LOG2

    term = 0.5 * (P * (logP - logM) + Q * (logQ - logM))
    acc = tl.sum(term, axis=1)

    acc = tl.where(mask_m, acc, 0.0)
    tl.atomic_add(out_ptr + m_offsets, acc, mask=mask_m)


def fused_linear_jsd(X: torch.Tensor, W1: torch.Tensor, B1: torch.Tensor, W2: torch.Tensor, B2: torch.Tensor) -> torch.Tensor:
    if not (X.is_cuda and W1.is_cuda and W2.is_cuda and B1.is_cuda and B2.is_cuda):
        raise ValueError("All inputs must be CUDA tensors")
    if X.dtype != torch.float16:
        X = X.to(torch.float16)
    if W1.dtype != torch.float16:
        W1 = W1.to(torch.float16)
    if W2.dtype != torch.float16:
        W2 = W2.to(torch.float16)
    if B1.dtype != torch.float32:
        B1 = B1.to(torch.float32)
    if B2.dtype != torch.float32:
        B2 = B2.to(torch.float32)

    if not X.is_contiguous():
        X = X.contiguous()
    if not B1.is_contiguous():
        B1 = B1.contiguous()
    if not B2.is_contiguous():
        B2 = B2.contiguous()

    M, K = X.shape
    if W1.shape[0] != K or W2.shape[0] != K:
        raise ValueError("Weight K dim mismatch")
    if W1.shape[1] != W2.shape[1]:
        raise ValueError("W1/W2 N mismatch")
    N = W1.shape[1]
    if B1.numel() != N or B2.numel() != N:
        raise ValueError("Bias N mismatch")

    Wcat = _get_wcat(W1, W2)
    logits = torch.mm(X, Wcat)
    if not logits.is_contiguous():
        logits = logits.contiguous()

    BLOCK_N = 256
    BLOCK_M = 4
    nblocks = triton.cdiv(N, BLOCK_N)

    max1 = torch.empty((M, nblocks), device=X.device, dtype=torch.float32)
    sum1 = torch.empty((M, nblocks), device=X.device, dtype=torch.float32)
    max2 = torch.empty((M, nblocks), device=X.device, dtype=torch.float32)
    sum2 = torch.empty((M, nblocks), device=X.device, dtype=torch.float32)

    stride_l0 = logits.stride(0)
    stride_l1 = logits.stride(1)
    stride_o0 = max1.stride(0)
    stride_o1 = max1.stride(1)

    grid_stats = (triton.cdiv(M, BLOCK_M), nblocks)
    _block_stats_kernel[grid_stats](
        logits,
        B1,
        B2,
        max1,
        sum1,
        max2,
        sum2,
        stride_l0=stride_l0,
        stride_l1=stride_l1,
        stride_o0=stride_o0,
        stride_o1=stride_o1,
        M=M,
        N=N,
        BLOCK_M=BLOCK_M,
        BLOCK_N=BLOCK_N,
        num_warps=4,
    )

    lse1 = torch.empty((M,), device=X.device, dtype=torch.float32)
    lse2 = torch.empty((M,), device=X.device, dtype=torch.float32)

    BLOCK_M_R = 16
    grid_reduce = (triton.cdiv(M, BLOCK_M_R),)
    _reduce_lse_kernel[grid_reduce](
        max1,
        sum1,
        max2,
        sum2,
        lse1,
        lse2,
        stride_in0=stride_o0,
        stride_in1=stride_o1,
        M=M,
        NBLOCKS=nblocks,
        BLOCK_M=BLOCK_M_R,
        num_warps=2,
    )

    out = torch.zeros((M,), device=X.device, dtype=torch.float32)

    grid_jsd = (triton.cdiv(M, BLOCK_M), nblocks)
    _jsd_kernel[grid_jsd](
        logits,
        B1,
        B2,
        lse1,
        lse2,
        out,
        stride_l0=stride_l0,
        stride_l1=stride_l1,
        M=M,
        N=N,
        BLOCK_M=BLOCK_M,
        BLOCK_N=BLOCK_N,
        num_warps=4,
    )

    return out


class Solution:
    def solve(self, spec_path: str = None) -> dict:
        code = r'''
import torch
import triton
import triton.language as tl
from collections import OrderedDict

_LOG2 = 0.6931471805599453
_EPS = 1.0e-20

_WCAT_CACHE = OrderedDict()
_WCAT_CACHE_MAX = 4


def _get_wcat(W1: torch.Tensor, W2: torch.Tensor) -> torch.Tensor:
    if not W1.is_cuda or not W2.is_cuda:
        raise ValueError("W1/W2 must be CUDA tensors")
    if W1.dtype != torch.float16 or W2.dtype != torch.float16:
        W1 = W1.to(torch.float16)
        W2 = W2.to(torch.float16)
    if not W1.is_contiguous():
        W1 = W1.contiguous()
    if not W2.is_contiguous():
        W2 = W2.contiguous()

    key = (W1.data_ptr(), W2.data_ptr(), W1._version, W2._version, tuple(W1.shape), tuple(W2.shape), W1.device)
    v = _WCAT_CACHE.get(key, None)
    if v is not None:
        _WCAT_CACHE.move_to_end(key)
        return v

    Wcat = torch.cat((W1, W2), dim=1).contiguous()
    _WCAT_CACHE[key] = Wcat
    if len(_WCAT_CACHE) > _WCAT_CACHE_MAX:
        _WCAT_CACHE.popitem(last=False)
    return Wcat


@triton.jit
def _block_stats_kernel(
    logits_ptr,
    b1_ptr,
    b2_ptr,
    max1_ptr,
    sum1_ptr,
    max2_ptr,
    sum2_ptr,
    stride_l0: tl.constexpr,
    stride_l1: tl.constexpr,
    stride_o0: tl.constexpr,
    stride_o1: tl.constexpr,
    M: tl.constexpr,
    N: tl.constexpr,
    BLOCK_M: tl.constexpr,
    BLOCK_N: tl.constexpr,
):
    pid_m = tl.program_id(0)
    pid_bn = tl.program_id(1)

    m_offsets = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
    n_offsets = pid_bn * BLOCK_N + tl.arange(0, BLOCK_N)

    mask_m = m_offsets < M
    mask_n = n_offsets < N
    mask = mask_m[:, None] & mask_n[None, :]

    offs1 = m_offsets[:, None] * stride_l0 + n_offsets[None, :] * stride_l1
    offs2 = m_offsets[:, None] * stride_l0 + (n_offsets[None, :] + N) * stride_l1

    x1 = tl.load(logits_ptr + offs1, mask=mask, other=-float("inf")).to(tl.float32)
    x2 = tl.load(logits_ptr + offs2, mask=mask, other=-float("inf")).to(tl.float32)

    b1 = tl.load(b1_ptr + n_offsets, mask=mask_n, other=0.0).to(tl.float32)
    b2 = tl.load(b2_ptr + n_offsets, mask=mask_n, other=0.0).to(tl.float32)

    x1 = x1 + b1[None, :]
    x2 = x2 + b2[None, :]

    m1 = tl.max(x1, axis=1)
    m2 = tl.max(x2, axis=1)

    e1 = tl.exp(x1 - m1[:, None])
    e2 = tl.exp(x2 - m2[:, None])

    s1 = tl.sum(e1, axis=1)
    s2 = tl.sum(e2, axis=1)

    out_offs = m_offsets * stride_o0 + pid_bn * stride_o1
    tl.store(max1_ptr + out_offs, m1, mask=mask_m)
    tl.store(sum1_ptr + out_offs, s1, mask=mask_m)
    tl.store(max2_ptr + out_offs, m2, mask=mask_m)
    tl.store(sum2_ptr + out_offs, s2, mask=mask_m)


@triton.jit
def _reduce_lse_kernel(
    max1_ptr,
    sum1_ptr,
    max2_ptr,
    sum2_ptr,
    lse1_ptr,
    lse2_ptr,
    stride_in0: tl.constexpr,
    stride_in1: tl.constexpr,
    M: tl.constexpr,
    NBLOCKS: tl.constexpr,
    BLOCK_M: tl.constexpr,
):
    pid_m = tl.program_id(0)
    m_offsets = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
    mask_m = m_offsets < M

    b = tl.arange(0, NBLOCKS)

    offs = m_offsets[:, None] * stride_in0 + b[None, :] * stride_in1

    m1b = tl.load(max1_ptr + offs, mask=mask_m[:, None], other=-float("inf")).to(tl.float32)
    s1b = tl.load(sum1_ptr + offs, mask=mask_m[:, None], other=0.0).to(tl.float32)
    m2b = tl.load(max2_ptr + offs, mask=mask_m[:, None], other=-float("inf")).to(tl.float32)
    s2b = tl.load(sum2_ptr + offs, mask=mask_m[:, None], other=0.0).to(tl.float32)

    m1 = tl.max(m1b, axis=1)
    m2 = tl.max(m2b, axis=1)

    w1 = tl.exp(m1b - m1[:, None])
    w2 = tl.exp(m2b - m2[:, None])

    ss1 = tl.sum(s1b * w1, axis=1)
    ss2 = tl.sum(s2b * w2, axis=1)

    ss1 = tl.where(mask_m, ss1, 0.0)
    ss2 = tl.where(mask_m, ss2, 0.0)

    lse1 = m1 + tl.log(ss1 + _EPS)
    lse2 = m2 + tl.log(ss2 + _EPS)

    tl.store(lse1_ptr + m_offsets, lse1, mask=mask_m)
    tl.store(lse2_ptr + m_offsets, lse2, mask=mask_m)


@triton.jit
def _jsd_kernel(
    logits_ptr,
    b1_ptr,
    b2_ptr,
    lse1_ptr,
    lse2_ptr,
    out_ptr,
    stride_l0: tl.constexpr,
    stride_l1: tl.constexpr,
    M: tl.constexpr,
    N: tl.constexpr,
    BLOCK_M: tl.constexpr,
    BLOCK_N: tl.constexpr,
):
    pid_m = tl.program_id(0)
    pid_bn = tl.program_id(1)

    m_offsets = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
    n_offsets = pid_bn * BLOCK_N + tl.arange(0, BLOCK_N)

    mask_m = m_offsets < M
    mask_n = n_offsets < N
    mask = mask_m[:, None] & mask_n[None, :]

    lse1 = tl.load(lse1_ptr + m_offsets, mask=mask_m, other=0.0).to(tl.float32)
    lse2 = tl.load(lse2_ptr + m_offsets, mask=mask_m, other=0.0).to(tl.float32)

    offs1 = m_offsets[:, None] * stride_l0 + n_offsets[None, :] * stride_l1
    offs2 = m_offsets[:, None] * stride_l0 + (n_offsets[None, :] + N) * stride_l1

    x1 = tl.load(logits_ptr + offs1, mask=mask, other=-float("inf")).to(tl.float32)
    x2 = tl.load(logits_ptr + offs2, mask=mask, other=-float("inf")).to(tl.float32)

    b1 = tl.load(b1_ptr + n_offsets, mask=mask_n, other=0.0).to(tl.float32)
    b2 = tl.load(b2_ptr + n_offsets, mask=mask_n, other=0.0).to(tl.float32)

    x1 = x1 + b1[None, :]
    x2 = x2 + b2[None, :]

    logP_raw = x1 - lse1[:, None]
    logQ_raw = x2 - lse2[:, None]

    P = tl.exp(logP_raw)
    Q = tl.exp(logQ_raw)

    P = tl.where(mask, P, 0.0)
    Q = tl.where(mask, Q, 0.0)

    logP = tl.where(P > 0.0, logP_raw, 0.0)
    logQ = tl.where(Q > 0.0, logQ_raw, 0.0)

    s = P + Q
    logM = tl.log(s + _EPS) - _LOG2

    term = 0.5 * (P * (logP - logM) + Q * (logQ - logM))
    acc = tl.sum(term, axis=1)

    acc = tl.where(mask_m, acc, 0.0)
    tl.atomic_add(out_ptr + m_offsets, acc, mask=mask_m)


def fused_linear_jsd(X: torch.Tensor, W1: torch.Tensor, B1: torch.Tensor, W2: torch.Tensor, B2: torch.Tensor) -> torch.Tensor:
    if not (X.is_cuda and W1.is_cuda and W2.is_cuda and B1.is_cuda and B2.is_cuda):
        raise ValueError("All inputs must be CUDA tensors")
    if X.dtype != torch.float16:
        X = X.to(torch.float16)
    if W1.dtype != torch.float16:
        W1 = W1.to(torch.float16)
    if W2.dtype != torch.float16:
        W2 = W2.to(torch.float16)
    if B1.dtype != torch.float32:
        B1 = B1.to(torch.float32)
    if B2.dtype != torch.float32:
        B2 = B2.to(torch.float32)

    if not X.is_contiguous():
        X = X.contiguous()
    if not B1.is_contiguous():
        B1 = B1.contiguous()
    if not B2.is_contiguous():
        B2 = B2.contiguous()

    M, K = X.shape
    if W1.shape[0] != K or W2.shape[0] != K:
        raise ValueError("Weight K dim mismatch")
    if W1.shape[1] != W2.shape[1]:
        raise ValueError("W1/W2 N mismatch")
    N = W1.shape[1]
    if B1.numel() != N or B2.numel() != N:
        raise ValueError("Bias N mismatch")

    Wcat = _get_wcat(W1, W2)
    logits = torch.mm(X, Wcat)
    if not logits.is_contiguous():
        logits = logits.contiguous()

    BLOCK_N = 256
    BLOCK_M = 4
    nblocks = triton.cdiv(N, BLOCK_N)

    max1 = torch.empty((M, nblocks), device=X.device, dtype=torch.float32)
    sum1 = torch.empty((M, nblocks), device=X.device, dtype=torch.float32)
    max2 = torch.empty((M, nblocks), device=X.device, dtype=torch.float32)
    sum2 = torch.empty((M, nblocks), device=X.device, dtype=torch.float32)

    stride_l0 = logits.stride(0)
    stride_l1 = logits.stride(1)
    stride_o0 = max1.stride(0)
    stride_o1 = max1.stride(1)

    grid_stats = (triton.cdiv(M, BLOCK_M), nblocks)
    _block_stats_kernel[grid_stats](
        logits,
        B1,
        B2,
        max1,
        sum1,
        max2,
        sum2,
        stride_l0=stride_l0,
        stride_l1=stride_l1,
        stride_o0=stride_o0,
        stride_o1=stride_o1,
        M=M,
        N=N,
        BLOCK_M=BLOCK_M,
        BLOCK_N=BLOCK_N,
        num_warps=4,
    )

    lse1 = torch.empty((M,), device=X.device, dtype=torch.float32)
    lse2 = torch.empty((M,), device=X.device, dtype=torch.float32)

    BLOCK_M_R = 16
    grid_reduce = (triton.cdiv(M, BLOCK_M_R),)
    _reduce_lse_kernel[grid_reduce](
        max1,
        sum1,
        max2,
        sum2,
        lse1,
        lse2,
        stride_in0=stride_o0,
        stride_in1=stride_o1,
        M=M,
        NBLOCKS=nblocks,
        BLOCK_M=BLOCK_M_R,
        num_warps=2,
    )

    out = torch.zeros((M,), device=X.device, dtype=torch.float32)

    grid_jsd = (triton.cdiv(M, BLOCK_M), nblocks)
    _jsd_kernel[grid_jsd](
        logits,
        B1,
        B2,
        lse1,
        lse2,
        out,
        stride_l0=stride_l0,
        stride_l1=stride_l1,
        M=M,
        N=N,
        BLOCK_M=BLOCK_M,
        BLOCK_N=BLOCK_N,
        num_warps=4,
    )

    return out
'''
        return {"code": code}
