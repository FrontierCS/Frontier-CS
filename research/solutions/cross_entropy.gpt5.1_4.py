import textwrap


class Solution:
    def solve(self, spec_path: str = None) -> dict:
        code = textwrap.dedent(
            """
            import torch
            import triton
            import triton.language as tl


            @triton.autotune(
                configs=[
                    triton.Config({'BLOCK_SIZE': 128}, num_warps=4, num_stages=2),
                    triton.Config({'BLOCK_SIZE': 256}, num_warps=4, num_stages=2),
                    triton.Config({'BLOCK_SIZE': 512}, num_warps=8, num_stages=2),
                    triton.Config({'BLOCK_SIZE': 1024}, num_warps=8, num_stages=2),
                    triton.Config({'BLOCK_SIZE': 2048}, num_warps=8, num_stages=2),
                ],
                key=['N'],
            )
            @triton.jit
            def _cross_entropy_kernel(
                logits_ptr,
                targets_ptr,
                loss_ptr,
                M,
                N,
                stride_lm,
                stride_ln,
                stride_t,
                stride_o,
                BLOCK_SIZE: tl.constexpr,
            ):
                row_idx = tl.program_id(0)
                if row_idx >= M:
                    return

                row_logits_ptr = logits_ptr + row_idx * stride_lm

                offs = tl.arange(0, BLOCK_SIZE)
                max_val = -float('inf')
                sum_exp = 0.0

                for col_start in range(0, N, BLOCK_SIZE):
                    col_idx = col_start + offs
                    mask = col_idx < N

                    logits = tl.load(
                        row_logits_ptr + col_idx * stride_ln,
                        mask=mask,
                        other=-float('inf'),
                    )

                    tile_max = tl.max(logits, axis=0)
                    new_max = tl.maximum(max_val, tile_max)

                    # Rescale the accumulated sum to the new maximum
                    scale = tl.exp(max_val - new_max)
                    sum_exp = sum_exp * scale

                    # Accumulate exponentials for this tile relative to new_max
                    logits = logits - new_max
                    exp_logits = tl.exp(logits)
                    tile_sum = tl.sum(exp_logits, axis=0)
                    sum_exp += tile_sum

                    max_val = new_max

                # Load target index and corresponding logit
                target_idx = tl.load(targets_ptr + row_idx * stride_t)
                target_idx = target_idx.to(tl.int32)
                target_logit = tl.load(row_logits_ptr + target_idx * stride_ln)

                loss_val = -target_logit + max_val + tl.log(sum_exp)
                tl.store(loss_ptr + row_idx * stride_o, loss_val)


            def cross_entropy(logits: torch.Tensor, targets: torch.Tensor) -> torch.Tensor:
                """
                Cross entropy loss computation.

                Args:
                    logits: (M, N) tensor of logits
                    targets: (M,) tensor of target class indices (int64)

                Returns:
                    (M,) tensor of per-sample negative log-likelihood loss (float32)
                """
                if not logits.is_cuda:
                    raise ValueError("logits tensor must be on CUDA device")
                if not targets.is_cuda:
                    raise ValueError("targets tensor must be on CUDA device")

                if logits.ndim != 2:
                    raise ValueError("logits must be a 2D tensor of shape (M, N)")
                if targets.ndim != 1:
                    raise ValueError("targets must be a 1D tensor of shape (M,)")

                M, N = logits.shape
                if targets.shape[0] != M:
                    raise ValueError("targets length must match logits batch size")

                # Handle empty batch gracefully
                if M == 0:
                    return torch.empty((0,), dtype=torch.float32, device=logits.device)

                # Ensure dtypes
                if logits.dtype != torch.float32:
                    logits = logits.to(torch.float32)
                if targets.dtype != torch.long:
                    targets = targets.to(torch.long)

                device = logits.device
                loss = torch.empty((M,), dtype=torch.float32, device=device)

                stride_lm, stride_ln = logits.stride()
                stride_t = targets.stride(0)
                stride_o = loss.stride(0)

                grid = (M,)

                _cross_entropy_kernel[grid](
                    logits,
                    targets,
                    loss,
                    M,
                    N,
                    stride_lm,
                    stride_ln,
                    stride_t,
                    stride_o,
                )

                return loss
            """
        )
        return {"code": code}