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

@triton.jit
def kernel(
    q_ptr, k_ptr, v_ptr, o_ptr,
    q_stride_z, q_stride_h, q_stride_m, q_stride_d,
    k_stride_z, k_stride_h, k_stride_n, k_stride_d,
    v_stride_z, v_stride_h, v_stride_n, v_stride_d,
    o_stride_z, o_stride_h, o_stride_m, o_stride_d,
    Z: tl.int32, H: tl.int32, M: tl.int32, N: tl.int32,
    BLOCK_N: tl.constexpr,
    scale: tl.float32
):
    pid_z = tl.program_id(0)
    pid_h = tl.program_id(1)
    pid_m = tl.program_id(2)
    if pid_z >= Z or pid_h >= H or pid_m >= M:
        return

    HEAD_DIM = 64

    q_offset = (pid_z * q_stride_z + pid_h * q_stride_h + pid_m * q_stride_m).to(tl.int64)
    q_ptr = q_ptr + q_offset
    q_idx = tl.arange(0, HEAD_DIM).to(tl.int64) * q_stride_d
    q = tl.load(q_ptr + q_idx, mask=tl.arange(0, HEAD_DIM) < HEAD_DIM).to(tl.float32)

    kv_offset_k = (pid_z * k_stride_z + pid_h * k_stride_h).to(tl.int64)
    k_base = k_ptr + kv_offset_k
    kv_offset_v = (pid_z * v_stride_z + pid_h * v_stride_h).to(tl.int64)
    v_base = v_ptr + kv_offset_v

    # first pass: compute max
    max_val = tl.float32(-1e4)
    for start_n in range(0, N, BLOCK_N):
        n_idx = tl.arange(0, BLOCK_N).to(tl.int32)
        mask_n = n_idx < (N - start_n)
        d_idx = tl.arange(0, HEAD_DIM).to(tl.int32)
        k_offs = (n_idx.to(tl.int64)[:, None] * k_stride_n) + (d_idx.to(tl.int64)[None, :] * k_stride_d)
        k_ptr_b = k_base + (start_n * k_stride_n) + k_offs
        mask_k = mask_n[:, None] & (d_idx[None, :] < HEAD_DIM)
        k = tl.load(k_ptr_b, mask=mask_k, other=0.0).to(tl.float32)

        scores = tl.sum(k * q[None, :], axis=1) * scale
        max_val = tl.maximum(max_val, tl.max(tl.where(mask_n, scores, tl.float32(-1e4))))

    # second pass
    sum_exp = tl.float32(0.0)
    out = tl.zeros((HEAD_DIM,), dtype=tl.float32)
    for start_n in range(0, N, BLOCK_N):
        n_idx = tl.arange(0, BLOCK_N).to(tl.int32)
        mask_n = n_idx < (N - start_n)
        d_idx = tl.arange(0, HEAD_DIM).to(tl.int32)
        # k
        k_offs = (n_idx.to(tl.int64)[:, None] * k_stride_n) + (d_idx.to(tl.int64)[None, :] * k_stride_d)
        k_ptr_b = k_base + (start_n * k_stride_n) + k_offs
        mask_k = mask_n[:, None] & (d_idx[None, :] < HEAD_DIM)
        k = tl.load(k_ptr_b, mask=mask_k, other=0.0).to(tl.float32)
        scores = tl.sum(k * q[None, :], axis=1) * scale
        exp_scores = tl.exp(scores - max_val)
        exp_scores = tl.where(mask_n, exp_scores, 0.0)
        sum_exp += tl.sum(exp_scores)
        # v
        v_offs = (n_idx.to(tl.int64)[:, None] * v_stride_n) + (d_idx.to(tl.int64)[None, :] * v_stride_d)
        v_ptr_b = v_base + (start_n * v_stride_n) + v_offs
        mask_v = mask_n[:, None] & (d_idx[None, :] < HEAD_DIM)
        v = tl.load(v_ptr_b, mask=mask_v, other=0.0).to(tl.float32)
        out += tl.sum(exp_scores[:, None] * v, axis=0)

    out /= sum_exp

    # store
    o_offset = (pid_z * o_stride_z + pid_h * o_stride_h + pid_m * o_stride_m).to(tl.int64)
    o_ptr += o_offset
    o_idx = tl.arange(0, HEAD_DIM).to(tl.int64) * o_stride_d
    tl.store(o_ptr + o_idx, out.to(tl.float16), mask=tl.arange(0, HEAD_DIM) < HEAD_DIM)

configs = [
    triton.Config({'BLOCK_N': bn}, num_stages=4, num_warps=8)
    for bn in [128, 256, 512, 1024, 2048]
]

@triton.autotune(configs, key=['N'])
def decoding_attn_triton(Q, K, V, output):
    Z, H, M, Dq = Q.shape
    assert Dq == 64
    _, _, N, Dv = V.shape
    assert Dv == 64 and N > 0
    scale = tl.float32(1.0 / math.sqrt(64))
    q_strides_b = [s * Q.element_size() for s in Q.stride()]
    k_strides_b = [s * K.element_size() for s in K.stride()]
    v_strides_b = [s * V.element_size() for s in V.stride()]
    o_strides_b = [s * output.element_size() for s in output.stride()]
    grid = (Z, H, M)
    kernel[grid](
        Q.data_ptr(), K.data_ptr(), V.data_ptr(), output.data_ptr(),
        q_strides_b[0], q_strides_b[1], q_strides_b[2], q_strides_b[3],
        k_strides_b[0], k_strides_b[1], k_strides_b[2], k_strides_b[3],
        v_strides_b[0], v_strides_b[1], v_strides_b[2], v_strides_b[3],
        o_strides_b[0], o_strides_b[1], o_strides_b[2], o_strides_b[3],
        tl.int32(Z), tl.int32(H), tl.int32(M), tl.int32(N),
        scale=scale,
    )

def decoding_attn(Q: torch.Tensor, K: torch.Tensor, V: torch.Tensor) -> torch.Tensor:
    Z, H, M, Dq = Q.shape
    assert Dq == 64
    _, _, N, Dv = V.shape
    assert Dv == 64
    output = torch.empty(Z, H, M, Dv, dtype=Q.dtype, device=Q.device)
    if N == 0 or M == 0:
        return output
    decoding_attn_triton(Q, K, V, output)
    return output
"""
        return {"code": code}
