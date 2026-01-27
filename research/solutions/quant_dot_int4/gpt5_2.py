import os
import textwrap
import torch
import triton
import triton.language as tl


FPINT = 8
GROUP = 8
K_FIXED = FPINT * GROUP  # 64


@triton.autotune(
    configs=[
        triton.Config({'BLOCK_M': 32, 'BLOCK_N': 64}, num_warps=2, num_stages=2),
        triton.Config({'BLOCK_M': 32, 'BLOCK_N': 128}, num_warps=4, num_stages=2),
        triton.Config({'BLOCK_M': 64, 'BLOCK_N': 128}, num_warps=4, num_stages=2),
        triton.Config({'BLOCK_M': 64, 'BLOCK_N': 256}, num_warps=8, num_stages=2),
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 128}, num_warps=8, num_stages=2),
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 256}, num_warps=8, num_stages=2),
    ],
    key=['M', 'N'],
)
@triton.jit
def _quant_dot_kernel(
    scale_ptr,            # (M, 8), fp16/fp32
    offset_packed_ptr,    # (M,), int32, 8 int4 packed in one int32
    weight_packed_ptr,    # (M, 8), int32, each packs 8 int4
    act_ptr,              # (64, N), fp16
    out_ptr,              # (M, N), fp16
    M: tl.constexpr, N: tl.constexpr,
    s_scale_m, s_scale_g,
    s_offset_m,
    s_w_m, s_w_g,
    s_act_k, s_act_n,
    s_out_m, s_out_n,
    BLOCK_M: tl.constexpr, BLOCK_N: tl.constexpr,
):
    pid_m = tl.program_id(0)
    pid_n = tl.program_id(1)

    offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
    offs_n = pid_n * BLOCK_N + tl.arange(0, BLOCK_N)

    mask_m = offs_m < M
    mask_n = offs_n < N

    # Initialize accumulator in fp32
    acc = tl.zeros((BLOCK_M, BLOCK_N), dtype=tl.float32)

    # Load packed offsets once per row
    offp = tl.load(offset_packed_ptr + offs_m * s_offset_m, mask=mask_m, other=0).to(tl.int32)

    # Loop over 8 groups (each handles 8 K-elements)
    for g in tl.static_range(0, 8):
        # Load scales for this group, cast to fp32
        sc = tl.load(scale_ptr + offs_m * s_scale_m + g * s_scale_g, mask=mask_m, other=0)
        sc = sc.to(tl.float32)

        # Load packed weights for this group
        w32 = tl.load(weight_packed_ptr + offs_m * s_w_m + g * s_w_g, mask=mask_m, other=0).to(tl.int32)

        # Extract the offset nibble for this group
        off_g = tl.logical_and(offp >> (g * 4), 0xF)  # off_g = (offp >> (g*4)) & 0xF
        # Triton doesn't guarantee bitwise and with python ints via logical_and; use & explicitly
        off_g = (offp >> (g * 4)) & 0xF
        off_g = off_g.to(tl.float32)

        # Sum of activation in this group across the 8 lanes, per column n
        sact = tl.zeros((BLOCK_N,), dtype=tl.float32)

        # Iterate over lanes within the group
        for t in tl.static_range(0, 8):
            k_idx = g * 8 + t
            # Load activation row for (k_idx, offs_n)
            a_row = tl.load(act_ptr + k_idx * s_act_k + offs_n * s_act_n, mask=mask_n, other=0.0)
            a_row = a_row.to(tl.float32)
            sact += a_row

            # Unpack current int4 weight for all rows in the block
            wt = (w32 >> (t * 4)) & 0xF
            wt = wt.to(tl.float32)

            # Accumulate: scale * wt * a_row
            # (BLOCK_M,) * (BLOCK_N,) -> (BLOCK_M, BLOCK_N) by broadcasting
            acc += (sc * wt)[:, None] * a_row[None, :]

        # Subtract scale * offset * sum(act) for this group
        acc -= (sc * off_g)[:, None] * sact[None, :]

    # Write back result cast to fp16
    out = acc.to(tl.float16)
    tl.store(out_ptr + offs_m[:, None] * s_out_m + offs_n[None, :] * s_out_n,
             out,
             mask=mask_m[:, None] & mask_n[None, :])


