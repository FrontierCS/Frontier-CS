import os
import textwrap

class Solution:
    def solve(self, spec_path: str = None) -> dict:
        code = textwrap.dedent("""
            import torch
            import triton
            import triton.language as tl


            @triton.jit
            def _fused_linear_ce_kernel(
                X_ptr, W_ptr, B_ptr, T_ptr, Out_ptr,
                M, N, K,
                stride_xm, stride_xk,
                stride_wk, stride_wn,
                stride_bn,
                BLOCK_M: tl.constexpr,
                BLOCK_N: tl.constexpr,
                BLOCK_K: tl.constexpr,
            ):
                pid_m = tl.program_id(0)
                offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
                mask_m = offs_m < M

                # Load targets for this block, cast to int32
                t = tl.load(T_ptr + offs_m, mask=mask_m, other=0).to(tl.int32)

                # First pass: compute row-wise max of logits
                row_max = tl.full((BLOCK_M,), -float('inf'), dtype=tl.float32)

                n_range = tl.arange(0, BLOCK_N)
                k_range = tl.arange(0, BLOCK_K)

                for n0 in range(0, N, BLOCK_N):
                    offs_n = n0 + n_range
                    mask_n = offs_n < N

                    acc = tl.zeros((BLOCK_M, BLOCK_N), dtype=tl.float32)

                    for k0 in range(0, K, BLOCK_K):
                        offs_k = k0 + k_range
                        # X tile: [BM, BK]
                        x_ptrs = X_ptr + (offs_m[:, None] * stride_xm + offs_k[None, :] * stride_xk)
                        # W tile: [BK, BN]
                        w_ptrs = W_ptr + (offs_k[:, None] * stride_wk + offs_n[None, :] * stride_wn)

                        a = tl.load(x_ptrs, mask=(mask_m[:, None] & (offs_k[None, :] < K)), other=0.0)
                        b = tl.load(w_ptrs, mask=((offs_k[:, None] < K) & (mask_n[None, :])), other=0.0)

                        acc += tl.dot(a, b)

                    # Add bias
                    bias = tl.load(B_ptr + offs_n, mask=mask_n, other=0.0)
                    acc += bias[None, :]

                    # Mask invalid columns to -inf for max reduction
                    acc = tl.where(mask_n[None, :], acc, -float('inf'))
                    tile_max = tl.max(acc, axis=1)
                    row_max = tl.maximum(row_max, tile_max)

                # Second pass: compute sumexp(logits - row_max) and gather target logits
                row_sumexp = tl.zeros((BLOCK_M,), dtype=tl.float32)
                tgt_logit = tl.zeros((BLOCK_M,), dtype=tl.float32)

                for n0 in range(0, N, BLOCK_N):
                    offs_n = n0 + n_range
                    mask_n = offs_n < N

                    acc = tl.zeros((BLOCK_M, BLOCK_N), dtype=tl.float32)

                    for k0 in range(0, K, BLOCK_K):
                        offs_k = k0 + k_range
                        x_ptrs = X_ptr + (offs_m[:, None] * stride_xm + offs_k[None, :] * stride_xk)
                        w_ptrs = W_ptr + (offs_k[:, None] * stride_wk + offs_n[None, :] * stride_wn)

                        a = tl.load(x_ptrs, mask=(mask_m[:, None] & (offs_k[None, :] < K)), other=0.0)
                        b = tl.load(w_ptrs, mask=((offs_k[:, None] < K) & (mask_n[None, :])), other=0.0)

                        acc += tl.dot(a, b)

                    bias = tl.load(B_ptr + offs_n, mask=mask_n, other=0.0)
                    acc += bias[None, :]

                    # Gather target logits
                    eq = (t[:, None] == offs_n[None, :]) & mask_m[:, None] & mask_n[None, :]
                    tgt_logit += tl.sum(tl.where(eq, acc, 0.0), axis=1)

                    # Stable sumexp
                    acc = tl.where(mask_n[None, :], acc, -float('inf'))
                    l = acc - row_max[:, None]
                    exp_l = tl.exp(l)
                    row_sumexp += tl.sum(exp_l, axis=1)

                # Final loss per row: logsumexp - target_logit
                out = (tl.log(row_sumexp) + row_max) - tgt_logit
                tl.store(Out_ptr + offs_m, out, mask=mask_m)


            def fused_linear_ce(X: torch.Tensor, W: torch.Tensor, B: torch.Tensor, targets: torch.Tensor) -> torch.Tensor:
                """
                Fused linear layer with cross entropy loss computation.

                Args:
                    X: Input tensor of shape (M, K) - float16
                    W: Weight tensor of shape (K, N) - float16
                    B: Bias tensor of shape (N,) - float32
                    targets: Target tensor of shape (M,) - int64

                Returns:
                    Tensor of shape (M,) - float32, per-sample NLL loss
                """
                assert X.is_cuda and W.is_cuda and B.is_cuda and targets.is_cuda, "All inputs must be on CUDA"
                assert X.dtype == torch.float16, "X must be float16"
                assert W.dtype == torch.float16, "W must be float16"
                assert B.dtype == torch.float32, "B must be float32"
                assert targets.dtype in (torch.int64, torch.long), "targets must be int64"
                assert X.dim() == 2 and W.dim() == 2 and B.dim() == 1 and targets.dim() == 1
                M, K = X.shape
                K_w, N = W.shape
                assert K == K_w, "Incompatible shapes between X and W"
                assert B.numel() == N, "Bias size must match N"
                assert targets.numel() == M, "Targets size must match M"

                # Output
                out = torch.empty((M,), device=X.device, dtype=torch.float32)

                # Choose block sizes heuristically
                # Favor larger BLOCK_N for large N, adjust BLOCK_M for occupancy
                if N >= 8192:
                    BLOCK_M = 32
                    BLOCK_N = 128
                elif N >= 4096:
                    BLOCK_M = 32
                    BLOCK_N = 128
                else:
                    BLOCK_M = 64
                    BLOCK_N = 64
                # BLOCK_K - small for better cache, large enough for throughput
                BLOCK_K = 64

                grid = (triton.cdiv(M, BLOCK_M),)

                _fused_linear_ce_kernel[grid](
                    X, W, B, targets, out,
                    M, N, K,
                    X.stride(0), X.stride(1),
                    W.stride(0), W.stride(1),
                    B.stride(0),
                    BLOCK_M=BLOCK_M, BLOCK_N=BLOCK_N, BLOCK_K=BLOCK_K,
                    num_warps=8 if BLOCK_M * BLOCK_N >= 8192 else 4,
                    num_stages=3,
                )
                return out
        """)
        return {"code": code}