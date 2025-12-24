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
                    triton.Config({'BLOCK_M': 64, 'BLOCK_N': 128, 'BLOCK_K': 32}, num_stages=4, num_warps=8),
                    triton.Config({'BLOCK_M': 128, 'BLOCK_N': 128, 'BLOCK_K': 32}, num_stages=4, num_warps=8),
                    triton.Config({'BLOCK_M': 64, 'BLOCK_N': 256, 'BLOCK_K': 32}, num_stages=4, num_warps=8),
                    triton.Config({'BLOCK_M': 32, 'BLOCK_N': 256, 'BLOCK_K': 32}, num_stages=4, num_warps=8),
                    triton.Config({'BLOCK_M': 128, 'BLOCK_N': 64, 'BLOCK_K': 32}, num_stages=4, num_warps=8),
                ],
                key=['M', 'N', 'K'],
            )
            @triton.jit
            def _kernel_gemm_store_logits(
                X_ptr, W1_ptr, B1_ptr, W2_ptr, B2_ptr, Y1_ptr, Y2_ptr,
                M, N, K,
                stride_xm, stride_xk,
                stride_w1k, stride_w1n,
                stride_w2k, stride_w2n,
                stride_y_m, stride_y_n,
                BLOCK_M: tl.constexpr, BLOCK_N: tl.constexpr, BLOCK_K: tl.constexpr
            ):
                pid_m = tl.program_id(0)
                pid_n = tl.program_id(1)
                offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
                offs_n = pid_n * BLOCK_N + tl.arange(0, BLOCK_N)
                offs_k = tl.arange(0, BLOCK_K)

                acc1 = tl.zeros((BLOCK_M, BLOCK_N), dtype=tl.float32)
                acc2 = tl.zeros((BLOCK_M, BLOCK_N), dtype=tl.float32)

                # Loop over K
                k = 0
                while k < K:
                    k_mask = k + offs_k < K
                    a_ptrs = X_ptr + (offs_m[:, None] * stride_xm + (k + offs_k[None, :]) * stride_xk)
                    b1_ptrs = W1_ptr + ((k + offs_k)[:, None] * stride_w1k + offs_n[None, :] * stride_w1n)
                    b2_ptrs = W2_ptr + ((k + offs_k)[:, None] * stride_w2k + offs_n[None, :] * stride_w2n)

                    a_mask = (offs_m[:, None] < M) & k_mask[None, :]
                    b_mask = k_mask[:, None] & (offs_n[None, :] < N)

                    a = tl.load(a_ptrs, mask=a_mask, other=0.).to(tl.float16)
                    b1 = tl.load(b1_ptrs, mask=b_mask, other=0.).to(tl.float16)
                    b2 = tl.load(b2_ptrs, mask=b_mask, other=0.).to(tl.float16)

                    acc1 += tl.dot(a, b1)
                    acc2 += tl.dot(a, b2)
                    k += BLOCK_K

                # Add bias
                bias_mask = offs_n < N
                bias1 = tl.load(B1_ptr + offs_n, mask=bias_mask, other=0.).to(tl.float32)
                bias2 = tl.load(B2_ptr + offs_n, mask=bias_mask, other=0.).to(tl.float32)
                acc1 += bias1[None, :]
                acc2 += bias2[None, :]

                # Store
                y_ptrs = Y1_ptr + (offs_m[:, None] * stride_y_m + offs_n[None, :] * stride_y_n)
                mask_store = (offs_m[:, None] < M) & (offs_n[None, :] < N)
                tl.store(y_ptrs, acc1.to(tl.float16), mask=mask_store)

                y_ptrs2 = Y2_ptr + (offs_m[:, None] * stride_y_m + offs_n[None, :] * stride_y_n)
                tl.store(y_ptrs2, acc2.to(tl.float16), mask=mask_store)


            @triton.jit
            def _kernel_row_lse(
                Y1_ptr, Y2_ptr,
                M, N,
                stride_y_m, stride_y_n,
                LSE1_ptr, LSE2_ptr,
                BLOCK_M: tl.constexpr, BLOCK_N: tl.constexpr
            ):
                pid_m = tl.program_id(0)
                offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
                m_mask = offs_m < M

                # Initialize running max and sumexp for both branches
                neg_inf = float('-inf')
                m1 = tl.full((BLOCK_M,), neg_inf, tl.float32)
                m2 = tl.full((BLOCK_M,), neg_inf, tl.float32)
                s1 = tl.zeros((BLOCK_M,), dtype=tl.float32)
                s2 = tl.zeros((BLOCK_M,), dtype=tl.float32)

                n = 0
                while n < N:
                    offs_n = n + tl.arange(0, BLOCK_N)
                    valid_n = offs_n < N
                    mask = m_mask[:, None] & valid_n[None, :]

                    y1_ptrs = Y1_ptr + (offs_m[:, None] * stride_y_m + offs_n[None, :] * stride_y_n)
                    y2_ptrs = Y2_ptr + (offs_m[:, None] * stride_y_m + offs_n[None, :] * stride_y_n)

                    v1 = tl.load(y1_ptrs, mask=mask, other=0.).to(tl.float32)
                    v2 = tl.load(y2_ptrs, mask=mask, other=0.).to(tl.float32)

                    # set masked to -inf for max/sumexp
                    v1 = tl.where(mask, v1, neg_inf)
                    v2 = tl.where(mask, v2, neg_inf)

                    tile_max1 = tl.max(v1, axis=1)
                    tile_max2 = tl.max(v2, axis=1)

                    new_m1 = tl.maximum(m1, tile_max1)
                    new_m2 = tl.maximum(m2, tile_max2)

                    # sumexp with new max
                    se1 = tl.sum(tl.exp(v1 - new_m1[:, None]), axis=1)
                    se2 = tl.sum(tl.exp(v2 - new_m2[:, None]), axis=1)

                    s1 = s1 * tl.exp(m1 - new_m1) + se1
                    s2 = s2 * tl.exp(m2 - new_m2) + se2
                    m1 = new_m1
                    m2 = new_m2
                    n += BLOCK_N

                # lse = log(sumexp) + max
                lse1 = tl.log(s1) + m1
                lse2 = tl.log(s2) + m2

                tl.store(LSE1_ptr + offs_m, lse1, mask=m_mask)
                tl.store(LSE2_ptr + offs_m, lse2, mask=m_mask)


            @triton.jit
            def _kernel_jsd(
                Y1_ptr, Y2_ptr,
                M, N,
                stride_y_m, stride_y_n,
                LSE1_ptr, LSE2_ptr,
                OUT_ptr,
                BLOCK_M: tl.constexpr, BLOCK_N: tl.constexpr
            ):
                pid_m = tl.program_id(0)
                offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
                m_mask = offs_m < M

                lse1 = tl.load(LSE1_ptr + offs_m, mask=m_mask, other=0.).to(tl.float32)
                lse2 = tl.load(LSE2_ptr + offs_m, mask=m_mask, other=0.).to(tl.float32)

                acc = tl.zeros((BLOCK_M,), dtype=tl.float32)

                ln2 = 0.6931471805599453
                n = 0
                while n < N:
                    offs_n = n + tl.arange(0, BLOCK_N)
                    valid_n = offs_n < N
                    mask = m_mask[:, None] & valid_n[None, :]

                    y1_ptrs = Y1_ptr + (offs_m[:, None] * stride_y_m + offs_n[None, :] * stride_y_n)
                    y2_ptrs = Y2_ptr + (offs_m[:, None] * stride_y_m + offs_n[None, :] * stride_y_n)

                    v1 = tl.load(y1_ptrs, mask=mask, other=0.).to(tl.float32)
                    v2 = tl.load(y2_ptrs, mask=mask, other=0.).to(tl.float32)

                    # Compute p_log and q_log
                    p_log = v1 - lse1[:, None]
                    q_log = v2 - lse2[:, None]

                    # Create safe versions to avoid NaN on masked elements
                    safe_p_log = tl.where(mask, p_log, 0.0)
                    safe_q_log = tl.where(mask, q_log, 0.0)

                    # p and q with masking to zero out invalid
                    p = tl.where(mask, tl.exp(p_log), 0.0)
                    q = tl.where(mask, tl.exp(q_log), 0.0)

                    # logm = logsumexp(p_log, q_log) - log(2), computed safely
                    mxy = tl.maximum(safe_p_log, safe_q_log)
                    expsum = tl.exp(safe_p_log - mxy) + tl.exp(safe_q_log - mxy)
                    logm = mxy + tl.log(expsum) - ln2

                    term = p * (safe_p_log - logm) + q * (safe_q_log - logm)
                    inc = tl.sum(term, axis=1)
                    acc += inc
                    n += BLOCK_N

                jsd = 0.5 * acc
                tl.store(OUT_ptr + offs_m, jsd, mask=m_mask)


            def fused_linear_jsd(X: torch.Tensor, W1: torch.Tensor, B1: torch.Tensor, W2: torch.Tensor, B2: torch.Tensor) -> torch.Tensor:
                """
                Fused linear layers with Jensen-Shannon Divergence computation.
                Computes logits for two branches using a fused GEMM kernel,
                computes row-wise log-sum-exp, then JSD per sample.
                """
                assert X.is_cuda and W1.is_cuda and W2.is_cuda and B1.is_cuda and B2.is_cuda, "All tensors must be on CUDA"
                assert X.dtype == torch.float16 and W1.dtype == torch.float16 and W2.dtype == torch.float16, "X, W1, W2 must be float16"
                assert B1.dtype == torch.float32 and B2.dtype == torch.float32, "Biases must be float32"
                assert X.ndim == 2 and W1.ndim == 2 and W2.ndim == 2 and B1.ndim == 1 and B2.ndim == 1, "Invalid shapes"
                M, K = X.shape
                K1, N = W1.shape
                K2, N2 = W2.shape
                assert K == K1 == K2, "Incompatible K dimensions"
                assert N == N2 == B1.numel() == B2.numel(), "Incompatible N dimensions"

                # Allocate logits buffers (half precision) and lse, out (float32)
                Y1 = torch.empty((M, N), dtype=torch.float16, device=X.device)
                Y2 = torch.empty((M, N), dtype=torch.float16, device=X.device)
                LSE1 = torch.empty((M,), dtype=torch.float32, device=X.device)
                LSE2 = torch.empty((M,), dtype=torch.float32, device=X.device)
                OUT = torch.empty((M,), dtype=torch.float32, device=X.device)

                # Strides
                stride_xm, stride_xk = X.stride()
                stride_w1k, stride_w1n = W1.stride()
                stride_w2k, stride_w2n = W2.stride()
                stride_ym, stride_yn = Y1.stride()

                # Grid for GEMM
                def grid_gemm(meta):
                    return (triton.cdiv(M, meta['BLOCK_M']), triton.cdiv(N, meta['BLOCK_N']))

                _kernel_gemm_store_logits[grid_gemm](
                    X, W1, B1, W2, B2, Y1, Y2,
                    M, N, K,
                    stride_xm, stride_xk,
                    stride_w1k, stride_w1n,
                    stride_w2k, stride_w2n,
                    stride_ym, stride_yn,
                )

                # Row-wise LSE
                BLOCK_M_LSE = 32
                BLOCK_N_LSE = 256
                grid_lse = (triton.cdiv(M, BLOCK_M_LSE),)

                _kernel_row_lse[grid_lse](
                    Y1, Y2,
                    M, N,
                    stride_ym, stride_yn,
                    LSE1, LSE2,
                    BLOCK_M=BLOCK_M_LSE, BLOCK_N=BLOCK_N_LSE
                )

                # JSD computation
                BLOCK_M_JSD = 32
                BLOCK_N_JSD = 256
                grid_jsd = (triton.cdiv(M, BLOCK_M_JSD),)

                _kernel_jsd[grid_jsd](
                    Y1, Y2,
                    M, N,
                    stride_ym, stride_yn,
                    LSE1, LSE2,
                    OUT,
                    BLOCK_M=BLOCK_M_JSD, BLOCK_N=BLOCK_N_JSD
                )
                return OUT
        """)
        return {"code": code}
