import torch
import triton
import triton.language as tl
import math

class Solution:
    def solve(self, spec_path: str = None) -> dict:
        code = """
import torch
import triton
import triton.language as tl
import math

def ragged_attn(Q: torch.Tensor, K: torch.Tensor, V: torch.Tensor, row_lens: torch.Tensor) -> torch.Tensor:
    M, D = Q.shape
    N, _ = K.shape
    _, Dv = V.shape
    if row_lens.dtype == torch.int64:
        row_lens = row_lens.to(torch.int32)
    scale = 1 / math.sqrt(D)
    O = torch.empty((M, Dv), dtype=Q.dtype, device=Q.device)
    @triton.jit
    def kernel(
        Q, K, V, row_lens, O,
        stride_qm: tl.int32, stride_qd: tl.int32,
        stride_kn: tl.int32, stride_kd: tl.int32,
        stride_vn: tl.int32, stride_vd: tl.int32,
        stride_rm: tl.int32,
        stride_om: tl.int32, stride_od: tl.int32,
        M: tl.int32, N: tl.int32, D: tl.int32, Dv: tl.int32,
        scale: tl.float32,
        BLOCK_M: tl.constexpr,
        BLOCK_NV: tl.constexpr
    ):
        pid_m = tl.program_id(0)
        block_start = pid_m * BLOCK_M
        offs_m = block_start + tl.arange(0, BLOCK_M)
        mask_m = offs_m < M
        offs_d = tl.arange(0, D)
        q_ptrs = Q + offs_m[:, None] * stride_qm + offs_d[None, :] * stride_qd
        q = tl.load(q_ptrs, mask=mask_m[:, None], other=0.0)
        q = q.to(tl.float32)
        lens_ptrs = row_lens + offs_m * stride_rm
        lens = tl.load(lens_ptrs, mask=mask_m, other=0)
        scores = tl.zeros((BLOCK_M, N), dtype=tl.float32)
        offs_n_full = tl.arange(0, N)
        for d in range(0, D):
            k_d_ptrs = K + offs_n_full * stride_kn + d * stride_kd
            k_d = tl.load(k_d_ptrs, mask=None, other=0.0)
            k_d = k_d.to(tl.float32)
            q_d = q[:, d]
            scores += q_d[:, None] * k_d[None, :] * scale
        mask = lens[:, None] > offs_n_full[None, :]
        scores = tl.where(mask, scores, -1e9)
        p = tl.softmax(scores, axis=1)
        o = tl.zeros((BLOCK_M, Dv), dtype=tl.float32)
        offs_dv = tl.arange(0, Dv)
        for start_n in range(0, N, BLOCK_NV):
            offs_nn = start_n + tl.arange(0, BLOCK_NV)
            mask_nn = offs_nn < N
            p_sub = p[:, offs_nn]
            v_ptrs = V + offs_nn[:, None] * stride_vn + offs_dv[None, :] * stride_vd
            v_sub = tl.load(v_ptrs, mask=mask_nn[:, None], other=0.0)
            v_sub = v_sub.to(tl.float32)
            o_add = tl.dot(p_sub, v_sub)
            o += o_add
        o = o.to(tl.float16)
        o_ptrs = O + offs_m[:, None] * stride_om + offs_dv[None, :] * stride_od
        tl.store(o_ptrs, o, mask=mask_m[:, None])
    BLOCK_M = 64
    BLOCK_NV = 64
    grid = (triton.cdiv(M, BLOCK_M), )
    kernel[grid](
        Q, K, V, row_lens, O,
        stride_qm=Q.stride(0), stride_qd=Q.stride(1),
        stride_kn=K.stride(0), stride_kd=K.stride(1),
        stride_vn=V.stride(0), stride_vd=V.stride(1),
        stride_rm=row_lens.stride(0),
        stride_om=O.stride(0), stride_od=O.stride(1),
        M=M, N=N, D=D, Dv=Dv,
        scale=scale,
        BLOCK_M=BLOCK_M,
        BLOCK_NV=BLOCK_NV
    )
    return O
"""
        return {"code": code}