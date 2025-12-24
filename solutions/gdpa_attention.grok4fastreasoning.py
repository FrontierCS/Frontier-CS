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

@triton.jit
def gdpa_attn_kernel(
    Q_PTR, K_PTR, V_PTR, GQ_PTR, GK_PTR, O_PTR,
    STRIDE_ZQ, STRIDE_HQ, STRIDE_MQ, STRIDE_DQ,
    STRIDE_ZK, STRIDE_HK, STRIDE_NK, STRIDE_DK,
    STRIDE_ZV, STRIDE_HV, STRIDE_NV, STRIDE_DV,
    STRIDE_ZGQ, STRIDE_HGQ, STRIDE_MGQ, STRIDE_DGQ,
    STRIDE_ZGK, STRIDE_HGK, STRIDE_NGK, STRIDE_DGK,
    STRIDE_ZO, STRIDE_HO, STRIDE_MO, STRIDE_DO,
    Z, H, M, N, Dq, Dv,
    BLOCK_M: tl.constexpr,
    BLOCK_N: tl.constexpr
):
    pid_z = tl.program_id(0)
    pid_h = tl.program_id(1)
    pid_q = tl.program_id(2)
    q_start = pid_q * BLOCK_M
    offs_q = q_start + tl.arange(0, BLOCK_M)
    scale = 1.0 / tl.sqrt(tl.cast(Dq, tl.float32))

    # Load Q and GQ blocks
    q_base = Q_PTR + pid_z * STRIDE_ZQ + pid_h * STRIDE_HQ + q_start * STRIDE_MQ
    q_ptr = tl.make_block_ptr(
        q_base,
        (BLOCK_M, Dq),
        (STRIDE_MQ, STRIDE_DQ),
        (0, 0),
    )
    q_block = tl.load(q_ptr)

    gq_base = GQ_PTR + pid_z * STRIDE_ZGQ + pid_h * STRIDE_HGQ + q_start * STRIDE_MGQ
    gq_ptr = tl.make_block_ptr(
        gq_base,
        (BLOCK_M, Dq),
        (STRIDE_MGQ, STRIDE_DGQ),
        (0, 0),
    )
    gq_block = tl.load(gq_ptr)

    qg_block = q_block * tl.sigmoid(gq_block)
    qg_f = tl.cast(qg_block, tl.float32)

    # Initialize accumulators
    acc = tl.zeros((BLOCK_M, Dv), dtype=tl.float32)
    m = tl.full((BLOCK_M,), float("-1e30"), dtype=tl.float32)
    l = tl.zeros((BLOCK_M,), dtype=tl.float32)

    # Loop over key blocks
    for kn in range(0, tl.cdiv(N, BLOCK_N)):
        k_start = kn * BLOCK_N
        offs_n = k_start + tl.arange(0, BLOCK_N)
        n_mask = offs_n < N

        # Load K and GK blocks
        k_base = K_PTR + pid_z * STRIDE_ZK + pid_h * STRIDE_HK + k_start * STRIDE_NK
        k_ptr = tl.make_block_ptr(
            k_base,
            (BLOCK_N, Dq),
            (STRIDE_NK, STRIDE_DK),
            (0, 0),
        )
        k_load_mask = n_mask[:, None]
        k_block = tl.load(k_ptr, mask=k_load_mask)

        gk_base = GK_PTR + pid_z * STRIDE_ZGK + pid_h * STRIDE_HGK + k_start * STRIDE_NGK
        gk_ptr = tl.make_block_ptr(
            gk_base,
            (BLOCK_N, Dq),
            (STRIDE_NGK, STRIDE_DGK),
            (0, 0),
        )
        gk_block = tl.load(gk_ptr, mask=k_load_mask)

        kg_block = k_block * tl.sigmoid(gk_block)
        kg_f = tl.cast(kg_block, tl.float32)

        # Compute attention scores
        s = tl.dot(qg_f, tl.trans(kg_f)) * scale

        # Mask invalid key positions
        s = tl.where(n_mask[None, :], s, float("-1e9"))

        # Streaming softmax
        m_new = tl.maximum(m, tl.max(s, 1))
        p = tl.exp(s - m_new[:, None])
        l_new = tl.exp(m - m_new) * l + tl.sum(p, 1)
        acc_new = tl.exp(m - m_new)[:, None] * acc + tl.dot(p.to(tl.float32), tl.cast(tl.load(
            tl.make_block_ptr(
                V_PTR + pid_z * STRIDE_ZV + pid_h * STRIDE_HV + k_start * STRIDE_NV,
                (BLOCK_N, Dv),
                (STRIDE_NV, STRIDE_DV),
                (0, 0),
            ), mask=k_load_mask
        ), tl.float32))

        m = m_new
        l = l_new
        acc = acc_new

    # Finalize output
    o_final = acc / l[:, None]
    o_base = O_PTR + pid_z * STRIDE_ZO + pid_h * STRIDE_HO + q_start * STRIDE_MO
    o_ptr = tl.make_block_ptr(
        o_base,
        (BLOCK_M, Dv),
        (STRIDE_MO, STRIDE_DO),
        (0, 0),
    )
    tl.store(o_ptr, tl.cast(o_final, tl.float16))

def gdpa_attn(Q: torch.Tensor, K: torch.Tensor, V: torch.Tensor, GQ: torch.Tensor, GK: torch.Tensor) -> torch.Tensor:
    Z, H, M, Dq = Q.shape
    _, _, N, _ = K.shape
    _, _, _, Dv = V.shape
    output = torch.empty(Z, H, M, Dv, dtype=Q.dtype, device=Q.device)

    stride_zq, stride_hq, stride_mq, stride_dq = Q.stride()
    stride_zk, stride_hk, stride_nk, stride_dk = K.stride()
    stride_zv, stride_hv, stride_nv, stride_dv = V.stride()
    stride_zgq, stride_hgq, stride_mgq, stride_dgq = GQ.stride()
    stride_zgk, stride_hgk, stride_ngk, stride_dgk = GK.stride()
    stride_zo, stride_ho, stride_mo, stride_do = output.stride()

    BLOCK_M = 64
    BLOCK_N = 64
    grid = (Z, H, M // BLOCK_M)
    gdpa_attn_kernel[grid](
        Q.data_ptr(), K.data_ptr(), V.data_ptr(), GQ.data_ptr(), GK.data_ptr(), output.data_ptr(),
        stride_zq, stride_hq, stride_mq, stride_dq,
        stride_zk, stride_hk, stride_nk, stride_dk,
        stride_zv, stride_hv, stride_nv, stride_dv,
        stride_zgq, stride_hgq, stride_mgq, stride_dgq,
        stride_zgk, stride_hgk, stride_ngk, stride_dgk,
        stride_zo, stride_ho, stride_mo, stride_do,
        Z, H, M, N, Dq, Dv,
        BLOCK_M=BLOCK_M,
        BLOCK_N=BLOCK_N,
    )
    return output
        """
        return {"code": code}
