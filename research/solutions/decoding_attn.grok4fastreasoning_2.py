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

@triton.autotune(
    configs=[
        triton.Config({'BLOCK_N': 64}, num_stages=1, num_warps=4),
        triton.Config({'BLOCK_N': 128}, num_stages=2, num_warps=4),
        triton.Config({'BLOCK_N': 256}, num_stages=3, num_warps=8),
        triton.Config({'BLOCK_N': 512}, num_stages=4, num_warps=8),
    ],
    key=['N'],
)
@triton.jit
def attn_kernel(
    Q_PTR, K_PTR, V_PTR, O_PTR,
    STRIDE_QZ, STRIDE_QH, STRIDE_QD,
    STRIDE_KZ, STRIDE_KH, STRIDE_KN, STRIDE_KD,
    STRIDE_VZ, STRIDE_VH, STRIDE_VN, STRIDE_VD,
    STRIDE_OZ, STRIDE_OH, STRIDE_OD,
    Z, H, N, D, DV, BLOCK_N: tl.constexpr
):
    pid_z = tl.program_id(0)
    pid_h = tl.program_id(1)
    if pid_z >= Z or pid_h >= H:
        return

    scale = 1.0 / tl.sqrt(tl.full([1], D, dtype=tl.float32))
    q_base = Q_PTR + pid_z * STRIDE_QZ + pid_h * STRIDE_QH
    q = tl.load(q_base + tl.arange(0, D) * STRIDE_QD, mask=tl.arange(0, D) < D).to(tl.float32)

    # First pass: compute max
    m = tl.full([1], -1e9, dtype=tl.float32)
    for start_n in range(0, N, BLOCK_N):
        offs_n = tl.arange(0, BLOCK_N)
        mask_n = offs_n < (N - start_n)
        k_base = K_PTR + pid_z * STRIDE_KZ + pid_h * STRIDE_KH + start_n * STRIDE_KN
        k_offsets = k_base + offs_n[:, None] * STRIDE_KN + tl.arange(0, D)[None, :] * STRIDE_KD
        k_mask = mask_n[:, None] & (tl.arange(0, D)[None, :] < D)
        k = tl.load(k_offsets, mask=k_mask, other=0.0).to(tl.float32)
        scores = tl.sum(q[None, :] * k, axis=1) * scale
        m = tl.maximum(m, tl.max(scores, axis=0))

    # Second pass: compute sum and output
    s = tl.zeros([1], dtype=tl.float32)
    o = tl.zeros([DV], dtype=tl.float32)
    for start_n in range(0, N, BLOCK_N):
        offs_n = tl.arange(0, BLOCK_N)
        mask_n = offs_n < (N - start_n)
        k_base = K_PTR + pid_z * STRIDE_KZ + pid_h * STRIDE_KH + start_n * STRIDE_KN
        k_offsets = k_base + offs_n[:, None] * STRIDE_KN + tl.arange(0, D)[None, :] * STRIDE_KD
        k_mask = mask_n[:, None] & (tl.arange(0, D)[None, :] < D)
        k = tl.load(k_offsets, mask=k_mask, other=0.0).to(tl.float32)
        scores = tl.sum(q[None, :] * k, axis=1) * scale
        p = tl.exp(scores - m)
        s += tl.sum(p, axis=0)

        v_base = V_PTR + pid_z * STRIDE_VZ + pid_h * STRIDE_VH + start_n * STRIDE_VN
        v_offsets = v_base + offs_n[:, None] * STRIDE_VN + tl.arange(0, DV)[None, :] * STRIDE_VD
        v_mask = mask_n[:, None] & (tl.arange(0, DV)[None, :] < DV)
        v = tl.load(v_offsets, mask=v_mask, other=0.0).to(tl.float32)
        o += tl.sum(p[:, None] * v, axis=0)

    o /= s
    o_base = O_PTR + pid_z * STRIDE_OZ + pid_h * STRIDE_OH
    o_fp16 = o.to(tl.float16)
    tl.store(o_base + tl.arange(0, DV) * STRIDE_OD, o_fp16, mask=tl.arange(0, DV) < DV)

def decoding_attn(Q: torch.Tensor, K: torch.Tensor, V: torch.Tensor) -> torch.Tensor:
    Z, H, M, D = Q.shape
    _, _, N, DV = V.shape
    assert M == 1
    output = torch.empty(Z, H, M, DV, dtype=Q.dtype, device=Q.device)

    strides_q = Q.stride()
    strides_k = K.stride()
    strides_v = V.stride()
    strides_o = output.stride()

    grid = (Z, H)
    attn_kernel[grid](
        Q.data_ptr(), K.data_ptr(), V.data_ptr(), output.data_ptr(),
        strides_q[0], strides_q[1], strides_q[3],
        strides_k[0], strides_k[1], strides_k[2], strides_k[3],
        strides_v[0], strides_v[1], strides_v[2], strides_v[3],
        strides_o[0], strides_o[1], strides_o[3],
        Z, H, N, D, DV,
        num_stages=4,
    )
    return output
"""
        return {"code": code}