def quant_dot(scale: torch.Tensor, offset_packed: torch.Tensor, weight_packed: torch.Tensor, activation: torch.Tensor) -> torch.Tensor:
    """
    Args:
        scale: float16/float32 tensor of shape (M, K/8)
        offset_packed: int32 tensor of shape (M,)
        weight_packed: int32 tensor of shape (M, K/8)
        activation: float16 tensor of shape (K, N)

    Returns:
        Output tensor of shape (M, N), dtype float16
    """
    assert activation.is_cuda and weight_packed.is_cuda and offset_packed.is_cuda and scale.is_cuda, "All inputs must be CUDA tensors"
    assert activation.dtype in (torch.float16, torch.bfloat16, torch.float32) or activation.dtype == torch.float16, "activation must be fp16/bf16/fp32"
    assert weight_packed.dtype == torch.int32, "weight_packed must be int32"
    assert offset_packed.dtype == torch.int32, "offset_packed must be int32"
    assert scale.dtype in (torch.float16, torch.float32), "scale must be float16 or float32"

    M = weight_packed.shape[0]
    G = weight_packed.shape[1]
    assert G == FPINT, f"weight_packed second dim must be {FPINT}, got {G}"
    assert scale.shape == (M, FPINT), "scale must have shape (M, K/8)"
    assert offset_packed.shape == (M,), "offset_packed must have shape (M,)"
    K, N = activation.shape
    assert K == K_FIXED, f"K must be {K_FIXED}, got {K}"

    # Allocate output
    out = torch.empty((M, N), device=activation.device, dtype=torch.float16)

    # Strides in elements
    s_scale_m, s_scale_g = scale.stride()
    s_offset_m = offset_packed.stride(0)
    s_w_m, s_w_g = weight_packed.stride()
    s_act_k, s_act_n = activation.stride()
    s_out_m, s_out_n = out.stride()

    # Grid
    def grid(meta):
        return (triton.cdiv(M, meta['BLOCK_M']), triton.cdiv(N, meta['BLOCK_N']))

    _quant_dot_kernel[grid](
        scale, offset_packed, weight_packed, activation, out,
        M, N,
        s_scale_m, s_scale_g,
        s_offset_m,
        s_w_m, s_w_g,
        s_act_k, s_act_n,
        s_out_m, s_out_n,
    )
    return out


