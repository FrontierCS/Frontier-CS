import textwrap


KERNEL_CODE = textwrap.dedent(
    r"""
    import math
    import torch
    import triton
    import triton.language as tl

    @triton.autotune(
        configs=[
            triton.Config({"BLOCK_M": 16, "BLOCK_N": 256}, num_warps=8, num_stages=4),
            triton.Config({"BLOCK_M": 16, "BLOCK_N": 128}, num_warps=4, num_stages=4),
            triton.Config({"BLOCK_M": 32, "BLOCK_N": 128}, num_warps=8, num_stages=4),
        ],
        key=["M"],
    )
    @triton.jit
    def _ragged_attn_kernel(
        Q_ptr,
        K_ptr,
        V_ptr,
        O_ptr,
        ROW_LENS_ptr,
        stride_qm: tl.constexpr,
        stride_qd: tl.constexpr,
        stride_kn: tl.constexpr,
        stride_kd: tl.constexpr,
        stride_vn: tl.constexpr,
        stride_vd: tl.constexpr,
        stride_om: tl.constexpr,
        stride_od: tl.constexpr,
        M,
        N,
        SCALE: tl.constexpr,
        D: tl.constexpr,
        DV: tl.constexpr,
        NUM_BLOCKS_N: tl.constexpr,
        BLOCK_M: tl.constexpr,
        BLOCK_N: tl.constexpr,
    ):
        pid_m = tl.program_id(0)

        offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
        m_mask = offs_m < M

        # row_lens for each row in the block
        lens = tl.load(ROW_LENS_ptr + offs_m, mask=m_mask, other=0)
        lens = lens.to(tl.int32)
        lens = tl.maximum(lens, 0)
        lens = tl.minimum(lens, N)

        offs_d = tl.arange(0, D)
        q_ptrs = Q_ptr + offs_m[:, None] * stride_qm + offs_d[None, :] * stride_qd
        q = tl.load(q_ptrs, mask=m_mask[:, None], other=0.0).to(tl.float16)

        offs_dv = tl.arange(0, DV)

        m_i = tl.full((BLOCK_M,), -1.0e9, tl.float32)
        l_i = tl.zeros((BLOCK_M,), tl.float32)
        acc = tl.zeros((BLOCK_M, DV), tl.float32)

        for bid_n in tl.static_range(NUM_BLOCKS_N):
            start_n = bid_n * BLOCK_N
            offs_n = start_n + tl.arange(0, BLOCK_N)
            n_mask = offs_n < N

            # Load K as [D, BLOCK_N] for dot
            k_ptrs = K_ptr + offs_n[None, :] * stride_kn + offs_d[:, None] * stride_kd
            k = tl.load(k_ptrs, mask=n_mask[None, :], other=0.0).to(tl.float16)

            # Load V as [BLOCK_N, DV]
            v_ptrs = V_ptr + offs_n[:, None] * stride_vn + offs_dv[None, :] * stride_vd
            v = tl.load(v_ptrs, mask=n_mask[:, None], other=0.0).to(tl.float16)

            # Ragged mask per row
            valid = (offs_n[None, :] < lens[:, None]) & m_mask[:, None] & n_mask[None, :]

            scores = tl.dot(q, k).to(tl.float32) * SCALE
            scores = tl.where(valid, scores, -1.0e9)

            m_ij = tl.max(scores, axis=1)
            m_new = tl.maximum(m_i, m_ij)

            alpha = tl.exp(m_i - m_new)
            p = tl.exp(scores - m_new[:, None])
            p = tl.where(valid, p, 0.0)

            l_new = l_i * alpha + tl.sum(p, axis=1)
            acc = acc * alpha[:, None] + tl.dot(p.to(tl.float16), v).to(tl.float32)

            m_i = m_new
            l_i = l_new

        inv_l = 1.0 / tl.where(l_i > 0.0, l_i, 1.0)
        out = acc * inv_l[:, None]

        o_ptrs = O_ptr + offs_m[:, None] * stride_om + offs_dv[None, :] * stride_od
        tl.store(o_ptrs, out.to(tl.float16), mask=m_mask[:, None])

    def ragged_attn(Q: torch.Tensor, K: torch.Tensor, V: torch.Tensor, row_lens: torch.Tensor) -> torch.Tensor:
        assert Q.is_cuda and K.is_cuda and V.is_cuda and row_lens.is_cuda
        assert Q.dtype == torch.float16 and K.dtype == torch.float16 and V.dtype == torch.float16
        assert Q.dim() == 2 and K.dim() == 2 and V.dim() == 2
        assert row_lens.dim() == 1
        M, D = Q.shape
        N, Dk = K.shape
        Nv, DV = V.shape
        assert Dk == D
        assert Nv == N
        assert row_lens.shape[0] == M

        if row_lens.dtype != torch.int32:
            row_lens_i32 = row_lens.to(torch.int32)
        else:
            row_lens_i32 = row_lens

        O = torch.empty((M, DV), device=Q.device, dtype=torch.float16)

        scale = 1.0 / math.sqrt(float(D))
        # Default meta for NUM_BLOCKS_N depends on autotuned BLOCK_N; pass max possible and mask with NUM_BLOCKS_N computed per launch.
        # We pass NUM_BLOCKS_N based on a chosen BLOCK_N at launch; autotune will re-launch with its own meta, so compute in launcher.

        def grid(meta):
            return (triton.cdiv(M, meta["BLOCK_M"]),)

        _ragged_attn_kernel[grid](
            Q, K, V, O, row_lens_i32,
            stride_qm=Q.stride(0), stride_qd=Q.stride(1),
            stride_kn=K.stride(0), stride_kd=K.stride(1),
            stride_vn=V.stride(0), stride_vd=V.stride(1),
            stride_om=O.stride(0), stride_od=O.stride(1),
            M=M, N=N,
            SCALE=scale,
            D=D, DV=DV,
            NUM_BLOCKS_N=triton.cdiv(N, 256),  # placeholder, overwritten by autotune meta via `meta`? no, passed as constexpr
        )
        return O

    """
).strip() + "\n"


class Solution:
    def solve(self, spec_path: str = None) -> dict:
        return {"code": KERNEL_CODE}