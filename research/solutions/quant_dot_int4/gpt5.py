import os
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
                    triton.Config({"BLOCK_M": 64, "BLOCK_N": 64}, num_warps=4, num_stages=2),
                    triton.Config({"BLOCK_M": 64, "BLOCK_N": 128}, num_warps=4, num_stages=2),
                    triton.Config({"BLOCK_M": 64, "BLOCK_N": 256}, num_warps=8, num_stages=2),
                    triton.Config({"BLOCK_M": 128, "BLOCK_N": 64}, num_warps=4, num_stages=2),
                    triton.Config({"BLOCK_M": 128, "BLOCK_N": 128}, num_warps=4, num_stages=2),
                    triton.Config({"BLOCK_M": 128, "BLOCK_N": 256}, num_warps=8, num_stages=2),
                    triton.Config({"BLOCK_M": 256, "BLOCK_N": 64}, num_warps=8, num_stages=2),
                    triton.Config({"BLOCK_M": 256, "BLOCK_N": 128}, num_warps=8, num_stages=2),
                    triton.Config({"BLOCK_M": 256, "BLOCK_N": 256}, num_warps=8, num_stages=2),
                ],
                key=['M', 'N'],
            )
            @triton.jit
            def _quant_dot_kernel(
                scale_ptr,            # * (float16|float32)[M, FPINT]
                offset_packed_ptr,    # * int32[M]
                weight_packed_ptr,    # * int32[M, FPINT]
                act_ptr,              # * float16[K, N]
                out_ptr,              # * float16[M, N]
                M: tl.constexpr, N: tl.constexpr,

                stride_scale_m, stride_scale_g,
                stride_off_m,
                stride_w_m, stride_w_g,
                stride_a_k, stride_a_n,
                stride_out_m, stride_out_n,

                BLOCK_M: tl.constexpr, BLOCK_N: tl.constexpr,
            ):
                pid_m = tl.program_id(0)
                pid_n = tl.program_id(1)

                offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
                offs_n = pid_n * BLOCK_N + tl.arange(0, BLOCK_N)

                m_mask = offs_m < M
                n_mask = offs_n < N

                # Pointers for offsets per row
                off_ptrs = offset_packed_ptr + offs_m * stride_off_m
                # Load per-row packed offsets (8 int4 in one int32)
                off32 = tl.load(off_ptrs, mask=m_mask, other=0)

                acc = tl.zeros((BLOCK_M, BLOCK_N), dtype=tl.float32)

                # Reuse shifts for nibble extraction
                nibble_shifts = tl.arange(0, FPINT, dtype=tl.int32) * 4

                # Loop over 8 groups (each corresponds to a packed int32 column)
                for g in range(FPINT):
                    # Load per-group scales [BLOCK_M]
                    s_ptrs = scale_ptr + offs_m * stride_scale_m + g * stride_scale_g
                    scale_g = tl.load(s_ptrs, mask=m_mask, other=0.0)
                    scale_g = tl.cast(scale_g, tl.float16)  # Use FP16 for tl.dot

                    # Extract per-group offset from packed offsets
                    o_g = (off32 >> (tl.int32(g) * 4)) & 0xF
                    o_g = tl.cast(o_g, tl.int32)  # [BLOCK_M]

                    # Load packed weights for this group [BLOCK_M]
                    w_ptrs = weight_packed_ptr + offs_m * stride_w_m + g * stride_w_g
                    w32 = tl.load(w_ptrs, mask=m_mask, other=0)

                    # Unpack 8 int4 weights -> [BLOCK_M, 8]
                    # Broadcast w32 across the nibble dimension
                    w_mat = (w32[:, None] >> nibble_shifts[None, :]) & 0xF
                    w_mat = tl.cast(w_mat, tl.int32)

                    # Broadcast offset across the 8 lanes within the group
                    o_mat = o_g[:, None]

                    # Compute dequantized A block for this group: (w - o) * scale
                    a_int = w_mat - o_mat  # int32
                    a_f16 = tl.cast(a_int, tl.float16) * scale_g[:, None]  # [BM, 8], fp16

                    # Load activation rows for this group: [8, BN]
                    k_idx = tl.arange(0, FPINT, dtype=tl.int32) + g * FPINT  # 8 contiguous k within group
                    a_cols = offs_n
                    b_ptrs = act_ptr + k_idx[:, None] * stride_a_k + a_cols[None, :] * stride_a_n
                    b_mask = (k_idx[:, None] < K) & (a_cols[None, :] < N)
                    b_f16 = tl.load(b_ptrs, mask=b_mask, other=0.0)

                    # Accumulate: [BM,BN] += [BM,8] @ [8,BN]
                    acc += tl.dot(a_f16, b_f16)

                # Store result
                out_ptrs = out_ptr + offs_m[:, None] * stride_out_m + offs_n[None, :] * stride_out_n
                tl.store(out_ptrs, tl.cast(acc, tl.float16), mask=m_mask[:, None] & n_mask[None, :])

            def quant_dot(scale: torch.Tensor, offset_packed: torch.Tensor, weight_packed: torch.Tensor, activation: torch.Tensor) -> torch.Tensor:
                """
                Args:
                    scale: float16/float32 tensor of shape (M, K/8)
                    offset_packed: int32 tensor of shape (M,)
                        Each int32 packs 8 int4 offsets (one per 8-wide group).
                    weight_packed: int32 tensor of shape (M, K/8)
                        Each int32 packs 8 int4 weights.
                    activation: float16 tensor of shape (K, N)

                Returns:
                    Output tensor of shape (M, N), dtype float16
                """
                assert activation.is_cuda and weight_packed.is_cuda and offset_packed.is_cuda and scale.is_cuda, "All tensors must be CUDA"
                assert activation.dtype == torch.float16, "activation must be float16"
                assert weight_packed.dtype == torch.int32, "weight_packed must be int32"
                assert offset_packed.dtype == torch.int32, "offset_packed must be int32"
                assert scale.dtype in (torch.float16, torch.float32), "scale must be float16 or float32"
                assert activation.dim() == 2 and weight_packed.dim() == 2 and scale.dim() == 2 and offset_packed.dim() == 1
                K_act, N = activation.shape
                M = weight_packed.shape[0]
                assert K_act == K, f"K must be {K}"
                assert scale.shape == (M, K // FPINT), f"scale must be shape (M, {K // FPINT})"
                assert weight_packed.shape == (M, K // FPINT), f"weight_packed must be shape (M, {K // FPINT})"
                assert offset_packed.shape == (M,), "offset_packed must be shape (M,)"

                # Ensure contiguous
                scale_c = scale.contiguous()
                off_c = offset_packed.contiguous()
                w_c = weight_packed.contiguous()
                act_c = activation.contiguous()

                out = torch.empty((M, N), device=activation.device, dtype=torch.float16)

                # Strides
                stride_scale_m, stride_scale_g = scale_c.stride()
                stride_off_m = off_c.stride(0)
                stride_w_m, stride_w_g = w_c.stride()
                stride_a_k, stride_a_n = act_c.stride()
                stride_out_m, stride_out_n = out.stride()

                # Launch
                grid = (
                    triton.cdiv(M, 128),  # heuristic; autotune will adapt BLOCK_M
                    triton.cdiv(N, 128),
                )
                _quant_dot_kernel[grid](
                    scale_c, off_c, w_c, act_c, out,
                    M, N,
                    stride_scale_m, stride_scale_g,
                    stride_off_m,
                    stride_w_m, stride_w_g,
                    stride_a_k, stride_a_n,
                    stride_out_m, stride_out_n,
                )
                return out
            '''
        )
        return {"code": code}