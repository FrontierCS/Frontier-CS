import torch
import triton
import triton.language as tl
import math

@triton.jit
def gdpa_attn_kernel(
    Q_PTR, K_PTR, V_PTR, GQ_PTR, GK_PTR, O_PTR,
    Z, H, M, N, Dq, Dv, scale,
    BLOCK_M: tl.constexpr,
    BLOCK_N: tl.constexpr,
    BLOCK_DMODEL: tl.constexpr,
    BLOCK_DV: tl.constexpr
):
    pid_batch = tl.program_id(0)
    pid_head = tl.program_id(1)
    pid_m = tl.program_id(2)

    offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
    offs_dm = tl.arange(0, BLOCK_DMODEL)
    offs_n_base = tl.arange(0, BLOCK_N)
    offs_dv = tl.arange(0, BLOCK_DV)

    q_ptrs = (
        Q_PTR + pid_batch * H * M * Dq + pid_head * M * Dq
        + offs_m[:, None] * Dq + offs_dm[None, :]
    )
    gq_ptrs = (
        GQ_PTR + pid_batch * H * M * Dq + pid_head * M * Dq
        + offs_m[:, None] * Dq + offs_dm[None, :]
    )
    mask_q = (offs_m[:, None] < M) & (offs_dm[None, :] < Dq)
    q = tl.load(q_ptrs, mask=mask_q, other=0.0)
    gq = tl.load(gq_ptrs, mask=mask_q, other=0.0)
    qg = q * tl.sigmoid(gq)
    qg = qg.to(tl.float32)

    row_max = tl.full((BLOCK_M,), float("-inf"), dtype=tl.float32)
    row_denom = tl.zeros((BLOCK_M,), dtype=tl.float32)
    acc_o = tl.zeros((BLOCK_M, BLOCK_DV), dtype=tl.float32)

    num_blocks = tl.cdiv(N, BLOCK_N)
    for start_n in range(num_blocks):
        offs_n = start_n * BLOCK_N + offs_n_base
        mask_n = offs_n < N
        mask_k = mask_n[:, None] & (offs_dm[None, :] < Dq)
        mask_v = mask_n[:, None] & (offs_dv[None, :] < Dv)

        k_ptrs = (
            K_PTR + pid_batch * H * N * Dq + pid_head * N * Dq
            + offs_n[:, None] * Dq + offs_dm[None, :]
        )
        gk_ptrs = (
            GK_PTR + pid_batch * H * N * Dq + pid_head * N * Dq
            + offs_n[:, None] * Dq + offs_dm[None, :]
        )
        k = tl.load(k_ptrs, mask=mask_k, other=0.0)
        gk = tl.load(gk_ptrs, mask=mask_k, other=0.0)
        kg = k * tl.sigmoid(gk)
        kg = kg.to(tl.float32)

        v_ptrs = (
            V_PTR + pid_batch * H * N * Dv + pid_head * N * Dv
            + offs_n[:, None] * Dv + offs_dv[None, :]
        )
        v = tl.load(v_ptrs, mask=mask_v, other=0.0).to(tl.float32)

        S = tl.dot(qg, tl.trans(kg)) * scale
        S = tl.where(mask_n[None, :], S, -1e9)
        m_block = tl.max(S, axis=1)
        delta = m_block - row_max
        scale_old = tl.exp(tl.where(delta > 0.0, -delta, 0.0))
        row_denom = row_denom * scale_old
        row_max = tl.where(delta > 0.0, m_block, row_max)
        p = tl.exp(S - row_max[:, None])
        row_denom += tl.sum(p, axis=1)

        partial_o = tl.dot(p, v)
        acc_o = acc_o * scale_old[:, None]
        acc_o += partial_o

    o = acc_o / row_denom[:, None]
    o = o.to(tl.float16)

    o_ptrs = (
        O_PTR + pid_batch * H * M * Dv + pid_head * M * Dv
        + offs_m[:, None] * Dv + offs_dv[None, :]
    )
    mask_o = (offs_m[:, None] < M) & (offs_dv[None, :] < Dv)
    tl.store(o_ptrs, o, mask=mask_o)

def gdpa_attn(Q: torch.Tensor, K: torch.Tensor, V: torch.Tensor, GQ: torch.Tensor, GK: torch.Tensor) -> torch.Tensor:
    Z, H, M, Dq = Q.shape
    _, _, N, _ = K.shape
    _, _, _, Dv = V.shape
    output = torch.empty(Z, H, M, Dv, dtype=torch.float16, device=Q.device)
    scale = 1.0 / math.sqrt(Dq)
    BLOCK_M = 64
    BLOCK_N = 64
    BLOCK_DMODEL = 64
    BLOCK_DV = 64
    def cdiv(n, b):
        return (n + b - 1) // b
    grid = (Z, H, cdiv(M, BLOCK_M))
    gdpa_attn_kernel[grid](
        Q, K, V, GQ, GK, output,
        Z=Z, H=H, M=M, N=N, Dq=Dq, Dv=Dv, scale=scale,
        BLOCK_M=BLOCK_M, BLOCK_N=BLOCK_N, BLOCK_DMODEL=BLOCK_DMODEL, BLOCK_DV=BLOCK_DV,
        num_stages=4,
        num_warps=8
    )
    return output

