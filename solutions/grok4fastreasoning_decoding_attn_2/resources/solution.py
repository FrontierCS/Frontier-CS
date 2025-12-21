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
def scores_kernel(
    Q_PTR, K_PTR, S_PTR,
    Z, H, M, N, D,
    stride_qz, stride_qh, stride_qm, stride_qd,
    stride_kz, stride_kh, stride_kn, stride_kd,
    stride_sz, stride_sh, stride_sm, stride_sn,
    BLOCK_N: tl.constexpr,
    SCALE: tl.float32
):
    pid_z = tl.program_id(0)
    pid_h = tl.program_id(1)
    pid_bn = tl.program_id(2)
    if pid_z >= Z or pid_h >= H:
        return

    q_ptr = Q_PTR + pid_z * stride_qz + pid_h * stride_qh + 0 * stride_qm
    ar_d = tl.arange(0, D)
    q = tl.load(q_ptr + ar_d * stride_qd, mask=ar_d < D, other=0.0).to(tl.float32)

    offs_n = pid_bn * BLOCK_N + tl.arange(0, BLOCK_N)
    mask_n = offs_n < N
    ar_dn = tl.arange(0, D)[None, :]
    k_ptr = K_PTR + pid_z * stride_kz + pid_h * stride_kh + offs_n[:, None] * stride_kn + ar_dn * stride_kd
    k = tl.load(k_ptr, mask=mask_n[:, None] & (ar_dn < D)[None, :], other=0.0).to(tl.float32)

    scores = tl.sum(k * q[None, :], axis=1) * SCALE

    s_ptr = S_PTR + pid_z * stride_sz + pid_h * stride_sh + 0 * stride_sm + offs_n * stride_sn
    tl.store(s_ptr, scores, mask=mask_n)

@triton.jit
def value_kernel(
    P_PTR, V_PTR, O_PTR,
    Z, H, N, Dv,
    stride_pz, stride_ph, stride_pn,
    stride_vz, stride_vh, stride_vn, stride_vd,
    stride_oz, stride_oh, stride_om, stride_od,
    BLOCK_N: tl.constexpr,
    BLOCK_DV: tl.constexpr
):
    pid_z = tl.program_id(0)
    pid_h = tl.program_id(1)
    pid_bd = tl.program_id(2)
    if pid_z >= Z or pid_h >= H:
        return

    offs_d = pid_bd * BLOCK_DV + tl.arange(0, BLOCK_DV)
    mask_d = offs_d < Dv

    p_base = P_PTR + pid_z * stride_pz + pid_h * stride_ph
    v_base = V_PTR + pid_z * stride_vz + pid_h * stride_vh
    o_base = O_PTR + pid_z * stride_oz + pid_h * stride_oh + 0 * stride_om

    acc = tl.zeros([BLOCK_DV], dtype=tl.float32)

    for start_n in range(0, N, BLOCK_N):
        offs_n = start_n + tl.arange(0, BLOCK_N)
        mask_n = offs_n < N

        p_block = tl.load(p_base + offs_n * stride_pn, mask=mask_n, other=0.0)

        v_offsets = offs_n[:, None] * stride_vn + offs_d[None, :] * stride_vd
        v_ptr = v_base + v_offsets
        v_mask = mask_n[:, None] & mask_d[None, :]
        v_block = tl.load(v_ptr, mask=v_mask, other=0.0).to(tl.float32)

        p_block = p_block.to(tl.float32)
        acc += tl.sum(p_block[:, None] * v_block, axis=0)

    o_offsets = offs_d * stride_od
    tl.store(o_base + o_offsets, acc, mask=mask_d)

def decoding_attn(Q: torch.Tensor, K: torch.Tensor, V: torch.Tensor) -> torch.Tensor:
    Z, H, M, Dq = Q.shape
    _, _, N, Dv = V.shape
    device = Q.device
    scale = 1.0 / math.sqrt(Dq)
    Scores = torch.empty((Z, H, N), dtype=torch.float32, device=device)
    s_qz = Q.stride(0)
    s_qh = Q.stride(1)
    s_qm = Q.stride(2)
    s_qd = Q.stride(3)
    s_kz = K.stride(0)
    s_kh = K.stride(1)
    s_kn = K.stride(2)
    s_kd = K.stride(3)
    s_sz = Scores.stride(0)
    s_sh = Scores.stride(1)
    s_sn = Scores.stride(2)
    BLOCK_N_score = 128
    grid_score = (Z, H, triton.cdiv(N, BLOCK_N_score))
    scores_kernel[grid_score](
        Q, K, Scores,
        Z, H, M, N, Dq,
        s_qz, s_qh, s_qm, s_qd,
        s_kz, s_kh, s_kn, s_kd,
        s_sz, s_sh, 0, s_sn,
        BLOCK_N=BLOCK_N_score,
        SCALE=scale,
        num_stages=1,
    )
    Probs = torch.softmax(Scores, dim=-1)
    O = torch.empty((Z, H, M, Dv), dtype=torch.float32, device=device)
    s_pz = Probs.stride(0)
    s_ph = Probs.stride(1)
    s_pn = Probs.stride(2)
    s_vz = V.stride(0)
    s_vh = V.stride(1)
    s_vn = V.stride(2)
    s_vd = V.stride(3)
    s_oz = O.stride(0)
    s_oh = O.stride(1)
    s_om = O.stride(2)
    s_od = O.stride(3)
    BLOCK_N_val = 128
    BLOCK_DV_val = 64
    grid_val = (Z, H, triton.cdiv(Dv, BLOCK_DV_val))
    value_kernel[grid_val](
        Probs, V, O,
        Z, H, N, Dv,
        s_pz, s_ph, s_pn,
        s_vz, s_vh, s_vn, s_vd,
        s_oz, s_oh, s_om, s_od,
        BLOCK_N=BLOCK_N_val,
        BLOCK_DV=BLOCK_DV_val,
        num_stages=2,
    )
    return O.to(Q.dtype)
"""
        return {"code": code}
