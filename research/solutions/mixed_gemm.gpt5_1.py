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
                    triton.Config({'BLOCK_M': 128, 'BLOCK_N': 128, 'BLOCK_K': 32, 'GROUP_M': 8},  num_warps=8, num_stages=3),
                    triton.Config({'BLOCK_M': 64,  'BLOCK_N': 128, 'BLOCK_K': 32, 'GROUP_M': 8},  num_warps=4, num_stages=3),
                    triton.Config({'BLOCK_M': 128, 'BLOCK_N': 64,  'BLOCK_K': 32, 'GROUP_M': 8},  num_warps=4, num_stages=3),
                    triton.Config({'BLOCK_M': 64,  'BLOCK_N': 64,  'BLOCK_K': 32, 'GROUP_M': 8},  num_warps=4, num_stages=3),
                    triton.Config({'BLOCK_M': 128, 'BLOCK_N': 128, 'BLOCK_K': 64, 'GROUP_M': 4},  num_warps=8, num_stages=4),
                    triton.Config({'BLOCK_M': 64,  'BLOCK_N': 128, 'BLOCK_K': 64, 'GROUP_M': 4},  num_warps=4, num_stages=4),
                    triton.Config({'BLOCK_M': 128, 'BLOCK_N': 64,  'BLOCK_K': 64, 'GROUP_M': 4},  num_warps=4, num_stages=4),
                ],
                key=['M', 'N', 'K'],
            )
            @triton.jit
            def _linear_bias_gelu_kernel(
                x_ptr, w_ptr, b_ptr, o_ptr,
                M, N, K,
                stride_xm, stride_xk,
                stride_wk, stride_wn,
                stride_om, stride_on,
                BLOCK_M: tl.constexpr, BLOCK_N: tl.constexpr, BLOCK_K: tl.constexpr,
                GROUP_M: tl.constexpr,
            ):
                pid = tl.program_id(axis=0)

                num_pid_m = tl.cdiv(M, BLOCK_M)
                num_pid_n = tl.cdiv(N, BLOCK_N)

                num_pid_in_group = GROUP_M * num_pid_n
                group_id = pid // num_pid_in_group
                first_pid_m = group_id * GROUP_M
                pid_in_group = pid % num_pid_in_group
                pid_m = first_pid_m + pid_in_group // num_pid_n
                pid_n = pid_in_group % num_pid_n

                offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
                offs_n = pid_n * BLOCK_N + tl.arange(0, BLOCK_N)
                offs_k = tl.arange(0, BLOCK_K)

                acc = tl.zeros((BLOCK_M, BLOCK_N), dtype=tl.float32)

                x_ptrs = x_ptr + (offs_m[:, None] * stride_xm + offs_k[None, :] * stride_xk)
                w_ptrs = w_ptr + (offs_k[:, None] * stride_wk + offs_n[None, :] * stride_wn)

                k_iter = 0
                while k_iter < K:
                    k_mask = offs_k[None, :] + k_iter < K
                    x_mask = (offs_m[:, None] < M) & k_mask
                    w_mask = k_mask.T & (offs_n[None, :] < N)

                    a = tl.load(x_ptrs, mask=x_mask, other=0.0)
                    b = tl.load(w_ptrs, mask=w_mask, other=0.0)
                    acc += tl.dot(a, b, out_dtype=tl.float32)

                    k_iter += BLOCK_K
                    x_ptrs += BLOCK_K * stride_xk
                    w_ptrs += BLOCK_K * stride_wk

                # Add bias
                b = tl.load(b_ptr + offs_n, mask=offs_n < N, other=0.0)
                acc = acc + b[None, :]

                # GELU activation: x * 0.5 * (1 + erf(x / sqrt(2)))
                inv_sqrt2 = 0.7071067811865476
                x_scaled = acc * inv_sqrt2
                # tl.math.erf is available in Triton 2.x
                erf_x = tl.math.erf(x_scaled)
                out = acc * 0.5 * (1.0 + erf_x)

                # Store result
                o_ptrs = o_ptr + (offs_m[:, None] * stride_om + offs_n[None, :] * stride_on)
                mask = (offs_m[:, None] < M) & (offs_n[None, :] < N)
                tl.store(o_ptrs, out.to(tl.float16), mask=mask)

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
                assert X.is_cuda and W.is_cuda and B.is_cuda, "All inputs must be on CUDA device"
                assert X.dtype == torch.float16 and W.dtype == torch.float16, "X and W must be float16"
                assert B.dtype == torch.float32, "B must be float32"
                assert X.dim() == 2 and W.dim() == 2 and B.dim() == 1, "Invalid input dimensions"
                M, Kx = X.shape
                Kw, N = W.shape
                assert Kx == Kw, "Inner dimensions must match"
                assert B.numel() == N, "Bias size must be N"

                M_int = int(M)
                N_int = int(N)
                K_int = int(Kx)

                Xc = X
                Wc = W
                Bc = B
                # Output
                O = torch.empty((M_int, N_int), device=X.device, dtype=torch.float16)

                grid = lambda META: (
                    triton.cdiv(M_int, META['BLOCK_M']) * triton.cdiv(N_int, META['BLOCK_N']),
                )

                _linear_bias_gelu_kernel[grid](
                    Xc, Wc, Bc, O,
                    M_int, N_int, K_int,
                    Xc.stride(0), Xc.stride(1),
                    Wc.stride(0), Wc.stride(1),
                    O.stride(0), O.stride(1),
                )
                return O
        """).strip("\n")
        return {"code": code}
