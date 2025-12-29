import textwrap

KERNEL_CODE = textwrap.dedent(
    '''
    import math
    import torch
    import triton
    import triton.language as tl


    @triton.jit
    def _flash_attn_fwd_kernel(
        Q, K, V, O,
        stride_qz, stride_qh, stride_qm, stride_qd,
        stride_kz, stride_kh, stride_kn, stride_kd,
        stride_vz, stride_vh, stride_vn, stride_vd,
        stride_oz, stride_oh, stride_om, stride_od,
        Z, H, M, N, D, Dv,
        sm_scale,
        causal: tl.constexpr,
        BLOCK_M: tl.constexpr,
        BLOCK_N: tl.constexpr,
        BLOCK_DMODEL: tl.constexpr,
        BLOCK_DV: tl.constexpr,
    ):
        pid_bh = tl.program_id(0)
        pid_m = tl.program_id(1)

        if pid_bh >= Z * H:
            return

        bh = pid_bh
        z = bh // H
        h = bh % H

        m_start = pid_m * BLOCK_M
        offs_m = m_start + tl.arange(0, BLOCK_M)
        offs_d = tl.arange(0, BLOCK_DMODEL)
        offs_dv = tl.arange(0, BLOCK_DV)

        Q_bh = Q + z * stride_qz + h * stride_qh
        K_bh = K + z * stride_kz + h * stride_kh
        V_bh = V + z * stride_vz + h * stride_vh
        O_bh = O + z * stride_oz + h * stride_oh

        # Load block of queries
        q_ptrs = Q_bh + offs_m[:, None] * stride_qm + offs_d[None, :] * stride_qd
        mask_q = (offs_m[:, None] < M) & (offs_d[None, :] < D)
        q = tl.load(q_ptrs, mask=mask_q, other=0.0).to(tl.float32)

        # Initialize softmax statistics
        m_i = tl.full([BLOCK_M], -float("inf"), dtype=tl.float32)
        l_i = tl.zeros([BLOCK_M], dtype=tl.float32)
        acc = tl.zeros([BLOCK_M, BLOCK_DV], dtype=tl.float32)

        # Loop over keys/values
        for n_start in range(0, N, BLOCK_N):
            offs_n = n_start + tl.arange(0, BLOCK_N)
            mask_n = offs_n < N

            # Load keys
            k_ptrs = K_bh + offs_n[:, None] * stride_kn + offs_d[None, :] * stride_kd
            mask_k = (offs_n[:, None] < N) & (offs_d[None, :] < D)
            k = tl.load(k_ptrs, mask=mask_k, other=0.0).to(tl.float32)

            # Compute scaled dot-product attention scores
            qk = tl.dot(q, tl.trans(k)) * sm_scale

            # Apply padding mask on keys
            qk = tl.where(mask_n[None, :], qk, -float("inf"))

            # Apply causal mask if needed
            if causal:
                q_idx = offs_m[:, None]
                k_idx = offs_n[None, :]
                causal_mask = q_idx >= k_idx
                qk = tl.where(causal_mask, qk, -float("inf"))

            # Numerically stable softmax
            max_k = tl.max(qk, axis=1)
            m_i_new = tl.maximum(m_i, max_k)
            alpha = tl.exp(m_i - m_i_new)
            p = tl.exp(qk - m_i_new[:, None])

            # Load values
            v_ptrs = V_bh + offs_n[:, None] * stride_vn + offs_dv[None, :] * stride_vd
            mask_v = (offs_n[:, None] < N) & (offs_dv[None, :] < Dv)
            v = tl.load(v_ptrs, mask=mask_v, other=0.0).to(tl.float32)

            # Update running statistics
            l_i = alpha * l_i + tl.sum(p, axis=1)
            acc = alpha[:, None] * acc + tl.dot(p, v)
            m_i = m_i_new

        # Normalize and write back
        out = acc / l_i[:, None]

        o_ptrs = O_bh + offs_m[:, None] * stride_om + offs_dv[None, :] * stride_od
        mask_o = (offs_m[:, None] < M) & (offs_dv[None, :] < Dv)
        tl.store(o_ptrs, out.to(tl.float16), mask=mask_o)


    def flash_attn(Q: torch.Tensor, K: torch.Tensor, V: torch.Tensor, causal: bool = True) -> torch.Tensor:
        """
        Flash attention computation with optional causal masking.

        Args:
            Q: Input tensor of shape (Z, H, M, Dq) - query tensor (float16)
            K: Input tensor of shape (Z, H, N, Dq) - key tensor (float16)
            V: Input tensor of shape (Z, H, N, Dv) - value tensor (float16)
            causal: Whether to apply causal masking (default True)

        Returns:
            Output tensor of shape (Z, H, M, Dv) - attention output (float16)
        """
        assert Q.is_cuda and K.is_cuda and V.is_cuda, "Inputs must be CUDA tensors"
        assert Q.dtype == torch.float16 and K.dtype == torch.float16 and V.dtype == torch.float16, "Inputs must be float16 tensors"
        assert Q.dim() == 4 and K.dim() == 4 and V.dim() == 4, "Inputs must be 4D tensors"

        Z, H, M, D = Q.shape
        Zk, Hk, N, Dk = K.shape
        Zv, Hv, Nv, Dv = V.shape

        assert Z == Zk == Zv and H == Hk == Hv, "Batch and head dimensions must match"
        assert N == Nv, "Key and value sequence lengths must match"
        assert D == Dk, "Query and key feature dimensions must match"

        O = torch.empty((Z, H, M, Dv), device=Q.device, dtype=Q.dtype)

        stride_qz, stride_qh, stride_qm, stride_qd = Q.stride()
        stride_kz, stride_kh, stride_kn, stride_kd = K.stride()
        stride_vz, stride_vh, stride_vn, stride_vd = V.stride()
        stride_oz, stride_oh, stride_om, stride_od = O.stride()

        sm_scale = 1.0 / math.sqrt(D)

        BLOCK_M = 64
        BLOCK_N = 64
        BLOCK_DMODEL = D
        BLOCK_DV = Dv

        grid = (Z * H, (M + BLOCK_M - 1) // BLOCK_M)

        _flash_attn_fwd_kernel[grid](
            Q, K, V, O,
            stride_qz, stride_qh, stride_qm, stride_qd,
            stride_kz, stride_kh, stride_kn, stride_kd,
            stride_vz, stride_vh, stride_vn, stride_vd,
            stride_oz, stride_oh, stride_om, stride_od,
            Z, H, M, N, D, Dv,
            sm_scale,
            causal=causal,
            BLOCK_M=BLOCK_M,
            BLOCK_N=BLOCK_N,
            BLOCK_DMODEL=BLOCK_DMODEL,
            BLOCK_DV=BLOCK_DV,
            num_warps=4,
            num_stages=2,
        )

        return O
    '''
)

exec(KERNEL_CODE, globals())


class Solution:
    def solve(self, spec_path: str = None) -> dict:
        return {"code": KERNEL_CODE}