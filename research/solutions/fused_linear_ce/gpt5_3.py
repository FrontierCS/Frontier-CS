import os
import textwrap

class Solution:
    def solve(self, spec_path: str = None) -> dict:
        code = textwrap.dedent('''
            import torch
            import triton
            import triton.language as tl

            @triton.autotune(
                configs=[
                    triton.Config({'BLOCK_M': 64, 'BLOCK_N': 128, 'BLOCK_K': 32}, num_warps=8, num_stages=4),
                    triton.Config({'BLOCK_M': 32, 'BLOCK_N': 128, 'BLOCK_K': 64}, num_warps=4, num_stages=4),
                    triton.Config({'BLOCK_M': 64, 'BLOCK_N': 64,  'BLOCK_K': 32}, num_warps=4, num_stages=3),
                ],
                key=['M', 'N', 'K'],
            )
            @triton.jit
            def _rowmax_kernel(
                X_ptr, W_ptr, B_ptr, rowmax_ptr,
                M: tl.constexpr, N: tl.constexpr, K: tl.constexpr,
                stride_xm, stride_xk,
                stride_wk, stride_wn,
                BLOCK_M: tl.constexpr, BLOCK_N: tl.constexpr, BLOCK_K: tl.constexpr,
            ):
                pid_m = tl.program_id(0)
                offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
                offs_k = tl.arange(0, BLOCK_K)
                mask_m = offs_m < M

                row_max = tl.full((BLOCK_M,), -float('inf'), tl.float32)

                # Loop over N tiles
                for n0 in range(0, N, BLOCK_N):
                    offs_n = n0 + tl.arange(0, BLOCK_N)
                    mask_n = offs_n < N

                    acc = tl.zeros((BLOCK_M, BLOCK_N), dtype=tl.float32)

                    # K loop
                    k = 0
                    while k < K:
                        cur_k = k + offs_k
                        mask_k = cur_k < K

                        a_ptrs = X_ptr + (offs_m[:, None] * stride_xm + cur_k[None, :] * stride_xk)
                        b_ptrs = W_ptr + (cur_k[:, None] * stride_wk + offs_n[None, :] * stride_wn)

                        a = tl.load(a_ptrs, mask=mask_m[:, None] & mask_k[None, :], other=0.0, eviction_policy='evict_last')
                        b = tl.load(b_ptrs, mask=mask_k[:, None] & mask_n[None, :], other=0.0, eviction_policy='evict_last')

                        acc += tl.dot(a, b)

                        k += BLOCK_K

                    bias = tl.load(B_ptr + offs_n, mask=mask_n, other=0.0).to(tl.float32)
                    acc = acc + bias[None, :]

                    # Invalidate out-of-range columns
                    acc = tl.where(mask_n[None, :], acc, -float('inf'))

                    tile_max = tl.max(acc, axis=1)
                    row_max = tl.maximum(row_max, tile_max)

                tl.store(rowmax_ptr + offs_m, row_max, mask=mask_m)


            @triton.autotune(
                configs=[
                    triton.Config({'BLOCK_M': 64, 'BLOCK_N': 128, 'BLOCK_K': 32}, num_warps=8, num_stages=4),
                    triton.Config({'BLOCK_M': 32, 'BLOCK_N': 128, 'BLOCK_K': 64}, num_warps=4, num_stages=4),
                    triton.Config({'BLOCK_M': 64, 'BLOCK_N': 64,  'BLOCK_K': 32}, num_warps=4, num_stages=3),
                ],
                key=['M', 'N', 'K'],
            )
            @triton.jit
            def _sumexp_target_kernel(
                X_ptr, W_ptr, B_ptr, T_ptr, rowmax_ptr, out_ptr,
                M: tl.constexpr, N: tl.constexpr, K: tl.constexpr,
                stride_xm, stride_xk,
                stride_wk, stride_wn,
                stride_t,
                BLOCK_M: tl.constexpr, BLOCK_N: tl.constexpr, BLOCK_K: tl.constexpr,
            ):
                pid_m = tl.program_id(0)
                offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
                mask_m = offs_m < M
                offs_k = tl.arange(0, BLOCK_K)

                row_max = tl.load(rowmax_ptr + offs_m, mask=mask_m, other=-float('inf'))

                # Load targets for rows in this block
                tgt_i64 = tl.load(T_ptr + offs_m * stride_t, mask=mask_m, other=0)
                tgt = tgt_i64.to(tl.int32)

                row_sum = tl.zeros((BLOCK_M,), dtype=tl.float32)
                tgt_logit = tl.zeros((BLOCK_M,), dtype=tl.float32)

                # Loop over N tiles
                for n0 in range(0, N, BLOCK_N):
                    offs_n = n0 + tl.arange(0, BLOCK_N)
                    mask_n = offs_n < N

                    acc = tl.zeros((BLOCK_M, BLOCK_N), dtype=tl.float32)

                    # K loop
                    k = 0
                    while k < K:
                        cur_k = k + offs_k
                        mask_k = cur_k < K

                        a_ptrs = X_ptr + (offs_m[:, None] * stride_xm + cur_k[None, :] * stride_xk)
                        b_ptrs = W_ptr + (cur_k[:, None] * stride_wk + offs_n[None, :] * stride_wn)

                        a = tl.load(a_ptrs, mask=mask_m[:, None] & mask_k[None, :], other=0.0, eviction_policy='evict_last')
                        b = tl.load(b_ptrs, mask=mask_k[:, None] & mask_n[None, :], other=0.0, eviction_policy='evict_last')

                        acc += tl.dot(a, b)

                        k += BLOCK_K

                    bias = tl.load(B_ptr + offs_n, mask=mask_n, other=0.0).to(tl.float32)
                    acc = acc + bias[None, :]

                    # Mask invalid columns to -inf for stability
                    acc = tl.where(mask_n[None, :], acc, -float('inf'))

                    # Sumexp with stability
                    acc_shifted = acc - row_max[:, None]
                    exp_vals = tl.exp(acc_shifted)
                    row_sum += tl.sum(exp_vals, axis=1)

                    # Gather target logits within this tile
                    cols = offs_n
                    # Broadcast compare: (BLOCK_M, BLOCK_N)
                    match = (tgt[:, None] == cols[None, :]) & mask_n[None, :]
                    picked = tl.where(match, acc, 0.0)
                    tgt_logit += tl.sum(picked, axis=1)

                # Compute final loss: logsumexp - target_logit
                loss = tl.log(row_sum) + row_max - tgt_logit
                tl.store(out_ptr + offs_m, loss, mask=mask_m)


            def fused_linear_ce(X: torch.Tensor, W: torch.Tensor, B: torch.Tensor, targets: torch.Tensor) -> torch.Tensor:
                """
                Fused linear layer with cross entropy loss computation.

                Args:
                    X: (M, K) float16 on CUDA
                    W: (K, N) float16 on CUDA
                    B: (N,) float32 on CUDA
                    targets: (M,) int64 on CUDA

                Returns:
                    (M,) float32 per-sample NLL loss on CUDA
                """
                assert X.is_cuda and W.is_cuda and B.is_cuda and targets.is_cuda, "All inputs must be CUDA tensors"
                assert X.dtype in (torch.float16, torch.bfloat16), "X must be float16/bfloat16"
                assert W.dtype in (torch.float16, torch.bfloat16), "W must be float16/bfloat16"
                assert B.dtype == torch.float32, "B must be float32"
                assert targets.dtype == torch.int64, "targets must be int64"
                M, K = X.shape
                K_w, N = W.shape
                assert K_w == K, "Incompatible shapes: X @ W"
                assert B.numel() == N, "Bias must match output size"

                # Strides in element units
                stride_xm, stride_xk = X.stride()
                stride_wk, stride_wn = W.stride()
                # Targets stride (elements)
                stride_t = targets.stride(0)

                # Allocate outputs
                row_max = torch.empty((M,), dtype=torch.float32, device=X.device)
                out = torch.empty((M,), dtype=torch.float32, device=X.device)

                # Kernel launches
                grid = lambda META: (triton.cdiv(M, META['BLOCK_M']),)

                _rowmax_kernel[grid](
                    X, W, B, row_max,
                    M, N, K,
                    stride_xm, stride_xk,
                    stride_wk, stride_wn,
                )

                _sumexp_target_kernel[grid](
                    X, W, B, targets, row_max, out,
                    M, N, K,
                    stride_xm, stride_xk,
                    stride_wk, stride_wn,
                    stride_t,
                )

                return out
        ''')
        return {"code": code}