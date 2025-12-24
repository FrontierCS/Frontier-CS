import torch
import triton
import triton.language as tl
import math


@triton.jit
def gdpa_fwd_kernel(
    Q_ptr, K_ptr, V_ptr, GQ_ptr, GK_ptr, O_ptr,
    stride_qz, stride_qh, stride_qm, stride_qd,
    stride_kz, stride_kh, stride_kn, stride_kd,
    stride_vz, stride_vh, stride_vn, stride_vd,
    stride_gqz, stride_gqh, stride_gqm, stride_gqd,
    stride_gkz, stride_gkh, stride_gkn, stride_gkd,
    stride_oz, stride_oh, stride_om, stride_od,
    Z, H, M, N, Dq, Dv,
    sm_scale,
    BLOCK_M: tl.constexpr, BLOCK_N: tl.constexpr,
):
    pid_zh = tl.program_id(0)
    pid_m = tl.program_id(1)

    z = pid_zh // H
    h = pid_zh % H

    offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
    offs_dq = tl.arange(0, BLOCK_DQ)
    offs_dn = tl.arange(0, BLOCK_N)
    offs_dv = tl.arange(0, BLOCK_DV)

    # Load Q and GQ for this block [BM, Dq]
    # Support arbitrary Dq and Dv by defining them as constexpr maximums via meta-parameters
    # Here, we tie BLOCK_DQ to Dq and BLOCK_DV to Dv at launch.
    q_ptrs = Q_ptr + z * stride_qz + h * stride_qh + (offs_m[:, None] * stride_qm) + (offs_dq[None, :] * stride_qd)
    gq_ptrs = GQ_ptr + z * stride_gqz + h * stride_gqh + (offs_m[:, None] * stride_gqm) + (offs_dq[None, :] * stride_gqd)
    mask_q = (offs_m[:, None] < M) & (offs_dq[None, :] < Dq)

    q = tl.load(q_ptrs, mask=mask_q, other=0.0)
    gq = tl.load(gq_ptrs, mask=mask_q, other=0.0)

    # Apply gating: sigmoid(GQ) * Q
    gq32 = gq.to(tl.float32)
    q32 = q.to(tl.float32)
    sig_gq = 1.0 / (1.0 + tl.exp(-gq32))
    qg = (q32 * sig_gq).to(tl.float16)

    # Initialize accumulators
    m_i = tl.full([BLOCK_M], -float("inf"), dtype=tl.float32)
    l_i = tl.zeros([BLOCK_M], dtype=tl.float32)
    acc = tl.zeros([BLOCK_M, BLOCK_DV], dtype=tl.float32)

    # Loop over K/V blocks along N
    for start_n in range(0, N, BLOCK_N):
        offs_n = start_n + offs_dn
        # Load K and GK [BN, Dq]
        k_ptrs = K_ptr + z * stride_kz + h * stride_kh + (offs_n[:, None] * stride_kn) + (offs_dq[None, :] * stride_kd)
        gk_ptrs = GK_ptr + z * stride_gkz + h * stride_gkh + (offs_n[:, None] * stride_gkn) + (offs_dq[None, :] * stride_gkd)
        mask_k = (offs_n[:, None] < N) & (offs_dq[None, :] < Dq)
        k = tl.load(k_ptrs, mask=mask_k, other=0.0)
        gk = tl.load(gk_ptrs, mask=mask_k, other=0.0)

        # Apply gating: sigmoid(GK) * K
        gk32 = gk.to(tl.float32)
        k32 = k.to(tl.float32)
        sig_gk = 1.0 / (1.0 + tl.exp(-gk32))
        kg = (k32 * sig_gk).to(tl.float16)

        # Compute logits [BM, BN]
        qk = tl.dot(qg, tl.trans(kg)) * sm_scale
        # Mask out-of-bounds columns
        mask_bn = offs_n[None, :] < N
        qk = tl.where(mask_bn, qk, -float("inf"))

        # Compute numerically stable softmax update
        m_ij = tl.max(qk, axis=1)
        m_new = tl.maximum(m_i, m_ij)
        p = tl.exp(qk - m_new[:, None])
        # For V multiply, we will cast p to fp16; keep p32 for l_i
        p32 = p
        alpha = tl.exp(m_i - m_new)
        l_new = l_i * alpha + tl.sum(p32, axis=1)

        # Load V block [BN, Dv]
        v_ptrs = V_ptr + z * stride_vz + h * stride_vh + (offs_n[:, None] * stride_vn) + (offs_dv[None, :] * stride_vd)
        mask_v = (offs_n[:, None] < N) & (offs_dv[None, :] < Dv)
        v = tl.load(v_ptrs, mask=mask_v, other=0.0)

        # Update acc: acc = acc * alpha + p @ v
        # Cast p to fp16 for tensor core friendly dot with fp16 V
        p16 = p32.to(tl.float16)
        acc_update = tl.dot(p16, v)
        acc = acc * alpha[:, None] + acc_update

        m_i = m_new
        l_i = l_new

    # Normalize
    o = acc / l_i[:, None]

    # Store result
    o_ptrs = O_ptr + z * stride_oz + h * stride_oh + (offs_m[:, None] * stride_om) + (offs_dv[None, :] * stride_od)
    mask_o = (offs_m[:, None] < M) & (offs_dv[None, :] < Dv)
    tl.store(o_ptrs, o.to(tl.float16), mask=mask_o)


