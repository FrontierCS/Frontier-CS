import os
import sys
import math
import torch

KERNEL_CODE = r'''
import math
import torch
import triton
import triton.language as tl

@triton.jit
def _quant_dot_kernel(
    scale_ptr, off_ptr, w_ptr, act_ptr, out_ptr,
    M: tl.constexpr, N: tl.constexpr,
    stride_sc_m: tl.constexpr, stride_sc_g: tl.constexpr,
    stride_w_m: tl.constexpr, stride_w_g: tl.constexpr,
    stride_act_k: tl.constexpr, stride_act_n: tl.constexpr,
    stride_out_m: tl.constexpr, stride_out_n: tl.constexpr,
    BLOCK_M: tl.constexpr, BLOCK_N: tl.constexpr,
):
    pid_m = tl.program_id(0)
    pid_n = tl.program_id(1)

    offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
    offs_n = pid_n * BLOCK_N + tl.arange(0, BLOCK_N)

    mask_m = offs_m < M
    mask_n = offs_n < N

    tl.multiple_of(offs_n, 8)

    off_packed = tl.load(off_ptr + offs_m, mask=mask_m, other=0).to(tl.uint32)
    g_ids = tl.arange(0, 8)
    g_shifts = g_ids * 4
    o_nibbles = ((off_packed[:, None] >> g_shifts[None, :]) & 0xF).to(tl.int32)

    w_ptrs = w_ptr + offs_m[:, None] * stride_w_m + g_ids[None, :] * stride_w_g
    w_packed_mat = tl.load(w_ptrs, mask=mask_m[:, None], other=0).to(tl.uint32)

    sc_ptrs = scale_ptr + offs_m[:, None] * stride_sc_m + g_ids[None, :] * stride_sc_g
    sc_mat = tl.load(sc_ptrs, mask=mask_m[:, None], other=0).to(tl.float16)

    acc = tl.zeros((BLOCK_M, BLOCK_N), dtype=tl.float32)
    nib_shifts = tl.arange(0, 8) * 4

    for g in tl.static_range(0, 8):
        wp = w_packed_mat[:, g]
        w = ((wp[:, None] >> nib_shifts[None, :]) & 0xF).to(tl.int32)
        o = o_nibbles[:, g]
        w = w - o[:, None]
        s = sc_mat[:, g]
        a = (w.to(tl.float16) * s[:, None]).to(tl.float16)

        k = g * 8 + tl.arange(0, 8)
        b_ptrs = act_ptr + k[:, None] * stride_act_k + offs_n[None, :] * stride_act_n
        b = tl.load(b_ptrs, mask=mask_n[None, :], other=0.0).to(tl.float16)

        acc += tl.dot(a, b)

    out = acc.to(tl.float16)
    out_ptrs = out_ptr + offs_m[:, None] * stride_out_m + offs_n[None, :] * stride_out_n
    tl.store(out_ptrs, out, mask=mask_m[:, None] & mask_n[None, :])


def quant_dot(scale: torch.Tensor, offset_packed: torch.Tensor, weight_packed: torch.Tensor, activation: torch.Tensor) -> torch.Tensor:
    if not (scale.is_cuda and offset_packed.is_cuda and weight_packed.is_cuda and activation.is_cuda):
        raise ValueError("All inputs must be CUDA tensors.")
    if offset_packed.dtype != torch.int32 or weight_packed.dtype != torch.int32:
        raise TypeError("offset_packed and weight_packed must be torch.int32.")
    if activation.dtype != torch.float16:
        raise TypeError("activation must be torch.float16.")
    if scale.dtype not in (torch.float16, torch.float32):
        raise TypeError("scale must be torch.float16 or torch.float32.")

    M = weight_packed.shape[0]
    if scale.shape[0] != M or offset_packed.shape[0] != M:
        raise ValueError("M dimension mismatch among inputs.")
    if weight_packed.shape[1] != 8 or scale.shape[1] != 8:
        raise ValueError("Expected weight_packed and scale to have second dimension == 8 (K/8 with K=64).")
    if activation.shape[0] != 64:
        raise ValueError("Expected activation.shape[0] == 64 (K fixed to 64).")
    N = activation.shape[1]

    out = torch.empty((M, N), device=activation.device, dtype=torch.float16)

    # Heuristic meta-params
    if N >= 256:
        BLOCK_N = 256
        num_warps = 8
        BLOCK_M = 16 if M >= 16 else 16
    elif N >= 128:
        BLOCK_N = 128
        num_warps = 4
        BLOCK_M = 32 if M >= 32 else 16
    else:
        BLOCK_N = 64
        num_warps = 4
        BLOCK_M = 64 if M >= 64 else (32 if M >= 32 else 16)

    num_stages = 2

    grid = (triton.cdiv(M, BLOCK_M), triton.cdiv(N, BLOCK_N))

    _quant_dot_kernel[grid](
        scale, offset_packed, weight_packed, activation, out,
        M=M, N=N,
        stride_sc_m=scale.stride(0), stride_sc_g=scale.stride(1),
        stride_w_m=weight_packed.stride(0), stride_w_g=weight_packed.stride(1),
        stride_act_k=activation.stride(0), stride_act_n=activation.stride(1),
        stride_out_m=out.stride(0), stride_out_n=out.stride(1),
        BLOCK_M=BLOCK_M, BLOCK_N=BLOCK_N,
        num_warps=num_warps, num_stages=num_stages,
    )
    return out
'''

exec(KERNEL_CODE, globals())


class Solution:
    def solve(self, spec_path: str = None) -> dict:
        try:
            fp = __file__
            if isinstance(fp, str) and os.path.exists(fp):
                return {"program_path": fp}
        except Exception:
            pass
        return {"code": KERNEL_CODE}