class Solution:
    def solve(self, spec_path: str = None) -> dict:
        code = textwrap.dedent("""
            import torch
            import triton
            import triton.language as tl

            FPINT = 8
            GROUP = 8
            K_FIXED = FPINT * GROUP  # 64


            @triton.autotune(
                configs=[
                    triton.Config({'BLOCK_M': 32, 'BLOCK_N': 64}, num_warps=2, num_stages=2),
                    triton.Config({'BLOCK_M': 32, 'BLOCK_N': 128}, num_warps=4, num_stages=2),
                    triton.Config({'BLOCK_M': 64, 'BLOCK_N': 128}, num_warps=4, num_stages=2),
                    triton.Config({'BLOCK_M': 64, 'BLOCK_N': 256}, num_warps=8, num_stages=2),
                    triton.Config({'BLOCK_M': 128, 'BLOCK_N': 128}, num_warps=8, num_stages=2),
                    triton.Config({'BLOCK_M': 128, 'BLOCK_N': 256}, num_warps=8, num_stages=2),
                ],
                key=['M', 'N'],
            )
            @triton.jit
            def _quant_dot_kernel(
                scale_ptr,            # (M, 8), fp16/fp32
                offset_packed_ptr,    # (M,), int32, 8 int4 packed in one int32
                weight_packed_ptr,    # (M, 8), int32, each packs 8 int4
                act_ptr,              # (64, N), fp16
                out_ptr,              # (M, N), fp16
                M: tl.constexpr, N: tl.constexpr,
                s_scale_m, s_scale_g,
                s_offset_m,
                s_w_m, s_w_g,
                s_act_k, s_act_n,
                s_out_m, s_out_n,
                BLOCK_M: tl.constexpr, BLOCK_N: tl.constexpr,
            ):
                pid_m = tl.program_id(0)
                pid_n = tl.program_id(1)

                offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
                offs_n = pid_n * BLOCK_N + tl.arange(0, BLOCK_N)

                mask_m = offs_m < M
                mask_n = offs_n < N

                acc = tl.zeros((BLOCK_M, BLOCK_N), dtype=tl.float32)

                offp = tl.load(offset_packed_ptr + offs_m * s_offset_m, mask=mask_m, other=0).to(tl.int32)

                for g in tl.static_range(0, 8):
                    sc = tl.load(scale_ptr + offs_m * s_scale_m + g * s_scale_g, mask=mask_m, other=0)
                    sc = sc.to(tl.float32)

                    w32 = tl.load(weight_packed_ptr + offs_m * s_w_m + g * s_w_g, mask=mask_m, other=0).to(tl.int32)

                    off_g = (offp >> (g * 4)) & 0xF
                    off_g = off_g.to(tl.float32)

                    sact = tl.zeros((BLOCK_N,), dtype=tl.float32)

                    for t in tl.static_range(0, 8):
                        k_idx = g * 8 + t
                        a_row = tl.load(act_ptr + k_idx * s_act_k + offs_n * s_act_n, mask=mask_n, other=0.0)
                        a_row = a_row.to(tl.float32)
                        sact += a_row

                        wt = (w32 >> (t * 4)) & 0xF
                        wt = wt.to(tl.float32)
                        acc += (sc * wt)[:, None] * a_row[None, :]

                    acc -= (sc * off_g)[:, None] * sact[None, :]

                out = acc.to(tl.float16)
                tl.store(out_ptr + offs_m[:, None] * s_out_m + offs_n[None, :] * s_out_n,
                         out,
                         mask=mask_m[:, None] & mask_n[None, :])


            def quant_dot(scale: torch.Tensor, offset_packed: torch.Tensor, weight_packed: torch.Tensor, activation: torch.Tensor) -> torch.Tensor:
                assert activation.is_cuda and weight_packed.is_cuda and offset_packed.is_cuda and scale.is_cuda, "All inputs must be CUDA tensors"
                assert weight_packed.dtype == torch.int32, "weight_packed must be int32"
                assert offset_packed.dtype == torch.int32, "offset_packed must be int32"
                assert scale.dtype in (torch.float16, torch.float32), "scale must be float16 or float32"

                M = weight_packed.shape[0]
                G = weight_packed.shape[1]
                assert G == FPINT, f"weight_packed second dim must be {FPINT}, got {G}"
                assert scale.shape == (M, FPINT), "scale must have shape (M, K/8)"
                assert offset_packed.shape == (M,), "offset_packed must have shape (M,)"

                K, N = activation.shape
                assert K == K_FIXED, f"K must be {K_FIXED}, got {K}"

                out = torch.empty((M, N), device=activation.device, dtype=torch.float16)

                s_scale_m, s_scale_g = scale.stride()
                s_offset_m = offset_packed.stride(0)
                s_w_m, s_w_g = weight_packed.stride()
                s_act_k, s_act_n = activation.stride()
                s_out_m, s_out_n = out.stride()

                def grid(meta):
                    return (triton.cdiv(M, meta['BLOCK_M']), triton.cdiv(N, meta['BLOCK_N']))

                _quant_dot_kernel[grid](
                    scale, offset_packed, weight_packed, activation, out,
                    M, N,
                    s_scale_m, s_scale_g,
                    s_offset_m,
                    s_w_m, s_w_g,
                    s_act_k, s_act_n,
                    s_out_m, s_out_n,
                )
                return out
        """)
        return {"code": code}