import torch
import triton
import triton.language as tl
import os


@triton.jit
def quant_dot_kernel(
    # Pointers to matrices
    weight_ptr,
    offset_ptr,
    scale_ptr,
    act_ptr,
    out_ptr,
    # Matrix dimensions
    M,
    N,
    K: tl.constexpr,
    # Strides
    stride_wm: tl.constexpr,
    stride_wk: tl.constexpr,
    stride_sm: tl.constexpr,
    stride_sk: tl.constexpr,
    stride_am: tl.constexpr,
    stride_an: tl.constexpr,
    stride_om: tl.constexpr,
    stride_on: tl.constexpr,
    # Meta-parameters
    BLOCK_M: tl.constexpr,
    BLOCK_N: tl.constexpr,
    GROUP_M: tl.constexpr,
):
    pid = tl.program_id(0)
    num_pid_n = tl.cdiv(N, BLOCK_N)
    num_pid_m = tl.cdiv(M, BLOCK_M)
    num_pid_in_group = GROUP_M * num_pid_n
    group_id = pid // num_pid_in_group
    first_pid_m = group_id * GROUP_M
    group_size_m = min(num_pid_m - first_pid_m, GROUP_M)
    pid_m = first_pid_m + (pid % group_size_m)
    pid_n = (pid % num_pid_in_group) // group_size_m

    offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
    offs_n = pid_n * BLOCK_N + tl.arange(0, BLOCK_N)
    offs_k = tl.arange(0, K)

    weight_ptrs = weight_ptr + (offs_m[:, None] * stride_wm + offs_k[None, :] // 8 * stride_wk)
    scale_ptrs = scale_ptr + (offs_m[:, None] * stride_sm + offs_k[None, :] // 8 * stride_sk)
    offset_ptrs = offset_ptr + offs_m

    act_ptrs = act_ptr + (offs_k[:, None] * stride_am + offs_n[None, :] * stride_an)
    out_ptrs = out_ptr + (offs_m[:, None] * stride_om + offs_n[None, :] * stride_on)

    mask_m = offs_m < M
    mask_n = offs_n < N

    acc = tl.zeros((BLOCK_M, BLOCK_N), dtype=tl.float32)

    for k in range(0, K, 8):
        k_offs = k + tl.arange(0, 8)
        k_mask = k_offs < K

        weight_packed = tl.load(weight_ptrs, mask=mask_m[:, None] & k_mask[None, :], other=0)
        scale_vals = tl.load(scale_ptrs, mask=mask_m[:, None] & k_mask[None, :], other=0)
        offset_packed = tl.load(offset_ptrs, mask=mask_m, other=0)

        act_block = tl.load(
            act_ptrs, mask=k_mask[:, None] & mask_n[None, :], other=0.0
        ).to(tl.float32)

        offset_expanded = (offset_packed[:, None] >> ((k_offs // 8) * 4)) & 0xF
        offset_expanded = offset_expanded.to(tl.float32)

        weight_unpacked = (weight_packed >> ((k_offs % 8) * 4)) & 0xF
        weight_unpacked = weight_unpacked.to(tl.float32)

        weight_dequant = (weight_unpacked - offset_expanded) * scale_vals
        acc += tl.dot(weight_dequant, act_block)

        weight_ptrs += 1 * stride_wk
        scale_ptrs += 1 * stride_sk
        act_ptrs += 8 * stride_am

    out = acc.to(tl.float16)
    tl.store(out_ptrs, out, mask=mask_m[:, None] & mask_n[None, :])


def quant_dot(
    scale: torch.Tensor,
    offset_packed: torch.Tensor,
    weight_packed: torch.Tensor,
    activation: torch.Tensor,
) -> torch.Tensor:
    M, K8 = weight_packed.shape
    K = K8 * 8
    N = activation.shape[1]

    assert K == 64, f"K must be 64, got {K}"
    assert scale.shape == (M, K8), f"scale shape mismatch"
    assert offset_packed.shape == (M,), f"offset shape mismatch"
    assert activation.shape[0] == K, f"activation shape mismatch"

    out = torch.empty((M, N), device=activation.device, dtype=activation.dtype)

    def grid(META):
        return (triton.cdiv(M, META["BLOCK_M"]) * triton.cdiv(N, META["BLOCK_N"]),)

    quant_dot_kernel[grid](
        weight_packed,
        offset_packed,
        scale,
        activation,
        out,
        M,
        N,
        K,
        weight_packed.stride(0),
        weight_packed.stride(1),
        scale.stride(0),
        scale.stride(1),
        activation.stride(0),
        activation.stride(1),
        out.stride(0),
        out.stride(1),
        BLOCK_M=64,
        BLOCK_N=64,
        GROUP_M=8,
        num_warps=4,
        num_stages=3,
    )
    return out


class Solution:
    def solve(self, spec_path: str = None) -> dict:
        return {"code": open(__file__).read()}