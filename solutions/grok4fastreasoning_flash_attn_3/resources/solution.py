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
def attn_kernel(
    Q_PTR,
    K_PTR,
    V_PTR,
    O_PTR,
    stride_qz: tl.int32,
    stride_qh: tl.int32,
    stride_qm: tl.int32,
    stride_qd: tl.int32,
    stride_kz: tl.int32,
    stride_kh: tl.int32,
    stride_kn: tl.int32,
    stride_kd: tl.int32,
    stride_vz: tl.int32,
    stride_vh: tl.int32,
    stride_vn: tl.int32,
    stride_vd: tl.int32,
    stride_oz: tl.int32,
    stride_oh: tl.int32,
    stride_om: tl.int32,
    stride_od: tl.int32,
    Z: tl.int32,
    H: tl.int32,
    M: tl.int32,
    N: tl.int32,
    D: tl.int32,
    Dv: tl.int32,
    scale: tl.float32,
    causal: tl.int32,
    num_blocks: tl.int32,
    BLOCK_M: tl.constexpr,
    BLOCK_N: tl.constexpr,
):
    pid_z = tl.program_id(0)
    pid_h = tl.program_id(1)
    pid_i = tl.program_id(2)

    # Q block
    q_offset = pid_z * stride_qz + pid_h * stride_qh + pid_i * BLOCK_M * stride_qm
    q_ptr = tl.make_block_ptr(
        Q_PTR,
        (M, D),
        (stride_qm, stride_qd),
        q_offset,
        (BLOCK_M, D),
        order=(0, 1),
    )
    q_block = tl.load(q_ptr).to(tl.float32)

    # O block ptr
    o_offset = pid_z * stride_oz + pid_h * stride_oh + pid_i * BLOCK_M * stride_om
    o_ptr = tl.make_block_ptr(
        O_PTR,
        (M, Dv),
        (stride_om, stride_od),
        o_offset,
        (BLOCK_M, Dv),
        order=(0, 1),
    )

    # Initialize
    m = tl.full((BLOCK_M,), -1e9, tl.float32)
    l = tl.zeros((BLOCK_M,), tl.float32)
    o = tl.zeros((BLOCK_M, Dv), tl.float32)

    for j in tl.range(0, num_blocks):
        if causal == 1 and j > pid_i:
            continue

        # K block
        k_offset = pid_z * stride_kz + pid_h * stride_kh + j * BLOCK_N * stride_kn
        k_ptr = tl.make_block_ptr(
            K_PTR,
            (N, D),
            (stride_kn, stride_kd),
            k_offset,
            (BLOCK_N, D),
            order=(0, 1),
        )
        k_block = tl.load(k_ptr).to(tl.float32)

        # V block
        v_offset = pid_z * stride_vz + pid_h * stride_vh + j * BLOCK_N * stride_vn
        v_ptr = tl.make_block_ptr(
            V_PTR,
            (N, Dv),
            (stride_vn, stride_vd),
            v_offset,
            (BLOCK_N, Dv),
            order=(0, 1),
        )
        v_block = tl.load(v_ptr).to(tl.float32)

        # Compute S
        s = tl.dot(q_block, tl.trans(k_block)) * scale

        # Causal mask on diagonal block
        do_mask = (causal == 1) and (j == pid_i)
        if do_mask:
            row_idx = tl.arange(0, BLOCK_M)[:, None]
            col_idx = tl.arange(0, BLOCK_N)[None, :]
            mask = col_idx > row_idx
            s = tl.where(mask, -1e9, s)

        # Online softmax
        local_m = tl.max(s, 1)
        p = tl.exp(s - local_m[:, None])
        local_l = tl.sum(p, 1)

        m_new = tl.maximum(m, local_m)
        alpha = tl.exp(m - m_new)
        beta = tl.exp(local_m - m_new)

        # Update l
        l = alpha * l + beta * local_l

        # Update o
        p_scaled = p * beta[:, None]
        o_new = tl.dot(p_scaled, v_block)
        o = alpha[:, None] * o + o_new

        # Update m
        m = m_new

    # Finalize
    o_final = o / l[:, None]
    tl.store(o_ptr, o_final.to(O_PTR.dtype.element_ty))


def flash_attn(Q: torch.Tensor, K: torch.Tensor, V: torch.Tensor, causal: bool = True) -> torch.Tensor:
    Z, H, M, D = Q.shape
    _, _, N, Dv = V.shape
    assert N == M
    assert K.shape == (Z, H, N, D)

    scale = 1.0 / math.sqrt(D)
    O = torch.empty((Z, H, M, Dv), dtype=Q.dtype, device=Q.device)

    if M == 0:
        return O

    BLOCK_M = 64
    BLOCK_N = 64
    num_blocks = M // BLOCK_M
    grid = lambda z, h, nb: (z, h, nb)

    q_strides = Q.stride()
    k_strides = K.stride()
    v_strides = V.stride()
    o_strides = O.stride()

    attn_kernel[grid](  # type: ignore
        Q,
        K,
        V,
        O,
        tl.int32(q_strides[0]),
        tl.int32(q_strides[1]),
        tl.int32(q_strides[2]),
        tl.int32(q_strides[3]),
        tl.int32(k_strides[0]),
        tl.int32(k_strides[1]),
        tl.int32(k_strides[2]),
        tl.int32(k_strides[3]),
        tl.int32(v_strides[0]),
        tl.int32(v_strides[1]),
        tl.int32(v_strides[2]),
        tl.int32(v_strides[3]),
        tl.int32(o_strides[0]),
        tl.int32(o_strides[1]),
        tl.int32(o_strides[2]),
        tl.int32(o_strides[3]),
        Z,
        H,
        M,
        N,
        D,
        Dv,
        tl.float32(scale),
        tl.int32(1 if causal else 0),
        num_blocks,
        BLOCK_M=BLOCK_M,
        BLOCK_N=BLOCK_N,
        num_stages=1,
    )

    return O
"""
        return {"code": code}
