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
                    triton.Config({"BLOCK_M": 128, "BLOCK_N": 128, "BLOCK_K": 64}, num_warps=8, num_stages=4),
                    triton.Config({"BLOCK_M": 64,  "BLOCK_N": 128, "BLOCK_K": 64}, num_warps=4, num_stages=4),
                    triton.Config({"BLOCK_M": 128, "BLOCK_N": 64,  "BLOCK_K": 64}, num_warps=4, num_stages=4),
                    triton.Config({"BLOCK_M": 128, "BLOCK_N": 256, "BLOCK_K": 32}, num_warps=8, num_stages=4),
                    triton.Config({"BLOCK_M": 64,  "BLOCK_N": 64,  "BLOCK_K": 32}, num_warps=4, num_stages=4),
                ],
                key=['M', 'N', 'K'],
            )
            @triton.jit
            def _fused_linear_bias_gelu_kernel(
                X_ptr, W_ptr, B_ptr, Y_ptr,
                M, N, K,
                stride_xm, stride_xk,
                stride_wk, stride_wn,
                stride_ym, stride_yn,
                BLOCK_M: tl.constexpr, BLOCK_N: tl.constexpr, BLOCK_K: tl.constexpr,
            ):
                pid_m = tl.program_id(0)
                pid_n = tl.program_id(1)

                offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
                offs_n = pid_n * BLOCK_N + tl.arange(0, BLOCK_N)
                offs_k = tl.arange(0, BLOCK_K)

                acc = tl.zeros((BLOCK_M, BLOCK_N), dtype=tl.float32)

                x_ptrs = X_ptr + offs_m[:, None] * stride_xm + offs_k[None, :] * stride_xk
                w_ptrs = W_ptr + offs_k[:, None] * stride_wk + offs_n[None, :] * stride_wn

                k = 0
                while k < K:
                    a = tl.load(
                        x_ptrs + k * stride_xk,
                        mask=(offs_m[:, None] < M) & (k + offs_k[None, :] < K),
                        other=0.0
                    )
                    b = tl.load(
                        w_ptrs + k * stride_wk,
                        mask=(k + offs_k[:, None] < K) & (offs_n[None, :] < N),
                        other=0.0
                    )
                    acc += tl.dot(a, b)
                    k += BLOCK_K

                bias = tl.load(B_ptr + offs_n, mask=offs_n < N, other=0.0).to(tl.float32)
                acc = acc + bias[None, :]

                inv_sqrt2 = 0.7071067811865476
                t = tl.libdevice.erf(acc * inv_sqrt2)
                acc = acc * 0.5 * (1.0 + t)

                y = acc.to(tl.float16)
                y_ptrs = Y_ptr + offs_m[:, None] * stride_ym + offs_n[None, :] * stride_yn
                tl.store(y_ptrs, y, mask=(offs_m[:, None] < M) & (offs_n[None, :] < N))

            def linear_gelu(X: torch.Tensor, W: torch.Tensor, B: torch.Tensor) -> torch.Tensor:
                """
                Linear layer with GELU activation computation.
                
                Args:
                    X: Input tensor of shape (M, K) - input features (float16)
                    W: Weight tensor of shape (K, N) - weight matrix (float16)
                    B: Bias tensor of shape (N,) - bias vector (float32)
                
                Returns:
                    Output tensor of shape (M, N) - output with GELU activation (float16)
                """
                assert X.is_cuda and W.is_cuda and B.is_cuda, "All tensors must be on CUDA device"
                assert X.dtype == torch.float16, "X must be float16"
                assert W.dtype == torch.float16, "W must be float16"
                assert B.dtype == torch.float32, "B must be float32"
                M, K = X.shape
                Kw, N = W.shape
                assert Kw == K, "Incompatible shapes for matmul"
                assert B.shape == (N,), "Bias shape must match output features"
                Y = torch.empty((M, N), device=X.device, dtype=torch.float16)

                grid = lambda META: (triton.cdiv(M, META['BLOCK_M']), triton.cdiv(N, META['BLOCK_N']))
                _fused_linear_bias_gelu_kernel[grid](
                    X, W, B, Y,
                    M, N, K,
                    X.stride(0), X.stride(1),
                    W.stride(0), W.stride(1),
                    Y.stride(0), Y.stride(1),
                )
                return Y
        ''')
        return {"code": code}