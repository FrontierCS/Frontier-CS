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
def gdpa_kernel(
    Q_PTR, K_PTR, V_PTR, GQ_PTR, GK_PTR, O_PTR,
    M: tl.int32, N: tl.int32, Dq: tl.int32, Dv: tl.int32,
    scale: tl.float32,
    stride_qm, stride_qd, stride_gqm, stride_gqd,
    stride_kn, stride_kd, stride_gkn, stride_gkd,
    stride_vn, stride_vd, stride_om, stride_od,
    BLOCK_M: tl.constexpr,
    BLOCK_N: tl.constexpr
):
    pid = tl.program_id(0)
    block_start = pid * BLOCK_M
    offs_m = block_start + tl.arange(0, BLOCK_M)
    mask_m = offs_m < M

    # Load Q and GQ blocks
    offs_d = tl.arange(0, Dq)
    q_ptrs = Q_PTR + offs_m[:, None] * stride_qm + offs_d[None, :] * stride_qd
    q = tl.load(q_ptrs, mask=(mask_m[:, None], None), other=0.0)
    gq_ptrs = GQ_PTR + offs_m[:, None] * stride_gqm + offs_d[None, :] * stride_gqd
    gq = tl.load(gq_ptrs, mask=(mask_m[:, None], None), other=0.0)
    qg = (q * tl.sigmoid(gq)).to(tl.float32)

    # Initialize softmax stats and output
    m = tl.full((BLOCK_M, 1), -1e9, dtype=tl.float32)
    l = tl.full((BLOCK_M, 1), 1.0, dtype=tl.float32)
    o = tl.zeros((BLOCK_M, Dv), dtype=tl.float32)

    # Loop over N blocks
    n_block_idx = 0
    n_blocks_total = tl.cdiv(N, tl.constexpr(BLOCK_N))
    while n_block_idx < n_blocks_total:
        start_n = n_block_idx * BLOCK_N
        offs_n = start_n + tl.arange(0, BLOCK_N)
        mask_n = offs_n < N

        # Load K and GK blocks as (Dq, BLOCK_N)
        k_ptrs = K_PTR + offs_d[:, None] * stride_kd + offs_n[None, :] * stride_kn
        k = tl.load(k_ptrs, mask=(None, mask_n), other=0.0)
        gk_ptrs = GK_PTR + offs_d[:, None] * stride_gkd + offs_n[None, :] * stride_gkn
        gk = tl.load(gk_ptrs, mask=(None, mask_n), other=0.0)
        kg = (k * tl.sigmoid(gk)).to(tl.float32)

        # Compute scores
        scores = tl.dot(qg, kg) * scale
        mask_sa = mask_m[:, None] & mask_n[None, :]
        scores = tl.where(mask_sa, scores, -1e9)

        # Online softmax update
        m_new = tl.maximum(m, tl.max(scores, axis=1, keepdims=True))
        e_m = tl.exp(m - m_new)
        p = tl.exp(scores - m_new[:, None])
        l_new = e_m * l + tl.sum(p, axis=1, keepdims=True)

        # Load V block as (BLOCK_N, Dv)
        offs_dv = tl.arange(0, Dv)
        v_ptrs = V_PTR + offs_n[:, None] * stride_vn + offs_dv[None, :] * stride_vd
        mask_v = mask_n[:, None] & (offs_dv[None, :] < Dv)
        v = tl.load(v_ptrs, mask=mask_v, other=0.0).to(tl.float32)

        # Update output
        o_new = e_m[:, None] * o + tl.dot(p, v)
        o = o_new / l_new[:, None]

        # Update stats
        m = m_new
        l = l_new

        n_block_idx += 1

    # Store output
    o_mask = mask_m[:, None] & (tl.arange(0, Dv)[None, :] < Dv)
    o_ptrs = O_PTR + offs_m[:, None] * stride_om + offs_dv[None, :] * stride_od
    tl.store(o_ptrs, o.to(tl.float16), mask=o_mask)

def gdpa_attn(Q: torch.Tensor, K: torch.Tensor, V: torch.Tensor, GQ: torch.Tensor, GK: torch.Tensor) -> torch.Tensor:
    Z, H, M, Dq = Q.shape
    _, _, N, _ = K.shape
    _, _, _, Dv = V.shape
    output = torch.empty((Z, H, M, Dv), dtype=Q.dtype, device=Q.device)
    scale = 1.0 / math.sqrt(Dq)
    BLOCK_M = 64
    BLOCK_N = 64

    for z in range(Z):
        for h in range(H):
            Q_ptr = Q.data_ptr() + z * Q.stride(0) + h * Q.stride(1)
            K_ptr = K.data_ptr() + z * K.stride(0) + h * K.stride(1)
            V_ptr = V.data_ptr() + z * V.stride(0) + h * V.stride(1)
            GQ_ptr = GQ.data_ptr() + z * GQ.stride(0) + h * GQ.stride(1)
            GK_ptr = GK.data_ptr() + z * GK.stride(0) + h * GK.stride(1)
            O_ptr = output.data_ptr() + z * output.stride(0) + h * output.stride(1)

            stride_qm = Q.stride(2)
            stride_qd = Q.stride(3)
            stride_gqm = GQ.stride(2)
            stride_gqd = GQ.stride(3)
            stride_kn = K.stride(2)
            stride_kd = K.stride(3)
            stride_gkn = GK.stride(2)
            stride_gkd = GK.stride(3)
            stride_vn = V.stride(2)
            stride_vd = V.stride(3)
            stride_om = output.stride(2)
            stride_od = output.stride(3)

            num_blocks_m = (M + BLOCK_M - 1) // BLOCK_M
            grid = (num_blocks_m,)
            gdpa_kernel[grid](
                Q_ptr, K_ptr, V_ptr, GQ_ptr, GK_ptr, O_ptr,
                M, N, Dq, Dv, scale,
                stride_qm, stride_qd, stride_gqm, stride_gqd,
                stride_kn, stride_kd, stride_gkn, stride_gkd,
                stride_vn, stride_vd, stride_om, stride_od,
                BLOCK_M=BLOCK_M, BLOCK_N=BLOCK_N
            )

    return output
"""
        return {"code": code}
