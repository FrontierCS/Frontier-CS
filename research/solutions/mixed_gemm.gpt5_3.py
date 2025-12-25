import os
import textwrap

class Solution:
    def solve(self, spec_path: str = None) -> dict:
        code = textwrap.dedent(
            '''
            import torch
            import triton
            import triton.language as tl

            HAS_LIBDEVICE_ERF = hasattr(tl, "libdevice") and hasattr(tl.libdevice, "erf")


            @triton.autotune(
                configs=[
                    triton.Config({'BLOCK_M': 128, 'BLOCK_N': 128, 'BLOCK_K': 32, 'GROUP_M': 8}, num_warps=8, num_stages=3),
                    triton.Config({'BLOCK_M': 64,  'BLOCK_N': 128, 'BLOCK_K': 32, 'GROUP_M': 8}, num_warps=4, num_stages=3),
                    triton.Config({'BLOCK_M': 128, 'BLOCK_N': 64,  'BLOCK_K': 32, 'GROUP_M': 8}, num_warps=4, num_stages=3),
                    triton.Config({'BLOCK_M': 64,  'BLOCK_N': 64,  'BLOCK_K': 32, 'GROUP_M': 8}, num_warps=4, num_stages=2),
                    triton.Config({'BLOCK_M': 128, 'BLOCK_N': 128, 'BLOCK_K': 64, 'GROUP_M': 8}, num_warps=8, num_stages=3),
                    triton.Config({'BLOCK_M': 256, 'BLOCK_N': 128, 'BLOCK_K': 32, 'GROUP_M': 8}, num_warps=8, num_stages=4),
                    triton.Config({'BLOCK_M': 128, 'BLOCK_N': 256, 'BLOCK_K': 32, 'GROUP_M': 8}, num_warps=8, num_stages=4),
                ],
                key=['M', 'N', 'K'],
            )
            @triton.jit
            def _fused_linear_bias_gelu_kernel(
                X_ptr, W_ptr, B_ptr, Y_ptr,
                M, N, K,
                stride_xm, stride_xk,
                stride_wk, stride_wn,
                stride_b,
                stride_ym, stride_yn,
                BLOCK_M: tl.constexpr, BLOCK_N: tl.constexpr, BLOCK_K: tl.constexpr,
                GROUP_M: tl.constexpr,
                USE_LIBDEVICE_ERF: tl.constexpr,
            ):
                pid = tl.program_id(axis=0)

                grid_m = tl.cdiv(M, BLOCK_M)
                grid_n = tl.cdiv(N, BLOCK_N)

                group_size = GROUP_M
                group_id = pid // (group_size * grid_n)
                first_pid_m = group_id * group_size
                group_size_m = tl.minimum(grid_m - first_pid_m, group_size)
                pid_in_group = pid % (group_size_m * grid_n)
                pid_m = first_pid_m + pid_in_group // grid_n
                pid_n = pid_in_group % grid_n

                offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
                offs_n = pid_n * BLOCK_N + tl.arange(0, BLOCK_N)
                offs_k = tl.arange(0, BLOCK_K)

                X_ptrs = X_ptr + offs_m[:, None] * stride_xm + offs_k[None, :] * stride_xk
                W_ptrs = W_ptr + offs_k[:, None] * stride_wk + offs_n[None, :] * stride_wn

                acc = tl.zeros((BLOCK_M, BLOCK_N), dtype=tl.float32)
                k_iter = 0
                while k_iter < K:
                    x = tl.load(
                        X_ptrs,
                        mask=(offs_m[:, None] < M) & (offs_k[None, :] + k_iter < K),
                        other=0.0
                    )
                    w = tl.load(
                        W_ptrs,
                        mask=(offs_k[:, None] + k_iter < K) & (offs_n[None, :] < N),
                        other=0.0
                    )
                    acc += tl.dot(x, w)
                    k_iter += BLOCK_K
                    X_ptrs += BLOCK_K * stride_xk
                    W_ptrs += BLOCK_K * stride_wk

                if stride_b == 1:
                    bias = tl.load(B_ptr + offs_n, mask=(offs_n < N), other=0.0)
                else:
                    bias = tl.load(B_ptr + offs_n * stride_b, mask=(offs_n < N), other=0.0)
                acc += bias[None, :]

                x = acc
                if USE_LIBDEVICE_ERF:
                    y = 0.5 * x * (1.0 + tl.libdevice.erf(x * 0.7071067811865476))
                else:
                    c0 = 0.7978845608028654  # sqrt(2/pi)
                    c1 = 0.044715
                    y = 0.5 * x * (1.0 + tl.tanh(c0 * (x + c1 * x * x * x)))

                y = y.to(tl.float16)

                Y_ptrs = Y_ptr + offs_m[:, None] * stride_ym + offs_n[None, :] * stride_yn
                tl.store(
                    Y_ptrs,
                    y,
                    mask=(offs_m[:, None] < M) & (offs_n[None, :] < N),
                )


            def linear_gelu(X: torch.Tensor, W: torch.Tensor, B: torch.Tensor) -> torch.Tensor:
                if not (X.is_cuda and W.is_cuda and B.is_cuda):
                    raise ValueError("All inputs must be CUDA tensors.")
                if X.dtype != torch.float16:
                    raise TypeError(f"X must be float16, got {X.dtype}")
                if W.dtype != torch.float16:
                    raise TypeError(f"W must be float16, got {W.dtype}")
                if B.dtype != torch.float32:
                    raise TypeError(f"B must be float32, got {B.dtype}")
                if X.dim() != 2 or W.dim() != 2 or B.dim() != 1:
                    raise ValueError("Shapes must be X:(M,K), W:(K,N), B:(N,)")

                M, K = X.shape
                K_w, N = W.shape
                if K != K_w:
                    raise ValueError(f"Incompatible shapes: X({X.shape}) and W({W.shape})")
                if B.numel() != N:
                    raise ValueError(f"Bias shape ({B.shape}) incompatible with output N={N}")

                Y = torch.empty((M, N), device=X.device, dtype=torch.float16)

                grid = lambda META: (
                    triton.cdiv(M, META['BLOCK_M']) * triton.cdiv(N, META['BLOCK_N']),
                )

                _fused_linear_bias_gelu_kernel[grid](
                    X, W, B, Y,
                    M, N, K,
                    X.stride(0), X.stride(1),
                    W.stride(0), W.stride(1),
                    B.stride(0),
                    Y.stride(0), Y.stride(1),
                    USE_LIBDEVICE_ERF=HAS_LIBDEVICE_ERF,
                )
                return Y
            '''
        )
        return {"code": code}
