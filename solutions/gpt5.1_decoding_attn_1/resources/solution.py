import torch
import triton
import triton.language as tl

kernel_code = r'''
import torch
import triton
import triton.language as tl


@triton.autotune(
    configs=[
        triton.Config({"BLOCK_N": 64, "BLOCK_DMODEL": 64, "BLOCK_DVALUE": 64}, num_warps=4),
        triton.Config({"BLOCK_N": 128, "BLOCK_DMODEL": 64, "BLOCK_DVALUE": 64}, num_warps=4),
        triton.Config({"BLOCK_N": 256, "BLOCK_DMODEL": 64, "BLOCK_DVALUE": 64}, num_warps=8),
    ],
    key=["N"],
)
@triton.jit
def decoding_attn_kernel(
    Q_ptr,
    K_ptr,
    V_ptr,
    Out_ptr,
    stride_qz,
    stride_qh,
    stride_qm,
    stride_qd,
    stride_kz,
    stride_kh,
    stride_kn,
    stride_kd,
    stride_vz,
    stride_vh,
    stride_vn,
    stride_vd,
    stride_oz,
    stride_oh,
    stride_om,
    stride_od,
    Z,
    H,
    M,
    N,
    Dq,
    Dv,
    sm_scale,
    BLOCK_N: tl.constexpr,
    BLOCK_DMODEL: tl.constexpr,
    BLOCK_DVALUE: tl.constexpr,
):
    token_id = tl.program_id(0)

    tokens_per_z = H * M
    z = token_id // tokens_per_z
    hm = token_id % tokens_per_z
    h = hm // M
    m = hm % M

    if z >= Z:
        return

    q_row_ptr = Q_ptr + z * stride_qz + h * stride_qh + m * stride_qm
    k_head_ptr = K_ptr + z * stride_kz + h * stride_kh
    v_head_ptr = V_ptr + z * stride_vz + h * stride_vh
    o_row_ptr = Out_ptr + z * stride_oz + h * stride_oh + m * stride_om

    d_model_offsets = tl.arange(0, BLOCK_DMODEL)
    q_ptrs = q_row_ptr + d_model_offsets * stride_qd
    q = tl.load(q_ptrs, mask=d_model_offsets < Dq, other=0.0).to(tl.float32)
    q = q * sm_scale

    m_i = tl.full((), -1.0e9, dtype=tl.float32)
    l_i = tl.zeros((), dtype=tl.float32)
    v_d_offsets = tl.arange(0, BLOCK_DVALUE)
    acc = tl.zeros((BLOCK_DVALUE,), dtype=tl.float32)

    n_range = tl.arange(0, BLOCK_N)
    for start_n in range(0, N, BLOCK_N):
        k_idx = start_n + n_range
        kv_mask = k_idx < N

        k_ptrs = (
            k_head_ptr
            + k_idx[:, None] * stride_kn
            + d_model_offsets[None, :] * stride_kd
        )
        k_block = tl.load(
            k_ptrs,
            mask=kv_mask[:, None] & (d_model_offsets[None, :] < Dq),
            other=0.0,
        ).to(tl.float32)

        qk = tl.dot(k_block, q)
        qk = tl.where(kv_mask, qk, -1.0e9)

        m_ij = tl.max(qk, axis=0)
        p = tl.exp(qk - m_ij)
        l_ij = tl.sum(p, axis=0)

        v_ptrs = (
            v_head_ptr
            + k_idx[:, None] * stride_vn
            + v_d_offsets[None, :] * stride_vd
        )
        v_block = tl.load(
            v_ptrs,
            mask=kv_mask[:, None] & (v_d_offsets[None, :] < Dv),
            other=0.0,
        ).to(tl.float32)

        acc_ij = tl.dot(p, v_block)

        m_i_new = tl.maximum(m_i, m_ij)
        alpha = tl.exp(m_i - m_i_new)
        beta = tl.exp(m_ij - m_i_new)

        l_i = alpha * l_i + beta * l_ij
        acc = alpha * acc + beta * acc_ij
        m_i = m_i_new

    inv_l_i = 1.0 / (l_i + 1e-6)
    o = acc * inv_l_i
    o = o.to(tl.float16)

    o_ptrs = o_row_ptr + v_d_offsets * stride_od
    tl.store(o_ptrs, o, mask=v_d_offsets < Dv)


def decoding_attn(Q: torch.Tensor, K: torch.Tensor, V: torch.Tensor) -> torch.Tensor:
    if Q.device.type != "cuda":
        raise ValueError("Q must be a CUDA tensor")
    if K.device != Q.device or V.device != Q.device:
        raise ValueError("K and V must be on the same device as Q")
    if Q.dtype != torch.float16 or K.dtype != torch.float16 or V.dtype != torch.float16:
        raise TypeError("Q, K, V must be float16 tensors")

    if Q.ndim != 4 or K.ndim != 4 or V.ndim != 4:
        raise ValueError("Q, K, V must be 4D tensors (Z, H, M/N, D)")

    Z, H, M, Dq = Q.shape
    Zk, Hk, N, Dk = K.shape
    Zv, Hv, Nv, Dv = V.shape

    if Z != Zk or Z != Zv:
        raise ValueError("Batch dimension Z must be the same for Q, K, V")
    if H != Hk or H != Hv:
        raise ValueError("Head dimension H must be the same for Q, K, V")
    if Dq != Dk:
        raise ValueError("Dq must equal K's last dimension")
    if N != Nv:
        raise ValueError("Sequence length N must match between K and V")

    out = torch.empty((Z, H, M, Dv), device=Q.device, dtype=torch.float16)

    stride_qz, stride_qh, stride_qm, stride_qd = Q.stride()
    stride_kz, stride_kh, stride_kn, stride_kd = K.stride()
    stride_vz, stride_vh, stride_vn, stride_vd = V.stride()
    stride_oz, stride_oh, stride_om, stride_od = out.stride()

    sm_scale = 1.0 / (Dq ** 0.5)

    grid = (Z * H * M,)

    decoding_attn_kernel[grid](
        Q,
        K,
        V,
        out,
        stride_qz,
        stride_qh,
        stride_qm,
        stride_qd,
        stride_kz,
        stride_kh,
        stride_kn,
        stride_kd,
        stride_vz,
        stride_vh,
        stride_vn,
        stride_vd,
        stride_oz,
        stride_oh,
        stride_om,
        stride_od,
        Z,
        H,
        M,
        N,
        Dq,
        Dv,
        sm_scale,
    )

    return out
'''

exec(kernel_code, globals())


class Solution:
    def solve(self, spec_path: str = None) -> dict:
        return {"code": kernel_code}
