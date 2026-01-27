import os
import torch
import triton
import triton.language as tl

FPINT = 8
GROUP = 8
K_CONST = FPINT * GROUP


@triton.jit
def _quant_dot_kernel(
    scale_ptr,
    offset_ptr,
    weight_ptr,
    act_ptr,
    out_ptr,
    M,
    N,
    stride_scale_m,
    stride_scale_g,
    stride_weight_m,
    stride_weight_g,
    stride_act_k,
    stride_act_n,
    stride_out_m,
    stride_out_n,
    BLOCK_M: tl.constexpr,
    BLOCK_N: tl.constexpr,
):
    pid_m = tl.program_id(0)
    pid_n = tl.program_id(1)

    offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
    offs_n = pid_n * BLOCK_N + tl.arange(0, BLOCK_N)

    mask_m = offs_m < M
    mask_n = offs_n < N

    # Load per-row packed offsets once
    raw_offset32 = tl.load(offset_ptr + offs_m, mask=mask_m, other=0)

    # Output accumulator in fp32
    out = tl.zeros((BLOCK_M, BLOCK_N), dtype=tl.float32)

    # Local indices within each 32-bit pack (8 int4 values)
    offs_l = tl.arange(0, FPINT)
    bit_shifts = (offs_l * 4).to(tl.int32)

    for g in range(0, FPINT):
        # Load scales for this group (broadcast over local lanes)
        scale_g = tl.load(
            scale_ptr + offs_m * stride_scale_m + g * stride_scale_g,
            mask=mask_m,
            other=0.0,
        ).to(tl.float16)
        scale_g = scale_g[:, None]  # (BLOCK_M, 1)

        # Decode offset int4 for this group
        nibble = (raw_offset32 >> (4 * g)) & 0xF
        offset_g = tl.where(nibble < 8, nibble, nibble - 16).to(tl.float16)
        offset_g = offset_g[:, None]  # (BLOCK_M, 1)

        # Load packed weights for this group
        w32 = tl.load(
            weight_ptr + offs_m * stride_weight_m + g * stride_weight_g,
            mask=mask_m,
            other=0,
        )  # (BLOCK_M,)
        w32_exp = w32[:, None]  # (BLOCK_M, 1)

        # Decode 8 int4 weights from each int32
        w_nibbles = (w32_exp >> bit_shifts[None, :]) & 0xF  # (BLOCK_M, 8)
        w_signed = tl.where(w_nibbles < 8, w_nibbles, w_nibbles - 16).to(tl.float16)

        # Dequantized A values for this group and 8 lanes
        a_vals = (w_signed - offset_g) * scale_g  # (BLOCK_M, 8), fp16

        # Load corresponding activation rows: k = g*GROUP + l
        offs_k = g * GROUP + offs_l  # (8,)
        act_block = tl.load(
            act_ptr
            + offs_k[:, None] * stride_act_k
            + offs_n[None, :] * stride_act_n,
            mask=offs_n[None, :] < N,
            other=0.0,
        ).to(tl.float16)  # (8, BLOCK_N), fp16

        # Dot product: (BLOCK_M, 8) x (8, BLOCK_N) -> (BLOCK_M, BLOCK_N), fp32 accum
        out += tl.dot(a_vals, act_block)

    out_fp16 = out.to(tl.float16)
    tl.store(
        out_ptr + offs_m[:, None] * stride_out_m + offs_n[None, :] * stride_out_n,
        out_fp16,
        mask=mask_m[:, None] & mask_n[None, :],
    )


def quant_dot(
    scale: torch.Tensor,
    offset_packed: torch.Tensor,
    weight_packed: torch.Tensor,
    activation: torch.Tensor,
) -> torch.Tensor:
    # Ensure CUDA tensors and contiguity
    assert scale.is_cuda and offset_packed.is_cuda and weight_packed.is_cuda and activation.is_cuda

    scale = scale.contiguous()
    weight_packed = weight_packed.contiguous()
    activation = activation.contiguous()

    M = weight_packed.shape[0]
    K_over8 = weight_packed.shape[1]
    K = activation.shape[0]
    N = activation.shape[1]

    assert K_over8 * GROUP == K, "Mismatch between weight_packed and activation K dimensions"
    assert scale.shape[0] == M and scale.shape[1] == K_over8, "Scale shape mismatch"
    assert offset_packed.numel() == M, "offset_packed must have M elements"

    offset_packed = offset_packed.view(M).contiguous()

    # Allocate output
    out = torch.empty((M, N), device=activation.device, dtype=torch.float16)

    # Strides in elements
    stride_scale_m, stride_scale_g = scale.stride()
    stride_weight_m, stride_weight_g = weight_packed.stride()
    stride_act_k, stride_act_n = activation.stride()
    stride_out_m, stride_out_n = out.stride()

    # Kernel launch configuration
    BLOCK_M = 64
    BLOCK_N = 64

    grid = (
        triton.cdiv(M, BLOCK_M),
        triton.cdiv(N, BLOCK_N),
    )

    _quant_dot_kernel[grid](
        scale,
        offset_packed,
        weight_packed,
        activation,
        out,
        M,
        N,
        stride_scale_m,
        stride_scale_g,
        stride_weight_m,
        stride_weight_g,
        stride_act_k,
        stride_act_n,
        stride_out_m,
        stride_out_n,
        BLOCK_M=BLOCK_M,
        BLOCK_N=BLOCK_N,
        num_warps=4,
        num_stages=1,
    )

    return out


class Solution:
    def solve(self, spec_path: str = None) -> dict:
        return {"program_path": os.path.abspath(__file__)}