import textwrap


class Solution:
    def solve(self, spec_path: str = None) -> dict:
        code = textwrap.dedent('''
            import torch
            import triton
            import triton.language as tl


            @triton.jit
            def _jsd_two_pass_kernel(
                logits1_ptr,
                logits2_ptr,
                out_ptr,
                M,
                N,
                stride1_m,
                stride1_n,
                stride2_m,
                stride2_n,
                stride_out,
                BLOCK_N: tl.constexpr,
                MAX_N_CHUNKS: tl.constexpr,
            ):
                row = tl.program_id(0)

                offs_n = tl.arange(0, BLOCK_N)
                row_offset1 = row * stride1_m
                row_offset2 = row * stride2_m
                out_offset = row * stride_out

                # First pass: compute log-sum-exp for logits1 and logits2
                m1 = tl.zeros([1], dtype=tl.float32) - float("inf")
                s1 = tl.zeros([1], dtype=tl.float32)
                m2 = tl.zeros([1], dtype=tl.float32) - float("inf")
                s2 = tl.zeros([1], dtype=tl.float32)

                for chunk in tl.static_range(0, MAX_N_CHUNKS):
                    col = chunk * BLOCK_N + offs_n
                    mask = col < N

                    ptr1 = logits1_ptr + row_offset1 + col * stride1_n
                    ptr2 = logits2_ptr + row_offset2 + col * stride2_n

                    l1 = tl.load(ptr1, mask=mask, other=-float("inf"))
                    l2 = tl.load(ptr2, mask=mask, other=-float("inf"))

                    l1 = l1.to(tl.float32)
                    l2 = l2.to(tl.float32)

                    tile_max1 = tl.max(l1, axis=0)
                    tile_max2 = tl.max(l2, axis=0)

                    m1_new = tl.maximum(m1, tile_max1)
                    m2_new = tl.maximum(m2, tile_max2)

                    s1 = s1 * tl.exp(m1 - m1_new) + tl.sum(tl.exp(l1 - m1_new), axis=0)
                    s2 = s2 * tl.exp(m2 - m2_new) + tl.sum(tl.exp(l2 - m2_new), axis=0)

                    m1 = m1_new
                    m2 = m2_new

                lse1 = m1 + tl.log(s1)
                lse2 = m2 + tl.log(s2)

                # Second pass: compute entropies and JSD
                hp = tl.zeros([1], dtype=tl.float32)
                hq = tl.zeros([1], dtype=tl.float32)
                hm = tl.zeros([1], dtype=tl.float32)
                eps = 1e-20

                for chunk in tl.static_range(0, MAX_N_CHUNKS):
                    col = chunk * BLOCK_N + offs_n
                    mask = col < N

                    ptr1 = logits1_ptr + row_offset1 + col * stride1_n
                    ptr2 = logits2_ptr + row_offset2 + col * stride2_n

                    l1 = tl.load(ptr1, mask=mask, other=-float("inf"))
                    l2 = tl.load(ptr2, mask=mask, other=-float("inf"))

                    l1 = l1.to(tl.float32)
                    l2 = l2.to(tl.float32)

                    p = tl.exp(l1 - lse1)
                    q = tl.exp(l2 - lse2)
                    m = 0.5 * (p + q)

                    p_safe = tl.maximum(p, eps)
                    q_safe = tl.maximum(q, eps)
                    m_safe = tl.maximum(m, eps)

                    hp_tile = -p * tl.log(p_safe)
                    hq_tile = -q * tl.log(q_safe)
                    hm_tile = -m * tl.log(m_safe)

                    hp += tl.sum(hp_tile, axis=0)
                    hq += tl.sum(hq_tile, axis=0)
                    hm += tl.sum(hm_tile, axis=0)

                jsd = hm - 0.5 * (hp + hq)

                tl.store(out_ptr + out_offset, jsd)

            def fused_linear_jsd(
                X: torch.Tensor,
                W1: torch.Tensor,
                B1: torch.Tensor,
                W2: torch.Tensor,
                B2: torch.Tensor,
            ) -> torch.Tensor:
                """
                Fused linear layers with Jensen-Shannon Divergence computation.

                Args:
                    X: (M, K) float16
                    W1: (K, N) float16
                    B1: (N,) float32
                    W2: (K, N) float16
                    B2: (N,) float32

                Returns:
                    (M,) float32 Jensen-Shannon divergence per sample.
                """
                if not (X.is_cuda and W1.is_cuda and W2.is_cuda and B1.is_cuda and B2.is_cuda):
                    raise ValueError("All inputs must be CUDA tensors.")

                # Ensure contiguous memory layout
                if not X.is_contiguous():
                    X = X.contiguous()
                if not W1.is_contiguous():
                    W1 = W1.contiguous()
                if not W2.is_contiguous():
                    W2 = W2.contiguous()
                if not B1.is_contiguous():
                    B1 = B1.contiguous()
                if not B2.is_contiguous():
                    B2 = B2.contiguous()

                # Linear layers using cuBLAS
                logits1 = X.matmul(W1)
                logits1 = logits1 + B1  # promotes to float32
                logits2 = X.matmul(W2)
                logits2 = logits2 + B2

                logits1 = logits1.to(torch.float32)
                logits2 = logits2.to(torch.float32)

                M, N = logits1.shape
                if logits2.shape != logits1.shape:
                    raise ValueError("Logits shapes from both branches must match.")

                out = torch.empty(M, device=X.device, dtype=torch.float32)

                BLOCK_N = 128
                MAX_N_CHUNKS = 64  # supports up to 8192 columns with BLOCK_N=128

                grid = (M,)

                _jsd_two_pass_kernel[grid](
                    logits1,
                    logits2,
                    out,
                    M,
                    N,
                    logits1.stride(0),
                    logits1.stride(1),
                    logits2.stride(0),
                    logits2.stride(1),
                    out.stride(0),
                    BLOCK_N=BLOCK_N,
                    MAX_N_CHUNKS=MAX_N_CHUNKS,
                    num_warps=4,
                    num_stages=2,
                )

                return out
        ''')
        return {"code": code}
