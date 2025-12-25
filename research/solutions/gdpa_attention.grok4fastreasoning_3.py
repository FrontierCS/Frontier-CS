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
def attn_kernel(
    Q_PTR, K_PTR, V_PTR, GQ_PTR, GK_PTR, O_PTR,
    M: tl.int32, N: tl.int32, D: tl.int32, Dv: tl.int32, SCALE: tl.float32,
    stride_qm, stride_qd, stride_km, stride_kd, stride_vm, stride_vd,
    stride_gqm, stride_gqd, stride_gkm, stride_gkd, stride_om, stride_od,
    BLOCK_M: tl.constexpr,
    BLOCK_N: tl.constexpr,
    BLOCK_D: tl.constexpr,
    BLOCK_DV: tl.constexpr
):
    pid = tl.program_id(0)
    block_start_m = pid * BLOCK_M
    m_offsets = block_start_m + tl.arange(0, BLOCK_M)
    d_offsets = tl.arange(0, BLOCK_D)
    dv_offsets = tl.arange(0, BLOCK_DV)
    mask_m = m_offsets < M
    mask_d = d_offsets < D
    mask_dv = dv_offsets < Dv
    # load q and gq
    q_ptrs = Q_PTR + (m_offsets[:, None] * stride_qm + d_offsets[None, :] * stride_qd)
    q = tl.load(q_ptrs, mask=(mask_m[:, None] & mask_d[None, :]), other=0.0)
    gq_ptrs = GQ_PTR + (m_offsets[:, None] * stride_gqm + d_offsets[None, :] * stride_gqd)
    gq = tl.load(gq_ptrs, mask=(mask_m[:, None] & mask_d[None, :]), other=0.0)
    qg = q * tl.sigmoid(gq)
    qg_f = qg.to(tl.float32)
    # init
    acc = tl.zeros((BLOCK_M, BLOCK_DV), dtype=tl.float32)
    m = tl.full((BLOCK_M,), -1e9, dtype=tl.float32)
    l = tl.zeros((BLOCK_M,), dtype=tl.float32)
    # loop
    lo = 0
    while lo < N:
        n_start = lo
        n_offsets = n_start + tl.arange(0, BLOCK_N)
        mask_n = n_offsets < N
        # load k and gk as [D, N]
        k_ptrs = K_PTR + (d_offsets[:, None] * stride_kd + n_offsets[None, :] * stride_km)
        k = tl.load(k_ptrs, mask=(mask_d[:, None] & mask_n[None, :]), other=0.0)
        gk_ptrs = GK_PTR + (d_offsets[:, None] * stride_gkd + n_offsets[None, :] * stride_gkm)
        gk = tl.load(gk_ptrs, mask=(mask_d[:, None] & mask_n[None, :]), other=0.0)
        kg = k * tl.sigmoid(gk)
        kg_f = kg.to(tl.float32)
        # s
        s = tl.dot(qg_f, kg_f) * SCALE
        # mask s for padding
        s = tl.where(mask_n[None, :], s, -1e9)
        # v [N, Dv]
        v_ptrs = V_PTR + (n_offsets[:, None] * stride_vm + dv_offsets[None, :] * stride_vd)
        v = tl.load(v_ptrs, mask=(mask_n[:, None] & mask_dv[None, :]), other=0.0)
        v_f = v.to(tl.float32)
        # softmax
        curr_m = tl.max(s, axis=1)
        m_new = tl.maximum(m, curr_m)
        alpha = tl.exp(m - m_new)
        p = tl.exp(s - m_new)
        l_new = alpha * l + tl.sum(p, axis=1)
        acc_new = alpha[:, None] * acc + tl.dot(p, v_f)
        m = m_new
        l = l_new
        acc = acc_new
        lo += BLOCK_N
    # normalize
    o = acc / l[:, None]
    # store
    o_ptrs = O_PTR + (m_offsets[:, None] * stride_om + dv_offsets[None, :] * stride_od)
    tl.store(o_ptrs, o.to(tl.float16), mask=(mask_m[:, None] & mask_dv[None, :]))

def gdpa_attn(Q: torch.Tensor, K: torch.Tensor, V: torch.Tensor, GQ: torch.Tensor, GK: torch.Tensor) -> torch.Tensor:
    Z, H, M, D = Q.shape
    _, _, N, Dv = V.shape
    output = torch.empty(Z, H, M, Dv, dtype=torch.float16, device=Q.device)
    scale = 1.0 / math.sqrt(D)
    for z in range(Z):
        for h in range(H):
            q = Q[z, h]
            k = K[z, h]
            v = V[z, h]
            gq = GQ[z, h]
            gk = GK[z, h]
            out = torch.empty(M, Dv, dtype=torch.float16, device=Q.device)
            stride_qm = q.stride(0)
            stride_qd = q.stride(1)
            stride_km = k.stride(0)
            stride_kd = k.stride(1)
            stride_vm = v.stride(0)
            stride_vd = v.stride(1)
            stride_gqm = gq.stride(0)
            stride_gqd = gq.stride(1)
            stride_gkm = gk.stride(0)
            stride_gkd = gk.stride(1)
            stride_om = out.stride(0)
            stride_od = out.stride(1)
            BLOCK_M = 64
            BLOCK_N = 64
            BLOCK_D = D
            BLOCK_DV = Dv
            grid = lambda meta: ((M + BLOCK_M - 1) // BLOCK_M,)
            attn_kernel[grid](
                q.data_ptr(), k.data_ptr(), v.data_ptr(), gq.data_ptr(), gk.data_ptr(), out.data_ptr(),
                M, N, D, Dv, scale,
                stride_qm, stride_qd,
                stride_km, stride_kd,
                stride_vm, stride_vd,
                stride_gqm, stride_gqd,
                stride_gkm, stride_gkd,
                stride_om, stride_od,
                BLOCK_M=BLOCK_M,
                BLOCK_N=BLOCK_N,
                BLOCK_D=BLOCK_D,
                BLOCK_DV=BLOCK_DV,
                num_stages=4,
            )
            output[z, h] = out
    return output
"""
        return {"code": code}
