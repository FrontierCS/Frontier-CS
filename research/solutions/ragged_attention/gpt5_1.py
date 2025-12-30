import math
import torch
import triton
import triton.language as tl


@triton.jit
def _ragged_attn_kernel(
    Q, K, V, O, ROW_LENS,
    M, N,
    stride_qm, stride_qd,
    stride_km, stride_kd,
    stride_vm, stride_vd,
    stride_om, stride_od,
    scale: tl.constexpr,
    BLOCK_M: tl.constexpr, BLOCK_N: tl.constexpr,
    D_HEAD: tl.constexpr, D_VALUE: tl.constexpr
):
    pid_m = tl.program_id(0)
    offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
    row_mask = offs_m < M

    # Load Q block [BM, D_HEAD] in f32
    offs_d = tl.arange(0, D_HEAD)
    q_ptrs = Q + offs_m[:, None] * stride_qm + offs_d[None, :] * stride_qd
    q = tl.load(q_ptrs, mask=row_mask[:, None], other=0.0)
    q = q.to(tl.float32)

    # Load row lengths
    lens = tl.load(ROW_LENS + offs_m, mask=row_mask, other=0).to(tl.int32)

    # Init streaming softmax state
    m_i = tl.full((BLOCK_M,), -float("inf"), dtype=tl.float32)
    l_i = tl.zeros((BLOCK_M,), dtype=tl.float32)
    acc = tl.zeros((BLOCK_M, D_VALUE), dtype=tl.float32)

    # Iterate over K/V blocks along N
    offs_n = tl.arange(0, BLOCK_N)
    for start_n in range(0, N, BLOCK_N):
        n_idx = start_n + offs_n
        n_mask = n_idx < N

        # Load K [BLOCK_N, D_HEAD] and V [BLOCK_N, D_VALUE] in f32
        k_ptrs = K + n_idx[:, None] * stride_km + offs_d[None, :] * stride_kd
        k = tl.load(k_ptrs, mask=n_mask[:, None], other=0.0).to(tl.float32)

        # Compute scores [BLOCK_M, BLOCK_N]
        scores = tl.dot(q, tl.trans(k)) * scale

        # Valid mask for ragged attention
        # valid if: row in bounds, n_idx < lens[row], and n_idx < N
        # Broadcast lens and n_idx to [BM, BN]
        valid = row_mask[:, None] & n_mask[None, :]
        valid = valid & (n_idx[None, :] < lens[:, None])

        # Mask scores for invalid positions
        scores = tl.where(valid, scores, -float("inf"))

        # Compute new row-wise max
        smax = tl.max(scores, axis=1)
        new_m = tl.maximum(m_i, smax)

        # Compute exp factors
        p_prev_scale = tl.exp(m_i - new_m)

        # Compute p = exp(scores - new_m) where valid else 0
        p = tl.where(valid, tl.exp(scores - new_m[:, None]), 0.0)

        # Update l_i and acc
        p_sum = tl.sum(p, axis=1)
        l_i = l_i * p_prev_scale + p_sum

        # Load V after p computed to save some bandwidth if desired
        offs_v = tl.arange(0, D_VALUE)
        v_ptrs = V + n_idx[:, None] * stride_vm + offs_v[None, :] * stride_vd
        v = tl.load(v_ptrs, mask=n_mask[:, None], other=0.0).to(tl.float32)

        pv = tl.dot(p, v)
        acc = acc * p_prev_scale[:, None] + pv

        # Update running max
        m_i = new_m

    # Normalize and store
    li_safe = tl.where(row_mask, l_i, 1.0)
    out = acc / li_safe[:, None]
    out = out.to(tl.float16)

    o_ptrs = O + offs_m[:, None] * stride_om + tl.arange(0, D_VALUE)[None, :] * stride_od
    tl.store(o_ptrs, out, mask=row_mask[:, None])


def ragged_attn(Q: torch.Tensor, K: torch.Tensor, V: torch.Tensor, row_lens: torch.Tensor) -> torch.Tensor:
    assert Q.is_cuda and K.is_cuda and V.is_cuda and row_lens.is_cuda, "All tensors must be CUDA tensors"
    assert Q.dtype == torch.float16 and K.dtype == torch.float16 and V.dtype == torch.float16, "Q, K, V must be float16"
    assert Q.dim() == 2 and K.dim() == 2 and V.dim() == 2, "Q, K, V must be 2D"
    assert Q.shape[1] == K.shape[1], "Q and K must have same feature dimension"
    assert K.shape[0] == V.shape[0], "K and V must have same number of rows"
    assert row_lens.shape[0] == Q.shape[0], "row_lens length must match Q rows"

    M, D = Q.shape
    N = K.shape[0]
    Dv = V.shape[1]

    O = torch.empty((M, Dv), device=Q.device, dtype=torch.float16)

    BLOCK_M = 64
    BLOCK_N = 128
    num_warps = 4
    num_stages = 2

    scale = 1.0 / math.sqrt(D)

    grid = (triton.cdiv(M, BLOCK_M),)

    _ragged_attn_kernel[grid](
        Q, K, V, O, row_lens,
        M, N,
        Q.stride(0), Q.stride(1),
        K.stride(0), K.stride(1),
        V.stride(0), V.stride(1),
        O.stride(0), O.stride(1),
        scale,
        BLOCK_M=BLOCK_M, BLOCK_N=BLOCK_N,
        D_HEAD=D, D_VALUE=Dv,
        num_warps=num_warps, num_stages=num_stages
    )
    return O


