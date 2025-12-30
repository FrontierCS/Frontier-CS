import textwrap


class Solution:
    def solve(self, spec_path: str = None) -> dict:
        code = textwrap.dedent(
            '''
            import torch
            import triton
            import triton.language as tl
            import math


            @triton.jit
            def flash_attn_fwd_kernel(
                Q, K, V, Out,
                stride_qz, stride_qh, stride_qm, stride_qd,
                stride_kz, stride_kh, stride_kn, stride_kd,
                stride_vz, stride_vh, stride_vn, stride_vd,
                stride_oz, stride_oh, stride_om, stride_od,
                Z, H, M, N,
                sm_scale,
                causal: tl.constexpr,
                BLOCK_M: tl.constexpr,
                BLOCK_N: tl.constexpr,
                HEAD_DIM: tl.constexpr,
                HEAD_DIM_V: tl.constexpr,
            ):
                batch_head = tl.program_id(0)
                batch = batch_head // H
                head = batch_head % H

                start_m = tl.program_id(1) * BLOCK_M
                offs_m = start_m + tl.arange(0, BLOCK_M)
                offs_d = tl.arange(0, HEAD_DIM)
                offs_dv = tl.arange(0, HEAD_DIM_V)

                # Load block of Q: [BLOCK_M, HEAD_DIM]
                q_ptrs = Q + (
                    batch * stride_qz
                    + head * stride_qh
                    + offs_m[:, None] * stride_qm
                    + offs_d[None, :] * stride_qd
                )
                q = tl.load(q_ptrs, mask=offs_m[:, None] < M, other=0.0)
                q = q.to(tl.float32)

                # Initialize streaming softmax state
                m_i = tl.full((BLOCK_M,), -float("inf"), dtype=tl.float32)
                l_i = tl.zeros((BLOCK_M,), dtype=tl.float32)
                acc = tl.zeros((BLOCK_M, HEAD_DIM_V), dtype=tl.float32)

                # Loop over K,V blocks
                for start_n in range(0, N, BLOCK_N):
                    offs_n = start_n + tl.arange(0, BLOCK_N)

                    # Load K: [BLOCK_N, HEAD_DIM]
                    k_ptrs = K + (
                        batch * stride_kz
                        + head * stride_kh
                        + offs_n[:, None] * stride_kn
                        + offs_d[None, :] * stride_kd
                    )
                    k = tl.load(k_ptrs, mask=offs_n[:, None] < N, other=0.0)
                    k = k.to(tl.float32)

                    # Compute attention scores
                    qk = tl.dot(q, tl.trans(k))
                    qk = qk * sm_scale

                    # Apply masks
                    mask_m = offs_m[:, None] < M
                    mask_n = offs_n[None, :] < N
                    mask = mask_m & mask_n
                    if causal:
                        row_idx = offs_m[:, None]
                        col_idx = offs_n[None, :]
                        mask = mask & (row_idx >= col_idx)
                    qk = tl.where(mask, qk, -float("inf"))

                    # Streaming softmax
                    qk_max = tl.max(qk, axis=1)
                    m_i_new = tl.maximum(m_i, qk_max)
                    alpha = tl.exp(m_i - m_i_new)
                    p = tl.exp(qk - m_i_new[:, None])
                    l_i_new = alpha * l_i + tl.sum(p, axis=1)

                    acc_scale = (alpha * l_i) / l_i_new
                    acc = acc * acc_scale[:, None]

                    p = p / l_i_new[:, None]

                    # Load V: [BLOCK_N, HEAD_DIM_V]
                    v_ptrs = V + (
                        batch * stride_vz
                        + head * stride_vh
                        + offs_n[:, None] * stride_vn
                        + offs_dv[None, :] * stride_vd
                    )
                    v = tl.load(
                        v_ptrs,
                        mask=(offs_n[:, None] < N) & (offs_dv[None, :] < HEAD_DIM_V),
                        other=0.0,
                    )
                    v = v.to(tl.float32)

                    acc += tl.dot(p, v)

                    m_i = m_i_new
                    l_i = l_i_new

                # Store outputs
                out_ptrs = Out + (
                    batch * stride_oz
                    + head * stride_oh
                    + offs_m[:, None] * stride_om
                    + offs_dv[None, :] * stride_od
                )
                out = acc.to(tl.float16)
                tl.store(
                    out_ptrs,
                    out,
                    mask=(offs_m[:, None] < M) & (offs_dv[None, :] < HEAD_DIM_V),
                )


            def flash_attn(Q: torch.Tensor, K: torch.Tensor, V: torch.Tensor, causal: bool = True) -> torch.Tensor:
                """
                Flash attention computation with optional causal masking.

                Args:
                    Q: Tensor of shape (Z, H, M, Dq), float16, CUDA
                    K: Tensor of shape (Z, H, N, Dq), float16, CUDA
                    V: Tensor of shape (Z, H, N, Dv), float16, CUDA
                    causal: Whether to apply causal masking.
                Returns:
                    Tensor of shape (Z, H, M, Dv), float16, CUDA
                """
                assert Q.is_cuda and K.is_cuda and V.is_cuda, "Inputs must be CUDA tensors"
                assert Q.dtype == torch.float16 and K.dtype == torch.float16 and V.dtype == torch.float16

                Zq, Hq, M, Dq = Q.shape
                Zk, Hk, N, Dk = K.shape
                Zv, Hv, Nv, Dv = V.shape

                assert Zq == Zk == Zv, "Batch dimensions must match"
                assert Hq == Hk == Hv, "Head dimensions must match"
                assert Dq == Dk, "Q and K must have the same feature dimension"
                assert N == Nv, "Key and value sequence lengths must match"
                if causal:
                    assert M <= N, "For causal attention, query length must be <= key length"

                Z, H = Zq, Hq

                Q = Q.contiguous()
                K = K.contiguous()
                V = V.contiguous()

                Out = torch.empty((Z, H, M, Dv), device=Q.device, dtype=Q.dtype)

                sm_scale = 1.0 / math.sqrt(Dq)

                BLOCK_M = 64
                BLOCK_N = 64

                grid = (Z * H, triton.cdiv(M, BLOCK_M))

                num_warps = 4 if Dq <= 64 else 8
                num_stages = 2

                flash_attn_fwd_kernel[grid](
                    Q, K, V, Out,
                    Q.stride(0), Q.stride(1), Q.stride(2), Q.stride(3),
                    K.stride(0), K.stride(1), K.stride(2), K.stride(3),
                    V.stride(0), V.stride(1), V.stride(2), V.stride(3),
                    Out.stride(0), Out.stride(1), Out.stride(2), Out.stride(3),
                    Z, H, M, N,
                    sm_scale,
                    causal=causal,
                    BLOCK_M=BLOCK_M,
                    BLOCK_N=BLOCK_N,
                    HEAD_DIM=Dq,
                    HEAD_DIM_V=Dv,
                    num_warps=num_warps,
                    num_stages=num_stages,
                )

                return Out
            '''
        )
        return {"code": code}