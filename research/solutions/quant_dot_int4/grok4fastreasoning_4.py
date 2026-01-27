class Solution:
    def solve(self, spec_path: str = None) -> dict:
        return {
            "code": """import torch
import triton
import triton.language as tl

@triton.jit
def quant_dot_kernel(
    scale_ptr, offset_ptr, weight_ptr, act_ptr, output_ptr,
    M, N, K: tl.constexpr,
    stride_scale_m, stride_scale_kg,
    stride_offset_m,
    stride_weight_m, stride_weight_kg,
    stride_act_k, stride_act_n,
    stride_out_m, stride_out_n,
    BLOCK_M: tl.constexpr,
    BLOCK_N: tl.constexpr,
):
    def unpack_int4(packed, num: tl.constexpr):
        ar = tl.arange(0, num)
        shifts = ar * 4
        extracted = ((packed[:, None] >> shifts[None, :]) & 0xF).to(tl.int32)
        sign_mask = extracted & 0x8
        unpacked = tl.where(sign_mask != 0, extracted - 16, extracted)
        return unpacked

    pid_m = tl.program_id(0)
    pid_n = tl.program_id(1)

    block_m = tl.arange(0, BLOCK_M)
    block_n = tl.arange(0, BLOCK_N)
    offs_m = pid_m * BLOCK_M + block_m
    offs_n = pid_n * BLOCK_N + block_n
    mask_m = offs_m < M
    mask_n = offs_n < N
    mask_mm = mask_m[:, None]
    mask_out = mask_m[:, None] & mask_n[None, :]

    # Load offsets
    offset_block = tl.load(offset_ptr + offs_m * stride_offset_m, mask=mask_m, other=0).to(tl.int32)
    offsets_unpacked = unpack_int4(offset_block, 8)

    # Load scales
    offs_kg = tl.arange(0, 8)
    scale_offsets = offs_m[:, None] * stride_scale_m + offs_kg[None, :] * stride_scale_kg
    scales_block = tl.load(scale_ptr + scale_offsets, mask=mask_mm, other=0.0).to(tl.float32)

    # Load weights packed
    weight_offsets = offs_m[:, None] * stride_weight_m + offs_kg[None, :] * stride_weight_kg
    weights_packed_block = tl.load(weight_ptr + weight_offsets, mask=mask_mm, other=0).to(tl.int32)

    # Load activations
    block_k = tl.arange(0, K)
    act_offsets = block_k[:, None] * stride_act_k + offs_n[None, :] * stride_act_n
    act_mask = (block_k[:, None] < K) & (offs_n[None, :] < N)
    act_block = tl.load(act_ptr + act_offsets, mask=act_mask, other=0.0).to(tl.float32)

    # Accumulator
    acc = tl.zeros((BLOCK_M, BLOCK_N), dtype=tl.float32)

    # Loop over groups
    for g in range(8):
        # Unpack weights for group g
        w_packed_g = weights_packed_block[:, g]
        w_int4_g = unpack_int4(w_packed_g, 8)

        # Get scale, offset for group g
        s_g = scales_block[:, g][:, None]
        o_g = offsets_unpacked[:, g][:, None]

        # Dequantize
        deq = s_g * (w_int4_g.to(tl.float32) - o_g.to(tl.float32))

        # Activation slice for group
        k_start = g * 8
        act_g = act_block[k_start : k_start + 8, :]

        # Dot product
        acc += tl.sum(deq[:, :, None] * act_g[None, :, :], axis=1)

    # Store output
    out_offsets = offs_m[:, None] * stride_out_m + offs_n[None, :] * stride_out_n
    tl.store(output_ptr + out_offsets, acc.to(tl.float16), mask=mask_out)

def quant_dot(scale: torch.Tensor, offset_packed: torch.Tensor, weight_packed: torch.Tensor, activation: torch.Tensor) -> torch.Tensor:
    M, Kgroup = scale.shape
    assert Kgroup == 8
    K = 64
    N = activation.shape[1]
    output = torch.empty((M, N), dtype=torch.float16, device=scale.device)
    if M == 0 or N == 0:
        return output

    stride_scale_m = scale.stride(0)
    stride_scale_kg = scale.stride(1)
    stride_offset_m = offset_packed.stride(0)
    stride_weight_m = weight_packed.stride(0)
    stride_weight_kg = weight_packed.stride(1)
    stride_act_k = activation.stride(0)
    stride_act_n = activation.stride(1)
    stride_out_m = output.stride(0)
    stride_out_n = output.stride(1)

    BLOCK_M = 256
    BLOCK_N = 128
    grid = (triton.cdiv(M, BLOCK_M), triton.cdiv(N, BLOCK_N))
    quant_dot_kernel[grid](
        scale.data_ptr(), offset_packed.data_ptr(), weight_packed.data_ptr(), activation.data_ptr(), output.data_ptr(),
        M, N, K,
        stride_scale_m, stride_scale_kg,
        stride_offset_m,
        stride_weight_m, stride_weight_kg,
        stride_act_k, stride_act_n,
        stride_out_m, stride_out_n,
        BLOCK_M=BLOCK_M,
        BLOCK_N=BLOCK_N,
        num_stages=2,
    )
    return output
"""
        }