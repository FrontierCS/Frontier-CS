import textwrap

KERNEL_CODE = textwrap.dedent(
    """
import torch
import triton
import triton.language as tl


@triton.jit
def _quant_dot_kernel(
    scale_ptr,
    offset_ptr,
    weight_ptr,
    act_ptr,
    out_ptr,
    M,
    N,
    stride_sm,
    stride_sk,
    stride_om,
    stride_wm,
    stride_wk,
    stride_ak,
    stride_an,
    stride_outm,
    stride_outn,
    BM: tl.constexpr,
    BN: tl.constexpr,
):
    pid_m = tl.program_id(0)
    pid_n = tl.program_id(1)

    offs_m = pid_m * BM + tl.arange(0, BM)
    offs_n = pid_n * BN + tl.arange(0, BN)

    mask_m = offs_m < M
    mask_n = offs_n < N

    g = tl.arange(0, 8).to(tl.int32)
    shift_g = (g * 4).to(tl.int32)

    o_pack = tl.load(offset_ptr + offs_m * stride_om, mask=mask_m, other=0).to(tl.int32)
    o_nib = (o_pack[:, None] >> shift_g[None, :]) & 0xF  # (BM, 8) int32

    s = tl.load(
        scale_ptr + offs_m[:, None] * stride_sm + g[None, :] * stride_sk,
        mask=mask_m[:, None],
        other=0.0,
    )
    s = tl.cast(s, tl.float16)  # (BM, 8)

    p = tl.load(
        weight_ptr + offs_m[:, None] * stride_wm + g[None, :] * stride_wk,
        mask=mask_m[:, None],
        other=0,
    ).to(tl.int32)  # (BM, 8)

    t = tl.arange(0, 8).to(tl.int32)
    shift_t = (t * 4).to(tl.int32)

    w = (p[:, :, None] >> shift_t[None, None, :]) & 0xF  # (BM, 8, 8) int32

    a3 = (tl.cast(w, tl.float16) - tl.cast(o_nib[:, :, None], tl.float16)) * s[:, :, None]  # (BM, 8, 8)
    a = tl.reshape(a3, (BM, 64))  # (BM, 64) fp16

    k = tl.arange(0, 64)
    b = tl.load(
        act_ptr + k[:, None] * stride_ak + offs_n[None, :] * stride_an,
        mask=mask_n[None, :],
        other=0.0,
    )
    b = tl.cast(b, tl.float16)  # (64, BN)

    acc = tl.dot(a, b)  # (BM, BN) fp32

    out_ptrs = out_ptr + offs_m[:, None] * stride_outm + offs_n[None, :] * stride_outn
    tl.store(out_ptrs, tl.cast(acc, tl.float16), mask=mask_m[:, None] & mask_n[None, :])


def quant_dot(scale: torch.Tensor, offset_packed: torch.Tensor, weight_packed: torch.Tensor, activation: torch.Tensor) -> torch.Tensor:
    if not (scale.is_cuda and offset_packed.is_cuda and weight_packed.is_cuda and activation.is_cuda):
        raise ValueError("All inputs must be CUDA tensors.")
    if activation.dtype != torch.float16:
        raise ValueError("activation must be float16.")
    if offset_packed.dtype != torch.int32 or weight_packed.dtype != torch.int32:
        raise ValueError("offset_packed and weight_packed must be int32.")
    if scale.ndim != 2 or weight_packed.ndim != 2 or activation.ndim != 2 or offset_packed.ndim != 1:
        raise ValueError("Invalid input ranks.")
    M = weight_packed.shape[0]
    if scale.shape[0] != M or offset_packed.shape[0] != M:
        raise ValueError("M dimension mismatch.")
    if weight_packed.shape[1] != 8 or scale.shape[1] != 8:
        raise ValueError("Expected K/8 == 8 (K == 64).")
    if activation.shape[0] != 64:
        raise ValueError("Expected activation.shape[0] == 64.")
    N = activation.shape[1]

    out = torch.empty((M, N), device=activation.device, dtype=torch.float16)

    BM = 64
    if N >= 128:
        BN = 128
        num_warps = 8
        num_stages = 3
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
        offset_packed.stride(0),
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
"""
).lstrip()


class Solution:
    def solve(self, spec_path: str = None) -> dict:
        return {"code": KERNEL_CODE}