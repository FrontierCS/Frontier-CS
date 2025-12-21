import os
import textwrap

class Solution:
    def solve(self, spec_path: str = None) -> dict:
        code = textwrap.dedent("""
            import torch
            import triton
            import triton.language as tl

            @triton.jit
            def _rowmax_pass_kernel(
                X_ptr, W_ptr, B_ptr, rowmax_ptr,
                M, N, K,
                stride_xm, stride_xk,
                stride_wk, stride_wn,
                stride_b,
                BLOCK_M: tl.constexpr, BLOCK_N: tl.constexpr, BLOCK_K: tl.constexpr
            ):
                pid_m = tl.program_id(0)
                offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
                mask_m = offs_m < M

                row_max = tl.full((BLOCK_M,), -float('inf'), dtype=tl.float32)

                n0 = 0
                while n0 < N:
                    offs_n = n0 + tl.arange(0, BLOCK_N)
                    acc = tl.zeros((BLOCK_M, BLOCK_N), dtype=tl.float32)

                    k0 = 0
                    while k0 < K:
                        offs_k = k0 + tl.arange(0, BLOCK_K)
                        a_ptrs = X_ptr + (offs_m[:, None] * stride_xm + offs_k[None, :] * stride_xk)
                        b_ptrs = W_ptr + (offs_k[:, None] * stride_wk + offs_n[None, :] * stride_wn)

                        a = tl.load(a_ptrs, mask=mask_m[:, None] & (offs_k[None, :] < K), other=0.0).to(tl.float16)
                        b = tl.load(b_ptrs, mask=(offs_k[:, None] < K) & (offs_n[None, :] < N), other=0.0).to(tl.float16)
                        acc += tl.dot(a, b)
                        k0 += BLOCK_K

                    bias = tl.load(B_ptr + offs_n * stride_b, mask=(offs_n < N), other=0.0).to(tl.float32)
                    acc += bias[None, :]

                    tile_row_max = tl.max(acc, axis=1)
                    row_max = tl.maximum(row_max, tile_row_max)
                    n0 += BLOCK_N

                tl.store(rowmax_ptr + offs_m, row_max, mask=mask_m)

            @triton.jit
            def _sumexp_target_kernel(
                X_ptr, W_ptr, B_ptr, rowmax_ptr, targets_ptr, out_ptr,
                M, N, K,
                stride_xm, stride_xk,
                stride_wk, stride_wn,
                stride_b,
                BLOCK_M: tl.constexpr, BLOCK_N: tl.constexpr, BLOCK_K: tl.constexpr
            ):
                pid_m = tl.program_id(0)
                offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
                mask_m = offs_m < M

                row_max = tl.load(rowmax_ptr + offs_m, mask=mask_m, other=-float('inf')).to(tl.float32)
                # sumexp accumulator and target logit accumulator per row
                row_sumexp = tl.zeros((BLOCK_M,), dtype=tl.float32)
                targ_logit = tl.zeros((BLOCK_M,), dtype=tl.float32)

                t = tl.load(targets_ptr + offs_m, mask=mask_m, other=0)
                t = tl.where(mask_m, t, 0)
                t = tl.astype(t, tl.int32)

                n0 = 0
                while n0 < N:
                    offs_n = n0 + tl.arange(0, BLOCK_N)
                    acc = tl.zeros((BLOCK_M, BLOCK_N), dtype=tl.float32)

                    k0 = 0
                    while k0 < K:
                        offs_k = k0 + tl.arange(0, BLOCK_K)
                        a_ptrs = X_ptr + (offs_m[:, None] * stride_xm + offs_k[None, :] * stride_xk)
                        b_ptrs = W_ptr + (offs_k[:, None] * stride_wk + offs_n[None, :] * stride_wn)

                        a = tl.load(a_ptrs, mask=mask_m[:, None] & (offs_k[None, :] < K), other=0.0).to(tl.float16)
                        b = tl.load(b_ptrs, mask=(offs_k[:, None] < K) & (offs_n[None, :] < N), other=0.0).to(tl.float16)
                        acc += tl.dot(a, b)
                        k0 += BLOCK_K

                    bias = tl.load(B_ptr + offs_n * stride_b, mask=(offs_n < N), other=0.0).to(tl.float32)
                    acc += bias[None, :]

                    # sumexp with numerical stability
                    acc_shifted = acc - row_max[:, None]
                    exp_vals = tl.exp(acc_shifted)
                    row_sumexp += tl.sum(exp_vals, axis=1)

                    # accumulate target logit from this tile
                    # Create one-hot like mask per row of where target column lies in this tile
                    # Compare each column offset with target
                    col_mask = (offs_n[None, :] == t[:, None])
                    selected = tl.where(col_mask, acc, 0.0)
                    targ_logit += tl.sum(selected, axis=1)

                    n0 += BLOCK_N

                loss = tl.log(row_sumexp) - targ_logit
                tl.store(out_ptr + offs_m, loss, mask=mask_m)

            def _ceil_div(a, b):
                return (a + b - 1) // b

            def fused_linear_ce(X: torch.Tensor, W: torch.Tensor, B: torch.Tensor, targets: torch.Tensor) -> torch.Tensor:
                assert X.is_cuda and W.is_cuda and B.is_cuda and targets.is_cuda, "All inputs must be on CUDA"
                assert X.dtype == torch.float16 and W.dtype == torch.float16, "X and W must be float16"
                assert B.dtype == torch.float32, "B must be float32"
                assert targets.dtype == torch.long, "targets must be int64 (long)"
                assert X.shape[1] == W.shape[0], "Incompatible K dimension"
                assert W.shape[1] == B.shape[0], "Bias size must match W output dimension"
                M, K = X.shape
                K_w, N = W.shape
                device = X.device

                # Heuristic block sizes
                BLOCK_M = 64 if M >= 64 else 32
                BLOCK_N = 128 if N >= 128 else 64
                BLOCK_K = 32 if K >= 32 else max(8, (K + 7) // 8 * 8)

                # Adjust warps based on tile sizes
                if BLOCK_M * BLOCK_N >= 128 * 128:
                    num_warps = 8
                elif BLOCK_M * BLOCK_N >= 64 * 128:
                    num_warps = 4
                else:
                    num_warps = 4
                num_stages = 3

                rowmax = torch.empty((M,), dtype=torch.float32, device=device)
                losses = torch.empty((M,), dtype=torch.float32, device=device)

                grid = (triton.cdiv(M, BLOCK_M),)

                _rowmax_pass_kernel[grid](
                    X, W, B, rowmax,
                    M, N, K,
                    X.stride(0), X.stride(1),
                    W.stride(0), W.stride(1),
                    B.stride(0),
                    BLOCK_M=BLOCK_M, BLOCK_N=BLOCK_N, BLOCK_K=BLOCK_K,
                    num_warps=num_warps, num_stages=num_stages
                )

                _sumexp_target_kernel[grid](
                    X, W, B, rowmax, targets, losses,
                    M, N, K,
                    X.stride(0), X.stride(1),
                    W.stride(0), W.stride(1),
                    B.stride(0),
                    BLOCK_M=BLOCK_M, BLOCK_N=BLOCK_N, BLOCK_K=BLOCK_K,
                    num_warps=num_warps, num_stages=num_stages
                )

                return losses
        """)
        return {"code": code}
