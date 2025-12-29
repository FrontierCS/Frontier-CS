import math
import torch
import triton
import triton.language as tl


@triton.jit
def flash_attn_fwd_kernel(
    Q_ptr, K_ptr, V_ptr, O_ptr,
    stride_qz, stride_qh, stride_qm, stride_qd,
    stride_kz, stride_kh, stride_kn, stride_kd,
    stride_vz, stride_vh, stride_vn, stride_vd,
    stride_oz, stride_oh, stride_om, stride_od,
    Z, H, M, N, D, DV,
    sm_scale,
    causal: tl.constexpr,
    BLOCK_M: tl.constexpr,
    BLOCK_N: tl.constexpr,
    BLOCK_DMODEL: tl.constexpr,
    BLOCK_DV: tl.constexpr,
):
    pid = tl.program_id(axis=0)
    m_blocks = tl.cdiv(M, BLOCK_M)
    zh = pid // m_blocks
    pid_m = pid % m_blocks
    z = zh // H
    h = zh % H

    offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
    offs_d = tl.arange(0, BLOCK_DMODEL)
    offs_n_base = tl.arange(0, BLOCK_N)
    offs_dv = tl.arange(0, BLOCK_DV)

    # Base pointers for this (z, h)
    Q_base = Q_ptr + z * stride_qz + h * stride_qh
    K_base = K_ptr + z * stride_kz + h * stride_kh
    V_base = V_ptr + z * stride_vz + h * stride_vh
    O_base = O_ptr + z * stride_oz + h * stride_oh

    # Load Q block [BM, D]
    q_ptrs = Q_base + offs_m[:, None] * stride_qm + offs_d[None, :] * stride_qd
    q_mask = (offs_m[:, None] < M) & (offs_d[None, :] < D)
    q = tl.load(q_ptrs, mask=q_mask, other=0.0).to(tl.float16)

    # Initialize streaming softmax variables
    m_i = tl.full((BLOCK_M,), -1.0e9, dtype=tl.float32)
    l_i = tl.zeros((BLOCK_M,), dtype=tl.float32)
    acc = tl.zeros((BLOCK_M, BLOCK_DV), dtype=tl.float32)

    # Iterate over K/V blocks
    n0 = 0
    while n0 < N:
        offs_n = n0 + offs_n_base

        # Load K tile [BN, D]
        k_ptrs = K_base + offs_n[:, None] * stride_kn + offs_d[None, :] * stride_kd
        k_mask = (offs_n[:, None] < N) & (offs_d[None, :] < D)
        k = tl.load(k_ptrs, mask=k_mask, other=0.0).to(tl.float16)

        # Compute attention scores [BM, BN]
        # q: [BM, D], k: [BN, D] -> s = q @ k.T in float32
        s = tl.dot(q, tl.trans(k)).to(tl.float32)
        s = s * sm_scale

        # Apply causal mask if needed
        if causal:
            m_ids = offs_m[:, None]
            n_ids = offs_n[None, :]
            causal_mask = n_ids <= m_ids
            s = tl.where(causal_mask, s, -1.0e9)

        # Mask for N tail
        n_mask = offs_n[None, :] < N
        s = tl.where(n_mask, s, -1.0e9)

        # Streaming softmax update
        row_max = tl.max(s, axis=1)
        m_i_new = tl.maximum(m_i, row_max)
        p = tl.exp(s - m_i_new[:, None])
        alpha = tl.exp(m_i - m_i_new)
        l_i = l_i * alpha + tl.sum(p, axis=1)

        # Load V tile [BN, DV]
        v_ptrs = V_base + offs_n[:, None] * stride_vn + offs_dv[None, :] * stride_vd
        v_mask = (offs_n[:, None] < N) & (offs_dv[None, :] < DV)
        v = tl.load(v_ptrs, mask=v_mask, other=0.0).to(tl.float16)

        # Update accumulator: acc = acc * alpha[:, None] + p @ v
        acc = acc * alpha[:, None] + tl.dot(p.to(tl.float32), v.to(tl.float32))

        m_i = m_i_new
        n0 += BLOCK_N

    # Normalize by l_i
    # Avoid division by zero for out-of-range rows
    row_mask = offs_m < M
    l_safe = tl.where(l_i > 0, l_i, 1.0)
    acc = acc / l_safe[:, None]
    acc = tl.where(row_mask[:, None], acc, 0.0)

    # Store output
    o_ptrs = O_base + offs_m[:, None] * stride_om + offs_dv[None, :] * stride_od
    o_mask = (offs_m[:, None] < M) & (offs_dv[None, :] < DV)
    tl.store(o_ptrs, acc.to(tl.float16), mask=o_mask)


def _next_power_of_2(x: int) -> int:
    if x <= 1:
        return 1
    return 1 << (x - 1).bit_length()