def gdpa_attn(Q: torch.Tensor, K: torch.Tensor, V: torch.Tensor, GQ: torch.Tensor, GK: torch.Tensor) -> torch.Tensor:
    assert Q.device.type == "cuda", "Q must be on CUDA device"
    assert K.device == Q.device and V.device == Q.device and GQ.device == Q.device and GK.device == Q.device
    assert Q.dtype == torch.float16 and K.dtype == torch.float16 and V.dtype == torch.float16
    assert GQ.dtype == torch.float16 and GK.dtype == torch.float16
    assert Q.dim() == 4 and K.dim() == 4 and V.dim() == 4 and GQ.dim() == 4 and GK.dim() == 4
    Z, H, M, Dq = Q.shape
    Zk, Hk, N, Dqk = K.shape
    Zv, Hv, Nv, Dv = V.shape
    Zgq, Hgq, Mgq, Dqg = GQ.shape
    Zgk, Hgk, Ngk, Dqkg = GK.shape
    assert Z == Zk == Zv == Zgq == Zgk
    assert H == Hk == Hv == Hgq == Hgk
    assert M == Mgq
    assert N == Nv == Ngk
    assert Dq == Dqk == Dqg == Dqkg
    assert M == N, "GDPA attention assumes N == M"

    O = torch.empty((Z, H, M, Dv), device=Q.device, dtype=torch.float16)

    # Strides
    stride_qz, stride_qh, stride_qm, stride_qd = Q.stride()
    stride_kz, stride_kh, stride_kn, stride_kd = K.stride()
    stride_vz, stride_vh, stride_vn, stride_vd = V.stride()
    stride_gqz, stride_gqh, stride_gqm, stride_gqd = GQ.stride()
    stride_gkz, stride_gkh, stride_gkn, stride_gkd = GK.stride()
    stride_oz, stride_oh, stride_om, stride_od = O.stride()

    # Choose block sizes
    BLOCK_M = 64
    BLOCK_N = 64
    # Set BLOCK_DQ and BLOCK_DV to actual dims for simplicity
    # Triton requires them as constexpr: we will set via globals at launch using kwargs
    meta = dict()
    meta['BLOCK_M'] = BLOCK_M
    meta['BLOCK_N'] = BLOCK_N

    # dynamic constexprs for K/V dims
    # Trick: define them as Python globals readable by kernel as constexpr through defaults via partial specialization.
    # Alternatively, we can use tl.constexpr through meta-parameters.
    # We'll supply them via Triton meta by monkey patching names.
    # However, Triton requires explicit constants in code; use static maxima and rely on masks.
    # Here, we bind BLOCK_DQ and BLOCK_DV in kernel launch via additional specialization kwargs.
    # We reuse the function's signature expecting these globals exist; set them in meta to proper ints.
    meta['BLOCK_DQ'] = Dq
    meta['BLOCK_DV'] = Dv

    # Attach constexprs into kernel call via kwargs
    grid = (Z * H, triton.cdiv(M, BLOCK_M))

    sm_scale = 1.0 / math.sqrt(Dq)

    gdpa_fwd_kernel[grid](
        Q, K, V, GQ, GK, O,
        stride_qz, stride_qh, stride_qm, stride_qd,
        stride_kz, stride_kh, stride_kn, stride_kd,
        stride_vz, stride_vh, stride_vn, stride_vd,
        stride_gqz, stride_gqh, stride_gqm, stride_gqd,
        stride_gkz, stride_gkh, stride_gkn, stride_gkd,
        stride_oz, stride_oh, stride_om, stride_od,
        Z, H, M, N, Dq, Dv,
        sm_scale,
        BLOCK_M=BLOCK_M, BLOCK_N=BLOCK_N,
        BLOCK_DQ=Dq, BLOCK_DV=Dv,
        num_warps=4, num_stages=2
    )

    return O


