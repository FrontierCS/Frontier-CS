import os
import math
import torch
import triton
import triton.language as tl


@triton.jit
def _quant_dot_kernel(
    scale_ptr,
    offset_packed_ptr,
    weight_packed_ptr,
    activation_ptr,
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
    BLOCK_M: tl.constexpr,
    BLOCK_N: tl.constexpr,
):
    pid_m = tl.program_id(0)
    pid_n = tl.program_id(1)

    offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
    offs_n = pid_n * BLOCK_N + tl.arange(0, BLOCK_N)

    mask_m = offs_m < M
    mask_n = offs_n < N

    g = tl.arange(0, 8)
    w_ptrs = weight_packed_ptr + offs_m[:, None] * stride_wm + g[None, :] * stride_wk
    s_ptrs = scale_ptr + offs_m[:, None] * stride_sm + g[None, :] * stride_sk

    w_pack = tl.load(w_ptrs, mask=mask_m[:, None], other=0).to(tl.int32)
    s_pack = tl.load(s_ptrs, mask=mask_m[:, None], other=0.0)
    s_pack = tl.cast(s_pack, tl.float16)

    o_pack = tl.load(offset_packed_ptr + offs_m, mask=mask_m, other=0).to(tl.int32)

    shifts = (tl.arange(0, 8).to(tl.int32) * 4)[None, None, :]
    w_unpacked = (w_pack[:, :, None] >> shifts) & 0xF  # (BM, 8, 8)

    shifts2 = (tl.arange(0, 8).to(tl.int32) * 4)[None, :]
    o_unpacked = (o_pack[:, None] >> shifts2) & 0xF  # (BM, 8)

    ones8_i32 = tl.full((8,), 1, tl.int32)
    ones8_f16 = tl.full((8,), 1.0, tl.float16)

    o_rep = o_unpacked[:, :, None] * ones8_i32[None, None, :]  # (BM, 8, 8)
    s_rep = s_pack[:, :, None] * ones8_f16[None, None, :]      # (BM, 8, 8)

    w_i = tl.reshape(w_unpacked, (BLOCK_M, 64)).to(tl.int16)
    o_i = tl.reshape(o_rep, (BLOCK_M, 64)).to(tl.int16)
    s_i = tl.reshape(s_rep, (BLOCK_M, 64)).to(tl.float16)

    a = tl.cast(w_i - o_i, tl.float16) * s_i  # (BM, 64), fp16

    k = tl.arange(0, 64)
    act_ptrs = activation_ptr + k[:, None] * stride_ak + offs_n[None, :] * stride_an
    b = tl.load(act_ptrs, mask=mask_n[None, :], other=0.0).to(tl.float16)  # (64, BN)

    acc = tl.dot(a, b, out_dtype=tl.float32)

    out_ptrs = out_ptr + offs_m[:, None] * stride_om + offs_n[None, :] * stride_on
    tl.store(out_ptrs, tl.cast(acc, tl.float16), mask=mask_m[:, None] & mask_n[None, :])


def _quant_dot_reference(scale: torch.Tensor, offset_packed: torch.Tensor, weight_packed: torch.Tensor, activation: torch.Tensor) -> torch.Tensor:
    FPINT = 8
    GROUP = 8
    K = FPINT * GROUP
    M = weight_packed.shape[0]
    N = activation.shape[1]
    w = weight_packed.view(M, FPINT).to(torch.int32)
    shifts = (torch.arange(FPINT, device=w.device, dtype=torch.int32) * 4)[None, :]
    w4 = ((w[:, :, None] >> shifts[:, None, :]) & 0xF).reshape(M, K).to(torch.int32)

    o = offset_packed.to(torch.int32)[:, None]
    o4 = ((o >> shifts) & 0xF).to(torch.int32)  # (M, FPINT)
    o4 = o4[:, :, None].expand(M, FPINT, GROUP).reshape(M, K).to(torch.int32)

    s = scale.to(torch.float32)
    s = s[:, :, None].expand(M, FPINT, GROUP).reshape(M, K)

    a = (w4 - o4).to(torch.float32) * s
    z = a @ activation.to(torch.float32)
    return z.to(torch.float16)


def quant_dot(scale: torch.Tensor, offset_packed: torch.Tensor, weight_packed: torch.Tensor, activation: torch.Tensor) -> torch.Tensor:
    if not (scale.is_cuda and offset_packed.is_cuda and weight_packed.is_cuda and activation.is_cuda):
        return _quant_dot_reference(scale, offset_packed, weight_packed, activation)

    if activation.dtype != torch.float16:
        activation = activation.to(torch.float16)
    if offset_packed.dtype != torch.int32:
        offset_packed = offset_packed.to(torch.int32)
    if weight_packed.dtype != torch.int32:
        weight_packed = weight_packed.to(torch.int32)
    if scale.dtype not in (torch.float16, torch.float32):
        scale = scale.to(torch.float16)

    assert activation.ndim == 2 and activation.shape[0] == 64
    assert weight_packed.ndim == 2 and weight_packed.shape[1] == 8
    assert scale.ndim == 2 and scale.shape[1] == 8
    assert offset_packed.ndim == 1 and offset_packed.shape[0] == weight_packed.shape[0]

    M = weight_packed.shape[0]
    N = activation.shape[1]
    out = torch.empty((M, N), device=activation.device, dtype=torch.float16)

    stride_sm, stride_sk = scale.stride()
    stride_wm, stride_wk = weight_packed.stride()
    stride_ak, stride_an = activation.stride()
    stride_om, stride_on = out.stride()

    if N >= 128:
        BLOCK_N = 128
        if M >= 64:
            BLOCK_M = 32
            num_warps = 8
        else:
            BLOCK_M = 32
            num_warps = 4
    elif N >= 64:
        BLOCK_N = 64
        BLOCK_M = 64 if M >= 64 else 32
        num_warps = 4
    else:
        BLOCK_N = 32
        BLOCK_M = 64 if M >= 64 else 32
        num_warps = 4

    grid = (triton.cdiv(M, BLOCK_M), triton.cdiv(N, BLOCK_N))
    _quant_dot_kernel[grid](
        scale,
        offset_packed,
        weight_packed,
        activation,
        out,
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
        BLOCK_M=BLOCK_M,
        BLOCK_N=BLOCK_N,
        num_warps=num_warps,
        num_stages=3,
    )
    return out


class Solution:
    def solve(self, spec_path: str = None) -> dict:
        return {"program_path": os.path.abspath(__file__)}