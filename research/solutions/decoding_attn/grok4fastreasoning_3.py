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

configs_qk = [
    triton.Config({'BLOCK_D': 64, 'BLOCK_N': 512}, num_warps=4, num_stages=1),
    triton.Config({'BLOCK_D': 64, 'BLOCK_N': 1024}, num_warps=8, num_stages=2),
    triton.Config({'BLOCK_D': 64, 'BLOCK_N': 2048}, num_warps=8, num_stages=4),
]

@triton.autotune(configs_qk, key=['N'])
def qk_kernel(
    Q_ptr, K_ptr, Scores_ptr, scale: tl.float32,
    Z: tl.int32, H: tl.int32, M: tl.int32, N: tl.int32, D: tl.int32,
    stride_qz: tl.int32, stride_qh: tl.int32, stride_qm: tl.int32, stride_qd: tl.int32,
    stride_kz: tl.int32, stride_kh: tl.int32, stride_kn: tl.int32, stride_kd: tl.int32,
    stride_sz: tl.int32, stride_sh: tl.int32, stride_sm: tl.int32, stride_sn: tl.int32,
    BLOCK_N: tl.constexpr,
    BLOCK_D: tl.constexpr
):
    pid_z = tl.program_id(0)
    pid_h = tl.program_id(1)
    pid_n = tl.program_id(2)
    offs_d = tl.arange(0, BLOCK_D)
    q_ptr = Q_ptr + pid_z * stride_qz + pid_h * stride_qh + 0 * stride_qm + offs_d * stride_qd
    q = tl.load(q_ptr, mask=offs_d < D, other=0.0).to(tl.float32)
    offs_n = pid_n * BLOCK_N + tl.arange(0, BLOCK_N)
    k_ptr = K_ptr + pid_z * stride_kz + pid_h * stride_kh + offs_n[:, None] * stride_kn + offs_d[None, :] * stride_kd
    k_mask = (offs_n[:, None] < N) & (offs_d[None, :] < D)
    k = tl.load(k_ptr, mask=k_mask, other=0.0).to(tl.float32)
    scores_block = tl.sum(q[None, :] * k, axis=1) * scale
    scores_ptr = Scores_ptr + pid_z * stride_sz + pid_h * stride_sh + 0 * stride_sm + offs_n * stride_sn
    tl.store(scores_ptr, scores_block.to(tl.float16), mask=offs_n < N)

configs_pv = [
    triton.Config({'BLOCK_DV': 64, 'BLOCK_N': 512}, num_warps=4, num_stages=1),
    triton.Config({'BLOCK_DV': 64, 'BLOCK_N': 1024}, num_warps=8, num_stages=2),
    triton.Config({'BLOCK_DV': 64, 'BLOCK_N': 2048}, num_warps=8, num_stages=4),
]

@triton.autotune(configs_pv, key=['N'])
def pv_kernel(
    P_ptr, V_ptr, Out_ptr,
    Z: tl.int32, H: tl.int32, M: tl.int32, N: tl.int32, Dv: tl.int32,
    stride_pz: tl.int32, stride_ph: tl.int32, stride_pm: tl.int32, stride_pn: tl.int32,
    stride_vz: tl.int32, stride_vh: tl.int32, stride_vn: tl.int32, stride_vd: tl.int32,
    stride_oz: tl.int32, stride_oh: tl.int32, stride_om: tl.int32, stride_od: tl.int32,
    BLOCK_N: tl.constexpr,
    BLOCK_DV: tl.constexpr
):
    pid_z = tl.program_id(0)
    pid_h = tl.program_id(1)
    pid_n = tl.program_id(2)
    offs_n = pid_n * BLOCK_N + tl.arange(0, BLOCK_N)
    p_ptr = P_ptr + pid_z * stride_pz + pid_h * stride_ph + 0 * stride_pm + offs_n * stride_pn
    p = tl.load(p_ptr, mask=offs_n < N, other=0.0).to(tl.float32)
    offs_dv = tl.arange(0, BLOCK_DV)
    v_ptr = V_ptr + pid_z * stride_vz + pid_h * stride_vh + offs_n[:, None] * stride_vn + offs_dv[None, :] * stride_vd
    v_mask = (offs_n[:, None] < N) & (offs_dv[None, :] < Dv)
    v = tl.load(v_ptr, mask=v_mask, other=0.0).to(tl.float32)
    partial = tl.sum(p[:, None] * v, axis=0)
    partial = partial.to(tl.float16)
    o_ptr = Out_ptr + pid_z * stride_oz + pid_h * stride_oh + 0 * stride_om + offs_dv * stride_od
    tl.atomic_add(o_ptr, partial, mask=offs_dv < Dv)

def decoding_attn(Q: torch.Tensor, K: torch.Tensor, V: torch.Tensor) -> torch.Tensor:
    Z, H, M, Dq = Q.shape
    _, _, N, Dv = V.shape
    Dk = K.shape[3]
    assert Dq == Dk
    assert M == 1
    D = Dq
    device = Q.device
    scale_val = 1.0 / math.sqrt(D)
    scale_tensor = torch.tensor(scale_val, dtype=torch.float32, device=device)
    scores = torch.empty((Z, H, M, N), dtype=torch.float16, device=device)
    stride_sz = scores.stride(0)
    stride_sh = scores.stride(1)
    stride_sm = scores.stride(2)
    stride_sn = scores.stride(3)
    stride_qz = Q.stride(0)
    stride_qh = Q.stride(1)
    stride_qm = Q.stride(2)
    stride_qd = Q.stride(3)
    stride_kz = K.stride(0)
    stride_kh = K.stride(1)
    stride_kn = K.stride(2)
    stride_kd = K.stride(3)
    stride_vz = V.stride(0)
    stride_vh = V.stride(1)
    stride_vn = V.stride(2)
    stride_vd = V.stride(3)
    grid_qk = (Z, H, triton.cdiv(N, 1024))
    qk_kernel[grid_qk](
        Q, K, scores, scale_tensor,
        Z, H, M, N, D,
        stride_qz, stride_qh, stride_qm, stride_qd,
        stride_kz, stride_kh, stride_kn, stride_kd,
        stride_sz, stride_sh, stride_sm, stride_sn,
    )
    scores_f32 = scores.float()
    probs = torch.softmax(scores_f32, dim=-1).to(torch.float16)
    out = torch.zeros((Z, H, M, Dv), dtype=torch.float16, device=device)
    stride_oz = out.stride(0)
    stride_oh = out.stride(1)
    stride_om = out.stride(2)
    stride_od = out.stride(3)
    stride_pz = probs.stride(0)
    stride_ph = probs.stride(1)
    stride_pm = probs.stride(2)
    stride_pn = probs.stride(3)
    grid_pv = (Z, H, triton.cdiv(N, 1024))
    pv_kernel[grid_pv](
        probs, V, out,
        Z, H, M, N, Dv,
        stride_pz, stride_ph, stride_pm, stride_pn,
        stride_vz, stride_vh, stride_vn, stride_vd,
        stride_oz, stride_oh, stride_om, stride_od,
    )
    return out
"""
        return {"code": code}