import os
import torch
import triton
import triton.language as tl


@triton.jit
def quant_dot_kernel(
    scale_ptr,            # *fp16
    offset_packed_ptr,    # *int32
    weight_packed_ptr,    # *int32
    act_ptr,              # *fp16
    out_ptr,              # *fp16
    M, N,
    stride_scale_m, stride_scale_k8,
    stride_offset_m,
    stride_weight_m, stride_weight_k8,
    stride_act_k, stride_act_n,
    stride_out_m, stride_out_n,
    BLOCK_M: tl.constexpr, BLOCK_N: tl.constexpr,
):
    FPINT = 8
    GROUP = 8

    pid_m = tl.program_id(axis=0)
    pid_n = tl.program_id(axis=1)

    offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
    offs_n = pid_n * BLOCK_N + tl.arange(0, BLOCK_N)

    mask_m = offs_m < M
    mask_n = offs_n < N

    acc = tl.zeros((BLOCK_M, BLOCK_N), dtype=tl.float32)

    # Load packed offsets for each row in this block
    offset_ptrs = offset_packed_ptr + offs_m * stride_offset_m
    packed_offsets = tl.load(offset_ptrs, mask=mask_m, other=0).to(tl.int32)

    for g in range(FPINT):
        shift_g = g * 4
        # Extract per-row offset for this group (int4)
        offset_g_i32 = ((packed_offsets >> shift_g) & 0xF).to(tl.int32)
        offset_g = offset_g_i32.to(tl.float32)

        # Load scale for this group
        scale_ptrs = scale_ptr + offs_m * stride_scale_m + g * stride_scale_k8
        scale_g = tl.load(scale_ptrs, mask=mask_m, other=0.0).to(tl.float32)

        # Load packed weights for this group
        weight_ptrs = weight_packed_ptr + offs_m * stride_weight_m + g * stride_weight_k8
        packed_w = tl.load(weight_ptrs, mask=mask_m, other=0).to(tl.int32)

        for l in range(GROUP):
            k_idx = g * GROUP + l
            shift_l = l * 4

            # Extract weight nibble for this lane
            w_lane_i32 = ((packed_w >> shift_l) & 0xF).to(tl.int32)
            w_lane = w_lane_i32.to(tl.float32)

            # Dequantize: a_vec = scale * (w - offset)
            a_vec = scale_g * (w_lane - offset_g)  # [BLOCK_M]

            # Load activation row for this k index
            act_row_ptrs = act_ptr + k_idx * stride_act_k + offs_n * stride_act_n
            act_row = tl.load(act_row_ptrs, mask=mask_n, other=0.0).to(tl.float32)  # [BLOCK_N]

            # Outer product and accumulate
            a_mat = a_vec[:, None]        # [BLOCK_M, 1]
            b_mat = act_row[None, :]      # [1, BLOCK_N]
            acc += a_mat * b_mat

    # Store result
    out_ptrs = out_ptr + offs_m[:, None] * stride_out_m + offs_n[None, :] * stride_out_n
    out_mask = mask_m[:, None] & mask_n[None, :]
    tl.store(out_ptrs, acc.to(tl.float16), mask=out_mask)


def quant_dot(scale: torch.Tensor, offset_packed: torch.Tensor, weight_packed: torch.Tensor, activation: torch.Tensor) -> torch.Tensor:
    FPINT = 8
    GROUP = 8
    K = FPINT * GROUP

    assert scale.is_cuda and offset_packed.is_cuda and weight_packed.is_cuda and activation.is_cuda
    assert activation.dim() == 2
    assert scale.dim() == 2
    assert weight_packed.dim() == 2
    assert offset_packed.dim() == 1

    M = scale.size(0)
    K_over_8 = scale.size(1)
    assert K_over_8 * GROUP == K
    assert activation.size(0) == K
    N = activation.size(1)

    # Ensure dtypes
    if scale.dtype != torch.float16:
        scale = scale.to(torch.float16)
    if activation.dtype != torch.float16:
        activation = activation.to(torch.float16)
    assert offset_packed.dtype == torch.int32
    assert weight_packed.dtype == torch.int32

    # Strides (in elements)
    stride_scale_m, stride_scale_k8 = scale.stride()
    (stride_offset_m,) = offset_packed.stride()
    stride_weight_m, stride_weight_k8 = weight_packed.stride()
    stride_act_k, stride_act_n = activation.stride()

    out = torch.empty((M, N), device=activation.device, dtype=torch.float16)
    stride_out_m, stride_out_n = out.stride()

    # Tiling configuration
    if N >= 256:
        BLOCK_N = 128
        num_warps = 8
    elif N >= 64:
        BLOCK_N = 64
        num_warps = 4
    else:
        BLOCK_N = 32
        num_warps = 2
    BLOCK_M = 64

    grid = (triton.cdiv(M, BLOCK_M), triton.cdiv(N, BLOCK_N))

    quant_dot_kernel[grid](
        scale,
        offset_packed,
        weight_packed,
        activation,
        out,
        M,
        N,
        stride_scale_m, stride_scale_k8,
        stride_offset_m,
        stride_weight_m, stride_weight_k8,
        stride_act_k, stride_act_n,
        stride_out_m, stride_out_n,
        BLOCK_M=BLOCK_M,
        BLOCK_N=BLOCK_N,
        num_warps=num_warps,
        num_stages=1,
    )

    return out


class Solution:
    def solve(self, spec_path: str = None) -> dict:
        try:
            path = os.path.abspath(__file__)
            return {"program_path": path}
        except NameError:
            # Fallback for environments without __file__
            import inspect
            code = inspect.getsource(inspect.getmodule(Solution))
            return {"code": code}