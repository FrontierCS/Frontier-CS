import torch
import triton
import triton.language as tl

class Solution:
    def solve(self, spec_path: str = None) -> dict:
        return {
            "code": r"""
import torch
import triton
import triton.language as tl

@triton.jit
def _split_flash_decoding_fwd_kernel(
    Q, K, V, sm_scale,
    Mid_O, Mid_L, Mid_M,
    stride_qz, stride_qh, stride_qm, stride_qk,
    stride_kz, stride_kh, stride_kn, stride_kk,
    stride_vz, stride_vh, stride_vn, stride_vk,
    stride_oz, stride_oh, stride_on, stride_ok,
    stride_lz, stride_lh, stride_ln,
    Z, H, N,
    BLOCK_N: tl.constexpr, BLOCK_D: tl.constexpr
):
    pid = tl.program_id(0)
    pid_z = tl.program_id(1)
    pid_h = tl.program_id(2)

    # Q ptr: (Z, H, 1, D) - Assume M=1
    q_offset = pid_z * stride_qz + pid_h * stride_qh
    q_ptr = Q + q_offset
    
    offs_d = tl.arange(0, BLOCK_D)
    q = tl.load(q_ptr + offs_d * stride_qk)

    # Range for this block
    start_n = pid * BLOCK_N
    offs_n = tl.arange(0, BLOCK_N)
    
    # K ptr: (Z, H, N, D)
    k_offset = pid_z * stride_kz + pid_h * stride_kh + start_n * stride_kn
    k_ptr = K + k_offset + (offs_n[:, None] * stride_kn + offs_d[None, :] * stride_kk)
    
    mask_n = (start_n + offs_n) < N
    
    k = tl.load(k_ptr, mask=mask_n[:, None], other=0.0)

    # QK^T
    # q: (D), k: (BLOCK_N, D) -> (BLOCK_N)
    qk = tl.sum(k * q[None, :], axis=1)
    qk *= sm_scale
    
    # Mask
    qk = tl.where(mask_n, qk, -float('inf'))

    # Softmax stats
    m = tl.max(qk, 0)
    p = tl.exp(qk - m)
    l = tl.sum(p, 0)

    # V ptr: (Z, H, N, D)
    v_offset = pid_z * stride_vz + pid_h * stride_vh + start_n * stride_vn
    v_ptr = V + v_offset + (offs_n[:, None] * stride_vn + offs_d[None, :] * stride_vk)
    v = tl.load(v_ptr, mask=mask_n[:, None], other=0.0)
    
    # Accumulate P*V
    # p: (BLOCK_N), v: (BLOCK_N, D) -> (D)
    acc = tl.sum(p[:, None] * v, axis=0)

    # Write partials
    off_mid_o = pid_z * stride_oz + pid_h * stride_oh + pid * stride_on
    off_mid_l = pid_z * stride_lz + pid_h * stride_lh + pid * stride_ln
    
    tl.store(Mid_M + off_mid_l, m)
    tl.store(Mid_L + off_mid_l, l)
    tl.store(Mid_O + off_mid_o + offs_d * stride_ok, acc)

@triton.jit
def _reduce_flash_decoding_fwd_kernel(
    Mid_O, Mid_L, Mid_M, Out,
    stride_mid_oz, stride_mid_oh, stride_mid_on, stride_mid_ok,
    stride_mid_lz, stride_mid_lh, stride_mid_ln,
    stride_out_z, stride_out_h, stride_out_m, stride_out_k,
    Z, H, NUM_SPLITS,
    BLOCK_D: tl.constexpr
):
    pid_z = tl.program_id(0)
    pid_h = tl.program_id(1)
    
    mid_o_base = pid_z * stride_mid_oz + pid_h * stride_mid_oh
    mid_l_base = pid_z * stride_mid_lz + pid_h * stride_mid_lh
    
    offs_d = tl.arange(0, BLOCK_D)

    acc = tl.zeros([BLOCK_D], dtype=tl.float32)
    m_global = -float('inf')
    l_global = 0.0

    for i in range(NUM_SPLITS):
        off_l = i * stride_mid_ln
        off_o = i * stride_mid_on
        
        m_i = tl.load(Mid_M + mid_l_base + off_l)
        l_i = tl.load(Mid_L + mid_l_base + off_l)
        o_i = tl.load(Mid_O + mid_o_base + off_o + offs_d * stride_mid_ok)

        m_new = tl.maximum(m_global, m_i)
        alpha = tl.exp(m_global - m_new)
        beta = tl.exp(m_i - m_new)

        acc = acc * alpha + o_i * beta
        l_global = l_global * alpha + l_i * beta
        m_global = m_new
    
    out = acc / l_global
    
    out_off = pid_z * stride_out_z + pid_h * stride_out_h
    tl.store(Out + out_off + offs_d * stride_out_k, out.to(tl.float16))

def decoding_attn(Q, K, V):
    Z, H, M, D = Q.shape
    _, _, N, _ = K.shape
    
    # Fixed block size for decoding
    BLOCK_N = 128
    BLOCK_D = D
    
    sm_scale = 1.0 / (D ** 0.5)
    
    # Calculate splits
    num_splits = (N + BLOCK_N - 1) // BLOCK_N
    
    # Allocate intermediate buffers
    # Mid_O: (Z, H, Splits, D)
    Mid_O = torch.empty((Z, H, num_splits, D), dtype=torch.float32, device=Q.device)
    Mid_L = torch.empty((Z, H, num_splits), dtype=torch.float32, device=Q.device)
    Mid_M = torch.empty((Z, H, num_splits), dtype=torch.float32, device=Q.device)
    
    Out = torch.empty_like(Q)
    
    # 1. Split Kernel
    grid_split = (num_splits, Z, H)
    _split_flash_decoding_fwd_kernel[grid_split](
        Q, K, V, sm_scale,
        Mid_O, Mid_L, Mid_M,
        Q.stride(0), Q.stride(1), Q.stride(2), Q.stride(3),
        K.stride(0), K.stride(1), K.stride(2), K.stride(3),
        V.stride(0), V.stride(1), V.stride(2), V.stride(3),
        Mid_O.stride(0), Mid_O.stride(1), Mid_O.stride(2), Mid_O.stride(3),
        Mid_L.stride(0), Mid_L.stride(1), Mid_L.stride(2),
        Z, H, N,
        BLOCK_N=BLOCK_N, BLOCK_D=BLOCK_D
    )
    
    # 2. Reduce Kernel
    grid_red = (Z, H)
    _reduce_flash_decoding_fwd_kernel[grid_red](
        Mid_O, Mid_L, Mid_M, Out,
        Mid_O.stride(0), Mid_O.stride(1), Mid_O.stride(2), Mid_O.stride(3),
        Mid_L.stride(0), Mid_L.stride(1), Mid_L.stride(2),
        Out.stride(0), Out.stride(1), Out.stride(2), Out.stride(3),
        Z, H, num_splits,
        BLOCK_D=BLOCK_D
    )
    
    return Out
"""
        }
