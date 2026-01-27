import torch
import triton
import triton.language as tl

FPINT = 8
GROUP = 8
GROUP_SIZE = GROUP
NUM_GROUPS = FPINT
K = GROUP_SIZE * NUM_GROUPS


@triton.jit
def quant_dot_kernel(
    scale_ptr,           # (M, NUM_GROUPS) float16
    offset_packed_ptr,   # (M,) int32
    weight_packed_ptr,   # (M, NUM_GROUPS) int32
    act_ptr,             # (K, N) float16
    out_ptr,             # (M, N) float16
    M, N,
    stride_scale_m, stride_scale_g,
    stride_offset_m,
    stride_weight_m, stride_weight_g,
    stride_act_k, stride_act_n,
    stride_out_m, stride_out_n,
    BLOCK_M: tl.constexpr, BLOCK_N: tl.constexpr,
):
    pid_m = tl.program_id(0)
    pid_n = tl.program_id(1)

    offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
    offs_n = pid_n * BLOCK_N + tl.arange(0, BLOCK_N)

    mask_m = offs_m < M
    mask_n = offs_n < N

    acc = tl.zeros((BLOCK_M, BLOCK_N), dtype=tl.float32)

    group_ids = tl.arange(0, NUM_GROUPS)

    # Load scales [BLOCK_M, NUM_GROUPS]
    scale_tile = tl.load(
        scale_ptr + offs_m[:, None] * stride_scale_m + group_ids[None, :] * stride_scale_g,
        mask=mask_m[:, None],
        other=0.0,
    )
    scale_tile = scale_tile.to(tl.float16)

    # Load packed offsets [BLOCK_M]
    offset_packed = tl.load(
        offset_packed_ptr + offs_m * stride_offset_m,
        mask=mask_m,
        other=0,
    )
    offset_packed = offset_packed.to(tl.int32)

    # Decode offsets for all groups: [BLOCK_M, NUM_GROUPS]
    shifts_off = group_ids * 4
    offsets_tile = ((offset_packed[:, None] >> shifts_off[None, :]) & 0xF).to(tl.float16)

    # Load packed weights [BLOCK_M, NUM_GROUPS]
    w_packed_tile = tl.load(
        weight_packed_ptr + offs_m[:, None] * stride_weight_m + group_ids[None, :] * stride_weight_g,
        mask=mask_m[:, None],
        other=0,
    )
    w_packed_tile = w_packed_tile.to(tl.int32)

    lane_ids = tl.arange(0, GROUP_SIZE)

    for g in range(NUM_GROUPS):
        scale_g = scale_tile[:, g]           # [BLOCK_M]
        offset_g = offsets_tile[:, g]        # [BLOCK_M]
        w_packed_g = w_packed_tile[:, g]     # [BLOCK_M] int32

        shifts = lane_ids * 4
        w_vals = ((w_packed_g[:, None] >> shifts[None, :]) & 0xF).to(tl.float16)  # [BLOCK_M, GROUP_SIZE]

        A_g = scale_g[:, None] * (w_vals - offset_g[:, None])  # [BLOCK_M, GROUP_SIZE]

        k_indices = g * GROUP_SIZE + lane_ids  # [GROUP_SIZE]

        B_g = tl.load(
            act_ptr + k_indices[:, None] * stride_act_k + offs_n[None, :] * stride_act_n,
            mask=(k_indices[:, None] < K) & mask_n[None, :],
            other=0.0,
        )  # [GROUP_SIZE, BLOCK_N], float16

        acc += tl.dot(A_g, B_g, out_dtype=tl.float32)

    out = acc.to(tl.float16)
    tl.store(
        out_ptr + offs_m[:, None] * stride_out_m + offs_n[None, :] * stride_out_n,
        out,
        mask=mask_m[:, None] & mask_n[None, :],
    )


def quant_dot(scale: torch.Tensor, offset_packed: torch.Tensor, weight_packed: torch.Tensor, activation: torch.Tensor) -> torch.Tensor:
    """
    Args:
        scale: float16/float32 tensor of shape (M, K/8) == (M, 8)
        offset_packed: int32 tensor of shape (M,)
        weight_packed: int32 tensor of shape (M, K/8) == (M, 8)
        activation: float16 tensor of shape (K, N) with K=64

    Returns:
        (M, N) float16 tensor
    """
    assert scale.is_cuda and offset_packed.is_cuda and weight_packed.is_cuda and activation.is_cuda

    if activation.dim() != 2:
        raise ValueError("activation must be 2D (K, N)")

    M = scale.shape[0]
    groups = scale.shape[1]
    if groups != NUM_GROUPS:
        raise ValueError(f"scale second dimension must be {NUM_GROUPS}, got {groups}")

    if activation.shape[0] != K:
        raise ValueError(f"activation first dimension must be {K}, got {activation.shape[0]}")

    N = activation.shape[1]

    if M == 0 or N == 0:
        return torch.empty((M, N), device=activation.device, dtype=torch.float16)

    # Ensure dtypes
    if scale.dtype != torch.float16:
        scale_half = scale.to(torch.float16)
    else:
        scale_half = scale

    if offset_packed.dtype != torch.int32:
        offset_packed = offset_packed.to(torch.int32)

    if weight_packed.dtype != torch.int32:
        weight_packed = weight_packed.to(torch.int32)

    if activation.dtype != torch.float16:
        activation = activation.to(torch.float16)

    # Ensure memory layouts are reasonable
    scale_half = scale_half.contiguous()
    offset_packed = offset_packed.contiguous()
    weight_packed = weight_packed.contiguous()
    activation = activation.contiguous()

    out = torch.empty((M, N), device=activation.device, dtype=torch.float16)

    stride_scale_m, stride_scale_g = scale_half.stride(0), scale_half.stride(1)
    stride_offset_m = offset_packed.stride(0)
    stride_weight_m, stride_weight_g = weight_packed.stride(0), weight_packed.stride(1)
    stride_act_k, stride_act_n = activation.stride(0), activation.stride(1)
    stride_out_m, stride_out_n = out.stride(0), out.stride(1)

    # Heuristic tile sizes
    if N >= 256:
        BLOCK_N = 128
    elif N >= 64:
        BLOCK_N = 64
    else:
        BLOCK_N = 32

    if M >= 128:
        BLOCK_M = 64
    elif M >= 64:
        BLOCK_M = 64
    else:
        BLOCK_M = 32

    tile_area = BLOCK_M * BLOCK_N
    if tile_area <= 4096:
        num_warps = 2
    elif tile_area <= 16384:
        num_warps = 4
    else:
        num_warps = 8

    grid = (triton.cdiv(M, BLOCK_M), triton.cdiv(N, BLOCK_N))

    quant_dot_kernel[grid](
        scale_half,
        offset_packed,
        weight_packed,
        activation,
        out,
        M,
        N,
        stride_scale_m, stride_scale_g,
        stride_offset_m,
        stride_weight_m, stride_weight_g,
        stride_act_k, stride_act_n,
        stride_out_m, stride_out_n,
        BLOCK_M=BLOCK_M,
        BLOCK_N=BLOCK_N,
        num_warps=num_warps,
        num_stages=2,
    )

    return out


class Solution:
    def solve(self, spec_path: str = None) -> dict:
        return {"program_path": __file__}