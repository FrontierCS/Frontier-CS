import os
import textwrap

class Solution:
    def solve(self, spec_path: str = None) -> dict:
        code = textwrap.dedent("""
            import torch
            import triton
            import triton.language as tl


            @triton.autotune(
                configs=[
                    triton.Config({'BLOCK_N': 64,  'BLOCK_K': 64},  num_stages=2, num_warps=4),
                    triton.Config({'BLOCK_N': 64,  'BLOCK_K': 128}, num_stages=2, num_warps=4),
                    triton.Config({'BLOCK_N': 128, 'BLOCK_K': 64},  num_stages=2, num_warps=4),
                    triton.Config({'BLOCK_N': 128, 'BLOCK_K': 128}, num_stages=2, num_warps=8),
                    triton.Config({'BLOCK_N': 256, 'BLOCK_K': 64},  num_stages=2, num_warps=8),
                    triton.Config({'BLOCK_N': 256, 'BLOCK_K': 128}, num_stages=2, num_warps=8),
                ],
                key=['M', 'N', 'K']
            )
            @triton.jit
            def fused_linear_ce_kernel(
                X_ptr, W_ptr, B_ptr, T_ptr, Out_ptr,
                M: tl.constexpr, N: tl.constexpr, K: tl.constexpr,
                stride_xm, stride_xk,
                stride_wk, stride_wn,
                stride_b,
                BLOCK_N: tl.constexpr, BLOCK_K: tl.constexpr
            ):
                pid_m = tl.program_id(axis=0)
                if pid_m >= M:
                    return

                # Offsets
                offs_n = tl.arange(0, BLOCK_N)
                # Load target class for this row
                t = tl.load(T_ptr + pid_m).to(tl.int32)

                # First pass: compute row-wise max over logits
                row_max = tl.full((), -float('inf'), tl.float32)

                n0 = 0
                while n0 < N:
                    cols = n0 + offs_n
                    mask_n = cols < N

                    # Accumulator for logits for current tile of N
                    acc = tl.zeros((BLOCK_N,), dtype=tl.float32)

                    k0 = 0
                    while k0 < K:
                        offs_k = k0 + tl.arange(0, BLOCK_K)
                        mask_k = offs_k < K

                        # Load X row slice
                        x = tl.load(X_ptr + pid_m * stride_xm + offs_k * stride_xk, mask=mask_k, other=0.0)
                        x = x.to(tl.float32)

                        # Load W tile [BLOCK_K, BLOCK_N]
                        w_ptrs = W_ptr + (offs_k[:, None] * stride_wk) + (cols[None, :] * stride_wn)
                        w_mask = (mask_k[:, None] & mask_n[None, :])
                        w = tl.load(w_ptrs, mask=w_mask, other=0.0)
                        w = w.to(tl.float32)

                        # Fused multiply-accumulate: acc += x @ w
                        acc += tl.sum(w * x[:, None], axis=0)

                        k0 += BLOCK_K

                    # Add bias
                    b = tl.load(B_ptr + cols * stride_b, mask=mask_n, other=0.0)
                    acc += b

                    # Update row_max with masking to ignore OOB columns
                    acc_masked = tl.where(mask_n, acc, -float('inf'))
                    tile_max = tl.max(acc_masked, axis=0)
                    row_max = tl.maximum(row_max, tile_max)

                    n0 += BLOCK_N

                # Second pass: compute sumexp(logits - row_max) and target logit
                sumexp = tl.zeros((), dtype=tl.float32)
                tgt_logit = tl.full((), 0.0, dtype=tl.float32)

                n0 = 0
                while n0 < N:
                    cols = n0 + offs_n
                    mask_n = cols < N

                    # Accumulator for logits for current tile of N
                    acc = tl.zeros((BLOCK_N,), dtype=tl.float32)

                    k0 = 0
                    while k0 < K:
                        offs_k = k0 + tl.arange(0, BLOCK_K)
                        mask_k = offs_k < K

                        # Load X row slice
                        x = tl.load(X_ptr + pid_m * stride_xm + offs_k * stride_xk, mask=mask_k, other=0.0)
                        x = x.to(tl.float32)

                        # Load W tile
                        w_ptrs = W_ptr + (offs_k[:, None] * stride_wk) + (cols[None, :] * stride_wn)
                        w_mask = (mask_k[:, None] & mask_n[None, :])
                        w = tl.load(w_ptrs, mask=w_mask, other=0.0)
                        w = w.to(tl.float32)

                        acc += tl.sum(w * x[:, None], axis=0)

                        k0 += BLOCK_K

                    b = tl.load(B_ptr + cols * stride_b, mask=mask_n, other=0.0)
                    logits = acc + b

                    # Compute sumexp with numerical stability
                    logits_centered = logits - row_max
                    expv = tl.where(mask_n, tl.exp(logits_centered), 0.0)
                    sumexp += tl.sum(expv, axis=0)

                    # Gather target logit from this tile if present
                    is_tgt = mask_n & (cols == t)
                    tgt_piece = tl.sum(tl.where(is_tgt, logits, 0.0), axis=0)
                    tgt_logit += tgt_piece

                    n0 += BLOCK_N

                # Final negative log-likelihood: logsumexp - target_logit
                loss = row_max + tl.log(sumexp) - tgt_logit
                tl.store(Out_ptr + pid_m, loss)


            def fused_linear_ce(X: torch.Tensor, W: torch.Tensor, B: torch.Tensor, targets: torch.Tensor) -> torch.Tensor:
                """
                Fused linear layer with cross entropy loss computation.

                Args:
                    X: (M, K) float16
                    W: (K, N) float16
                    B: (N,) float32
                    targets: (M,) int64

                Returns:
                    (M,) float32 negative log-likelihood per sample
                """
                assert X.is_cuda and W.is_cuda and B.is_cuda and targets.is_cuda, "All inputs must be CUDA tensors"
                assert X.dtype == torch.float16 and W.dtype == torch.float16, "X and W must be float16"
                assert B.dtype == torch.float32, "B must be float32"
                assert targets.dtype == torch.long, "targets must be int64 (long)"

                M, K = X.shape
                K_w, N = W.shape
                assert K_w == K, "Incompatible shapes: X @ W"
                assert B.shape[0] == N, "Bias shape mismatch"
                assert targets.shape[0] == M, "Targets shape mismatch"

                # Ensure tensors are contiguous for predictable strides
                Xc = X.contiguous()
                Wc = W.contiguous()
                Bc = B.contiguous()
                Tc = targets.contiguous()

                out = torch.empty((M,), dtype=torch.float32, device=X.device)

                grid = (triton.cdiv(M, 1),)

                fused_linear_ce_kernel[grid](
                    Xc, Wc, Bc, Tc, out,
                    M, N, K,
                    Xc.stride(0), Xc.stride(1),
                    Wc.stride(0), Wc.stride(1),
                    Bc.stride(0),
                )
                return out
        """)
        return {"code": code}
