import textwrap


class Solution:
    def solve(self, spec_path: str = None) -> dict:
        code = textwrap.dedent(
            '''
            import torch
            import triton
            import triton.language as tl


            FPINT = 8
            GROUP = 8
            K = FPINT * GROUP  # 64


            @triton.autotune(
                configs=[
                    triton.Config({'BLOCK_M': 32, 'BLOCK_N': 64}, num_warps=4, num_stages=2),
                    triton.Config({'BLOCK_M': 64, 'BLOCK_N': 64}, num_warps=4, num_stages=2),
                    triton.Config({'BLOCK_M': 32, 'BLOCK_N': 128}, num_warps=8, num_stages=2),
                    triton.Config({'BLOCK_M': 64, 'BLOCK_N': 128}, num_warps=8, num_stages=2),
                ],
                key=['M', 'N'],
            )
            @triton.jit
            def _quant_dot_kernel(
                scale_ptr,          # *f16/f32, shape (M, FPINT)
                offset_ptr,         # *i32, shape (M,)
                weight_ptr,         # *i32, shape (M, FPINT)
                act_ptr,            # *f16, shape (K, N)
                out_ptr,            # *f16, shape (M, N)
                M: tl.int32,
                N: tl.int32,
                stride_sc_m: tl.int32,
                stride_sc_k: tl.int32,
                stride_off_m: tl.int32,
                stride_w_m: tl.int32,
                stride_w_k: tl.int32,
                stride_a_k: tl.int32,
                stride_a_n: tl.int32,
                stride_out_m: tl.int32,
                stride_out_n: tl.int32,
                BLOCK_M: tl.constexpr,
                BLOCK_N: tl.constexpr,
            ):
                pid_m = tl.program_id(0)
                pid_n = tl.program_id(1)

                offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
                offs_n = pid_n * BLOCK_N + tl.arange(0, BLOCK_N)

                mask_m = offs_m < M
                mask_n = offs_n < N

                # [BLOCK_M, BLOCK_N] accumulator
                acc = tl.zeros((BLOCK_M, BLOCK_N), dtype=tl.float32)

                # load packed offsets once per row
                offsets32 = tl.load(
                    offset_ptr + offs_m * stride_off_m,
                    mask=mask_m,
                    other=0,
                ).to(tl.int32)

                # loop over FPINT groups
                for g in range(FPINT):
                    # per-row scale for this group
                    scale_g = tl.load(
                        scale_ptr + offs_m * stride_sc_m + g * stride_sc_k,
                        mask=mask_m,
                        other=0.0,
                    ).to(tl.float32)

                    # per-row packed weights for this group
                    w_pack = tl.load(
                        weight_ptr + offs_m * stride_w_m + g * stride_w_k,
                        mask=mask_m,
                        other=0,
                    ).to(tl.int32)

                    # per-row offset nibble for this group
                    offs_int4 = (offsets32 >> (g * 4)) & 0xF

                    # iterate over lanes inside the group
                    for lane in range(GROUP):
                        k_idx = g * GROUP + lane

                        # decode 4-bit weight for this lane
                        w_int4 = (w_pack >> (lane * 4)) & 0xF

                        # dequantized A values for this (g, lane) => shape (BLOCK_M,)
                        diff = (w_int4 - offs_int4).to(tl.float32) * scale_g

                        # load corresponding activation row, shape (BLOCK_N,)
                        act_row = tl.load(
                            act_ptr + k_idx * stride_a_k + offs_n * stride_a_n,
                            mask=mask_n,
                            other=0.0,
                        ).to(tl.float32)

                        # outer product: (BLOCK_M,) x (BLOCK_N,)
                        acc += diff[:, None] * act_row[None, :]

                # store result
                out = acc.to(tl.float16)
                mask = mask_m[:, None] & mask_n[None, :]
                tl.store(
                    out_ptr + offs_m[:, None] * stride_out_m + offs_n[None, :] * stride_out_n,
                    out,
                    mask=mask,
                )


            def quant_dot(scale: torch.Tensor,
                          offset_packed: torch.Tensor,
                          weight_packed: torch.Tensor,
                          activation: torch.Tensor) -> torch.Tensor:
                """
                Args:
                    scale: float16/float32 tensor of shape (M, K/8)
                    offset_packed: int32 tensor of shape (M,)
                    weight_packed: int32 tensor of shape (M, K/8)
                    activation: float16 tensor of shape (K, N)
                Returns:
                    float16 tensor of shape (M, N)
                """
                assert scale.is_cuda and offset_packed.is_cuda and weight_packed.is_cuda and activation.is_cuda, "All tensors must be CUDA tensors"

                M, fpint = scale.shape
                K_local = fpint * GROUP
                assert fpint == FPINT, f"Expected K/8 == {FPINT}, got {fpint}"
                assert activation.shape[0] == K_local, "Activation K dimension mismatch"
                N = activation.shape[1]

                # ensure dtypes
                if offset_packed.dtype != torch.int32:
                    offset_packed = offset_packed.to(torch.int32)
                if weight_packed.dtype != torch.int32:
                    weight_packed = weight_packed.to(torch.int32)

                out = torch.empty((M, N), device=activation.device, dtype=torch.float16)

                grid = lambda META: (
                    triton.cdiv(M, META['BLOCK_M']),
                    triton.cdiv(N, META['BLOCK_N']),
                )

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
                )

                return out
            '''
        )
        return {"code": code}