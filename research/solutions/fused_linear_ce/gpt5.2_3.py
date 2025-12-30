import textwrap


class Solution:
    def solve(self, spec_path: str = None) -> dict:
        code = textwrap.dedent(
            r"""
            import math
            import torch
            import triton
            import triton.language as tl


            @triton.jit
            def _linear_ce_stage1(
                X_ptr, W_ptr, B_ptr,
                MAX_ptr, SUM_ptr,
                M: tl.constexpr, N: tl.constexpr, K: tl.constexpr,
                stride_xm: tl.constexpr, stride_xk: tl.constexpr,
                stride_wk: tl.constexpr, stride_wn: tl.constexpr,
                stride_max_m: tl.constexpr, stride_sum_m: tl.constexpr,
                BLOCK_M: tl.constexpr, BLOCK_N: tl.constexpr, BLOCK_K: tl.constexpr,
                EVEN_K: tl.constexpr, EVEN_N: tl.constexpr,
            ):
                pid_m = tl.program_id(0)
                pid_n = tl.program_id(1)

                rm = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
                rn = pid_n * BLOCK_N + tl.arange(0, BLOCK_N)

                mask_m = rm < M
                if EVEN_N:
                    mask_n = tl.full((BLOCK_N,), True, tl.int1)
                else:
                    mask_n = rn < N

                acc = tl.zeros((BLOCK_M, BLOCK_N), dtype=tl.float32)

                if EVEN_K:
                    for k0 in tl.static_range(0, K, BLOCK_K):
                        rk = k0 + tl.arange(0, BLOCK_K)
                        x = tl.load(
                            X_ptr + rm[:, None] * stride_xm + rk[None, :] * stride_xk,
                            mask=mask_m[:, None],
                            other=0.0,
                        ).to(tl.float16)
                        if EVEN_N:
                            w = tl.load(
                                W_ptr + rk[:, None] * stride_wk + rn[None, :] * stride_wn
                            ).to(tl.float16)
                        else:
                            w = tl.load(
                                W_ptr + rk[:, None] * stride_wk + rn[None, :] * stride_wn,
                                mask=mask_n[None, :],
                                other=0.0,
                            ).to(tl.float16)
                        acc += tl.dot(x, w)
                else:
                    for k0 in tl.static_range(0, K, BLOCK_K):
                        rk = k0 + tl.arange(0, BLOCK_K)
                        mask_k = rk < K
                        x = tl.load(
                            X_ptr + rm[:, None] * stride_xm + rk[None, :] * stride_xk,
                            mask=mask_m[:, None] & mask_k[None, :],
                            other=0.0,
                        ).to(tl.float16)
                        if EVEN_N:
                            w = tl.load(
                                W_ptr + rk[:, None] * stride_wk + rn[None, :] * stride_wn,
                                mask=mask_k[:, None],
                                other=0.0,
                            ).to(tl.float16)
                        else:
                            w = tl.load(
                                W_ptr + rk[:, None] * stride_wk + rn[None, :] * stride_wn,
                                mask=mask_k[:, None] & mask_n[None, :],
                                other=0.0,
                            ).to(tl.float16)
                        acc += tl.dot(x, w)

                b = tl.load(B_ptr + rn, mask=mask_n, other=0.0).to(tl.float32)
                acc += b[None, :]

                if not EVEN_N:
                    acc = tl.where(mask_n[None, :], acc, -float("inf"))

                block_max = tl.max(acc, axis=1)
                block_sum = tl.sum(tl.exp(acc - block_max[:, None]), axis=1)

                out_ptr_max = MAX_ptr + rm * stride_max_m + pid_n
                out_ptr_sum = SUM_ptr + rm * stride_sum_m + pid_n
                tl.store(out_ptr_max, block_max, mask=mask_m)
                tl.store(out_ptr_sum, block_sum, mask=mask_m)


            @triton.jit
            def _linear_ce_target_logit(
                X_ptr, W_ptr, B_ptr, T_ptr,
                TLOG_ptr,
                M: tl.constexpr, K: tl.constexpr,
                stride_xm: tl.constexpr, stride_xk: tl.constexpr,
                stride_wk: tl.constexpr, stride_wn: tl.constexpr,
                BLOCK_M: tl.constexpr, BLOCK_K: tl.constexpr,
                EVEN_K: tl.constexpr,
            ):
                pid = tl.program_id(0)
                rm = pid * BLOCK_M + tl.arange(0, BLOCK_M)
                mask_m = rm < M

                t = tl.load(T_ptr + rm, mask=mask_m, other=0).to(tl.int32)
                acc = tl.zeros((BLOCK_M,), dtype=tl.float32)

                if EVEN_K:
                    for k0 in tl.static_range(0, K, BLOCK_K):
                        rk = k0 + tl.arange(0, BLOCK_K)
                        x = tl.load(
                            X_ptr + rm[:, None] * stride_xm + rk[None, :] * stride_xk,
                            mask=mask_m[:, None],
                            other=0.0,
                        ).to(tl.float16)
                        w = tl.load(
                            W_ptr + rk[None, :] * stride_wk + t[:, None] * stride_wn,
                            mask=mask_m[:, None],
                            other=0.0,
                        ).to(tl.float16)
                        acc += tl.sum(x.to(tl.float32) * w.to(tl.float32), axis=1)
                else:
                    for k0 in tl.static_range(0, K, BLOCK_K):
                        rk = k0 + tl.arange(0, BLOCK_K)
                        mask_k = rk < K
                        x = tl.load(
                            X_ptr + rm[:, None] * stride_xm + rk[None, :] * stride_xk,
                            mask=mask_m[:, None] & mask_k[None, :],
                            other=0.0,
                        ).to(tl.float16)
                        w = tl.load(
                            W_ptr + rk[None, :] * stride_wk + t[:, None] * stride_wn,
                            mask=mask_m[:, None] & mask_k[None, :],
                            other=0.0,
                        ).to(tl.float16)
                        acc += tl.sum(x.to(tl.float32) * w.to(tl.float32), axis=1)

                b = tl.load(B_ptr + t, mask=mask_m, other=0.0).to(tl.float32)
                out = acc + b
                tl.store(TLOG_ptr + rm, out, mask=mask_m)


            @triton.jit
            def _linear_ce_stage2(
                MAX_ptr, SUM_ptr, TLOG_ptr,
                OUT_ptr,
                M: tl.constexpr,
                stride_max_m: tl.constexpr, stride_sum_m: tl.constexpr,
                NUM_BLOCKS: tl.constexpr,
                BLOCK_M: tl.constexpr,
            ):
                pid = tl.program_id(0)
                rm = pid * BLOCK_M + tl.arange(0, BLOCK_M)
                mask_m = rm < M

                rb = tl.arange(0, NUM_BLOCKS)

                maxes = tl.load(
                    MAX_ptr + rm[:, None] * stride_max_m + rb[None, :],
                    mask=mask_m[:, None],
                    other=-float("inf"),
                ).to(tl.float32)

                sums = tl.load(
                    SUM_ptr + rm[:, None] * stride_sum_m + rb[None, :],
                    mask=mask_m[:, None],
                    other=0.0,
                ).to(tl.float32)

                row_max = tl.max(maxes, axis=1)
                sumexp = tl.sum(sums * tl.exp(maxes - row_max[:, None]), axis=1)

                tlog = tl.load(TLOG_ptr + rm, mask=mask_m, other=0.0).to(tl.float32)
                loss = (tl.log(sumexp) + row_max) - tlog
                tl.store(OUT_ptr + rm, loss, mask=mask_m)


            def fused_linear_ce(X: torch.Tensor, W: torch.Tensor, B: torch.Tensor, targets: torch.Tensor) -> torch.Tensor:
                if not (X.is_cuda and W.is_cuda and B.is_cuda and targets.is_cuda):
                    logits = X.to(torch.float32) @ W.to(torch.float32) + B.to(torch.float32)
                    return torch.nn.functional.cross_entropy(logits, targets, reduction="none")

                if X.dtype != torch.float16:
                    X = X.to(torch.float16)
                if W.dtype != torch.float16:
                    W = W.to(torch.float16)
                if B.dtype != torch.float32:
                    B = B.to(torch.float32)
                if targets.dtype != torch.int64:
                    targets = targets.to(torch.int64)

                X = X.contiguous()
                W = W.contiguous()
                B = B.contiguous()
                targets = targets.contiguous()

                M, K = X.shape
                K2, N = W.shape
                assert K2 == K
                assert B.numel() == N
                assert targets.numel() == M

                BLOCK_M1 = 16
                BLOCK_N = 128
                BLOCK_K1 = 64

                num_blocks = triton.cdiv(N, BLOCK_N)

                max_buf = torch.empty((M, num_blocks), device=X.device, dtype=torch.float32)
                sum_buf = torch.empty((M, num_blocks), device=X.device, dtype=torch.float32)
                tlog_buf = torch.empty((M,), device=X.device, dtype=torch.float32)
                out = torch.empty((M,), device=X.device, dtype=torch.float32)

                grid1 = (triton.cdiv(M, BLOCK_M1), num_blocks)
                _linear_ce_stage1[grid1](
                    X, W, B,
                    max_buf, sum_buf,
                    M=M, N=N, K=K,
                    stride_xm=X.stride(0), stride_xk=X.stride(1),
                    stride_wk=W.stride(0), stride_wn=W.stride(1),
                    stride_max_m=max_buf.stride(0), stride_sum_m=sum_buf.stride(0),
                    BLOCK_M=BLOCK_M1, BLOCK_N=BLOCK_N, BLOCK_K=BLOCK_K1,
                    EVEN_K=(K % BLOCK_K1 == 0),
                    EVEN_N=(N % BLOCK_N == 0),
                    num_warps=8,
                    num_stages=4,
                )

                BLOCK_MT = 64
                BLOCK_KT = 128
                gridt = (triton.cdiv(M, BLOCK_MT),)
                _linear_ce_target_logit[gridt](
                    X, W, B, targets,
                    tlog_buf,
                    M=M, K=K,
                    stride_xm=X.stride(0), stride_xk=X.stride(1),
                    stride_wk=W.stride(0), stride_wn=W.stride(1),
                    BLOCK_M=BLOCK_MT, BLOCK_K=BLOCK_KT,
                    EVEN_K=(K % BLOCK_KT == 0),
                    num_warps=4,
                    num_stages=3,
                )

                BLOCK_M2 = 64
                grid2 = (triton.cdiv(M, BLOCK_M2),)
                _linear_ce_stage2[grid2](
                    max_buf, sum_buf, tlog_buf,
                    out,
                    M=M,
                    stride_max_m=max_buf.stride(0),
                    stride_sum_m=sum_buf.stride(0),
                    NUM_BLOCKS=num_blocks,
                    BLOCK_M=BLOCK_M2,
                    num_warps=4,
                    num_stages=2,
                )
                return out
            """
        )
        return {"code": code}