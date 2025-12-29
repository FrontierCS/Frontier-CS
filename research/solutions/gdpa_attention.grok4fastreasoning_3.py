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
def flash_attn_kernel(
    q_ptr,
    gq_ptr,
    k_ptr,
    gk_ptr,
    v_ptr,
    o_ptr,
    M: tl.int32,
    N: tl.int32,
    Dq: tl.int32,
    Dv: tl.int32,
    scale: tl.float32,
    H: tl.int32,
    BLOCK_M: tl.constexpr,
    BLOCK_N: tl.constexpr,
):
    b = tl.program_id(0)
    m_start = tl.program_id(1) * BLOCK_M
    z = b // H
    h = b % H
    total_per_z_q = H * M * Dq
    stride_bh_q = M * Dq
    q_base = q_ptr + z * total_per_z_q + h * stride_bh_q
    gq_base = gq_ptr + z * total_per_z_q + h * stride_bh_q
    total_per_z_k = H * N * Dq
    stride_bh_k = N * Dq
    k_base = k_ptr + z * total_per_z_k + h * stride_bh_k
    gk_base = gk_ptr + z * total_per_z_k + h * stride_bh_k
    total_per_z_v = H * N * Dv
    stride_bh_v = N * Dv
    v_base = v_ptr + z * total_per_z_v + h * stride_bh_v
    o_base = o_ptr + z * total_per_z_v + h * stride_bh_v
    m_end = tl.minimum(m_start + BLOCK_M, M)
    BM = m_end - m_start
    q_block_ptr = tl.make_block_ptr(
        base=q_base,
        shape=(M, Dq),
        strides=(Dq, 1),
        block_shape=(BLOCK_M, Dq),
        order=(1, 0),
    )
    q_block = tl.load(q_block_ptr + (m_start, 0), mask=(BM, Dq), other=0.0)
    gq_block_ptr = tl.make_block_ptr(
        base=gq_base,
        shape=(M, Dq),
        strides=(Dq, 1),
        block_shape=(BLOCK_M, Dq),
        order=(1, 0),
    )
    gq_block = tl.load(gq_block_ptr + (m_start, 0), mask=(BM, Dq), other=0.0)
    sig_gq = tl.sigmoid(tl.cast(gq_block, tl.float32))
    qg = q_block * tl.cast(sig_gq, tl.float16)
    acc_o = tl.zeros((BLOCK_M, Dv), dtype=tl.float32)
    m = tl.full((BLOCK_M,), tl.float32(-1e9), dtype=tl.float32)
    l = tl.zeros((BLOCK_M,), dtype=tl.float32)
    num_n_tiles = (N + BLOCK_N - 1) // BLOCK_N
    for n_idx in range(num_n_tiles):
        n_start = n_idx * BLOCK_N
        n_end = tl.minimum(n_start + BLOCK_N, N)
        BN = n_end - n_start
        k_block_ptr = tl.make_block_ptr(
            base=k_base,
            shape=(N, Dq),
            strides=(Dq, 1),
            block_shape=(BLOCK_N, Dq),
            order=(1, 0),
        )
        k_block = tl.load(k_block_ptr + (n_start, 0), mask=(BN, Dq), other=0.0)
        gk_block_ptr = tl.make_block_ptr(
            base=gk_base,
            shape=(N, Dq),
            strides=(Dq, 1),
            block_shape=(BLOCK_N, Dq),
            order=(1, 0),
        )
        gk_block = tl.load(gk_block_ptr + (n_start, 0), mask=(BN, Dq), other=0.0)
        sig_gk = tl.sigmoid(tl.cast(gk_block, tl.float32))
        kg = k_block * tl.cast(sig_gk, tl.float16)
        qg_f = tl.cast(qg, tl.float32)
        kg_f = tl.cast(kg, tl.float32)
        s = tl.dot(qg_f, tl.trans(kg_f)) * scale
        col_idx = tl.arange(0, BLOCK_N)
        n_mask = col_idx < BN
        s = tl.where(n_mask[None, :], s, tl.float32(-1e9))
        m_local = tl.max(s, axis=1)
        p = tl.exp(s - m_local[:, None])
        l_local = tl.sum(p, axis=1)
        m_new = tl.maximum(m, m_local)
        alpha = tl.exp(m - m_new)[:, None]
        beta = tl.exp(m_local - m_new)[:, None]
        v_block_ptr = tl.make_block_ptr(
            base=v_base,
            shape=(N, Dv),
            strides=(Dv, 1),
            block_shape=(BLOCK_N, Dv),
            order=(1, 0),
        )
        v_block = tl.load(v_block_ptr + (n_start, 0), mask=(BN, Dv), other=0.0)
        v_f = tl.cast(v_block, tl.float32)
        po = tl.dot(p, v_f)
        acc_o = alpha * acc_o + beta * po
        l = alpha[:, 0] * l + tl.exp(m_local - m_new) * l_local
        m = m_new
    row_idx = tl.arange(0, BLOCK_M)
    row_mask = row_idx < BM
    l_safe = tl.where(row_mask, l, tl.float32(1.0))
    acc_o = acc_o / l_safe[:, None]
    o_block = tl.cast(acc_o, tl.float16)
    o_block_ptr = tl.make_block_ptr(
        base=o_base,
        shape=(M, Dv),
        strides=(Dv, 1),
        block_shape=(BLOCK_M, Dv),
        order=(1, 0),
    )
    tl.store(o_block_ptr + (m_start, 0), o_block, mask=(BM, Dv))

def gdpa_attn(Q: torch.Tensor, K: torch.Tensor, V: torch.Tensor, GQ: torch.Tensor, GK: torch.Tensor) -> torch.Tensor:
    Z, H, M, Dq = Q.shape
    N = K.shape[2]
    Dv = V.shape[3]
    output = torch.empty(Z, H, M, Dv, dtype=torch.float16, device=Q.device)
    B = Z * H
    BLOCK_M = 128
    BLOCK_N = 128
    scale_val = 1.0 / math.sqrt(Dq)
    num_m_blocks = (M + BLOCK_M - 1) // BLOCK_M
    flash_attn_kernel[(B, num_m_blocks)](
        Q.data_ptr(),
        GQ.data_ptr(),
        K.data_ptr(),
        GK.data_ptr(),
        V.data_ptr(),
        output.data_ptr(),
        M,
        N,
        Dq,
        Dv,
        scale_val,
        H,
        BLOCK_M=BLOCK_M,
        BLOCK_N=BLOCK_N,
        num_stages=3
    )
    return output
"""
        return {"code": code}