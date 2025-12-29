import torch
import triton
import triton.language as tl

class Solution:
    def solve(self, spec_path: str = None) -> dict:
        return {
            "code": """
import torch
import triton
import triton.language as tl
import math

@triton.autotune(
    configs=[
        triton.Config({'BLOCK_N': 128, 'num_warps': 4}, num_stages=2),
        triton.Config({'BLOCK_N': 64, 'num_warps': 4}, num_stages=2),
        triton.Config({'BLOCK_N': 128, 'num_warps': 8}, num_stages=2),
    ],
    key=['N']
)
@triton.jit
def _decode_split_kernel(
    Q, K, V, sm_scale,
    Out_acc, Out_l, Out_m,
    stride_qz, stride_qh, stride_qm, stride_qk,
    stride_kz, stride_kh, stride_kn, stride_kk,
    stride_vz, stride_vh, stride_vn, stride_vk,
    stride_oaz, stride_oah, stride_oam, stride_oas, stride_oak,
    stride_olz, stride_olh, stride_olm, stride_ols,
    Z, H, N,
    BLOCK_N: tl.constexpr,
    BLOCK_DMODEL: tl.constexpr,
    SPLIT_K: tl.constexpr
):
    pid_s = tl.program_id(0)
    pid_zh = tl.program_id(1)
    pid_m = tl.program_id(2)

    idx_z = pid_zh // H
    idx_h = pid_zh % H

    # Offsets for Q
    q_ptr = Q + idx_z * stride_qz + idx_h * stride_qh + pid_m * stride_qm
    q_offsets = tl.arange(0, BLOCK_DMODEL)
    q = tl.load(q_ptr + q_offsets, mask=q_offsets < BLOCK_DMODEL, other=0.0)

    # Split logic
    total_blocks = tl.cdiv(N, BLOCK_N)
    blocks_per_split = tl.cdiv(total_blocks, SPLIT_K)
    start_block = pid_s * blocks_per_split
    end_block = min((pid_s + 1) * blocks_per_split, total_blocks)

    # Accumulators
    m_i = -float('inf')
    l_i = 0.0
    acc = tl.zeros([BLOCK_DMODEL], dtype=tl.float32)

    kv_offset_base = idx_z * stride_kz + idx_h * stride_kh
    v_offset_base = idx_z * stride_vz + idx_h * stride_vh

    for block_idx in range(start_block, end_block):
        start_n = block_idx * BLOCK_N
        cols = start_n + tl.arange(0, BLOCK_N)
        mask_k = cols < N

        # Load K
        k_ptr = K + kv_offset_base + (cols[:, None] * stride_kn + q_offsets[None, :] * stride_kk)
        k = tl.load(k_ptr, mask=mask_k[:, None] & (q_offsets[None, :] < BLOCK_DMODEL), other=0.0)

        # Compute QK^T
        qk = tl.sum(q[None, :] * k, axis=1)
        qk *= sm_scale
        qk = tl.where(mask_k, qk, -float('inf'))

        # Online Softmax
        m_curr = tl.max(qk, 0)
        p = tl.exp(qk - m_curr)
        l_curr = tl.sum(p, 0)

        # Load V
        v_ptr = V + v_offset_base + (cols[:, None] * stride_vn + q_offsets[None, :] * stride_vk)
        v = tl.load(v_ptr, mask=mask_k[:, None] & (q_offsets[None, :] < BLOCK_DMODEL), other=0.0)

        # Accumulate
        w_v = tl.sum(p[:, None] * v, axis=0)

        if m_curr > m_i:
            alpha = tl.exp(m_i - m_curr)
            l_i = l_i * alpha + l_curr
            acc = acc * alpha + w_v
            m_i = m_curr
        else:
            alpha = tl.exp(m_curr - m_i)
            l_i = l_i + l_curr * alpha
            acc = acc + w_v * alpha

    # Store partial results
    off_out_base = idx_z * stride_oaz + idx_h * stride_oah + pid_m * stride_oam + pid_s * stride_oas
    tl.store(Out_acc + off_out_base + q_offsets, acc, mask=q_offsets < BLOCK_DMODEL)

    off_l = idx_z * stride_olz + idx_h * stride_olh + pid_m * stride_olm + pid_s * stride_ols
    tl.store(Out_l + off_l, l_i)
    tl.store(Out_m + off_l, m_i)

@triton.jit
def _reduce_kernel(
    Out_acc, Out_l, Out_m,
    Out,
    stride_oaz, stride_oah, stride_oam, stride_oas, stride_oak,
    stride_olz, stride_olh, stride_olm, stride_ols,
    stride_oz, stride_oh, stride_om, stride_od,
    Z, H, M,
    SPLIT_K: tl.constexpr, BLOCK_DMODEL: tl.constexpr
):
    pid_zh = tl.program_id(0)
    pid_m = tl.program_id(1)

    idx_z = pid_zh // H
    idx_h = pid_zh % H

    off_acc_base = idx_z * stride_oaz + idx_h * stride_oah + pid_m * stride_oam
    off_l_base = idx_z * stride_olz + idx_h * stride_olh + pid_m * stride_olm

    m_global = -float('inf')
    l_global = 0.0
    acc_global = tl.zeros([BLOCK_DMODEL], dtype=tl.float32)

    offs_d = tl.arange(0, BLOCK_DMODEL)

    for s in range(SPLIT_K):
        m_curr = tl.load(Out_m + off_l_base + s * stride_ols)
        
        # Skip if block was empty (init to -inf)
        if m_curr == -float('inf'):
            continue
            
        l_curr = tl.load(Out_l + off_l_base + s * stride_ols)
        acc_curr = tl.load(Out_acc + off_acc_base + s * stride_oas + offs_d, mask=offs_d < BLOCK_DMODEL)

        if m_curr > m_global:
            alpha = tl.exp(m_global - m_curr)
            l_global = l_global * alpha + l_curr
            acc_global = acc_global * alpha + acc_curr
            m_global = m_curr
        else:
            alpha = tl.exp(m_curr - m_global)
            l_global = l_global + l_curr * alpha
            acc_global = acc_global + acc_curr * alpha

    out = acc_global / l_global
    
    out_ptr = Out + idx_z * stride_oz + idx_h * stride_oh + pid_m * stride_om + offs_d
    tl.store(out_ptr, out.to(Out.dtype.element_ty), mask=offs_d < BLOCK_DMODEL)

def decoding_attn(Q: torch.Tensor, K: torch.Tensor, V: torch.Tensor) -> torch.Tensor:
    Z, H, M, D = Q.shape
    _, _, N, _ = K.shape

    sm_scale = 1.0 / math.sqrt(D)

    # Calculate BLOCK_DMODEL (next power of 2)
    BLOCK_DMODEL = 1 << (D - 1).bit_length()

    # Heuristic for Split-K
    # Target ~128+ blocks to fill GPU
    # Total tasks = Z * H * M
    target_blocks = 128
    tasks = Z * H * M
    split_k = max(1, target_blocks // tasks)
    
    # Clamp split_k so we don't have tiny blocks (min 128 elems per split)
    max_splits = max(1, N // 128)
    split_k = min(split_k, max_splits)

    Out_acc = torch.empty((Z, H, M, split_k, D), device=Q.device, dtype=torch.float32)
    Out_l = torch.empty((Z, H, M, split_k), device=Q.device, dtype=torch.float32)
    Out_m = torch.empty((Z, H, M, split_k), device=Q.device, dtype=torch.float32)
    Output = torch.empty((Z, H, M, D), device=Q.device, dtype=Q.dtype)

    grid_split = (split_k, Z * H, M)
    _decode_split_kernel[grid_split](
        Q, K, V, sm_scale,
        Out_acc, Out_l, Out_m,
        Q.stride(0), Q.stride(1), Q.stride(2), Q.stride(3),
        K.stride(0), K.stride(1), K.stride(2), K.stride(3),
        V.stride(0), V.stride(1), V.stride(2), V.stride(3),
        Out_acc.stride(0), Out_acc.stride(1), Out_acc.stride(2), Out_acc.stride(3), Out_acc.stride(4),
        Out_l.stride(0), Out_l.stride(1), Out_l.stride(2), Out_l.stride(3),
        Z, H, N,
        BLOCK_DMODEL=BLOCK_DMODEL,
        SPLIT_K=split_k
    )

    grid_reduce = (Z * H, M)
    _reduce_kernel[grid_reduce](
        Out_acc, Out_l, Out_m,
        Output,
        Out_acc.stride(0), Out_acc.stride(1), Out_acc.stride(2), Out_acc.stride(3), Out_acc.stride(4),
        Out_l.stride(0), Out_l.stride(1), Out_l.stride(2), Out_l.stride(3),
        Output.stride(0), Output.stride(1), Output.stride(2), Output.stride(3),
        Z, H, M,
        SPLIT_K=split_k,
        BLOCK_DMODEL=BLOCK_DMODEL
    )

    return Output
"""
        }