import torch
import triton
import triton.language as tl
import math

@triton.jit
def fwd_kernel(
    Q, K, V, Output, row_lens,
    s_qm, s_qd, s_km, s_kd, s_vm, s_vd, s_rm, s_om, s_od,
    M, N, D, Dv, scale,
    BLOCK_M: tl.constexpr,
    BLOCK_N: tl.constexpr,
    BLOCK_DV: tl.constexpr
):
    pid = tl.program_id(0)
    block_start = pid * BLOCK_M
    offsets_m = block_start + tl.arange(0, BLOCK_M)
    mask_m = offsets_m < M
    d_offsets = tl.arange(0, D)
    q_ptrs = Q + offsets_m[:, None] * s_qm + d_offsets[None, :] * s_qd
    Qb = tl.load(q_ptrs, mask=mask_m[:, None], other=0.0).to(tl.float32)
    lens_ptrs = row_lens + offsets_m * s_rm
    lens_block = tl.load(lens_ptrs, mask=mask_m, other=0).to(tl.int32)
    row_max = tl.full([BLOCK_M], -1e9, dtype=tl.float32)
    n_arange = tl.arange(0, BLOCK_N)
    for start_n in range(0, N, BLOCK_N):
        offsets_n = start_n + n_arange
        mask_n = offsets_n < N
        k_ptrs = K + offsets_n[:, None] * s_km + d_offsets[None, :] * s_kd
        Kb = tl.load(k_ptrs, mask=mask_n[:, None], other=0.0).to(tl.float32)
        scores = tl.dot(Qb, Kb, trans_b=True) * scale
        attn_mask = (start_n + n_arange[None, :]) < lens_block[:, None]
        scores_masked = tl.where(attn_mask, scores, -1e9)
        partial_max = tl.max(scores_masked, axis=1)
        row_max = tl.maximum(row_max, partial_max)
    row_sum = tl.zeros([BLOCK_M], dtype=tl.float32)
    dv_offsets = tl.arange(0, BLOCK_DV)
    oacc = tl.zeros([BLOCK_M, BLOCK_DV], dtype=tl.float32)
    for start_n in range(0, N, BLOCK_N):
        offsets_n = start_n + n_arange
        mask_n = offsets_n < N
        k_ptrs = K + offsets_n[:, None] * s_km + d_offsets[None, :] * s_kd
        Kb = tl.load(k_ptrs, mask=mask_n[:, None], other=0.0).to(tl.float32)
        scores = tl.dot(Qb, Kb, trans_b=True) * scale
        attn_mask = (start_n + n_arange[None, :]) < lens_block[:, None]
        m = scores - row_max[:, None]
        p = tl.where(attn_mask, tl.exp(m), 0.0)
        row_sum += tl.sum(p, axis=1)
        v_ptrs = V + offsets_n[:, None] * s_vm + dv_offsets[None, :] * s_vd
        Vb = tl.load(v_ptrs, mask=mask_n[:, None], other=0.0).to(tl.float32)
        partial_o = tl.dot(p, Vb)
        oacc += partial_o
    o = tl.where(row_sum[:, None] > 0.0, oacc / row_sum[:, None], 0.0)
    o_ptrs = Output + offsets_m[:, None] * s_om + dv_offsets[None, :] * s_od
    tl.store(o_ptrs, o.to(tl.float16), mask=mask_m[:, None])

def ragged_attn(Q: torch.Tensor, K: torch.Tensor, V: torch.Tensor, row_lens: torch.Tensor) -> torch.Tensor:
    M, D = Q.shape
    N, _ = K.shape
    _, Dv = V.shape
    scale = 1.0 / math.sqrt(D)
    output = torch.empty((M, Dv), dtype=Q.dtype, device=Q.device)
    BLOCK_M = 128
    BLOCK_N = 64
    BLOCK_DV = Dv
    es = Q.element_size()
    s_qm = Q.stride(0) // es
    s_qd = Q.stride(1) // es
    s_km = K.stride(0) // es
    s_kd = K.stride(1) // es
    s_vm = V.stride(0) // es
    s_vd = V.stride(1) // es
    es_r = row_lens.element_size()
    s_rm = row_lens.stride(0) // es_r
    s_om = output.stride(0) // es
    s_od = output.stride(1) // es
    grid = (triton.cdiv(M, BLOCK_M), )
    fwd_kernel[grid](
        Q, K, V, output, row_lens,
        s_qm, s_qd, s_km, s_kd, s_vm, s_vd, s_rm, s_om, s_od,
        M, N, D, Dv, scale,
        BLOCK_M=BLOCK_M, BLOCK_N=BLOCK_N, BLOCK_DV=BLOCK_DV,
        num_stages=4
    )
    return output

class Solution:
    def solve(self, spec_path: str = None) -> dict:
        return {"code": "import torch\nimport triton\nimport triton.language as tl\nimport math\n\n" + inspect.getsource(fwd_kernel) + "\n" + inspect.getsource(ragged_attn)}