class Solution:
    def solve(self, spec_path: str = None) -> dict:
        code = """
import torch
import triton
import triton.language as tl

@triton.autotune(
    configs=[
        triton.Config({'BLOCK_N': 64}, num_stages=1, num_warps=2),
        triton.Config({'BLOCK_N': 128}, num_stages=3, num_warps=4),
        triton.Config({'BLOCK_N': 256}, num_stages=4, num_warps=4),
        triton.Config({'BLOCK_N': 512}, num_stages=2, num_warps=8),
    ],
    key=['N', 'D_Q', 'D_V'],
)
@triton.jit
def decoding_attn_kernel(
    Q_PTR,
    Q_STRIDE_Z, Q_STRIDE_H, Q_STRIDE_M, Q_STRIDE_D,
    K_PTR,
    K_STRIDE_Z, K_STRIDE_H, K_STRIDE_N, K_STRIDE_D,
    V_PTR,
    V_STRIDE_Z, V_STRIDE_H, V_STRIDE_N, V_STRIDE_V,
    O_PTR,
    O_STRIDE_Z, O_STRIDE_H, O_STRIDE_M, O_STRIDE_V,
    Z: tl.int32,
    H: tl.int32,
    M: tl.int32,
    N: tl.int32,
    D_Q: tl.int32,
    D_V: tl.int32,
    BLOCK_N: tl.constexpr,
):
    pid_z = tl.program_id(0)
    pid_h = tl.program_id(1)
    pid_m = tl.program_id(2)
    if pid_z >= Z or pid_h >= H or pid_m >= M:
        return

    # Load Q
    q_offset = pid_z * Q_STRIDE_Z + pid_h * Q_STRIDE_H + pid_m * Q_STRIDE_M
    q_ptr = Q_PTR + q_offset
    ar_d = tl.arange(0, D_Q)
    q = tl.load(q_ptr + ar_d * Q_STRIDE_D, mask=ar_d < D_Q, other=tl.float16(0)).to(tl.float32)
    q_scale = tl.sqrt(tl.float32(D_Q))
    q = q / q_scale

    # First pass: compute m = max(scores)
    m = tl.float32(-10000.0)
    start = tl.int32(0)
    while start < N:
        end = tl.minimum(start + BLOCK_N, N)
        n_len = end - start
        valid_mask = tl.arange(0, BLOCK_N) < n_len
        n_idx = start + tl.arange(0, BLOCK_N)
        k_offset = pid_z * K_STRIDE_Z + pid_h * K_STRIDE_H + n_idx * K_STRIDE_N
        k_ptr = K_PTR + k_offset
        ar_dk = tl.arange(0, D_Q)
        k = tl.load(k_ptr + ar_dk[None, :] * K_STRIDE_D, mask=valid_mask[:, None], other=tl.float16(0)).to(tl.float32)
        dots = tl.sum(k * q[None, :], axis=1)
        dots_masked = tl.where(valid_mask, dots, tl.float32(-10000.0))
        block_max = tl.max(dots_masked, axis=0)
        m = tl.maximum(m, block_max)
        start += BLOCK_N

    # Second pass: compute denom and num
    denom = tl.float32(0.0)
    num = tl.zeros((D_V,), dtype=tl.float32)
    start = tl.int32(0)
    while start < N:
        end = tl.minimum(start + BLOCK_N, N)
        n_len = end - start
        valid_mask = tl.arange(0, BLOCK_N) < n_len
        n_idx = start + tl.arange(0, BLOCK_N)
        # Load K
        k_offset = pid_z * K_STRIDE_Z + pid_h * K_STRIDE_H + n_idx * K_STRIDE_N
        k_ptr = K_PTR + k_offset
        ar_dk = tl.arange(0, D_Q)
        k = tl.load(k_ptr + ar_dk[None, :] * K_STRIDE_D, mask=valid_mask[:, None], other=tl.float16(0)).to(tl.float32)
        dots = tl.sum(k * q[None, :], axis=1)
        # Load V
        v_offset = pid_z * V_STRIDE_Z + pid_h * V_STRIDE_H + n_idx * V_STRIDE_N
        v_ptr = V_PTR + v_offset
        ar_dv = tl.arange(0, D_V)
        v = tl.load(v_ptr + ar_dv[None, :] * V_STRIDE_V, mask=valid_mask[:, None], other=tl.float16(0)).to(tl.float32)
        e = tl.exp(dots - m)
        e_masked = tl.where(valid_mask, e, tl.float32(0.0))
        denom += tl.sum(e_masked)
        num += tl.sum(e_masked[:, None] * v, axis=0)
        start += BLOCK_N

    # Compute and store output
    out_vec = num / denom
    o_offset = pid_z * O_STRIDE_Z + pid_h * O_STRIDE_H + pid_m * O_STRIDE_M
    o_ptr = O_PTR + o_offset
    ar_dv = tl.arange(0, D_V)
    tl.store(o_ptr + ar_dv * O_STRIDE_V, out_vec.to(tl.float16), mask=ar_dv < D_V)


def decoding_attn(Q: torch.Tensor, K: torch.Tensor, V: torch.Tensor) -> torch.Tensor:
    Z, H, M, D_Q = Q.shape
    _, _, N, D_V = V.shape
    assert K.shape[0] == Z and K.shape[1] == H and K.shape[3] == D_Q
    assert V.shape[0] == Z and V.shape[1] == H
    output = torch.empty((Z, H, M, D_V), dtype=Q.dtype, device=Q.device)
    if M == 0 or N == 0:
        return output
    q_strides = Q.stride()
    k_strides = K.stride()
    v_strides = V.stride()
    o_strides = output.stride()
    grid = (Z, H, M)
    decoding_attn_kernel[grid](
        Q.data_ptr(),
        tl.int32(q_strides[0]), tl.int32(q_strides[1]), tl.int32(q_strides[2]), tl.int32(q_strides[3]),
        K.data_ptr(),
        tl.int32(k_strides[0]), tl.int32(k_strides[1]), tl.int32(k_strides[2]), tl.int32(k_strides[3]),
        V.data_ptr(),
        tl.int32(v_strides[0]), tl.int32(v_strides[1]), tl.int32(v_strides[2]), tl.int32(v_strides[3]),
        output.data_ptr(),
        tl.int32(o_strides[0]), tl.int32(o_strides[1]), tl.int32(o_strides[2]), tl.int32(o_strides[3]),
        tl.int32(Z), tl.int32(H), tl.int32(M), tl.int32(N), tl.int32(D_Q), tl.int32(D_V),
    )
    return output
"""
        return {"code": code}