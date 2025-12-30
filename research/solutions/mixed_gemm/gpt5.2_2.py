import textwrap

class Solution:
    _CODE = textwrap.dedent(
        r"""
        import torch
        import triton
        import triton.language as tl

        def _get_erf():
            try:
                return tl.extra.cuda.libdevice.erf
            except Exception:
                try:
                    return tl.math.erf
                except Exception:
                    return tl.erf

        _ERF = _get_erf()

        @triton.autotune(
            configs=[
                triton.Config({"BLOCK_M": 128, "BLOCK_N": 128, "BLOCK_K": 32, "GROUP_M": 8}, num_warps=8, num_stages=5),
                triton.Config({"BLOCK_M": 64, "BLOCK_N": 128, "BLOCK_K": 32, "GROUP_M": 8}, num_warps=4, num_stages=4),
                triton.Config({"BLOCK_M": 64, "BLOCK_N": 256, "BLOCK_K": 32, "GROUP_M": 8}, num_warps=8, num_stages=4),
                triton.Config({"BLOCK_M": 128, "BLOCK_N": 64, "BLOCK_K": 32, "GROUP_M": 8}, num_warps=4, num_stages=4),
            ],
            key=["M"],
        )
        @triton.jit
        def _linear_bias_gelu_kernel(
            X_ptr, W_ptr, B_ptr, Y_ptr,
            M: tl.int32, N: tl.int32, K: tl.int32,
            stride_xm: tl.int32, stride_xk: tl.int32,
            stride_wk: tl.int32, stride_wn: tl.int32,
            stride_ym: tl.int32, stride_yn: tl.int32,
            BLOCK_M: tl.constexpr, BLOCK_N: tl.constexpr, BLOCK_K: tl.constexpr,
            GROUP_M: tl.constexpr,
        ):
            pid = tl.program_id(0)

            num_pid_m = tl.cdiv(M, BLOCK_M)
            num_pid_n = tl.cdiv(N, BLOCK_N)

            num_pid_in_group = GROUP_M * num_pid_n
            group_id = pid // num_pid_in_group
            first_pid_m = group_id * GROUP_M
            group_size_m = tl.minimum(num_pid_m - first_pid_m, GROUP_M)
            pid_in_group = pid - group_id * num_pid_in_group
            pid_m = first_pid_m + (pid_in_group % group_size_m)
            pid_n = pid_in_group // group_size_m

            offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
            offs_n = pid_n * BLOCK_N + tl.arange(0, BLOCK_N)
            offs_k = tl.arange(0, BLOCK_K)

            x_ptrs = X_ptr + (offs_m[:, None] * stride_xm + offs_k[None, :] * stride_xk)
            w_ptrs = W_ptr + (offs_k[:, None] * stride_wk + offs_n[None, :] * stride_wn)

            acc = tl.zeros((BLOCK_M, BLOCK_N), dtype=tl.float32)

            rm_mask = offs_m < M
            rn_mask = offs_n < N

            k = 0
            while k < K:
                k_mask = (k + offs_k) < K

                a = tl.load(
                    x_ptrs,
                    mask=rm_mask[:, None] & k_mask[None, :],
                    other=0.0,
                ).to(tl.float16)

                b = tl.load(
                    w_ptrs,
                    mask=k_mask[:, None] & rn_mask[None, :],
                    other=0.0,
                ).to(tl.float16)

                acc += tl.dot(a, b, out_dtype=tl.float32)

                x_ptrs += BLOCK_K * stride_xk
                w_ptrs += BLOCK_K * stride_wk
                k += BLOCK_K

            bias = tl.load(B_ptr + offs_n, mask=rn_mask, other=0.0).to(tl.float32)
            x = acc + bias[None, :]

            t = x * 0.7071067811865476
            y = x * 0.5 * (1.0 + _ERF(t))

            out = y.to(tl.float16)

            y_ptrs = Y_ptr + (offs_m[:, None] * stride_ym + offs_n[None, :] * stride_yn)
            tl.store(y_ptrs, out, mask=rm_mask[:, None] & rn_mask[None, :])

        def linear_gelu(X: torch.Tensor, W: torch.Tensor, B: torch.Tensor) -> torch.Tensor:
            if not X.is_cuda or not W.is_cuda or not B.is_cuda:
                raise ValueError("All inputs must be CUDA tensors")
            if X.dtype != torch.float16 or W.dtype != torch.float16:
                raise ValueError("X and W must be float16")
            if B.dtype != torch.float32:
                raise ValueError("B must be float32")
            if X.ndim != 2 or W.ndim != 2 or B.ndim != 1:
                raise ValueError("Shapes must be X(M,K), W(K,N), B(N,)")

            M, K = X.shape
            Kw, N = W.shape
            if Kw != K:
                raise ValueError("Incompatible shapes: X is (M,K) and W is (K,N)")
            if B.shape[0] != N:
                raise ValueError("Bias must have shape (N,)")

            Y = torch.empty((M, N), device=X.device, dtype=torch.float16)

            grid = lambda meta: (triton.cdiv(M, meta["BLOCK_M"]) * triton.cdiv(N, meta["BLOCK_N"]),)

            _linear_bias_gelu_kernel[grid](
                X, W, B, Y,
                M, N, K,
                X.stride(0), X.stride(1),
                W.stride(0), W.stride(1),
                Y.stride(0), Y.stride(1),
            )
            return Y
        """
    ).strip()

    def solve(self, spec_path: str = None) -> dict:
        return {"code": self._CODE}