import torch
import triton
import triton.language as tl
import textwrap

class Solution:
    def solve(self, spec_path: str = None) -> dict:
        kernel_code = textwrap.dedent("""
            import torch
            import triton
            import triton.language as tl

            @triton.autotune(
                configs=[
                    # Basic configurations
                    triton.Config({'BLOCK_SIZE_M': 64, 'BLOCK_SIZE_N': 64, 'BLOCK_SIZE_K': 32, 'num_stages': 2, 'num_warps': 4}),
                    triton.Config({'BLOCK_SIZE_M': 128, 'BLOCK_SIZE_N': 64, 'BLOCK_SIZE_K': 32, 'num_stages': 3, 'num_warps': 4}),
                    triton.Config({'BLOCK_SIZE_M': 64, 'BLOCK_SIZE_N': 128, 'BLOCK_SIZE_K': 32, 'num_stages': 3, 'num_warps': 4}),
                    triton.Config({'BLOCK_SIZE_M': 128, 'BLOCK_SIZE_N': 128, 'BLOCK_SIZE_K': 32, 'num_stages': 3, 'num_warps': 8}),
                    # Configurations with larger K block size
                    triton.Config({'BLOCK_SIZE_M': 128, 'BLOCK_SIZE_N': 128, 'BLOCK_SIZE_K': 64, 'num_stages': 3, 'num_warps': 8}),
                    triton.Config({'BLOCK_SIZE_M': 64, 'BLOCK_SIZE_N': 256, 'BLOCK_SIZE_K': 64, 'num_stages': 2, 'num_warps': 8}),
                    triton.Config({'BLOCK_SIZE_M': 256, 'BLOCK_SIZE_N': 64, 'BLOCK_SIZE_K': 64, 'num_stages': 2, 'num_warps': 8}),
                    # High performance configurations for modern GPUs
                    triton.Config({'BLOCK_SIZE_M': 256, 'BLOCK_SIZE_N': 128, 'BLOCK_SIZE_K': 64, 'num_stages': 3, 'num_warps': 8}),
                    triton.Config({'BLOCK_SIZE_M': 128, 'BLOCK_SIZE_N': 256, 'BLOCK_SIZE_K': 64, 'num_stages': 3, 'num_warps': 8}),
                    # Balanced config with more stages
                    triton.Config({'BLOCK_SIZE_M': 128, 'BLOCK_SIZE_N': 128, 'BLOCK_SIZE_K': 64, 'num_stages': 4, 'num_warps': 8}),
                ],
                key=['M', 'N', 'K'],
            )
            @triton.jit
            def _linear_gelu_kernel(
                X, W, B, Y,
                M, N, K,
                stride_xm, stride_xk,
                stride_wk, stride_wn,
                stride_ym, stride_yn,
                BLOCK_SIZE_M: tl.constexpr,
                BLOCK_SIZE_N: tl.constexpr,
                BLOCK_SIZE_K: tl.constexpr,
            ):
                '''
                Triton kernel for Fused GEMM (Linear + Bias + GELU).
                '''
                pid_m = tl.program_id(axis=0)
                pid_n = tl.program_id(axis=1)

                # --- GEMM COMPUTATION ---
                x_block_ptr = tl.make_block_ptr(
                    base=X,
                    shape=(M, K),
                    strides=(stride_xm, stride_xk),
                    offsets=(pid_m * BLOCK_SIZE_M, 0),
                    block_shape=(BLOCK_SIZE_M, BLOCK_SIZE_K),
                    order=(1, 0)
                )
                w_block_ptr = tl.make_block_ptr(
                    base=W,
                    shape=(K, N),
                    strides=(stride_wk, stride_wn),
                    offsets=(0, pid_n * BLOCK_SIZE_N),
                    block_shape=(BLOCK_SIZE_K, BLOCK_SIZE_N),
                    order=(1, 0)
                )

                accumulator = tl.zeros((BLOCK_SIZE_M, BLOCK_SIZE_N), dtype=tl.float32)

                # Iterate over K dimension
                for k in range(0, tl.cdiv(K, BLOCK_SIZE_K)):
                    x = tl.load(x_block_ptr, boundary_check=(0, 1), padding_option="zero")
                    w = tl.load(w_block_ptr, boundary_check=(0, 1), padding_option="zero")
                    
                    accumulator += tl.dot(x, w)

                    x_block_ptr = tl.advance(x_block_ptr, (0, BLOCK_SIZE_K))
                    w_block_ptr = tl.advance(w_block_ptr, (BLOCK_SIZE_K, 0))

                # --- BIAS ADDITION ---
                offs_n = pid_n * BLOCK_SIZE_N + tl.arange(0, BLOCK_SIZE_N)
                b_ptrs = B + offs_n
                b_mask = offs_n < N
                b = tl.load(b_ptrs, mask=b_mask, other=0.0)
                
                accumulator += b

                # --- GELU ACTIVATION ---
                # gelu(x) = x * 0.5 * (1.0 + erf(x / sqrt(2)))
                GELU_COEFF_A = 0.5
                GELU_COEFF_B = 0.7071067811865476  # 1/sqrt(2)
                
                arg = accumulator * GELU_COEFF_B
                erf_val = tl.extra.cuda.libdevice.erf(arg)
                gelu_result = accumulator * GELU_COEFF_A * (1.0 + erf_val)
                
                # --- STORE OUTPUT ---
                y_block_ptr = tl.make_block_ptr(
                    base=Y,
                    shape=(M, N),
                    strides=(stride_ym, stride_yn),
                    offsets=(pid_m * BLOCK_SIZE_M, pid_n * BLOCK_SIZE_N),
                    block_shape=(BLOCK_SIZE_M, BLOCK_SIZE_N),
                    order=(1, 0)
                )
                tl.store(y_block_ptr, gelu_result.to(Y.dtype.element_ty), boundary_check=(0, 1))


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
                M, K = X.shape
                K_w, N = W.shape
                
                assert K == K_w, f"Incompatible dimensions for matmul: X({M},{K}) @ W({K_w},{N})"
                assert B.shape == (N,), f"Incompatible bias shape: B({B.shape[0]}) for output ({M},{N})"
                assert X.is_cuda and W.is_cuda and B.is_cuda, "All tensors must be on a CUDA device"
                assert X.dtype == torch.float16 and W.dtype == torch.float16, "X and W must be float16"
                assert B.dtype == torch.float32, "Bias must be float32"
                
                Y = torch.empty((M, N), device=X.device, dtype=torch.float16)

                grid = lambda META: (
                    triton.cdiv(M, META['BLOCK_SIZE_M']),
                    triton.cdiv(N, META['BLOCK_SIZE_N']),
                )
                
                _linear_gelu_kernel[grid](
                    X, W, B, Y,
                    M, N, K,
                    X.stride(0), X.stride(1),
                    W.stride(0), W.stride(1),
                    Y.stride(0), Y.stride(1),
                )
                
                return Y
        """)
        return {"code": kernel_code}