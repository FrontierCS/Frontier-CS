import os
import math
import torch
import triton
import triton.language as tl


@triton.autotune(
    configs=[
        triton.Config({"BLOCK_M": 128, "BLOCK_N": 64}, num_warps=4, num_stages=3),
        triton.Config({"BLOCK_M": 64, "BLOCK_N": 128}, num_warps=4, num_stages=4),
        triton.Config({"BLOCK_M": 64, "BLOCK_N": 64}, num_warps=2, num_stages=4),
        triton.Config({"BLOCK_M": 128, "BLOCK_N": 32}, num_warps=2, num_stages=3),
    ],
    key=["N"],
)
@triton.jit
def _quant_dot_kernel(
    scale_ptr,
    offset_packed_ptr,
    weight_packed_ptr,
    activation_ptr,
    out_ptr,
    M: tl.constexpr,
    N: tl.constexpr,
    stride_sm: tl.constexpr,
    stride_sk: tl.constexpr,
    stride_wm: tl.constexpr,
    stride_wk: tl.constexpr,
    stride_ak: tl.constexpr,
    stride_an: tl.constexpr,
    stride_om: tl.constexpr,
    stride_on: tl.constexpr,
    BLOCK_M: tl.constexpr,
    BLOCK_N: tl.constexpr,
):
    pid_m = tl.program_id(0)
    pid_n = tl.program_id(1)

    offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
    offs_n = pid_n * BLOCK_N + tl.arange(0, BLOCK_N)

    mask_m = offs_m < M
    mask_n = offs_n < N

    off32 = tl.load(offset_packed_ptr + offs_m, mask=mask_m, other=0).to(tl.uint32)

    acc = tl.zeros((BLOCK_M, BLOCK_N), dtype=tl.float32)

    bits16 = tl.arange(0, 16)
    bits16_f = bits16[None, :] < 8
    n_broadcast = offs_n[None, :]

    # K = 64, process in chunks of 16 (2 packed int32 groups per iteration)
    for g in tl.static_range(0, 8, 2):
        # weights: two int32 packs -> one uint64 (16 nibbles)
        w0_u32 = tl.load(weight_packed_ptr + offs_m * stride_wm + g * stride_wk, mask=mask_m, other=0).to(tl.uint32)
        w1_u32 = tl.load(weight_packed_ptr + offs_m * stride_wm + (g + 1) * stride_wk, mask=mask_m, other=0).to(tl.uint32)
        w0_u64 = w0_u32.to(tl.uint64)
        w1_u64 = w1_u32.to(tl.uint64)
        w64 = w0_u64 | (w1_u64 << 32)

        w16 = ((w64[:, None] >> (bits16[None, :] * 4)) & 0xF).to(tl.float32)

        # offsets: one packed int32 per row, extract 2 nibbles and broadcast to 16 lanes
        o0 = ((off32 >> (4 * g)) & 0xF).to(tl.float32)
        o1 = ((off32 >> (4 * (g + 1))) & 0xF).to(tl.float32)
        off16 = tl.where(bits16_f, o0[:, None], o1[:, None])

        # scale: (M, 8), broadcast 2 scales across 16 lanes
        sc0 = tl.load(scale_ptr + offs_m * stride_sm + g * stride_sk, mask=mask_m, other=0.0).to(tl.float32)
        sc1 = tl.load(scale_ptr + offs_m * stride_sm + (g + 1) * stride_sk, mask=mask_m, other=0.0).to(tl.float32)
        sc16 = tl.where(bits16_f, sc0[:, None], sc1[:, None])

        a16 = (w16 - off16) * sc16
        a16 = a16.to(tl.float16)

        k_offsets = (g * 8 + tl.arange(0, 16))[:, None]
        b16 = tl.load(
            activation_ptr + k_offsets * stride_ak + n_broadcast * stride_an,
            mask=mask_n[None, :],
            other=0.0,
            cache_modifier=".ca",
        ).to(tl.float16)

        acc += tl.dot(a16, b16)

    out = acc.to(tl.float16)
    tl.store(out_ptr + offs_m[:, None] * stride_om + offs_n[None, :] * stride_on, out, mask=mask_m[:, None] & mask_n[None, :])


def quant_dot(scale: torch.Tensor, offset_packed: torch.Tensor, weight_packed: torch.Tensor, activation: torch.Tensor) -> torch.Tensor:
    if not (scale.is_cuda and offset_packed.is_cuda and weight_packed.is_cuda and activation.is_cuda):
        raise ValueError("All inputs must be CUDA tensors.")
    if activation.dtype != torch.float16:
        raise ValueError("activation must be torch.float16.")
    if offset_packed.dtype != torch.int32:
        offset_packed = offset_packed.to(torch.int32)
    if weight_packed.dtype != torch.int32:
        weight_packed = weight_packed.to(torch.int32)
    if scale.dtype not in (torch.float16, torch.float32):
        scale = scale.to(torch.float16)

    if scale.dim() != 2 or weight_packed.dim() != 2 or activation.dim() != 2 or offset_packed.dim() != 1:
        raise ValueError("Invalid input ranks.")
    M, k8 = scale.shape
    if k8 != 8:
        raise ValueError("scale must have shape (M, K/8) with K=64 -> K/8=8.")
    if weight_packed.shape != (M, 8):
        raise ValueError("weight_packed must have shape (M, 8).")
    if offset_packed.shape[0] != M:
        raise ValueError("offset_packed must have shape (M,).")
    K, N = activation.shape
    if K != 64:
        raise ValueError("activation must have shape (64, N).")

    out = torch.empty((M, N), device=activation.device, dtype=torch.float16)

    stride_sm, stride_sk = scale.stride()
    stride_wm, stride_wk = weight_packed.stride()
    stride_ak, stride_an = activation.stride()
    stride_om, stride_on = out.stride()

    grid = lambda meta: (triton.cdiv(M, meta["BLOCK_M"]), triton.cdiv(N, meta["BLOCK_N"]))

    _quant_dot_kernel[grid](
        scale,
        offset_packed,
        weight_packed,
        activation,
        out,
        M=M,
        N=N,
        stride_sm=stride_sm,
        stride_sk=stride_sk,
        stride_wm=stride_wm,
        stride_wk=stride_wk,
        stride_ak=stride_ak,
        stride_an=stride_an,
        stride_om=stride_om,
        stride_on=stride_on,
    )
    return out


class Solution:
    def solve(self, spec_path: str = None) -> dict:
        return {"program_path": os.path.abspath(__file__)}