class Solution:
    def solve(self, spec_path: str = None) -> dict:
        code = '''
import torch
import triton
import triton.language as tl
import math


@triton.jit
def gdpa_fwd_kernel(
    Q_ptr, K_ptr, V_ptr, GQ_ptr, GK_ptr, O_ptr,
    stride_qz, stride_qh, stride_qm, stride_qd,
    stride_kz, stride_kh, stride_kn, stride_kd,
    stride_vz, stride_vh, stride_vn, stride_vd,
    stride_gqz, stride_gqh, stride_gqm, stride_gqd,
    stride_gkz, stride_gkh, stride_gkn, stride_gkd,
    stride_oz, stride_oh, stride_om, stride_od,
    Z, H, M, N, Dq, Dv,
    sm_scale,
    BLOCK_M: tl.constexpr, BLOCK_N: tl.constexpr,
    BLOCK_DQ: tl.constexpr, BLOCK_DV: tl.constexpr,
):
    pid_zh = tl.program_id(0)
    pid_m = tl.program_id(1)

    z = pid_zh // H
    h = pid_zh % H

    offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
    offs_dq = tl.arange(0, BLOCK_DQ)
    offs_dn = tl.arange(0, BLOCK_N)
    offs_dv = tl.arange(0, BLOCK_DV)

    # Load Q and GQ for this block [BM, Dq]
    q_ptrs = Q_ptr + z * stride_qz + h * stride_qh + (offs_m[:, None] * stride_qm) + (offs_dq[None, :] * stride_qd)
    gq_ptrs = GQ_ptr + z * stride_gqz + h * stride_gqh + (offs_m[:, None] * stride_gqm) + (offs_dq[None, :] * stride_gqd)
    mask_q = (offs_m[:, None] < M) & (offs_dq[None, :] < Dq)

    q = tl.load(q_ptrs, mask=mask_q, other=0.0)
    gq = tl.load(gq_ptrs, mask=mask_q, other=0.0)

    # Apply gating: sigmoid(GQ) * Q
    gq32 = gq.to(tl.float32)
    q32 = q.to(tl.float32)
    sig_gq = 1.0 / (1.0 + tl.exp(-gq32))
    qg = (q32 * sig_gq).to(tl.float16)

    # Initialize accumulators
    m_i = tl.full([BLOCK_M], -float("inf"), dtype=tl.float32)
    l_i = tl.zeros([BLOCK_M], dtype=tl.float32)
    acc = tl.zeros([BLOCK_M, BLOCK_DV], dtype=tl.float32)

    # Loop over K/V blocks along N
    for start_n in range(0, N, BLOCK_N):
        offs_n = start_n + offs_dn
        # Load K and GK [BN, Dq]
        k_ptrs = K_ptr + z * stride_kz + h * stride_kh + (offs_n[:, None] * stride_kn) + (offs_dq[None, :] * stride_kd)
        gk_ptrs = GK_ptr + z * stride_gkz + h * stride_gkh + (offs_n[:, None] * stride_gkn) + (offs_dq[None, :] * stride_gkd)
        mask_k = (offs_n[:, None] < N) & (offs_dq[None, :] < Dq)
        k = tl.load(k_ptrs, mask=mask_k, other=0.0)
        gk = tl.load(gk_ptrs, mask=mask_k, other=0.0)

        # Apply gating: sigmoid(GK) * K
        gk32 = gk.to(tl.float32)
        k32 = k.to(tl.float32)
        sig_gk = 1.0 / (1.0 + tl.exp(-gk32))
        kg = (k32 * sig_gk).to(tl.float16)

        # Compute logits [BM, BN]
        qk = tl.dot(qg, tl.trans(kg)) * sm_scale
        # Mask out-of-bounds columns
        mask_bn = offs_n[None, :] < N
        qk = tl.where(mask_bn, qk, -float("inf"))

        # Compute numerically stable softmax update
        m_ij = tl.max(qk, axis=1)
        m_new = tl.maximum(m_i, m_ij)
        p = tl.exp(qk - m_new[:, None])
        # For V multiply, we will cast p to fp16; keep p32 for l_i
        p32 = p
        alpha = tl.exp(m_i - m_new)
        l_new = l_i * alpha + tl.sum(p32, axis=1)

        # Load V block [BN, Dv]
        v_ptrs = V_ptr + z * stride_vz + h * stride_vh + (offs_n[:, None] * stride_vn) + (offs_dv[None, :] * stride_vd)
        mask_v = (offs_n[:, None] < N) & (offs_dv[None, :] < Dv)
        v = tl.load(v_ptrs, mask=mask_v, other=0.0)

        # Update acc: acc = acc * alpha + p @ v
        p16 = p32.to(tl.float16)
        acc_update = tl.dot(p16, v)
        acc = acc * alpha[:, None] + acc_update

        m_i = m_new
        l_i = l_new

    # Normalize
    o = acc / l_i[:, None]

    # Store result
    o_ptrs = O_ptr + z * stride_oz + h * stride_oh + (offs_m[:, None] * stride_om) + (offs_dv[None, :] * stride_od)
    mask_o = (offs_m[:, None] < M) & (offs_dv[None, :] < Dv)
    tl.store(o_ptrs, o.to(tl.float16), mask=mask_o)


def gdpa_attn(Q: torch.Tensor, K: torch.Tensor, V: torch.Tensor, GQ: torch.Tensor, GK: torch.Tensor) -> torch.Tensor:
    assert Q.device.type == "cuda", "Q must be on CUDA device"
    assert K.device == Q.device and V.device == Q.device and GQ.device == Q.device and GK.device == Q.device
    assert Q.dtype == torch.float16 and K.dtype == torch.float16 and V.dtype == torch.float16
    assert GQ.dtype == torch.float16 and GK.dtype == torch.float16
    assert Q.dim() == 4 and K.dim() == 4 and V.dim() == 4 and GQ.dim() == 4 and GK.dim() == 4
    Z, H, M, Dq = Q.shape
    Zk, Hk, N, Dqk = K.shape
    Zv, Hv, Nv, Dv = V.shape
    Zgq, Hgq, Mgq, Dqg = GQ.shape
    Zgk, Hgk, Ngk, Dqkg = GK.shape
    assert Z == Zk == Zv == Zgq == Zgk
    assert H == Hk == Hv == Hgq == Hgk
    assert M == Mgq
    assert N == Nv == Ngk
    assert Dq == Dqk == Dqg == Dqkg
    assert M == N, "GDPA attention assumes N == M"

    O = torch.empty((Z, H, M, Dv), device=Q.device, dtype=torch.float16)

    # Strides
    stride_qz, stride_qh, stride_qm, stride_qd = Q.stride()
    stride_kz, stride_kh, stride_kn, stride_kd = K.stride()
    stride_vz, stride_vh, stride_vn, stride_vd = V.stride()
    stride_gqz, stride_gqh, stride_gqm, stride_gqd = GQ.stride()
    stride_gkz, stride_gkh, stride_gkn, stride_gkd = GK.stride()
    stride_oz, stride_oh, stride_om, stride_od = O.stride()

    BLOCK_M = 64
    BLOCK_N = 64
    grid = (Z * H, triton.cdiv(M, BLOCK_M))
    sm_scale = 1.0 / math.sqrt(Dq)

    gdpa_fwd_kernel[grid](
        Q, K, V, GQ, GK, O,
        stride_qz, stride_qh, stride_qm, stride_qd,
        stride_kz, stride_kh, stride_kn, stride_kd,
        stride_vz, stride_vh, stride_vn, stride_vd,
        stride_gqz, stride_gqh, stride_gqm, stride_gqd,
        stride_gkz, stride_gkh, stride_gkn, stride_gkd,
        stride_oz, stride_oh, stride_om, stride_od,
        Z, H, M, N, Dq, Dv,
        sm_scale,
        BLOCK_M=BLOCK_M, BLOCK_N=BLOCK_N,
        BLOCK_DQ=Dq, BLOCK_DV=Dv,
        num_warps=4, num_stages=2
    )

    return O
'''
        return {"code": code}
