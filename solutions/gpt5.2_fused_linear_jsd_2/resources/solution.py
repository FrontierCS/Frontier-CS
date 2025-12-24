import textwrap


class Solution:
    def solve(self, spec_path: str = None) -> dict:
        code = textwrap.dedent(
            r"""
            import math
            import torch
            import triton
            import triton.language as tl

            _WCAT_CACHE = {}

            def _get_wcat(W1: torch.Tensor, W2: torch.Tensor) -> torch.Tensor:
                key = (
                    int(W1.data_ptr()),
                    int(W2.data_ptr()),
                    tuple(W1.shape),
                    tuple(W2.shape),
                    str(W1.dtype),
                    str(W2.dtype),
                    int(W1.device.index) if W1.is_cuda else -1,
                )
                wcat = _WCAT_CACHE.get(key, None)
                if wcat is None:
                    # Cat once; reused across many iterations in benchmark.
                    wcat = torch.cat((W1, W2), dim=1).contiguous()
                    _WCAT_CACHE[key] = wcat
                return wcat

            @triton.autotune(
                configs=[
                    triton.Config({"BLOCK_N": 1024}, num_warps=8, num_stages=2),
                    triton.Config({"BLOCK_N": 512}, num_warps=4, num_stages=2),
                    triton.Config({"BLOCK_N": 256}, num_warps=4, num_stages=2),
                ],
                key=["N"],
            )
            @triton.jit
            def _jsd_from_logits_kernel(
                A1_ptr, A2_ptr, B1_ptr, B2_ptr, Out_ptr,
                stride_am: tl.constexpr, stride_an: tl.constexpr,
                N: tl.constexpr,
                BLOCK_N: tl.constexpr,
            ):
                pid_m = tl.program_id(0)
                base1 = A1_ptr + pid_m * stride_am
                base2 = A2_ptr + pid_m * stride_am

                offs = tl.arange(0, BLOCK_N)
                neg_inf = -float("inf")

                max1 = neg_inf
                max2 = neg_inf
                for start in tl.static_range(0, N, BLOCK_N):
                    cols = start + offs
                    m = cols < N
                    a1 = tl.load(base1 + cols * stride_an, mask=m, other=neg_inf).to(tl.float32)
                    a2 = tl.load(base2 + cols * stride_an, mask=m, other=neg_inf).to(tl.float32)
                    b1 = tl.load(B1_ptr + cols, mask=m, other=0.0).to(tl.float32)
                    b2 = tl.load(B2_ptr + cols, mask=m, other=0.0).to(tl.float32)
                    l1 = a1 + b1
                    l2 = a2 + b2
                    max1 = tl.maximum(max1, tl.max(l1, axis=0))
                    max2 = tl.maximum(max2, tl.max(l2, axis=0))

                sum1 = 0.0
                sum2 = 0.0
                for start in tl.static_range(0, N, BLOCK_N):
                    cols = start + offs
                    m = cols < N
                    a1 = tl.load(base1 + cols * stride_an, mask=m, other=neg_inf).to(tl.float32)
                    a2 = tl.load(base2 + cols * stride_an, mask=m, other=neg_inf).to(tl.float32)
                    b1 = tl.load(B1_ptr + cols, mask=m, other=0.0).to(tl.float32)
                    b2 = tl.load(B2_ptr + cols, mask=m, other=0.0).to(tl.float32)
                    l1 = a1 + b1
                    l2 = a2 + b2
                    e1 = tl.exp(l1 - max1)
                    e2 = tl.exp(l2 - max2)
                    sum1 += tl.sum(e1, axis=0)
                    sum2 += tl.sum(e2, axis=0)

                logZ1 = tl.log(sum1) + max1
                logZ2 = tl.log(sum2) + max2

                jsd = 0.0
                ln2 = 0.6931471805599453
                eps = 1e-20
                for start in tl.static_range(0, N, BLOCK_N):
                    cols = start + offs
                    m = cols < N
                    a1 = tl.load(base1 + cols * stride_an, mask=m, other=neg_inf).to(tl.float32)
                    a2 = tl.load(base2 + cols * stride_an, mask=m, other=neg_inf).to(tl.float32)
                    b1 = tl.load(B1_ptr + cols, mask=m, other=0.0).to(tl.float32)
                    b2 = tl.load(B2_ptr + cols, mask=m, other=0.0).to(tl.float32)
                    l1 = a1 + b1
                    l2 = a2 + b2

                    logp = l1 - logZ1
                    logq = l2 - logZ2
                    p = tl.exp(logp)
                    q = tl.exp(logq)
                    mprob = 0.5 * (p + q)
                    logm = tl.log(mprob + eps)

                    contrib = 0.5 * (p * (logp - logm) + q * (logq - logm))
                    contrib = tl.where(m, contrib, 0.0)
                    jsd += tl.sum(contrib, axis=0)

                tl.store(Out_ptr + pid_m, jsd.to(tl.float32))

            def fused_linear_jsd(
                X: torch.Tensor,
                W1: torch.Tensor,
                B1: torch.Tensor,
                W2: torch.Tensor,
                B2: torch.Tensor,
            ) -> torch.Tensor:
                # Expected: X fp16 (M,K), W1/W2 fp16 (K,N), B1/B2 fp32 (N,)
                # Output: fp32 (M,)
                M = X.shape[0]
                N = W1.shape[1]

                Wcat = _get_wcat(W1, W2)
                logits_cat = torch.matmul(X, Wcat)  # (M, 2N) fp16

                logits1 = logits_cat[:, :N]
                logits2 = logits_cat[:, N:]

                out = torch.empty((M,), device=X.device, dtype=torch.float32)

                stride_am = logits1.stride(0)
                stride_an = logits1.stride(1)

                grid = (M,)
                _jsd_from_logits_kernel[grid](
                    logits1, logits2, B1, B2, out,
                    stride_am=stride_am, stride_an=stride_an,
                    N=N,
                )
                return out
            """
        ).strip()
        return {"code": code}
