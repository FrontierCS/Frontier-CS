import os
import textwrap

class Solution:
    def solve(self, spec_path: str = None) -> dict:
        code = textwrap.dedent("""
            import math
            import torch
            import triton
            import triton.language as tl

            @triton.jit
            def _flash_attn_fwd(
                Q_ptr, K_ptr, V_ptr, O_ptr,
                Z, H, M, N, D, DV,
                stride_qz, stride_qh, stride_qm, stride_qd,
                stride_kz, stride_kh, stride_kn, stride_kd,
                stride_vz, stride_vh, stride_vn, stride_vd,
                stride_oz, stride_oh, stride_om, stride_od,
                CAUSAL: tl.constexpr,
                BLOCK_M: tl.constexpr,
                BLOCK_N: tl.constexpr,
                BLOCK_DMODEL: tl.constexpr,
                BLOCK_DVALUE: tl.constexpr,
            ):
                pid_m = tl.program_id(0)
                pid_zh = tl.program_id(1)

                # derive z, h from pid_zh
                z = pid_zh // H
                h = pid_zh % H

                # offsets
                m_offsets = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
                n_range = tl.arange(0, BLOCK_N)
                d_range = tl.arange(0, BLOCK_DMODEL)
                dv_range = tl.arange(0, BLOCK_DVALUE)

                # base pointers for (z,h)
                q_base = Q_ptr + z * stride_qz + h * stride_qh
                k_base = K_ptr + z * stride_kz + h * stride_kh
                v_base = V_ptr + z * stride_vz + h * stride_vh
                o_base = O_ptr + z * stride_oz + h * stride_oh

                # load Q block [BLOCK_M, D]
                q_ptrs = q_base + (m_offsets[:, None] * stride_qm + d_range[None, :] * stride_qd)
                q_mask_m = m_offsets[:, None] < M
                q_mask_d = d_range[None, :] < D
                q_mask = q_mask_m & q_mask_d
                q = tl.load(q_ptrs, mask=q_mask, other=0.0).to(tl.float32)

                # initialize m_i, l_i, and output accumulator
                m_i = tl.full((BLOCK_M,), -float("inf"), dtype=tl.float32)
                l_i = tl.zeros((BLOCK_M,), dtype=tl.float32)
                o_acc = tl.zeros((BLOCK_M, BLOCK_DVALUE), dtype=tl.float32)

                # precompute scaling
                scale = 1.0 / tl.sqrt(tl.float32(D))

                # main loop over keys/values
                for start_n in range(0, N, BLOCK_N):
                    n_offsets = start_n + n_range

                    # Load K block [BLOCK_N, D]
                    k_ptrs = k_base + (n_offsets[:, None] * stride_kn + d_range[None, :] * stride_kd)
                    k_mask_n = n_offsets[:, None] < N
                    k_mask_d = d_range[None, :] < D
                    k_mask = k_mask_n & k_mask_d
                    k = tl.load(k_ptrs, mask=k_mask, other=0.0).to(tl.float32)

                    # Compute QK^T
                    qk = tl.dot(q, tl.trans(k)) * scale  # [BLOCK_M, BLOCK_N]

                    # Apply causal mask if needed
                    if CAUSAL:
                        # mask positions where key index > query index
                        m_broadcast = m_offsets[:, None]
                        n_broadcast = n_offsets[None, :]
                        causal_mask = n_broadcast > m_broadcast
                        qk = tl.where(causal_mask, -float("inf"), qk)

                    # Mask out-of-bounds n
                    kv_inbounds = n_offsets[None, :] < N
                    qk = tl.where(kv_inbounds, qk, -float("inf"))

                    # Also mask out-of-bounds m rows
                    q_inbounds = m_offsets[:, None] < M
                    qk = tl.where(q_inbounds, qk, -float("inf"))

                    # Compute new row-wise max for numerical stability
                    qk_max = tl.max(qk, axis=1)
                    new_m = tl.maximum(m_i, qk_max)

                    # Compute exponentials with streaming softmax
                    # p = exp(qk - new_m)
                    exp_qk = tl.exp(qk - new_m[:, None])

                    # Update l_i: new_l = exp(m_i - new_m) * l_i + sum(exp_qk)
                    alpha = tl.exp(m_i - new_m)
                    sum_exp = tl.sum(exp_qk, axis=1)
                    l_new = alpha * l_i + sum_exp

                    # Load V block [BLOCK_N, DV]
                    v_ptrs = v_base + (n_offsets[:, None] * stride_vn + dv_range[None, :] * stride_vd)
                    v_mask_n = n_offsets[:, None] < N
                    v_mask_dv = dv_range[None, :] < DV
                    v_mask = v_mask_n & v_mask_dv
                    v = tl.load(v_ptrs, mask=v_mask, other=0.0).to(tl.float32)

                    # Update o_acc: o = alpha * o + exp_qk @ V
                    update = tl.dot(exp_qk, v)
                    o_acc = o_acc * alpha[:, None] + update

                    # Commit updates
                    m_i = new_m
                    l_i = l_new

                # Finalize: o = o_acc / l_i[:, None]
                o_final = o_acc / l_i[:, None]

                # Store result
                o_ptrs = o_base + (m_offsets[:, None] * stride_om + dv_range[None, :] * stride_od)
                o_store_mask = (m_offsets[:, None] < M) & (dv_range[None, :] < DV)
                tl.store(o_ptrs, o_final.to(tl.float16), mask=o_store_mask)


            def _pick_block_sizes(M: int, N: int, D: int, DV: int):
                # Heuristics for block sizes
                # Favor 128x64 tiles for typical D=64 cases
                if D <= 64:
                    BLOCK_DMODEL = 64
                elif D <= 128:
                    BLOCK_DMODEL = 128
                else:
                    # Clamp to 128 for register pressure
                    BLOCK_DMODEL = 128

                # Choose BLOCK_M and BLOCK_N based on sequence length
                if M >= 2048:
                    BLOCK_M = 128
                elif M >= 1024:
                    BLOCK_M = 128
                else:
                    BLOCK_M = 64

                if N >= 2048:
                    BLOCK_N = 128
                elif N >= 1024:
                    BLOCK_N = 128
                else:
                    BLOCK_N = 64

                # Pick DV block size
                if DV <= 64:
                    BLOCK_DVALUE = 64
                elif DV <= 128:
                    BLOCK_DVALUE = 128
                else:
                    # For larger DV, tile to 128 chunks for register pressure
                    BLOCK_DVALUE = 128

                # Tune num_warps
                if BLOCK_M * BLOCK_N >= 128 * 128:
                    num_warps = 8
                else:
                    num_warps = 4

                # Stages
                num_stages = 2 if D <= 64 else 3

                return BLOCK_M, BLOCK_N, BLOCK_DMODEL, BLOCK_DVALUE, num_warps, num_stages


            def flash_attn(Q: torch.Tensor, K: torch.Tensor, V: torch.Tensor, causal: bool = True) -> torch.Tensor:
                """
                Flash attention computation with optional causal masking.

                Args:
                    Q: (Z, H, M, Dq) float16 CUDA tensor
                    K: (Z, H, N, Dq) float16 CUDA tensor
                    V: (Z, H, N, Dv) float16 CUDA tensor
                    causal: Whether to apply causal masking

                Returns:
                    O: (Z, H, M, Dv) float16 CUDA tensor
                """
                assert Q.is_cuda and K.is_cuda and V.is_cuda, "Inputs must be CUDA tensors"
                assert Q.dtype == torch.float16 and K.dtype == torch.float16 and V.dtype == torch.float16, "Inputs must be float16"
                assert Q.dim() == 4 and K.dim() == 4 and V.dim() == 4, "Inputs must be 4D: (Z, H, S, D)"
                Z, H, M, D = Q.shape
                Zk, Hk, N, Dk = K.shape
                Zv, Hv, Nv, DV = V.shape
                assert Z == Zk == Zv and H == Hk == Hv, "Batch and head dims must match"
                assert D == Dk, "Q and K feature dims must match"
                assert N == Nv, "K and V sequence lengths must match"
                assert N == M or not causal, "For causal flash attention, N should equal M"

                # Ensure contiguous memory layout for efficient access
                Qc = Q.contiguous()
                Kc = K.contiguous()
                Vc = V.contiguous()

                O = torch.empty((Z, H, M, DV), device=Q.device, dtype=torch.float16)

                # Strides
                stride_qz, stride_qh, stride_qm, stride_qd = Qc.stride()
                stride_kz, stride_kh, stride_kn, stride_kd = Kc.stride()
                stride_vz, stride_vh, stride_vn, stride_vd = Vc.stride()
                stride_oz, stride_oh, stride_om, stride_od = O.stride()

                BLOCK_M, BLOCK_N, BLOCK_DMODEL, BLOCK_DVALUE, num_warps, num_stages = _pick_block_sizes(M, N, D, DV)

                grid = (triton.cdiv(M, BLOCK_M), Z * H)

                _flash_attn_fwd[grid](
                    Qc, Kc, Vc, O,
                    Z, H, M, N, D, DV,
                    stride_qz, stride_qh, stride_qm, stride_qd,
                    stride_kz, stride_kh, stride_kn, stride_kd,
                    stride_vz, stride_vh, stride_vn, stride_vd,
                    stride_oz, stride_oh, stride_om, stride_od,
                    CAUSAL=causal,
                    BLOCK_M=BLOCK_M,
                    BLOCK_N=BLOCK_N,
                    BLOCK_DMODEL=BLOCK_DMODEL,
                    BLOCK_DVALUE=BLOCK_DVALUE,
                    num_warps=num_warps,
                    num_stages=num_stages,
                )
                return O
        """)
        return {"code": code}
