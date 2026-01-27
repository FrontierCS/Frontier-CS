import math
import os
from typing import Dict, Optional

import torch
import triton
import triton.language as tl

_TL_RESHAPE = getattr(tl, "reshape", None) or getattr(tl, "view", None)


@triton.jit
def _quant_dot_kernel(
    scale_ptr,
    offset_packed_ptr,
    weight_packed_ptr,
    act_ptr,
    out_ptr,
    M,
    N,
    stride_sm,
    stride_sk,
    stride_wm,
    stride_wk,
    stride_ak,
    stride_an,
    stride_om,
    stride_on,
    BM: tl.constexpr,
    BN: tl.constexpr,
):
    pid_m = tl.program_id(0)
    pid_n = tl.program_id(1)

    offs_m = pid_m * BM + tl.arange(0, BM)
    offs_n = pid_n * BN + tl.arange(0, BN)

    mask_m = offs_m < M
    mask_n = offs_n < N

    g = tl.arange(0, 8)
    shifts4 = tl.arange(0, 8) * 4

    off_pack = tl.load(offset_packed_ptr + offs_m, mask=mask_m, other=0).to(tl.int32)
    off_vals = (off_pack[:, None] >> shifts4[None, :]) & 0xF  # (BM, 8) int32

    scale = tl.load(
        scale_ptr + offs_m[:, None] * stride_sm + g[None, :] * stride_sk,
        mask=mask_m[:, None],
        other=0.0,
    ).to(tl.float16)  # (BM, 8)

    w_pack = tl.load(
        weight_packed_ptr + offs_m[:, None] * stride_wm + g[None, :] * stride_wk,
        mask=mask_m[:, None],
        other=0,
    ).to(tl.int32)  # (BM, 8)

    w_vals = (w_pack[:, :, None] >> shifts4[None, None, :]) & 0xF  # (BM, 8, 8) int32
    diff = w_vals - off_vals[:, :, None]  # (BM, 8, 8) int32
    a = diff.to(tl.float16) * scale[:, :, None]  # (BM, 8, 8) fp16

    if _TL_RESHAPE is not None:
        a2d = _TL_RESHAPE(a, (BM, 64))
    else:
        a2d = a.reshape((BM, 64))

    k = tl.arange(0, 64)
    b = tl.load(
        act_ptr + k[:, None] * stride_ak + offs_n[None, :] * stride_an,
        mask=mask_n[None, :],
        other=0.0,
    )  # (64, BN) fp16

    acc = tl.dot(a2d, b)  # (BM, BN) fp32

    tl.store(
        out_ptr + offs_m[:, None] * stride_om + offs_n[None, :] * stride_on,
        acc.to(tl.float16),
        mask=mask_m[:, None] & mask_n[None, :],
    )


def _unpack_int4_from_int32(packed: torch.Tensor, count: int = 8) -> torch.Tensor:
    shifts = (torch.arange(count, device=packed.device, dtype=torch.int32) * 4).view(
        *((1,) * packed.ndim), count
    )
    x = ((packed.unsqueeze(-1).to(torch.int32) >> shifts) & 0xF).to(torch.int16)
    return x


def quant_dot(scale: torch.Tensor, offset_packed: torch.Tensor, weight_packed: torch.Tensor, activation: torch.Tensor) -> torch.Tensor:
    if activation.ndim != 2:
        raise ValueError("activation must be 2D (K, N)")
    K, N = activation.shape
    if K != 64:
        raise ValueError(f"K must be 64, got {K}")
    if weight_packed.ndim != 2 or weight_packed.shape[1] != 8:
        raise ValueError("weight_packed must have shape (M, 8)")
    if scale.ndim != 2 or scale.shape[1] != 8:
        raise ValueError("scale must have shape (M, 8)")
    M = weight_packed.shape[0]
    if scale.shape[0] != M or offset_packed.shape[0] != M:
        raise ValueError("scale/offset_packed/weight_packed must agree on M")
    if activation.dtype != torch.float16:
        activation = activation.to(torch.float16)

    if not (scale.is_cuda and offset_packed.is_cuda and weight_packed.is_cuda and activation.is_cuda):
        w = _unpack_int4_from_int32(weight_packed, 8).reshape(M, 64).to(torch.float32)
        o = _unpack_int4_from_int32(offset_packed, 8).reshape(M, 8).to(torch.float32)
        o = o.repeat_interleave(8, dim=1)
        s = scale.to(torch.float32).repeat_interleave(8, dim=1)
        a = s * (w - o)
        out = a @ activation.to(torch.float32)
        return out.to(torch.float16)

    out = torch.empty((M, N), device=activation.device, dtype=torch.float16)

    BM = 64
    if N >= 256:
        BN = 256
        num_warps = 8
        num_stages = 2
    elif N >= 128:
        BN = 128
        num_warps = 4
        num_stages = 2
    else:
        BN = 64
        num_warps = 4
        num_stages = 2

    grid = (triton.cdiv(M, BM), triton.cdiv(N, BN))

    _quant_dot_kernel[grid](
        scale,
        offset_packed,
        weight_packed,
        activation,
        out,
        M,
        N,
        scale.stride(0),
        scale.stride(1),
        weight_packed.stride(0),
        weight_packed.stride(1),
        activation.stride(0),
        activation.stride(1),
        out.stride(0),
        out.stride(1),
        BM=BM,
        BN=BN,
        num_warps=num_warps,
        num_stages=num_stages,
    )
    return out


class Solution:
    def solve(self, spec_path: str = None) -> dict:
        try:
            program_path = __file__
            if program_path is not None and os.path.exists(program_path):
                return {"program_path": program_path}
        except Exception:
            program_path = None

        import inspect
        import sys

        mod = sys.modules[__name__]
        try:
            code = inspect.getsource(mod)
        except Exception:
            code = ""
        return {"code": code}