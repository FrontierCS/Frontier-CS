import torch
import triton
import triton.language as tl

class Solution:
    def solve(self, spec_path: str = None) -> dict:
        code = """
import torch
import triton
import triton.language as tl

@triton.autotune(
    configs=[
        triton.Config({'BLOCK_M': 64, 'BLOCK_N': 128}),
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 128}),
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 256}),
        triton.Config({'BLOCK_M': 256, 'BLOCK_N': 128}),
    ],
    key=['M', 'N'],
)
@triton.jit
def quant_dot_kernel(
    scale_ptr, offset_ptr, weight_ptr, act_ptr, output_ptr,
    M, N, K: tl.constexpr,
    stride_scale_m, stride_scale_k,
    stride_offset_m,
    stride_weight_m, stride_weight_k,
    stride_act_k, stride_act_n,
    stride_out_m, stride_out_n,
    BLOCK_M: tl.constexpr,
    BLOCK_N: tl.constexpr,
    GROUP: tl.constexpr,
):
    pid_m = tl.program_id(0)
    pid_n = tl.program_id(1)

    rm = tl.arange(0, BLOCK_M)
    rm_mask = pid_m * BLOCK_M + rm < M

    # Load scales (BLOCK_M, GROUP)
    scales = tl.load(
        scale_ptr + (pid_m * BLOCK_M + rm)[:, None] * stride_scale_m + tl.arange(0, GROUP)[None, :] * stride_scale_k,
        mask=rm_mask[:, None],
        other=0.0
    )

    # Load offset_packed (BLOCK_M,)
    offsets_packed = tl.load(
        offset_ptr + (pid_m * BLOCK_M + rm) * stride_offset_m,
        mask=rm_mask,
        other=0
    ).to(tl.int32)

    # Load weight_packed (BLOCK_M, GROUP)
    weights_packed = tl.load(
        weight_ptr + (pid_m * BLOCK_M + rm)[:, None] * stride_weight_m + tl.arange(0, GROUP)[None, :] * stride_weight_k,
        mask=rm_mask[:, None],
        other=0
    ).to(tl.int32)

    # Load activations (K, BLOCK_N)
    rn = tl.arange(0, BLOCK_N)
    rn_mask = pid_n * BLOCK_N + rn < N
    acts = tl.load(
        act_ptr + tl.arange(0, K)[:, None] * stride_act_k + (pid_n * BLOCK_N + rn)[None, :] * stride_act_n,
        mask=(None, rn_mask),
        other=0.0
    )

    acc = tl.zeros((BLOCK_M, BLOCK_N), dtype=tl.float32)

    for g in tl.static_range(GROUP):
        # Unpack offset for group g (BLOCK_M,)
        shift = g * 4
        offset_int4 = ((offsets_packed >> shift) & 15).to(tl.float32)
        offset_signed = tl.where(offset_int4 >= 8.0, offset_int4 - 16.0, offset_int4)

        # Unpack weights for group g (BLOCK_M, GROUP)
        w_packed_g = weights_packed[:, g]
        w_unpacked = tl.zeros((BLOCK_M, GROUP), dtype=tl.float32)
        for i in tl.static_range(GROUP):
            shift_i = i * 4
            w_int4 = ((w_packed_g >> shift_i) & 15).to(tl.float32)
            w_signed = tl.where(w_int4 >= 8.0, w_int4 - 16.0, w_int4)
            w_unpacked[:, i] = w_signed

        # Activations for group g (GROUP, BLOCK_N)
        start_k = g * GROUP
        end_k = start_k + GROUP
        a_g = acts[start_k:end_k, :].to(tl.float32)

        # Dots (BLOCK_M, BLOCK_N)
        dots = tl.dot(w_unpacked, a_g)

        # Sum over group (BLOCK_N,)
        sum_a = tl.sum(a_g, axis=0)

        # Scales for group (BLOCK_M,)
        scale_g = scales[:, g].to(tl.float32)

        # Contribution
        contrib = scale_g[:, None] * (dots - offset_signed[:, None] * sum_a[None, :])
        acc += contrib

    # Store
    rm_out = pid_m * BLOCK_M + rm
    rn_out = pid_n * BLOCK_N + rn
    mask_out = (rm_out[:, None] < M) & (rn_out[None, :] < N)
    tl.store(
        output_ptr + rm_out[:, None] * stride_out_m + rn_out[None, :] * stride_out_n,
        acc.to(tl.float16),
        mask=mask_out
    )

def quant_dot(scale: torch.Tensor, offset_packed: torch.Tensor, weight_packed: torch.Tensor, activation: torch.Tensor) -> torch.Tensor:
    M, num_groups = scale.shape
    K = 64
    N = activation.shape[1]
    assert activation.shape[0] == K
    assert num_groups * 8 == K
    output = torch.empty((M, N), dtype=torch.float16, device=scale.device)
    GROUP = 8

    def grid(meta):
        return (
            triton.cdiv(M, meta['BLOCK_M']),
            triton.cdiv(N, meta['BLOCK_N']),
        )

    quant_dot_kernel[grid](
        scale, offset_packed, weight_packed, activation, output,
        M, N, K,
        scale.stride(0), scale.stride(1),
        offset_packed.stride(0),
        weight_packed.stride(0), weight_packed.stride(1),
        activation.stride(0), activation.stride(1),
        output.stride(0), output.stride(1),
        GROUP=GROUP,
    )
    return output
"""
        return {"code": code}