def _pick_configs(M, N, D, DV):
    # Heuristic configuration
    BLOCK_M = 64
    # Choose BLOCK_N larger for throughput
    if N >= 2048:
        BLOCK_N = 128
    else:
        BLOCK_N = 64
    # D and DV blocks
    BLOCK_DMODEL = min(128, _next_power_of_2(D))
    if BLOCK_DMODEL < D:
        BLOCK_DMODEL = D  # ensure at least D if D <= 128
    BLOCK_DV = min(128, _next_power_of_2(DV))
    if BLOCK_DV < DV:
        BLOCK_DV = DV if DV <= 128 else 128
    # Warps heuristic
    num_warps = 4 if BLOCK_N <= 64 else 8
    num_stages = 2
    return {
        "BLOCK_M": BLOCK_M,
        "BLOCK_N": BLOCK_N,
        "BLOCK_DMODEL": BLOCK_DMODEL,
        "BLOCK_DV": BLOCK_DV,
        "num_warps": num_warps,
        "num_stages": num_stages,
    }


def flash_attn(Q: torch.Tensor, K: torch.Tensor, V: torch.Tensor, causal: bool = True) -> torch.Tensor:
    assert Q.is_cuda and K.is_cuda and V.is_cuda, "Inputs must be CUDA tensors"
    assert Q.dtype == torch.float16 and K.dtype == torch.float16 and V.dtype == torch.float16, "Inputs must be float16"
    assert Q.ndim == 4 and K.ndim == 4 and V.ndim == 4, "Inputs must be 4D tensors (Z,H,Seq,Dim)"
    Z, H, M, Dq = Q.shape
    Zk, Hk, N, Dk = K.shape
    Zv, Hv, Nv, Dv = V.shape
    assert Z == Zk == Zv and H == Hk == Hv and Dq == Dk and N == Nv, "Shape mismatch"
    device = Q.device

    # Fallback to PyTorch naive implementation if dims too large
    if Dq > 128 or Dv > 128:
        scale = 1.0 / math.sqrt(Dq)
        scores = torch.matmul(Q.to(torch.float32), K.transpose(-1, -2).to(torch.float32)) * scale
        if causal:
            # causal mask: allow j <= i
            mask = torch.triu(torch.ones((M, N), device=device, dtype=torch.bool), diagonal=1)
            scores = scores.masked_fill(mask, float("-inf"))
        probs = torch.softmax(scores, dim=-1).to(torch.float32)
        out = torch.matmul(probs, V.to(torch.float32)).to(torch.float16)
        return out

    # Prepare output
    O = torch.empty((Z, H, M, Dv), device=device, dtype=torch.float16)

    # Strides
    stride_qz, stride_qh, stride_qm, stride_qd = Q.stride()
    stride_kz, stride_kh, stride_kn, stride_kd = K.stride()
    stride_vz, stride_vh, stride_vn, stride_vd = V.stride()
    stride_oz, stride_oh, stride_om, stride_od = O.stride()

    cfg = _pick_configs(M, N, Dq, Dv)
    BLOCK_M = cfg["BLOCK_M"]
    BLOCK_N = cfg["BLOCK_N"]
    BLOCK_DMODEL = cfg["BLOCK_DMODEL"]
    BLOCK_DV = cfg["BLOCK_DV"]
    num_warps = cfg["num_warps"]
    num_stages = cfg["num_stages"]

    # Grid: one program per (z,h,m_block)
    grid = (triton.cdiv(M, BLOCK_M) * Z * H,)

    sm_scale = 1.0 / math.sqrt(Dq)

    flash_attn_fwd_kernel[grid](
        Q, K, V, O,
        stride_qz, stride_qh, stride_qm, stride_qd,
        stride_kz, stride_kh, stride_kn, stride_kd,
        stride_vz, stride_vh, stride_vn, stride_vd,
        stride_oz, stride_oh, stride_om, stride_od,
        Z, H, M, N, Dq, Dv,
        sm_scale,
        causal=causal,
        BLOCK_M=BLOCK_M,
        BLOCK_N=BLOCK_N,
        BLOCK_DMODEL=BLOCK_DMODEL,
        BLOCK_DV=BLOCK_DV,
        num_warps=num_warps,
        num_stages=num_stages,
    )
    return O


class Solution:
    def solve(self, spec_path: str = None) -> dict:
        src = []
        src.append("import math")
        src.append("import torch")
        src.append("import triton")
        src.append("import triton.language as tl")
        src.append(inspect.getsource(flash_attn_fwd_kernel))
        src.append(inspect.getsource(_next_power_of_2))
        src.append(inspect.getsource(_pick_configs))
        src.append(inspect.getsource(flash_attn))
        code = "\n".join(src)
        return {"code": code}