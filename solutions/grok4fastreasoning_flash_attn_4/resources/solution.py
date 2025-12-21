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

def flash_attn(Q: torch.Tensor, K: torch.Tensor, V: torch.Tensor, causal: bool = True) -> torch.Tensor:
    Z, H, M, Dq = Q.shape
    _, _, N, Dv = V.shape
    assert N == M
    assert Q.dtype == torch.float16
    assert K.dtype == torch.float16
    assert V.dtype == torch.float16
    scale = 1.0 / math.sqrt(Dq)
    output = torch.empty((Z, H, M, Dv), dtype=torch.float16, device=Q.device)

    @triton.jit
    def kernel(
        Q_ptr, K_ptr, V_ptr, O_ptr,
        stride_qz, stride_qh, stride_qm, stride_qd,
        stride_kz, stride_kh, stride_km, stride_kd,
        stride_vz, stride_vh, stride_vm, stride_vd,
        stride_oz, stride_oh, stride_om, stride_od,
        Z, H, M, N, Dq, Dv, scale,
        causal: tl.constexpr,
        BLOCK_M: tl.constexpr,
        BLOCK_N: tl.constexpr,
    ):
        block_m = tl.program_id(0)
        batch = tl.program_id(1)
        head = tl.program_id(2)

        q_start = block_m * BLOCK_M
        q_base = Q_ptr + batch * stride_qz + head * stride_qh
        k_base = K_ptr + batch * stride_kz + head * stride_kh
        v_base = V_ptr + batch * stride_vz + head * stride_vh
        o_base = O_ptr + batch * stride_oz + head * stride_oh

        arange_m = tl.arange(0, BLOCK_M)
        arange_d = tl.arange(0, Dq)
        q_ptrs = q_base + (q_start + arange_m)[:, None] * stride_qm + arange_d[None, :] * stride_qd
        q = tl.load(q_ptrs).to(tl.float32)

        m = tl.full((BLOCK_M,), -float("inf"), dtype=tl.float32)
        l = tl.zeros((BLOCK_M,), dtype=tl.float32)
        o = tl.zeros((BLOCK_M, Dv), dtype=tl.float32)

        arange_kn = tl.arange(0, BLOCK_N)
        arange_vd = tl.arange(0, Dv)

        num_k_blocks = (N + BLOCK_N - 1) // BLOCK_N
        for k_block in range(num_k_blocks):
            k_start = k_block * BLOCK_N
            if causal and k_start >= q_start + BLOCK_M:
                break
            k_ptrs = k_base + (k_start + arange_kn)[:, None] * stride_km + arange_d[None, :] * stride_kd
            k = tl.load(k_ptrs).to(tl.float32)

            s = tl.matmul(q, tl.trans(k)) * scale

            if causal:
                delta = q_start - k_start
                i_indices = tl.arange(0, BLOCK_M)[:, None]
                j_indices = tl.arange(0, BLOCK_N)[None, :]
                mask_causal = j_indices <= (i_indices + delta)
                s = tl.where(mask_causal, s, -1e9)

            m_new = tl.maximum(m, tl.max(s, axis=1))
            p = tl.exp(s - m_new[:, None])
            l_temp = tl.sum(p, axis=1)
            exp_diff = tl.exp(m - m_new)
            l = l * exp_diff + l_temp

            v_ptrs = v_base + (k_start + arange_kn)[:, None] * stride_vm + arange_vd[None, :] * stride_vd
            v = tl.load(v_ptrs).to(tl.float32)

            pv = tl.matmul(p, v)
            o = o * exp_diff[:, None] + pv

            m = m_new

        o = o / l[:, None]
        o_ptrs = o_base + (q_start + arange_m)[:, None] * stride_om + arange_vd[None, :] * stride_od
        tl.store(o_ptrs, o.to(tl.float16))

    grid = (triton.cdiv(M, 64), Z, H)
    kernel[grid](
        Q, K, V, output,
        stride_qz=Q.stride(0), stride_qh=Q.stride(1), stride_qm=Q.stride(2), stride_qd=Q.stride(3),
        stride_kz=K.stride(0), stride_kh=K.stride(1), stride_km=K.stride(2), stride_kd=K.stride(3),
        stride_vz=V.stride(0), stride_vh=V.stride(1), stride_vm=V.stride(2), stride_vd=V.stride(3),
        stride_oz=output.stride(0), stride_oh=output.stride(1), stride_om=output.stride(2), stride_od=output.stride(3),
        Z=Z, H=H, M=M, N=N, Dq=Dq, Dv=Dv, scale=scale, causal=causal,
        BLOCK_M=64, BLOCK_N=64,
    )
    return output
"""
        return {"code": code}
