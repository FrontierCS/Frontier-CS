import textwrap


class Solution:
    def solve(self, spec_path: str = None) -> dict:
        code = textwrap.dedent(
            """
            import torch
            import triton
            import triton.language as tl

            MAX_BLOCK_SIZE = 8192


            @triton.autotune(
                configs=[
                    triton.Config({}, num_warps=4, num_stages=1),
                    triton.Config({}, num_warps=8, num_stages=1),
                    triton.Config({}, num_warps=4, num_stages=2),
                    triton.Config({}, num_warps=8, num_stages=2),
                    triton.Config({}, num_warps=16, num_stages=2),
                ],
                key=["M", "N"],
            )
            @triton.jit
            def _cross_entropy_kernel(
                logits_ptr,
                targets_ptr,
                output_ptr,
                M,
                N,
                stride_logits_m,
                stride_logits_n,
                stride_targets,
                stride_output,
                BLOCK_SIZE: tl.constexpr,
            ):
                row_id = tl.program_id(0)

                # Pointers for this row
                row_logits_ptr = logits_ptr + row_id * stride_logits_m

                # Column indices
                col_offsets = tl.arange(0, BLOCK_SIZE)
                mask = col_offsets < N

                # Load logits for this row
                logits = tl.load(
                    row_logits_ptr + col_offsets * stride_logits_n,
                    mask=mask,
                    other=-float("inf"),
                )

                # Compute max for numerical stability
                row_max = tl.max(logits, axis=0)
                logits = logits - row_max

                # Compute log-sum-exp denominator: log(sum_j exp(logits_j - max))
                exp_logits = tl.exp(logits)
                denom = tl.sum(exp_logits, axis=0)
                log_denom = tl.log(denom)

                # Load target index for this row
                target_index = tl.load(targets_ptr + row_id * stride_targets)
                target_index = target_index.to(tl.int32)

                # Extract centered logit at target index: logits[target] - row_max
                is_target = col_offsets == target_index
                x_t_centered = tl.sum(tl.where(is_target, logits, 0.0), axis=0)

                # loss = log_sum_exp - x_t
                #     = (log(denom) + row_max) - (x_t_centered + row_max)
                #     = log(denom) - x_t_centered
                loss = log_denom - x_t_centered

                tl.store(output_ptr + row_id * stride_output, loss)


            def cross_entropy(logits: torch.Tensor, targets: torch.Tensor) -> torch.Tensor:
                """
                Cross entropy loss computation using a Triton kernel.

                Args:
                    logits: Tensor of shape (M, N), float16/bfloat16/float32, on CUDA.
                    targets: Tensor of shape (M,), int64/int32, on CUDA.

                Returns:
                    Tensor of shape (M,), float32, per-sample negative log-likelihood.
                """
                if logits.ndim != 2:
                    raise ValueError(f"logits must be 2D, got shape {tuple(logits.shape)}")
                if targets.ndim != 1:
                    raise ValueError(f"targets must be 1D, got shape {tuple(targets.shape)}")
                if logits.shape[0] != targets.shape[0]:
                    raise ValueError(
                        f"Batch size mismatch: logits.shape[0]={logits.shape[0]} "
                        f"vs targets.shape[0]={targets.shape[0]}"
                    )

                M, N = logits.shape

                # Fallback for non-CUDA tensors or mismatched devices
                if logits.device.type != "cuda" or targets.device.type != "cuda":
                    device = logits.device
                    targets_dev = targets.to(device=device, non_blocking=True)
                    log_probs = torch.log_softmax(logits, dim=-1)
                    idx = torch.arange(M, device=device)
                    loss = -log_probs[idx, targets_dev]
                    return loss.to(torch.float32)

                if targets.dtype not in (torch.int64, torch.int32):
                    raise TypeError(
                        f"targets must be int64 or int32, got dtype {targets.dtype}"
                    )

                if logits.dtype not in (torch.float16, torch.bfloat16, torch.float32):
                    raise TypeError(
                        f"logits must be float16, bfloat16, or float32, got dtype {logits.dtype}"
                    )

                # Upcast logits to float32 for numeric stability
                if logits.dtype != torch.float32:
                    logits_fp32 = logits.to(torch.float32)
                else:
                    logits_fp32 = logits

                # Handle very large vocab sizes with a safe PyTorch fallback
                if N > MAX_BLOCK_SIZE:
                    log_probs = torch.log_softmax(logits_fp32, dim=-1)
                    idx = torch.arange(M, device=logits_fp32.device)
                    loss = -log_probs[idx, targets]
                    return loss

                # Allocate output
                out = torch.empty((M,), device=logits.device, dtype=torch.float32)

                # Strides in elements
                stride_logits_m, stride_logits_n = logits_fp32.stride()
                stride_targets = targets.stride(0)
                stride_output = out.stride(0)

                if N == 0:
                    return out.zero_()

                # BLOCK_SIZE: next power of two >= N, capped by MAX_BLOCK_SIZE
                block_size = 1 << (int(N) - 1).bit_length()
                if block_size > MAX_BLOCK_SIZE:
                    block_size = MAX_BLOCK_SIZE  # N <= MAX_BLOCK_SIZE already ensured

                grid = (M,)

                _cross_entropy_kernel[grid](
                    logits_fp32,
                    targets,
                    out,
                    M,
                    N,
                    stride_logits_m,
                    stride_logits_n,
                    stride_targets,
                    stride_output,
                    BLOCK_SIZE=block_size,
                )

                return out

            """
        )
        return {"code": code}