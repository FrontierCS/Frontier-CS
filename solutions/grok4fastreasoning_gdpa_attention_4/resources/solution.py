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
    q_ptr, gq_ptr, k_ptr, gk_ptr, v_ptr, o_ptr,
    M: tl.constexpr,
    N: tl.constexpr,
    D: tl.constexpr,
    Dv: tl.constexpr,
    scale: tl.float32,
    BLOCK_M: tl.constexpr,
    BLOCK_N: tl.constexpr,
    BLOCK_D: tl.constexpr,
    BLOCK_DV: tl.constexpr
):
    pid_m = tl.program_id(0)
    block_start_m = pid_m * BLOCK_M
    offs_m = block_start_m + tl.arange(0, BLOCK_M)
    offs_n = tl.arange(0, BLOCK_N)
    offs_d = tl.arange(0, BLOCK_D)
    offs_dv = tl.arange(0, BLOCK_DV)

    q_ptr_block = tl.make_block_ptr(
        base=q_ptr,
        shape=(M, D),
        strides=(D, 1),
        offsets=(block_start_m, 0),
        block_shape=(BLOCK_M, BLOCK_D),
        order=(1, 0)
    )
    q = tl.load(q_ptr_block, boundary_check=(0, 0), other=0.0)

    gq_ptr_block = tl.make_block_ptr(
        base=gq_ptr,
        shape=(M, D),
        strides=(D, 1),
        offsets=(block_start_m, 0),
        block_shape=(BLOCK_M, BLOCK_D),
        order=(1, 0)
    )
    gq = tl.load(gq_ptr_block, boundary_check=(0, 0), other=0.0)

    gq_f = gq.to(tl.float32)
    qg = q.to(tl.float32) * tl.sigmoid(gq_f)

    row_m = tl.full((BLOCK_M,), -1e9, dtype=tl.float32)
    row_l = tl.zeros((BLOCK_M,), dtype=tl.float32)
    row_o = tl.zeros((BLOCK_M, BLOCK_DV), dtype=tl.float32)

    block_start_n = 0
    while block_start_n < N:
        mask_n = (block_start_n + offs_n) < N

        k_ptr_block = tl.make_block_ptr(
            base=k_ptr,
            shape=(N, D),
            strides=(D, 1),
            offsets=(block_start_n, 0),
            block_shape=(BLOCK_N, BLOCK_D),
            order=(1, 0)
        )
        k = tl.load(k_ptr_block, boundary_check=(0, 0), other=0.0)

        gk_ptr_block = tl.make_block_ptr(
            base=gk_ptr,
            shape=(N, D),
            strides=(D, 1),
            offsets=(block_start_n, 0),
            block_shape=(BLOCK_N, BLOCK_D),
            order=(1, 0)
        )
        gk = tl.load(gk_ptr_block, boundary_check=(0, 0), other=0.0)

        gk_f = gk.to(tl.float32)
        kg = k.to(tl.float32) * tl.sigmoid(gk_f)

        v_ptr_block = tl.make_block_ptr(
            base=v_ptr,
            shape=(N, Dv),
            strides=(Dv, 1),
            offsets=(block_start_n, 0),
            block_shape=(BLOCK_N, BLOCK_DV),
            order=(1, 0)
        )
        v = tl.load(v_ptr_block, boundary_check=(0, 0), other=0.0)
        v_f = v.to(tl.float32)

        local_scores = tl.dot(qg, tl.trans(kg)) * scale
        local_scores = tl.where(mask_n[None, :], local_scores, -1e9)

        local_m = tl.max(local_scores, axis=1)
        m_new = tl.maximum(row_m, local_m)
        row_scale = tl.exp(row_m - m_new)

        row_l = row_l * row_scale
        row_o = row_o * row_scale[:, None]
        row_m = m_new

        local_p = tl.exp(local_scores - row_m[:, None])
        row_o = row_o + tl.dot(local_p, v_f)
        row_l = row_l + tl.sum(local_p, axis=1)

        block_start_n += BLOCK_N

    row_out = row_o / row_l[:, None]

    o_ptr_block = tl.make_block_ptr(
        base=o_ptr,
        shape=(M, Dv),
        strides=(Dv, 1),
        offsets=(block_start_m, 0),
        block_shape=(BLOCK_M, BLOCK_DV),
        order=(1, 0)
    )
    tl.store(o_ptr_block, row_out.to(o_ptr.dtype.element_ty), boundary_check=(0, 0))


def gdpa_attn(Q: torch.Tensor, K: torch.Tensor, V: torch.Tensor, GQ: torch.Tensor, GK: torch.Tensor) -> torch.Tensor:
    Z, H, M, D = Q.shape
    _, _, N, Dv = V.shape
    assert N == M
    output = torch.empty(Z, H, M, Dv, dtype=Q.dtype, device=Q.device)
    scale = 1.0 / math.sqrt(D)
    BLOCK_M = 128
    BLOCK_N = 64
    BLOCK_D = 64
    BLOCK_DV = 64
    for z in range(Z):
        for h in range(H):
            q = Q[z, h].contiguous()
            gq = GQ[z, h].contiguous()
            k = K[z, h].contiguous()
            gk = GK[z, h].contiguous()
            v = V[z, h].contiguous()
            o = output[z, h]
            def grid(meta):
                return (triton.cdiv(M, meta['BLOCK_M']), )
            attn_kernel[grid](
                q, gq, k, gk, v, o,
                M, N, D, Dv, scale,
                BLOCK_M=BLOCK_M, BLOCK_N=BLOCK_N, BLOCK_D=BLOCK_D, BLOCK_DV=BLOCK_DV,
                num_stages=1,
                num_warps=4,
            )
    return output
"""
        return {"code": code}
