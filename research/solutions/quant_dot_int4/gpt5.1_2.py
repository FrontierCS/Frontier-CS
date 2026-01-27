import torch
import triton
import triton.language as tl


@triton.jit
def _quant_dot_kernel(
    OUT_PTR,
    SCALE_PTR,
    OFFSET_PTR,
    WEIGHT_PTR,
    ACT_PTR,
    M,
    N,
    stride_scale_m,
    stride_scale_pack,
    stride_offset_m,
    stride_w_m,
    stride_w_pack,
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

    acc = tl.zeros((BLOCK_M, BLOCK_N), dtype=tl.float32)

    offset_row = tl.load(
        OFFSET_PTR + offs_m * stride_offset_m,
        mask=mask_m,
        other=0,
    ).to(tl.int32)

    for pack_idx in tl.static_range(8):
        scale_vals = tl.load(
            SCALE_PTR + offs_m * stride_scale_m + pack_idx * stride_scale_pack,
            mask=mask_m,
            other=0,
        ).to(tl.float32)

        offset4 = (offset_row >> (pack_idx * 4)) & 0xF
        offset4_f = offset4.to(tl.float32)

        w_packed = tl.load(
            WEIGHT_PTR + offs_m * stride_w_m + pack_idx * stride_w_pack,
            mask=mask_m,
            other=0,
        ).to(tl.int32)

        for lane in tl.static_range(8):
            k_idx = pack_idx * 8 + lane

            w_lane = (w_packed >> (lane * 4)) & 0xF
            w_lane_f = w_lane.to(tl.float32)

            a_vals = scale_vals * (w_lane_f - offset4_f)

            act_row = tl.load(
                ACT_PTR + k_idx * stride_act_k + offs_n * stride_act_n,
                mask=mask_n,
                other=0,
            ).to(tl.float32)

            acc += a_vals[:, None] * act_row[None, :]

    out = acc.to(tl.float16)
    out_ptrs = OUT_PTR + offs_m[:, None] * stride_out_m + offs_n[None, :] * stride_out_n
    tl.store(out_ptrs, out, mask=mask_m[:, None] & mask_n[None, :])


def quant_dot(
    scale: torch.Tensor,
    offset_packed: torch.Tensor,
    weight_packed: torch.Tensor,
    activation: torch.Tensor,
) -> torch.Tensor:
    if not (scale.is_cuda and offset_packed.is_cuda and weight_packed.is_cuda and activation.is_cuda):
        raise ValueError("All input tensors must be CUDA tensors")

    if activation.dim() != 2:
        raise ValueError("activation must be 2D (K, N)")
    if scale.dim() != 2 or weight_packed.dim() != 2 or offset_packed.dim() != 1:
        raise ValueError("scale (M, K/8), weight_packed (M, K/8), offset_packed (M,) expected")

    M = scale.shape[0]
    K_packed = scale.shape[1]
    K = K_packed * 8
    if activation.shape[0] != K:
        raise ValueError("activation.shape[0] must equal K (= scale.shape[1] * 8)")
    if weight_packed.shape[0] != M or weight_packed.shape[1] != K_packed:
        raise ValueError("weight_packed must have shape (M, K/8)")
    if offset_packed.shape[0] != M:
        raise ValueError("offset_packed must have shape (M,)")

    N = activation.shape[1]

    out = torch.empty((M, N), device=activation.device, dtype=torch.float16)

    BLOCK_M = 32
    BLOCK_N = 128

    grid = (triton.cdiv(M, BLOCK_M), triton.cdiv(N, BLOCK_N))

    _quant_dot_kernel[grid](
        out,
        scale,
        offset_packed,
        weight_packed,
        activation,
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
        BLOCK_M=BLOCK_M,
        BLOCK_N=BLOCK_N,
        num_warps=4,
        num_stages=1,
    )

    return out


class Solution:
    def solve(self, spec_path: str = None) -> dict:
        return {"program_path": __file__}