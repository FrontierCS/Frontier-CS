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
def compute_attn_kernel(
    Q, K, V, scores, out,
    Z, H, N, D, scale: tl.float32,
    stride_qz, stride_qh, stride_qm, stride_qd,
    stride_kz, stride_kh, stride_kn, stride_kd,
    stride_vz, stride_vh, stride_vn, stride_vd,
    stride_sz, stride_sh, stride_sn,
    stride_oz, stride_oh, stride_om, stride_od,
    BLOCK_N: tl.constexpr,
    BLOCK_D: tl.constexpr
):
    pid_z = tl.program_id(0)
    pid_h = tl.program_id(1)
    if pid_z >= Z or pid_h >= H:
        return

    offs_d = tl.arange(0, BLOCK_D)
    q_ptr = Q + pid_z * stride_qz + pid_h * stride_qh + 0 * stride_qm + offs_d * stride_qd
    q = tl.load(q_ptr, mask=(offs_d < D), other=0.0).to(tl.float32)
    q *= scale

    scores_base = scores + pid_z * stride_sz + pid_h * stride_sh
    lo = 0
    while lo < N:
        offs_n = tl.arange(0, BLOCK_N) + lo
        n_mask = offs_n < N
        k_ptr = K + pid_z * stride_kz + pid_h * stride_kh + offs_n[:, None] * stride_kn + offs_d[None, :] * stride_kd
        k_mask = n_mask[:, None] & (offs_d < D)[None, :]
        k = tl.load(k_ptr, mask=k_mask, other=0.0).to(tl.float32)
        scores_block = tl.sum(k * q[None, :], axis=1)
        s_ptr = scores_base + offs_n * stride_sn
        tl.store(s_ptr, scores_block, mask=n_mask)
        lo += BLOCK_N

    row_max = -1e9
    lo = 0
    while lo < N:
        offs_n = tl.arange(0, BLOCK_N) + lo
        n_mask = offs_n < N
        s_ptr = scores_base + offs_n * stride_sn
        s_block = tl.load(s_ptr, mask=n_mask, other=0.0)
        row_max = tl.maximum(row_max, tl.max(s_block))
        lo += BLOCK_N

    row_sum = 0.0
    lo = 0
    while lo < N:
        offs_n = tl.arange(0, BLOCK_N) + lo
        n_mask = offs_n < N
        s_ptr = scores_base + offs_n * stride_sn
        s_block = tl.load(s_ptr, mask=n_mask, other=0.0) - row_max
        row_sum += tl.sum(tl.exp(s_block))
        lo += BLOCK_N

    offs_dv = tl.arange(0, BLOCK_D)
    o = tl.zeros((BLOCK_D,), dtype=tl.float32)
    lo = 0
    while lo < N:
        offs_n = tl.arange(0, BLOCK_N) + lo
        n_mask = offs_n < N
        s_ptr = scores_base + offs_n * stride_sn
        s_block = tl.load(s_ptr, mask=n_mask, other=0.0) - row_max
        p_block = tl.exp(s_block) / row_sum
        v_ptr = V + pid_z * stride_vz + pid_h * stride_vh + offs_n[:, None] * stride_vn + offs_dv[None, :] * stride_vd
        v_mask = n_mask[:, None] & (offs_dv < D)[None, :]
        v = tl.load(v_ptr, mask=v_mask, other=0.0).to(tl.float32)
        o += tl.sum(p_block[:, None] * v, axis=0)
        lo += BLOCK_N

    o_ptr = out + pid_z * stride_oz + pid_h * stride_oh + 0 * stride_om + offs_dv * stride_od
    tl.store(o_ptr, o.to(tl.float16), mask=(offs_dv < D))


def decoding_attn(Q: torch.Tensor, K: torch.Tensor, V: torch.Tensor) -> torch.Tensor:
    Z, H, M, D = Q.shape
    _, _, N, Dv = V.shape
    assert M == 1
    assert D == 64 and Dv == 64
    scale = 1.0 / math.sqrt(D)
    scores = torch.zeros((Z, H, N), dtype=torch.float32, device=Q.device)
    out = torch.empty((Z, H, M, Dv), dtype=Q.dtype, device=Q.device)
    BLOCK_N = 256
    BLOCK_D = 64
    stride_qz, stride_qh, stride_qm, stride_qd = Q.stride()
    stride_kz, stride_kh, stride_kn, stride_kd = K.stride()
    stride_vz, stride_vh, stride_vn, stride_vd = V.stride()
    stride_sz, stride_sh, stride_sn = scores.stride()
    stride_oz, stride_oh, stride_om, stride_od = out.stride()
    grid = (Z, H)
    compute_attn_kernel[grid](
        Q, K, V, scores, out,
        Z, H, N, D, scale,
        stride_qz, stride_qh, stride_qm, stride_qd,
        stride_kz, stride_kh, stride_kn, stride_kd,
        stride_vz, stride_vh, stride_vn, stride_vd,
        stride_sz, stride_sh, stride_sn,
        stride_oz, stride_oh, stride_om, stride_od,
        BLOCK_N=BLOCK_N,
        BLOCK_D=BLOCK_D,
    )
    return out
"""
        return {"code": code}