class Solution:
    def solve(self, spec_path: str = None) -> dict:
        code = """
import torch
import triton
import triton.language as tl
import math

@triton.jit
def gdpa_attn_kernel(
    Q_PTR, K_PTR, V_PTR, GQ_PTR, GK_PTR, O_PTR,
    Z, H, M, N, Dq, Dv, scale,
    BLOCK_M: tl.constexpr,
    BLOCK_N: tl.constexpr,
    BLOCK_DMODEL: tl.constexpr,
    BLOCK_DV: tl.constexpr
):
    pid_batch = tl.program_id(0)
    pid_head = tl.program_id(1)
    pid_m = tl.program_id(2)

    offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
    offs_dm = tl.arange(0, BLOCK_DMODEL)
    offs_n_base = tl.arange(0, BLOCK_N)
    offs_dv = tl.arange(0, BLOCK_DV)

    q_ptrs = (
        Q_PTR + pid_batch * H * M * Dq + pid_head * M * Dq
        + offs_m[:, None] * Dq + offs_dm[None, :]
    )
    gq_ptrs = (
        GQ_PTR + pid_batch * H * M * Dq + pid_head * M * Dq
        + offs_m[:, None] * Dq + offs_dm[None, :]
    )
    mask_q = (offs_m[:, None] < M) & (offs_dm[None, :] < Dq)
    q = tl.load(q_ptrs, mask=mask_q, other=0.0)
    gq = tl.load(gq_ptrs, mask=mask_q, other=0.0)
    qg = q * tl.sigmoid(gq)
    qg = qg.to(tl.float32)

    row_max = tl.full((BLOCK_M,), float("-inf"), dtype=tl.float32)
    row_denom = tl.zeros((BLOCK_M,), dtype=tl.float32)
    acc_o = tl.zeros((BLOCK_M, BLOCK_DV), dtype=tl.float32)

    num_blocks = tl.cdiv(N, BLOCK_N)
    for start_n in range(num_blocks):
        offs_n = start_n * BLOCK_N + offs_n_base
        mask_n = offs_n < N
        mask_k = mask_n[:, None] & (offs_dm[None, :] < Dq)
        mask_v = mask_n[:, None] & (offs_dv[None, :] < Dv)

        k_ptrs = (
            K_PTR + pid_batch * H * N * Dq + pid_head * N * Dq
            + offs_n[:, None] * Dq + offs_dm[None, :]
        )
        gk_ptrs = (
            GK_PTR + pid_batch * H * N * Dq + pid_head * N * Dq
            + offs_n[:, None] * Dq + offs_dm[None, :]
        )
        k = tl.load(k_ptrs, mask=mask_k, other=0.0)
        gk = tl.load(gk_ptrs, mask=mask_k, other=0.0)
        kg = k * tl.sigmoid(gk)
        kg = kg.to(tl.float32)

        v_ptrs = (
            V_PTR + pid_batch * H * N * Dv + pid_head * N * Dv
            + offs_n[:, None] * Dv + offs_dv[None, :]
        )
        v = tl.load(v_ptrs, mask=mask_v, other=0.0).to(tl.float32)

        S = tl.dot(qg, tl.trans(kg)) * scale
        S = tl.where(mask_n[None, :], S, -1e9)
        m_block = tl.max(S, axis=1)
        delta = m_block - row_max
        scale_old = tl.exp(tl.where(delta > 0.0, -delta, 0.0))
        row_denom = row_denom * scale_old
        row_max = tl.where(delta > 0.0, m_block, row_max)
        p = tl.exp(S - row_max[:, None])
        row_denom += tl.sum(p, axis=1)

        partial_o = tl.dot(p, v)
        acc_o = acc_o * scale_old[:, None]
        acc_o += partial_o

    o = acc_o / row_denom[:, None]
    o = o.to(tl.float16)

    o_ptrs = (
        O_PTR + pid_batch * H * M * Dv + pid_head * M * Dv
        + offs_m[:, None] * Dv + offs_dv[None, :]
    )
    mask_o = (offs_m[:, None] < M) & (offs_dv[None, :] < Dv)
    tl.store(o_ptrs, o, mask=mask_o)

def gdpa_attn(Q: torch.Tensor, K: torch.Tensor, V: torch.Tensor, GQ: torch.Tensor, GK: torch.Tensor) -> torch.Tensor:
    Z, H, M, Dq = Q.shape
    _, _, N, _ = K.shape
    _, _, _, Dv = V.shape
    output = torch.empty(Z, H, M, Dv, dtype=torch.float16, device=Q.device)
    scale = 1.0 / math.sqrt(Dq)
    BLOCK_M = 64
    BLOCK_N = 64
    BLOCK_DMODEL = 64
    BLOCK_DV = 64
    def cdiv(n, b):
        return (n + b - 1) // b
    grid = (Z, H, cdiv(M, BLOCK_M))
    gdpa_attn_kernel[grid](
        Q, K, V, GQ, GK, output,
        Z=Z, H=H, M=M, N=N, Dq=Dq, Dv=Dv, scale=scale,
        BLOCK_M=BLOCK_M, BLOCK_N=BLOCK_N, BLOCK_DMODEL=BLOCK_DMODEL, BLOCK_DV=BLOCK_DV,
        num_stages=4,
        num_warps=8
    )
    return output
        """
        return {"code": code}