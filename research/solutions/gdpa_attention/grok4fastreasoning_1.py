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
def _gdpa_attn_kernel(
    Q_PTR, K_PTR, V_PTR, GQ_PTR, GK_PTR, O_PTR,
    stride_qm, stride_qd,
    stride_km, stride_kd,
    stride_vm, stride_vd,
    stride_gqm, stride_gqd,
    stride_gkm, stride_gkd,
    stride_om, stride_od,
    M: tl.constexpr, N: tl.constexpr,
    BLOCK_M: tl.constexpr, BLOCK_N: tl.constexpr, BLOCK_D: tl.constexpr
):
    pid_m = tl.program_id(0)
    offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)

    # Load Q and GQ
    offs_d = tl.arange(0, BLOCK_D)
    q_ptrs = Q_PTR + (offs_m[:, None] * stride_qm + offs_d[None, :] * stride_qd)
    q = tl.load(q_ptrs, other=0.0)

    gq_ptrs = GQ_PTR + (offs_m[:, None] * stride_gqm + offs_d[None, :] * stride_gqd)
    gq = tl.load(gq_ptrs, other=0.0)

    qg = q * tl.sigmoid(gq)
    qg = qg.to(tl.float32)

    # Initialize softmax stats
    m = tl.full([BLOCK_M], -1e4, dtype=tl.float32)
    l = tl.zeros([BLOCK_M], dtype=tl.float32)

    # Initialize output accumulator
    offs_do = tl.arange(0, BLOCK_D)
    o = tl.zeros((BLOCK_M, BLOCK_D), dtype=tl.float32)

    # Scale
    scale = 1.0 / tl.sqrt(tl.float32(BLOCK_D))

    # Loop over key blocks
    num_blocks = tl.cdiv(N, BLOCK_N)
    for start_n in range(num_blocks):
        offs_n = start_n * BLOCK_N + tl.arange(0, BLOCK_N)
        n_mask = offs_n < N

        # Load K and GK
        k_ptrs = K_PTR + (offs_n[:, None] * stride_km + offs_d[None, :] * stride_kd)
        k = tl.load(k_ptrs, mask=n_mask[:, None], other=0.0)

        gk_ptrs = GK_PTR + (offs_n[:, None] * stride_gkm + offs_d[None, :] * stride_gkd)
        gk = tl.load(gk_ptrs, mask=n_mask[:, None], other=0.0)

        kg = k * tl.sigmoid(gk)
        kg = kg.to(tl.float32)

        # Compute attention scores
        s = tl.dot(qg, tl.trans(kg)) * scale
        s = tl.where(n_mask[None, :], s, -1e4)

        m_curr = tl.max(s, axis=1)
        p = tl.exp(s - m_curr[:, None])
        l_curr = tl.sum(p, axis=1)

        m_new = tl.maximum(m, m_curr)
        l_scale = tl.exp(m - m_new)
        l_curr_scale = tl.exp(m_curr - m_new)
        l_new = l_scale * l + l_curr_scale * l_curr

        p = p * l_curr_scale[:, None]

        # Load V
        v_ptrs = V_PTR + (offs_n[:, None] * stride_vm + offs_do[None, :] * stride_vd)
        v = tl.load(v_ptrs, mask=n_mask[:, None], other=0.0)
        v = v.to(tl.float32)

        # Compute contrib
        o_contrib = tl.dot(p, v) / l_new[:, None]

        # Update o
        o_scale = l_scale * (l / l_new)
        o = o * o_scale[:, None] + o_contrib

        # Update stats
        m = m_new
        l = l_new

    # Store output
    o_ptrs = O_PTR + (offs_m[:, None] * stride_om + offs_do[None, :] * stride_od)
    o = o.to(tl.float16)
    tl.store(o_ptrs, o)

def gdpa_attn(Q: torch.Tensor, K: torch.Tensor, V: torch.Tensor, GQ: torch.Tensor, GK: torch.Tensor) -> torch.Tensor:
    Z, H, M, Dq = Q.shape
    _, _, N, _ = K.shape
    _, _, _, Dv = V.shape
    assert N == M
    assert Dq == 64
    assert Dv == 64

    output = torch.empty((Z, H, M, Dv), dtype=Q.dtype, device=Q.device)

    BLOCK_M = 64
    BLOCK_N = 64
    BLOCK_D = 64

    def kernel_launcher(q, k, v, gq, gk, o):
        grid = (M // BLOCK_M,)
        _gdpa_attn_kernel[grid](
            q.data_ptr(), k.data_ptr(), v.data_ptr(), gq.data_ptr(), gk.data_ptr(), o.data_ptr(),
            stride_qm=q.stride(0) * q.element_size(),
            stride_qd=q.stride(1) * q.element_size(),
            stride_km=k.stride(0) * k.element_size(),
            stride_kd=k.stride(1) * k.element_size(),
            stride_vm=v.stride(0) * v.element_size(),
            stride_vd=v.stride(1) * v.element_size(),
            stride_gqm=gq.stride(0) * gq.element_size(),
            stride_gqd=gq.stride(1) * gq.element_size(),
            stride_gkm=gk.stride(0) * gk.element_size(),
            stride_gkd=gk.stride(1) * gk.element_size(),
            stride_om=o.stride(0) * o.element_size(),
            stride_od=o.stride(1) * o.element_size(),
            M=M, N=N,
            BLOCK_M=BLOCK_M, BLOCK_N=BLOCK_N, BLOCK_D=BLOCK_D,
            num_stages=1,
        )

    for z in range(Z):
        for h in range(H):
            q_slice = Q[z, h].contiguous()
            k_slice = K[z, h].contiguous()
            v_slice = V[z, h].contiguous()
            gq_slice = GQ[z, h].contiguous()
            gk_slice = GK[z, h].contiguous()
            o_slice = output[z, h]

            kernel_launcher(q_slice, k_slice, v_slice, gq_slice, gk_slice, o_slice)

    return output
"""
        return {"code": code}