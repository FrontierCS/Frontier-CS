import math
from triton import cdiv

class Solution:
    def solve(self, spec_path: str = None) -> dict:
        code = """
import torch
import triton
import triton.language as tl
import math
from triton import cdiv

def flash_attn(Q: torch.Tensor, K: torch.Tensor, V: torch.Tensor, causal: bool = True) -> torch.Tensor:
    Z, H, M, Dq = Q.shape
    _, _, N, Dv = V.shape
    assert K.shape == (Z, H, N, Dq)
    out = torch.empty((Z, H, M, Dv), dtype=Q.dtype, device=Q.device)
    scale = 1 / math.sqrt(Dq)
    BLOCK_M = 128
    BLOCK_N = 64

    stride_q = Q.stride()
    stride_k = K.stride()
    stride_v = V.stride()
    stride_o = out.stride()

    @triton.jit
    def kernel(
        Q_ptr, K_ptr, V_ptr, O_ptr,
        stride_qz, stride_qh, stride_qm, stride_qd,
        stride_kz, stride_kh, stride_kn, stride_kd,
        stride_vz, stride_vh, stride_vn, stride_vd,
        stride_oz, stride_oh, stride_om, stride_od,
        Z, H, M, N, Dq, Dv,
        scale,
        causal: tl.constexpr
    ):
        pid_z = tl.program_id(0)
        pid_h = tl.program_id(1)
        pid_m = tl.program_id(2)

        block_start_m = pid_m * BLOCK_M
        offs_m = tl.arange(0, BLOCK_M)
        row_idx = block_start_m + offs_m
        mask_m = row_idx < M
        offs_d = tl.arange(0, Dq)
        offs_n = tl.arange(0, BLOCK_N)
        offs_dv = tl.arange(0, Dv)

        q_base = pid_z * stride_qz + pid_h * stride_qh + block_start_m * stride_qm
        q_ptrs = Q_ptr + q_base + offs_m[:, None] * stride_qm + offs_d[None, :] * stride_qd
        Q = tl.load(q_ptrs, mask=mask_m[:, None], other=0.0).to(tl.float32)

        row_max = tl.full((BLOCK_M,), -1e4, dtype=tl.float32)
        row_l = tl.zeros((BLOCK_M,), dtype=tl.float32)
        local_O = tl.zeros((BLOCK_M, Dv), dtype=tl.float32)

        bn = 0
        while bn * BLOCK_N < N:
            block_start_n = bn * BLOCK_N
            col_idx = block_start_n + offs_n
            mask_n = col_idx < N

            k_base = pid_z * stride_kz + pid_h * stride_kh + block_start_n * stride_kn
            k_ptrs = K_ptr + k_base + offs_n[:, None] * stride_kn + offs_d[None, :] * stride_kd
            K_block = tl.load(k_ptrs, mask=mask_n[:, None], other=0.0).to(tl.float32)

            v_base = pid_z * stride_vz + pid_h * stride_vh + block_start_n * stride_vn
            v_ptrs = V_ptr + v_base + offs_n[:, None] * stride_vn + offs_dv[None, :] * stride_vd
            V_block = tl.load(v_ptrs, mask=mask_n[:, None], other=0.0).to(tl.float32)

            S = tl.dot(Q, tl.trans(K_block)) * scale

            if causal:
                mask_causal = col_idx[None, :] <= row_idx[:, None]
                S = tl.where(mask_causal, S, -1e4)

            m_curr = tl.max(S, axis=1)
            new_m = tl.maximum(row_max, m_curr)
            scale_fct = tl.exp(row_max - new_m)
            P = tl.exp(S - new_m[:, None])
            l_update = tl.sum(P, axis=1)
            new_l = row_l * scale_fct + l_update

            O_update = tl.dot(P, V_block)
            local_O = (local_O * row_l[:, None] * scale_fct[:, None] + O_update) / new_l[:, None]

            row_max = new_m
            row_l = new_l

            bn += 1

        o_base = pid_z * stride_oz + pid_h * stride_oh + block_start_m * stride_om
        o_ptrs = O_ptr + o_base + offs_m[:, None] * stride_om + offs_dv[None, :] * stride_od
        tl.store(o_ptrs, local_O.to(tl.float16), mask=mask_m[:, None])

    kernel = triton.jit(kernel, constants={"BLOCK_M": BLOCK_M, "BLOCK_N": BLOCK_N})

    grid = (Z, H, cdiv(M, BLOCK_M))
    kernel[grid](
        Q, K, V, out,
        *stride_q,
        *stride_k,
        *stride_v,
        *stride_o,
        Z=Z, H=H, M=M, N=N, Dq=Dq, Dv=Dv,
        scale=float(scale),
        causal=causal
    )

    return out
"""
        return {"code": code}