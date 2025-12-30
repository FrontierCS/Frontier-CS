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

def decoding_attn(Q: torch.Tensor, K: torch.Tensor, V: torch.Tensor) -> torch.Tensor:
    Z, H, M, Dq = Q.shape
    if M != 1:
        raise NotImplementedError("Only M=1 is supported")
    _, _, N, Dv = V.shape
    B = Z * H
    device = Q.device
    dtype = Q.dtype
    scale_val = 1.0 / math.sqrt(Dq)
    scale_t = torch.tensor([scale_val], dtype=torch.float32, device=device)

    Q_flat = Q.reshape(B, M, Dq).squeeze(1)  # (B, Dq)
    K_flat = K.reshape(B, N, Dq)  # (B, N, Dq)
    V_flat = V.reshape(B, N, Dv)  # (B, N, Dv)

    scores = torch.empty(B, N, dtype=torch.float32, device=device)

    @triton.jit
    def qk_kernel(
        scores_ptr, Q_ptr, K_ptr, scale_ptr,
        b_stride_Q, b_stride_K, n_stride_K, d_stride_K,
        B_i32, N_i32, Dq_i32
    ):
        BLOCK_N = 256
        pid_b = tl.program_id(0)
        if pid_b >= B_i32:
            return
        pid_n = tl.program_id(1)
        n_start = pid_n * BLOCK_N
        if n_start >= N_i32:
            return

        scale = tl.load(scale_ptr)
        ar_d = tl.arange(0, Dq_i32)
        q_offsets = pid_b * b_stride_Q + ar_d
        q = tl.load(Q_ptr + q_offsets, mask=ar_d < Dq_i32, other=0.0).to(tl.float32)
        q *= scale

        ar_n = tl.arange(0, BLOCK_N)
        n_idx = n_start + ar_n
        mask_n = n_idx < N_i32
        k_offsets = pid_b * b_stride_K + n_idx[:, None] * n_stride_K + ar_d[None, :] * d_stride_K
        k_mask = mask_n[:, None] & (ar_d < Dq_i32)[None, :]
        k_block = tl.load(K_ptr + k_offsets, mask=k_mask, other=0.0).to(tl.float32)

        scores_block = tl.sum(k_block * q[None, :], axis=-1)

        s_offsets = pid_b * N_i32 + n_start + ar_n
        tl.store(scores_ptr + s_offsets, scores_block, mask=mask_n)

    num_n_blocks = math.ceil(N / 256)
    grid_qk = (B, num_n_blocks)
    b_stride_Q = Q_flat.stride(0)
    b_stride_K = K_flat.stride(0)
    n_stride_K = K_flat.stride(1)
    d_stride_K = K_flat.stride(2)
    qk_kernel[grid_qk](
        scores.data_ptr(),
        Q_flat.data_ptr(),
        K_flat.data_ptr(),
        scale_t.data_ptr(),
        b_stride_Q, b_stride_K, n_stride_K, d_stride_K,
        tl.int32(B), tl.int32(N), tl.int32(Dq)
    )

    probs = torch.softmax(scores, dim=-1)

    output_flat = torch.empty(B, Dv, dtype=torch.float32, device=device)

    @triton.jit
    def ov_kernel(
        o_ptr, probs_ptr, V_ptr,
        b_stride_o, b_stride_probs, n_stride_probs,
        b_stride_V, n_stride_V, d_stride_V,
        B_i32, N_i32, Dv_i32
    ):
        BLOCK_N = 256
        BLOCK_DV = 64
        pid_b = tl.program_id(0)
        if pid_b >= B_i32:
            return
        pid_d = tl.program_id(1)
        d_start = pid_d * BLOCK_DV
        if d_start >= Dv_i32:
            return
        d_end = min(d_start + BLOCK_DV, Dv_i32)

        acc = tl.zeros([BLOCK_DV], dtype=tl.float32)

        for start_n in range(0, N_i32, BLOCK_N):
            ar_n = tl.arange(0, BLOCK_N)
            n_idx = start_n + ar_n
            mask_n = n_idx < N_i32
            p_offsets = pid_b * b_stride_probs + n_idx
            p_block = tl.load(probs_ptr + p_offsets, mask=mask_n, other=0.0).to(tl.float32)

            ar_d = tl.arange(0, BLOCK_DV)
            v_offsets = pid_b * b_stride_V + n_idx[:, None] * n_stride_V + (d_start + ar_d)[None, :] * d_stride_V
            v_mask = mask_n[:, None] & (ar_d < d_end - d_start)[None, :]
            v_block = tl.load(V_ptr + v_offsets, mask=v_mask, other=0.0).to(tl.float32)

            acc += tl.sum(p_block[:, None] * v_block, axis=0)

        o_offsets = pid_b * b_stride_o + d_start + ar_d
        o_mask = ar_d < d_end - d_start
        tl.store(o_ptr + o_offsets, acc, mask=o_mask)

    num_d_blocks = math.ceil(Dv / 64)
    grid_ov = (B, num_d_blocks)
    b_stride_o = output_flat.stride(0)
    b_stride_probs = probs.stride(0)
    n_stride_probs = probs.stride(1)
    b_stride_V = V_flat.stride(0)
    n_stride_V = V_flat.stride(1)
    d_stride_V = V_flat.stride(2)
    ov_kernel[grid_ov](
        output_flat.data_ptr(),
        probs.data_ptr(),
        V_flat.data_ptr(),
        b_stride_o, b_stride_probs, n_stride_probs,
        b_stride_V, n_stride_V, d_stride_V,
        tl.int32(B), tl.int32(N), tl.int32(Dv)
    )

    output_flat = output_flat.to(dtype)
    output = output_flat.view(Z, H, 1, Dv)
    return output
"""
        return {"code": code}