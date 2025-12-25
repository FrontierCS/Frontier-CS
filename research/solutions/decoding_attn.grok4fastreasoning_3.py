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
def stats_kernel(
    Q_PTR, K_PTR, STATS_PTR,
    stride_qz, stride_qh, stride_qm, stride_qd,
    stride_kz, stride_kh, stride_kn, stride_kd,
    stride_statsz, stride_statsh, stride_statsm, stride_statsd,
    Z, H, M, N, D,
    BLOCK_N: tl.constexpr,
    scale: tl.float32
):
    pid = tl.program_id(0)
    z = pid // H
    h = pid % H
    m = 0
    q_offset = z * stride_qz + h * stride_qh + m * stride_qm
    q = tl.load(Q_PTR + q_offset + tl.arange(0, D) * stride_qd).to(tl.float32)
    m_s = float("-inf")
    sum_exp_f = 0.0
    k_base = K_PTR + z * stride_kz + h * stride_kh
    start_n = 0
    while start_n < N:
        offs_n = start_n + tl.arange(0, BLOCK_N)
        mask = offs_n < N
        k_ptrs = k_base + offs_n[:, None] * stride_kn + tl.arange(0, D)[None, :] * stride_kd
        k = tl.load(k_ptrs, mask=mask[:, None], other=0.0).to(tl.float32)
        s = tl.sum(q[None, :] * k, axis=1) * scale
        m_block = tl.max(tl.where(mask, s, float("-inf")), axis=0)
        m_new = tl.max(m_s, m_block)
        exp_old = tl.exp(m_s - m_new)
        s_adj = tl.where(mask, s - m_new, float("-inf"))
        exp_s_adj = tl.exp(s_adj)
        sum_exp_block = tl.sum(exp_s_adj, axis=0)
        sum_exp_f = sum_exp_f * exp_old + sum_exp_block
        m_s = m_new
        start_n += BLOCK_N
    stats_offset = z * stride_statsz + h * stride_statsh + m * stride_statsm
    tl.store(STATS_PTR + stats_offset + 0 * stride_statsd, m_s)
    tl.store(STATS_PTR + stats_offset + 1 * stride_statsd, sum_exp_f)

@triton.jit
def out_kernel(
    Q_PTR, K_PTR, V_PTR, O_PTR, STATS_PTR,
    stride_qz, stride_qh, stride_qm, stride_qd,
    stride_kz, stride_kh, stride_kn, stride_kd,
    stride_vz, stride_vh, stride_vn, stride_vd,
    stride_oz, stride_oh, stride_om, stride_od,
    stride_statsz, stride_statsh, stride_statsm, stride_statsd,
    Z, H, M, N, Dq, Dv,
    BLOCK_N: tl.constexpr,
    scale: tl.float32
):
    pid = tl.program_id(0)
    z = pid // H
    h = pid % H
    m = 0
    q_offset = z * stride_qz + h * stride_qh + m * stride_qm
    q = tl.load(Q_PTR + q_offset + tl.arange(0, Dq) * stride_qd).to(tl.float32)
    stats_offset = z * stride_statsz + h * stride_statsh + m * stride_statsm
    m_s = tl.load(STATS_PTR + stats_offset + 0 * stride_statsd)
    sum_exp_f = tl.load(STATS_PTR + stats_offset + 1 * stride_statsd)
    row_scale = tl.where(sum_exp_f > 0, 1.0 / sum_exp_f, 0.0)
    out = tl.zeros([Dv], dtype=tl.float32)
    k_base = K_PTR + z * stride_kz + h * stride_kh
    v_base = V_PTR + z * stride_vz + h * stride_vh
    start_n = 0
    while start_n < N:
        offs_n = start_n + tl.arange(0, BLOCK_N)
        mask = offs_n < N
        k_ptrs = k_base + offs_n[:, None] * stride_kn + tl.arange(0, Dq)[None, :] * stride_kd
        k = tl.load(k_ptrs, mask=mask[:, None], other=0.0).to(tl.float32)
        s = tl.sum(q[None, :] * k, axis=1) * scale
        s_adj = tl.where(mask, s - m_s, float("-inf"))
        exp_s_adj = tl.exp(s_adj)
        p = exp_s_adj * row_scale
        v_ptrs = v_base + offs_n[:, None] * stride_vn + tl.arange(0, Dv)[None, :] * stride_vd
        v = tl.load(v_ptrs, mask=mask[:, None], other=0.0).to(tl.float32)
        out += tl.sum(p[:, None] * v, axis=0)
        start_n += BLOCK_N
    o_offset = z * stride_oz + h * stride_oh + m * stride_om
    tl.store(O_PTR + o_offset + tl.arange(0, Dv) * stride_od, out.to(tl.float16))

def decoding_attn(Q: torch.Tensor, K: torch.Tensor, V: torch.Tensor) -> torch.Tensor:
    Z, H, M, Dq = Q.shape
    N, Dv = K.shape[-2], V.shape[-1]
    scale = 1 / math.sqrt(Dq)
    device = Q.device
    stats = torch.empty((Z, H, M, 2), dtype=torch.float32, device=device)
    O = torch.empty((Z, H, M, Dv), dtype=Q.dtype, device=device)
    s_q = Q.stride()
    s_k = K.stride()
    s_v = V.stride()
    s_o = O.stride()
    s_stats = stats.stride()
    BLOCK_N = 256
    grid = (Z * H,)
    stats_kernel[grid](
        Q, K, stats,
        s_q[0], s_q[1], s_q[2], s_q[3],
        s_k[0], s_k[1], s_k[2], s_k[3],
        s_stats[0], s_stats[1], s_stats[2], s_stats[3],
        Z, H, M, N, Dq,
        BLOCK_N=BLOCK_N,
        scale=scale,
    )
    out_kernel[grid](
        Q, K, V, O, stats,
        s_q[0], s_q[1], s_q[2], s_q[3],
        s_k[0], s_k[1], s_k[2], s_k[3],
        s_v[0], s_v[1], s_v[2], s_v[3],
        s_o[0], s_o[1], s_o[2], s_o[3],
        s_stats[0], s_stats[1], s_stats[2], s_stats[3],
        Z, H, M, N, Dq, Dv,
        BLOCK_N=BLOCK_N,
        scale=scale,
    )
    return O
"""
        return {"code": code}
