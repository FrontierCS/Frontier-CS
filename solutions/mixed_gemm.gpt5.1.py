import textwrap


class Solution:
    def solve(self, spec_path: str = None) -> dict:
        code = textwrap.dedent('''\
            import torch
            import triton
            import triton.language as tl


            @triton.autotune(
                configs=[
                    triton.Config({"BLOCK_M": 128, "BLOCK_N": 128, "BLOCK_K": 32}, num_warps=8, num_stages=3),
                    triton.Config({"BLOCK_M": 64, "BLOCK_N": 128, "BLOCK_K": 32}, num_warps=4, num_stages=3),
                    triton.Config({"BLOCK_M": 128, "BLOCK_N": 64, "BLOCK_K": 32}, num_warps=4, num_stages=3),
                    triton.Config({"BLOCK_M": 64, "BLOCK_N": 64, "BLOCK_K": 32}, num_warps=4, num_stages=2),
                ],
                key=["M", "N", "K"],
            )
            @triton.jit
            def _linear_gelu_kernel(
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

                x_ptrs = X_ptr + offs_m[:, None] * stride_xm + offs_k[None, :] * stride_xk
                w_ptrs = W_ptr + offs_k[:, None] * stride_wk + offs_n[None, :] * stride_wn

                acc = tl.zeros((BLOCK_M, BLOCK_N), dtype=tl.float32)

                for k in range(0, K, BLOCK_K):
                    k_offsets = k + offs_k
                    x_mask = (offs_m[:, None] < M) & (k_offsets[None, :] < K)
                    w_mask = (k_offsets[:, None] < K) & (offs_n[None, :] < N)
                    x = tl.load(x_ptrs, mask=x_mask, other=0.0)
                    w = tl.load(w_ptrs, mask=w_mask, other=0.0)
                    acc += tl.dot(x, w, out_dtype=tl.float32)
                    x_ptrs += BLOCK_K * stride_xk
                    w_ptrs += BLOCK_K * stride_wk

                bias = tl.load(B_ptr + offs_n, mask=offs_n < N, other=0.0)
                acc += bias[None, :]

                # GELU approximation using tanh formulation implemented via exp
                # gelu(x) ≈ 0.5 * x * (1 + tanh(√(2/π) * (x + 0.044715 x^3)))
                c0 = 0.7978845608028654  # sqrt(2/pi)
                c1 = 0.044715
                x = acc
                x_cubed = x * x * x
                t = c0 * (x + c1 * x_cubed)
                exp_term = tl.exp(2.0 * t)
                tanh_t = (exp_term - 1.0) / (exp_term + 1.0)
                x = 0.5 * x * (1.0 + tanh_t)

                y = x.to(tl.float16)
                y_mask = (offs_m[:, None] < M) & (offs_n[None, :] < N)
                tl.store(
                    Y_ptr + offs_m[:, None] * stride_ym + offs_n[None, :] * stride_yn,
                    y,
                    mask=y_mask,
                )


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
                if not (X.is_cuda and W.is_cuda and B.is_cuda):
                    raise ValueError("All inputs must be CUDA tensors")
                if X.dtype != torch.float16 or W.dtype != torch.float16:
                    raise ValueError("X and W must be float16 tensors")
                if B.dtype != torch.float32:
                    raise ValueError("B must be a float32 tensor")
                if X.ndim != 2 or W.ndim != 2 or B.ndim != 1:
                    raise ValueError("X and W must be 2D, B must be 1D")

                M, K = X.shape
                K_w, N = W.shape
                if K_w != K:
                    raise ValueError("Incompatible shapes: X.shape[1] must equal W.shape[0]")
                if B.shape[0] != N:
                    raise ValueError("Incompatible shapes: B.shape[0] must equal W.shape[1]")

                Y = torch.empty((M, N), device=X.device, dtype=torch.float16)

                grid = lambda META: (
                    triton.cdiv(M, META["BLOCK_M"]),
                    triton.cdiv(N, META["BLOCK_N"]),
                )

                _linear_gelu_kernel[grid](
                    X, W, B, Y,
                    M, N, K,
                    X.stride(0), X.stride(1),
                    W.stride(0), W.stride(1),
                    Y.stride(0), Y.stride(1),
                )

                return Y
        ''')
        return {"code": code}
