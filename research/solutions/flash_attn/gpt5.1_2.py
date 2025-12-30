import textwrap


class Solution:
    def solve(self, spec_path: str = None) -> dict:
        kernel_code = textwrap.dedent('''\
import math
import torch
import triton
import triton.language as tl


@triton.jit
def flash_attn_fwd_kernel(
    Q, K, V, Out,
    sm_scale,
    M, N,
    stride_qb, stride_qm, stride_qd,
    stride_kb, stride_kn, stride_kd,
    stride_vb, stride_vn, stride_vd,
    stride_ob, stride_om, stride_od,
    BH,
    D_HEAD,
    D_VALUE,
    causal: tl.constexpr,
    BLOCK_M: tl.constexpr,
    BLOCK_N: tl.constexpr,
    BLOCK_DHEAD: tl.constexpr,
    BLOCK_DVALUE: tl.constexpr,
):
    pid_m = tl.program_id(0)
    pid_bh = tl.program_id(1)

    if pid_bh >= BH:
        return

    offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
    offs_dq = tl.arange(0, BLOCK_DHEAD)
    offs_dv = tl.arange(0, BLOCK_DVALUE)

    q_mask = offs_m < M
    dq_mask = offs_dq < D_HEAD
    dv_mask = offs_dv < D_VALUE

    # Load Q block [BLOCK_M, BLOCK_DHEAD]
    q_ptrs = Q + pid_bh * stride_qb + offs_m[:, None] * stride_qm + offs_dq[None, :] * stride_qd
    q = tl.load(q_ptrs, mask=q_mask[:, None] & dq_mask[None, :], other=0.0)
    q = q.to(tl.float32)

    neg_inf = float("-inf")
    m_i_init = tl.full((BLOCK_M,), neg_inf, dtype=tl.float32)
    l_i_init = tl.zeros((BLOCK_M,), dtype=tl.float32)

    # For rows outside [0, M), use benign initial values to avoid NaNs
    m_i = tl.where(q_mask, m_i_init, 0.0)
    l_i = tl.where(q_mask, l_i_init, 1.0)

    acc = tl.zeros((BLOCK_M, BLOCK_DVALUE), dtype=tl.float32)

    # Loop over keys/values blocks
    for start_n in range(0, N, BLOCK_N):
        offs_n = start_n + tl.arange(0, BLOCK_N)
        n_mask = offs_n < N

        k_ptrs = K + pid_bh * stride_kb + offs_n[:, None] * stride_kn + offs_dq[None, :] * stride_kd
        v_ptrs = V + pid_bh * stride_vb + offs_n[:, None] * stride_vn + offs_dv[None, :] * stride_vd

        k = tl.load(k_ptrs, mask=n_mask[:, None] & dq_mask[None, :], other=0.0)
        v = tl.load(v_ptrs, mask=n_mask[:, None] & dv_mask[None, :], other=0.0)

        k = k.to(tl.float32)
        v = v.to(tl.float32)

        # [BLOCK_M, BLOCK_N] = [BLOCK_M, D] x [D, BLOCK_N]
        qk = tl.dot(q, tl.trans(k))
        qk = qk * sm_scale

        # Build mask: valid positions and (optionally) causal constraint
        mask = n_mask[None, :] & q_mask[:, None]
        if causal:
            q_idx = offs_m[:, None]
            k_idx = offs_n[None, :]
            causal_mask = k_idx <= q_idx
            mask = mask & causal_mask

        qk = tl.where(mask, qk, neg_inf)

        # Streaming softmax update
        m_i_block = tl.max(qk, axis=1)
        m_i_new = tl.maximum(m_i, m_i_block)

        p = tl.exp(qk - m_i_new[:, None])
        alpha = tl.exp(m_i - m_i_new)

        l_i_new = l_i * alpha + tl.sum(p, axis=1)
        acc = acc * alpha[:, None] + tl.dot(p, v)

        m_i = m_i_new
        l_i = l_i_new

    # Normalize
    output = acc / l_i[:, None]

    o_ptrs = Out + pid_bh * stride_ob + offs_m[:, None] * stride_om + offs_dv[None, :] * stride_od
    tl.store(o_ptrs, output.to(tl.float16), mask=q_mask[:, None] & dv_mask[None, :])


def _next_power_of_2(x: int) -> int:
    if x < 1:
        return 1
    return 1 << (x - 1).bit_length()


def _flash_attn_pytorch(Q: torch.Tensor, K: torch.Tensor, V: torch.Tensor, causal: bool = True) -> torch.Tensor:
    Z, H, M, Dq = Q.shape
    Zk, Hk, N, Dk = K.shape
    Zv, Hv, Nv, Dv = V.shape

    assert Z == Zk == Zv, "Batch dimension mismatch"
    assert H == Hk == Hv, "Head dimension mismatch"
    assert N == Nv, "Sequence length mismatch between K and V"
    assert Dq == Dk, "Q and K must have the same feature dimension"

    scale = 1.0 / math.sqrt(Dq)

    q = Q.to(torch.float32)
    k = K.to(torch.float32)
    v = V.to(torch.float32)

    scores = torch.matmul(q, k.transpose(-2, -1)) * scale  # (Z, H, M, N)

    if causal:
        mask = torch.triu(torch.ones(M, N, device=scores.device, dtype=torch.bool), diagonal=1)
        scores = scores.masked_fill(mask.view(1, 1, M, N), float("-inf"))

    attn = torch.softmax(scores, dim=-1)
    out = torch.matmul(attn, v)
    return out.to(torch.float16)


def flash_attn(Q: torch.Tensor, K: torch.Tensor, V: torch.Tensor, causal: bool = True) -> torch.Tensor:
    """
    Flash attention computation with optional causal masking.

    Args:
        Q: Tensor of shape (Z, H, M, Dq), dtype float16, CUDA.
        K: Tensor of shape (Z, H, N, Dq), dtype float16, CUDA.
        V: Tensor of shape (Z, H, N, Dv), dtype float16, CUDA.
        causal: Whether to apply causal masking.

    Returns:
        Tensor of shape (Z, H, M, Dv), dtype float16, CUDA.
    """
    assert Q.is_cuda and K.is_cuda and V.is_cuda, "All tensors must be on CUDA"
    assert Q.dtype == torch.float16 and K.dtype == torch.float16 and V.dtype == torch.float16, \
        "Q, K, V must be float16"

    Z, H, M, Dq = Q.shape
    Zk, Hk, N, Dk = K.shape
    Zv, Hv, Nv, Dv = V.shape

    assert Z == Zk == Zv, "Batch dimension mismatch"
    assert H == Hk == Hv, "Head dimension mismatch"
    assert N == Nv, "Sequence length mismatch between K and V"
    assert Dq == Dk, "Q and K must have the same feature dimension"

    # For larger feature sizes, fall back to PyTorch implementation
    if Dq > 64 or Dv > 64:
        return _flash_attn_pytorch(Q, K, V, causal)

    Qc = Q.contiguous()
    Kc = K.contiguous()
    Vc = V.contiguous()

    BH = Z * H

    Q_flat = Qc.view(BH, M, Dq)
    K_flat = Kc.view(BH, N, Dq)
    V_flat = Vc.view(BH, N, Dv)

    Out_flat = torch.empty((BH, M, Dv), device=Q.device, dtype=torch.float16)

    stride_qb, stride_qm, stride_qd = Q_flat.stride()
    stride_kb, stride_kn, stride_kd = K_flat.stride()
    stride_vb, stride_vn, stride_vd = V_flat.stride()
    stride_ob, stride_om, stride_od = Out_flat.stride()

    BLOCK_M = 64
    BLOCK_N = 64
    BLOCK_DHEAD = _next_power_of_2(Dq)
    BLOCK_DVALUE = _next_power_of_2(Dv)

    # Ensure block sizes are within reasonable limits
    if BLOCK_DHEAD > 64 or BLOCK_DVALUE > 64:
        return _flash_attn_pytorch(Q, K, V, causal)

    grid = (triton.cdiv(M, BLOCK_M), BH)

    sm_scale = 1.0 / math.sqrt(Dq)

    flash_attn_fwd_kernel[grid](
        Q_flat, K_flat, V_flat, Out_flat,
        sm_scale,
        M, N,
        stride_qb, stride_qm, stride_qd,
        stride_kb, stride_kn, stride_kd,
        stride_vb, stride_vn, stride_vd,
        stride_ob, stride_om, stride_od,
        BH,
        Dq,
        Dv,
        causal=causal,
        BLOCK_M=BLOCK_M,
        BLOCK_N=BLOCK_N,
        BLOCK_DHEAD=BLOCK_DHEAD,
        BLOCK_DVALUE=BLOCK_DVALUE,
        num_warps=4,
        num_stages=2,
    )

    return Out_flat.view(Z, H, M, Dv)
''')
        return {"code": kernel_code}