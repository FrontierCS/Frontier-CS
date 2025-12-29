class Solution:
    def solve(self, spec_path: str = None) -> dict:
        code = """
import torch
import triton
import triton.language as tl
import math

@triton.jit
def flash_attn_kernel(
    Q_PTR, K_PTR, V_PTR, O_PTR,
    M: tl.constexpr, N: tl.constexpr, D: tl.constexpr,
    BLOCK_M: tl.constexpr, BLOCK_N: tl.constexpr, BLOCK_D: tl.constexpr,
    CAUSAL: tl.constexpr,
    STRIDE_QM, STRIDE_QD,
    STRIDE_KN, STRIDE_KD,
    STRIDE_VN, STRIDE_VD,
    STRIDE_OM, STRIDE_OD,
    scale: tl.float32
):
    pid_m = tl.program_id(0)
    lo = pid_m * BLOCK_M
    m_end = (pid_m + 1) * BLOCK_M
    if m_end > M:
        m_end = M
    offs_m = lo + tl.arange(0, BLOCK_M)
    offs_n_base = tl.arange(0, BLOCK_N)
    offs_d = tl.arange(0, BLOCK_D)
    q_ptr = Q_PTR + offs_m[:, None] * STRIDE_QM + offs_d[None, :] * STRIDE_QD
    q_mask = (offs_m[:, None] < M) & (offs_d[None, :] < D)
    q = tl.load(q_ptr, mask=q_mask, other=0.0).to(tl.float32) * scale
    m_i = tl.full([BLOCK_M], -1e9, dtype=tl.float32)
    l_i = tl.zeros([BLOCK_M], dtype=tl.float32)
    o = tl.zeros([BLOCK_M, BLOCK_D], dtype=tl.float32)
    num_blks_n = (N + BLOCK_N - 1) // BLOCK_N
    for blk_n in range(num_blks_n):
        start_n = blk_n * BLOCK_N
        if CAUSAL and start_n >= m_end:
            break
        offs_n = start_n + offs_n_base
        k_ptr = K_PTR + offs_n[None, :] * STRIDE_KN + offs_d[:, None] * STRIDE_KD
        k_mask = (offs_n[None, :] < N) & (offs_d[:, None] < D)
        k = tl.load(k_ptr, mask=k_mask, other=0.0).to(tl.float32)
        v_ptr = V_PTR + offs_n[:, None] * STRIDE_VN + offs_d[None, :] * STRIDE_VD
        v_mask = (offs_n[:, None] < N) & (offs_d[None, :] < D)
        v = tl.load(v_ptr, mask=v_mask, other=0.0).to(tl.float32)
        s = tl.dot(q, k)
        if CAUSAL:
            i_idx = lo + tl.arange(0, BLOCK_M)[:, None]
            j_idx = start_n + tl.arange(0, BLOCK_N)[None, :]
            causal_mask = i_idx >= j_idx
            s = tl.where(causal_mask, s, -1e9)
        m_new = tl.maximum(m_i, tl.max(s, 1))
        exp_scale = tl.exp(m_i - m_new)
        p = tl.exp(s - m_new[:, None])
        l_new = l_i * exp_scale + tl.sum(p, 1)
        p_v = tl.dot(p, v)
        o = (o * (l_i * exp_scale)[:, None] + p_v) / l_new[:, None]
        m_i = m_new
        l_i = l_new
    o_ptr = O_PTR + offs_m[:, None] * STRIDE_OM + offs_d[None, :] * STRIDE_OD
    o_mask = (offs_m[:, None] < M) & (offs_d[None, :] < D)
    tl.store(o_ptr, o.to(tl.float16), mask=o_mask)

def flash_attn(Q: torch.Tensor, K: torch.Tensor, V: torch.Tensor, causal: bool = True) -> torch.Tensor:
    Z, H, M, Dq = Q.shape
    N = K.shape[2]
    Dv = V.shape[3]
    assert N == M
    assert K.shape[3] == Dq
    assert V.shape == (Z, H, N, Dv)
    out = torch.empty(Z, H, M, Dv, dtype=Q.dtype, device=Q.device)
    BLOCK_M = 64
    BLOCK_N = 64
    BLOCK_D = 64
    scale = 1.0 / math.sqrt(Dq)
    for z in range(Z):
        for h in range(H):
            q = Q[z, h]
            k = K[z, h]
            v = V[z, h]
            o = out[z, h]
            es = q.element_size()
            stride_qm = q.stride(0) // es
            stride_qd = q.stride(1) // es
            stride_kn = k.stride(0) // es
            stride_kd = k.stride(1) // es
            stride_vn = v.stride(0) // es
            stride_vd = v.stride(1) // es
            stride_om = o.stride(0) // es
            stride_od = o.stride(1) // es
            grid = (triton.cdiv(M, BLOCK_M),)
            flash_attn_kernel[grid](
                q, k, v, o,
                M=M, N=N, D=BLOCK_D,
                BLOCK_M=BLOCK_M, BLOCK_N=BLOCK_N, BLOCK_D=BLOCK_D,
                CAUSAL=causal,
                STRIDE_QM=stride_qm, STRIDE_QD=stride_qd,
                STRIDE_KN=stride_kn, STRIDE_KD=stride_kd,
                STRIDE_VN=stride_vn, STRIDE_VD=stride_vd,
                STRIDE_OM=stride_om, STRIDE_OD=stride_od,
                scale=scale
            )
    return out
"""
        return {"code": code}