class Solution:
    def solve(self, spec_path: str = None) -> dict:
        code = r'''
import math
import torch
import triton
import triton.language as tl


@triton.jit
def _ragged_attn_kernel(
    Q, K, V, O, ROW_LENS,
    M, N,
    stride_qm, stride_qd,
    stride_km, stride_kd,
    stride_vm, stride_vd,
    stride_om, stride_od,
    scale: tl.constexpr,
    BLOCK_M: tl.constexpr, BLOCK_N: tl.constexpr,
    D_HEAD: tl.constexpr, D_VALUE: tl.constexpr
):
    pid_m = tl.program_id(0)
    offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
    row_mask = offs_m < M

    # Load Q block [BM, D_HEAD] in f32
    offs_d = tl.arange(0, D_HEAD)
    q_ptrs = Q + offs_m[:, None] * stride_qm + offs_d[None, :] * stride_qd
    q = tl.load(q_ptrs, mask=row_mask[:, None], other=0.0)
    q = q.to(tl.float32)

    # Load row lengths
    lens = tl.load(ROW_LENS + offs_m, mask=row_mask, other=0).to(tl.int32)

    # Init streaming softmax state
    m_i = tl.full((BLOCK_M,), -float("inf"), dtype=tl.float32)
    l_i = tl.zeros((BLOCK_M,), dtype=tl.float32)
    acc = tl.zeros((BLOCK_M, D_VALUE), dtype=tl.float32)

    # Iterate over K/V blocks along N
    offs_n = tl.arange(0, BLOCK_N)
    for start_n in range(0, N, BLOCK_N):
        n_idx = start_n + offs_n
        n_mask = n_idx < N

        # Load K [BLOCK_N, D_HEAD] and V [BLOCK_N, D_VALUE] in f32
        k_ptrs = K + n_idx[:, None] * stride_km + offs_d[None, :] * stride_kd
        k = tl.load(k_ptrs, mask=n_mask[:, None], other=0.0).to(tl.float32)

        # Compute scores [BLOCK_M, BLOCK_N]
        scores = tl.dot(q, tl.trans(k)) * scale

        # Valid mask for ragged attention
        # valid if: row in bounds, n_idx < lens[row], and n_idx < N
        # Broadcast lens and n_idx to [BM, BN]
        valid = row_mask[:, None] & n_mask[None, :]
        valid = valid & (n_idx[None, :] < lens[:, None])

        # Mask scores for invalid positions
        scores = tl.where(valid, scores, -float("inf"))

        # Compute new row-wise max
        smax = tl.max(scores, axis=1)
        new_m = tl.maximum(m_i, smax)

        # Compute exp factors
        p_prev_scale = tl.exp(m_i - new_m)

        # Compute p = exp(scores - new_m) where valid else 0
        p = tl.where(valid, tl.exp(scores - new_m[:, None]), 0.0)

        # Update l_i and acc
        p_sum = tl.sum(p, axis=1)
        l_i = l_i * p_prev_scale + p_sum

        # Load V after p computed to save some bandwidth if desired
        offs_v = tl.arange(0, D_VALUE)
        v_ptrs = V + n_idx[:, None] * stride_vm + offs_v[None, :] * stride_vd
        v = tl.load(v_ptrs, mask=n_mask[:, None], other=0.0).to(tl.float32)

        pv = tl.dot(p, v)
        acc = acc * p_prev_scale[:, None] + pv

        # Update running max
        m_i = new_m

    # Normalize and store
    li_safe = tl.where(row_mask, l_i, 1.0)
    out = acc / li_safe[:, None]
    out = out.to(tl.float16)

    o_ptrs = O + offs_m[:, None] * stride_om + tl.arange(0, D_VALUE)[None, :] * stride_od
    tl.store(o_ptrs, out, mask=row_mask[:, None])


def ragged_attn(Q: torch.Tensor, K: torch.Tensor, V: torch.Tensor, row_lens: torch.Tensor) -> torch.Tensor:
    assert Q.is_cuda and K.is_cuda and V.is_cuda and row_lens.is_cuda, "All tensors must be CUDA tensors"
    assert Q.dtype == torch.float16 and K.dtype == torch.float16 and V.dtype == torch.float16, "Q, K, V must be float16"
    assert Q.dim() == 2 and K.dim() == 2 and V.dim() == 2, "Q, K, V must be 2D"
    assert Q.shape[1] == K.shape[1], "Q and K must have same feature dimension"
    assert K.shape[0] == V.shape[0], "K and V must have same number of rows"
    assert row_lens.shape[0] == Q.shape[0], "row_lens length must match Q rows"

    M, D = Q.shape
    N = K.shape[0]
    Dv = V.shape[1]

    O = torch.empty((M, Dv), device=Q.device, dtype=torch.float16)

    BLOCK_M = 64
    BLOCK_N = 128
    num_warps = 4
    num_stages = 2

    scale = 1.0 / math.sqrt(D)

    grid = (triton.cdiv(M, BLOCK_M),)

    _ragged_attn_kernel[grid](
        Q, K, V, O, row_lens,
        M, N,
        Q.stride(0), Q.stride(1),
        K.stride(0), K.stride(1),
        V.stride(0), V.stride(1),
        O.stride(0), O.stride(1),
        scale,
        BLOCK_M=BLOCK_M, BLOCK_N=BLOCK_N,
        D_HEAD=D, D_VALUE=Dv,
        num_warps=num_warps, num_stages=num_stages
    )
    return O
'''
        return {"code": code}