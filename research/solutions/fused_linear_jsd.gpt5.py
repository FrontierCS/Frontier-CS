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
                    triton.Config({'BM': 32, 'BN': 128}, num_warps=4, num_stages=2),
                    triton.Config({'BM': 64, 'BN': 128}, num_warps=8, num_stages=2),
                    triton.Config({'BM': 32, 'BN': 256}, num_warps=8, num_stages=2),
                    triton.Config({'BM': 64, 'BN': 256}, num_warps=8, num_stages=2),
                    triton.Config({'BM': 128, 'BN': 128}, num_warps=8, num_stages=2),
                ],
                key=['M', 'N'],
            )
            @triton.jit
            def _jsd_two_pass_kernel(
                L1_ptr, L2_ptr, Out_ptr,
                M, N,
                stride_l1m, stride_l1n,
                stride_l2m, stride_l2n,
                stride_outm,
                BM: tl.constexpr, BN: tl.constexpr,
            ):
                pid_m = tl.program_id(0)
                offs_m = pid_m * BM + tl.arange(0, BM)
                mask_m = offs_m < M

                # First pass: compute LSE for both branches with online log-sum-exp
                m1 = tl.full([BM], -float('inf'), dtype=tl.float32)
                m2 = tl.full([BM], -float('inf'), dtype=tl.float32)
                s1 = tl.zeros([BM], dtype=tl.float32)
                s2 = tl.zeros([BM], dtype=tl.float32)

                n = 0
                while n < N:
                    offs_n = n + tl.arange(0, BN)
                    mask_n = offs_n < N

                    ptrs1 = L1_ptr + offs_m[:, None] * stride_l1m + offs_n[None, :] * stride_l1n
                    ptrs2 = L2_ptr + offs_m[:, None] * stride_l2m + offs_n[None, :] * stride_l2n

                    logits1 = tl.load(ptrs1, mask=mask_m[:, None] & mask_n[None, :], other=-float('inf'))
                    logits2 = tl.load(ptrs2, mask=mask_m[:, None] & mask_n[None, :], other=-float('inf'))

                    tmax1 = tl.max(logits1, 1)
                    tmax2 = tl.max(logits2, 1)

                    new_m1 = tl.maximum(m1, tmax1)
                    new_m2 = tl.maximum(m2, tmax2)

                    s1 = s1 * tl.exp(m1 - new_m1) + tl.sum(tl.exp(logits1 - new_m1[:, None]), 1)
                    s2 = s2 * tl.exp(m2 - new_m2) + tl.sum(tl.exp(logits2 - new_m2[:, None]), 1)

                    m1 = new_m1
                    m2 = new_m2

                    n += BN

                lse1 = tl.log(s1) + m1
                lse2 = tl.log(s2) + m2

                # Second pass: compute JSD accumulation
                ln2 = 0.6931471805599453
                eps = 1e-30
                acc = tl.zeros([BM], dtype=tl.float32)

                n = 0
                while n < N:
                    offs_n = n + tl.arange(0, BN)
                    mask_n = offs_n < N

                    ptrs1 = L1_ptr + offs_m[:, None] * stride_l1m + offs_n[None, :] * stride_l1n
                    ptrs2 = L2_ptr + offs_m[:, None] * stride_l2m + offs_n[None, :] * stride_l2n

                    logits1 = tl.load(ptrs1, mask=mask_m[:, None] & mask_n[None, :], other=-float('inf'))
                    logits2 = tl.load(ptrs2, mask=mask_m[:, None] & mask_n[None, :], other=-float('inf'))

                    logp = logits1 - lse1[:, None]
                    logq = logits2 - lse2[:, None]

                    p = tl.exp(logp)
                    q = tl.exp(logq)

                    s = p + q
                    logm = tl.log(tl.maximum(s, eps)) - ln2

                    termp = tl.where(p > 0, p * (logp - logm), 0.0)
                    termq = tl.where(q > 0, q * (logq - logm), 0.0)

                    contrib = 0.5 * (termp + termq)
                    acc += tl.sum(contrib, 1)

                    n += BN

                tl.store(Out_ptr + offs_m * stride_outm, acc, mask=mask_m)

            def fused_linear_jsd(X: torch.Tensor, W1: torch.Tensor, B1: torch.Tensor, W2: torch.Tensor, B2: torch.Tensor) -> torch.Tensor:
                """
                Fused linear layers with Jensen-Shannon Divergence computation.
                
                Args:
                    X: Input tensor of shape (M, K) - input features (float16)
                    W1: Weight tensor of shape (K, N) - first weight matrix (float16)
                    B1: Bias tensor of shape (N,) - first bias vector (float32)
                    W2: Weight tensor of shape (K, N) - second weight matrix (float16)
                    B2: Bias tensor of shape (N,) - second bias vector (float32)
                
                Returns:
                    Output tensor of shape (M,) - Jensen-Shannon Divergence per sample (float32)
                """
                # Validate device
                assert X.is_cuda and W1.is_cuda and W2.is_cuda and B1.is_cuda and B2.is_cuda, "All tensors must be on CUDA"
                # Validate dtypes (convert if necessary)
                if X.dtype != torch.float16:
                    X = X.to(torch.float16)
                if W1.dtype != torch.float16:
                    W1 = W1.to(torch.float16)
                if W2.dtype != torch.float16:
                    W2 = W2.to(torch.float16)
                if B1.dtype != torch.float32:
                    B1 = B1.to(torch.float32)
                if B2.dtype != torch.float32:
                    B2 = B2.to(torch.float32)

                M, K = X.shape
                K1, N = W1.shape
                K2, N2 = W2.shape
                assert K == K1 == K2, "Input feature dimension K mismatch"
                assert N == N2, "Vocabulary size N mismatch"
                assert B1.numel() == N and B2.numel() == N, "Bias size mismatch"

                # Compute logits using highly optimized cuBLAS (torch.matmul), then run a fused Triton kernel for JSD
                # Logits in float32 for stability
                logits1 = torch.matmul(X, W1).to(torch.float32)
                logits1 = logits1.add(B1)  # bias add
                logits2 = torch.matmul(X, W2).to(torch.float32)
                logits2 = logits2.add(B2)  # bias add

                logits1 = logits1.contiguous()
                logits2 = logits2.contiguous()

                out = torch.empty(M, dtype=torch.float32, device=X.device)

                grid = lambda meta: (triton.cdiv(M, meta['BM']),)
                _jsd_two_pass_kernel[grid](
                    logits1, logits2, out,
                    M, N,
                    logits1.stride(0), logits1.stride(1),
                    logits2.stride(0), logits2.stride(1),
                    out.stride(0),
                )
                return out
        """)
        return {"code": code}
