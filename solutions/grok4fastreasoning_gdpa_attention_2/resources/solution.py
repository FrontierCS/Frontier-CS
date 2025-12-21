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
    q_ptr, gq_ptr, k_ptr, gk_ptr, v_ptr, out_ptr,
    M, N, Dq, Dv, scale: tl.float32,
    BLOCK_M: tl.constexpr,
    BLOCK_N: tl.constexpr
):
    pid = tl.program_id(0)
    block_start_m = pid * BLOCK_M
    offs_m = block_start_m + tl.arange(0, BLOCK_M)
    offs_d = tl.arange(0, Dq)
    offs_dv = tl.arange(0, Dv)
    mask_m = offs_m < M

    # Load Q and GQ
    q_ptrs = tl.make_block_ptr(
        base=q_ptr,
        shape=(M, Dq),
        strides=(Dq, 1),
        offsets=(block_start_m, 0),
        block_shape=(BLOCK_M, Dq)
    )
    q_mask = mask_m[:, None]
    q = tl.load(q_ptrs, mask=q_mask, other=0.0).to(tl.float32)
    gq_ptrs = tl.make_block_ptr(
        base=gq_ptr,
        shape=(M, Dq),
        strides=(Dq, 1),
        offsets=(block_start_m, 0),
        block_shape=(BLOCK_M, Dq)
    )
    gq = tl.load(gq_ptrs, mask=q_mask, other=0.0).to(tl.float32)
    qg = q * tl.sigmoid(gq)

    # Initialize accumulators
    acc = tl.zeros((BLOCK_M, Dv), dtype=tl.float32)
    m = tl.full((BLOCK_M,), -1e9, dtype=tl.float32)
    l = tl.zeros((BLOCK_M,), dtype=tl.float32)

    # Loop over K blocks
    lo = 0
    while lo < N:
        offs_n = lo + tl.arange(0, BLOCK_N)
        mask_n = offs_n < N

        # Load K and GK
        k_ptrs = tl.make_block_ptr(
            base=k_ptr,
            shape=(N, Dq),
            strides=(Dq, 1),
            offsets=(lo, 0),
            block_shape=(BLOCK_N, Dq)
        )
        k_mask = mask_n[:, None]
        k = tl.load(k_ptrs, mask=k_mask, other=0.0).to(tl.float32)
        gk_ptrs = tl.make_block_ptr(
            base=gk_ptr,
            shape=(N, Dq),
            strides=(Dq, 1),
            offsets=(lo, 0),
            block_shape=(BLOCK_N, Dq)
        )
        gk = tl.load(gk_ptrs, mask=k_mask, other=0.0).to(tl.float32)
        kg = k * tl.sigmoid(gk)

        # Compute attention scores
        s = tl.dot(qg, tl.trans(kg)) * scale
        s = tl.where(mask_n[None, :], s, -1e9)

        # Online softmax
        m_new = tl.maximum(m, tl.max(s, axis=1))
        exp_scale = tl.exp(m - m_new)
        exp_s = tl.exp(s - m_new[:, None])
        l_new = l * exp_scale + tl.sum(exp_s, axis=1)

        # Update acc
        scale_acc = l * exp_scale / l_new
        acc = acc * scale_acc[:, None]

        # Load V and compute contribution
        v_ptrs = tl.make_block_ptr(
            base=v_ptr,
            shape=(N, Dv),
            strides=(Dv, 1),
            offsets=(lo, 0),
            block_shape=(BLOCK_N, Dv)
        )
        v = tl.load(v_ptrs, mask=mask_n[:, None], other=0.0).to(tl.float32)
        dv = tl.dot(exp_s, v)
        acc = acc + dv / l_new[:, None]

        # Update stats
        m = m_new
        l = l_new
        lo += BLOCK_N

    # Store output
    out_ptrs = tl.make_block_ptr(
        base=out_ptr,
        shape=(M, Dv),
        strides=(Dv, 1),
        offsets=(block_start_m, 0),
        block_shape=(BLOCK_M, Dv)
    )
    out_mask = mask_m[:, None]
    tl.store(out_ptrs, acc.to(tl.float16), mask=out_mask)

def triton_gdpa_attn(q, k, v, gq, gk, scale, M, N, Dq, Dv, BLOCK_M=64, BLOCK_N=64):
    out = torch.empty((M, Dv), dtype=torch.float16, device=q.device)
    grid = lambda meta: (triton.cdiv(M, meta['BLOCK_M']),)
    attn_kernel[grid](
        q.data_ptr(), gq.data_ptr(), k.data_ptr(), gk.data_ptr(), v.data_ptr(), out.data_ptr(),
        M, N, Dq, Dv, scale,
        BLOCK_M=BLOCK_M, BLOCK_N=BLOCK_N
    )
    return out

def gdpa_attn(Q: torch.Tensor, K: torch.Tensor, V: torch.Tensor, GQ: torch.Tensor, GK: torch.Tensor) -> torch.Tensor:
    Z, H, M, Dq = Q.shape
    _, _, N, Dv = V.shape
    assert K.shape[2] == N and GQ.shape == Q.shape and GK.shape[:3] + (Dq,) == K.shape
    out = torch.empty(Z, H, M, Dv, dtype=torch.float16, device=Q.device)
    scale = 1.0 / math.sqrt(Dq)
    BLOCK_M = 64
    BLOCK_N = 64
    for z in range(Z):
        for h in range(H):
            q = Q[z, h].contiguous()
            k = K[z, h].contiguous()
            v = V[z, h].contiguous()
            gq = GQ[z, h].contiguous()
            gk = GK[z, h].contiguous()
            out_zh = triton_gdpa_attn(q, k, v, gq, gk, scale, M, N, Dq, Dv, BLOCK_M, BLOCK_N)
            out[z, h] = out_zh
    return out
"""
        return {"code": code}
