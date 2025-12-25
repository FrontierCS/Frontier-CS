import torch
import triton
import triton.language as tl

class Solution:
    def solve(self, spec_path: str = None) -> dict:
        code = """
import torch
import triton
import triton.language as tl

@triton.jit
def _gdpa_attn_kernel(
    Q_ptr, K_ptr, V_ptr, GQ_ptr, GK_ptr, O_ptr,
    stride_qb, stride_qm, stride_qd,
    stride_kb, stride_kn, stride_kd,
    stride_vb, stride_vn, stride_vd,
    stride_gqb, stride_gqm, stride_gqd,
    stride_gkb, stride_gkn, stride_gkd,
    stride_ob, stride_om, stride_od,
    M, N,
    scale: tl.constexpr,
    BLOCK_M: tl.constexpr,
    BLOCK_N: tl.constexpr,
    BLOCK_D: tl.constexpr,
):
    '''
    Triton kernel for Gated Dot-Product Attention.
    Computes O = softmax( (Q*sig(GQ)) @ (K*sig(GK))^T * scale) @ V
    using a tiled approach with online softmax for numerical stability.
    '''
    # Program IDs identify the work item for this kernel instance.
    pid_b = tl.program_id(0)  # Batch and Head dimension
    pid_m = tl.program_id(1)  # M (Query sequence length) dimension

    # Offsets for the M and D dimensions for the current block.
    offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
    offs_d = tl.arange(0, BLOCK_D)

    # Pointers to the current block of Q, GQ, and O.
    q_ptrs = Q_ptr + pid_b * stride_qb + offs_m[:, None] * stride_qm + offs_d[None, :] * stride_qd
    gq_ptrs = GQ_ptr + pid_b * stride_gqb + offs_m[:, None] * stride_gqm + offs_d[None, :] * stride_gqd
    o_ptrs = O_ptr + pid_b * stride_ob + offs_m[:, None] * stride_om + offs_d[None, :] * stride_od

    # Base pointers for K, GK, and V for the current batch/head.
    k_base_ptr = K_ptr + pid_b * stride_kb
    gk_base_ptr = GK_ptr + pid_b * stride_gkb
    v_base_ptr = V_ptr + pid_b * stride_vb

    # Initialize accumulators for the online softmax algorithm.
    m_i = tl.full([BLOCK_M], -float("inf"), dtype=tl.float32)
    l_i = tl.zeros([BLOCK_M], dtype=tl.float32)
    acc = tl.zeros([BLOCK_M, BLOCK_D], dtype=tl.float32)

    # Load the block of Q and its gate GQ.
    mask_m = offs_m < M
    q = tl.load(q_ptrs, mask=mask_m[:, None], other=0.0)
    gq = tl.load(gq_ptrs, mask=mask_m[:, None], other=0.0)

    # Apply gating to Q. Computation is done in float32 for precision.
    q_gated = (q.to(tl.float32) * tl.sigmoid(gq.to(tl.float32))).to(q.dtype)

    # Loop over blocks of K, GK, and V along the N dimension.
    offs_n = tl.arange(0, BLOCK_N)
    for start_n in range(0, N, BLOCK_N):
        current_offs_n = start_n + offs_n
        mask_n = current_offs_n < N
        
        # Load K and GK blocks, transposed for efficient dot product.
        k_ptrs = k_base_ptr + offs_d[:, None] * stride_kd + current_offs_n[None, :] * stride_kn
        gk_ptrs = gk_base_ptr + offs_d[:, None] * stride_gkd + current_offs_n[None, :] * stride_gkn
        k = tl.load(k_ptrs, mask=mask_n[None, :], other=0.0)
        gk = tl.load(gk_ptrs, mask=mask_n[None, :], other=0.0)
        
        # Load V block.
        v_ptrs = v_base_ptr + current_offs_n[:, None] * stride_vn + offs_d[None, :] * stride_vd
        v = tl.load(v_ptrs, mask=mask_n[:, None], other=0.0)

        # Apply gating to K.
        k_gated = (k.to(tl.float32) * tl.sigmoid(gk.to(tl.float32))).to(k.dtype)
        
        # Compute attention scores (S = Q_gated @ K_gated^T * scale).
        s = tl.dot(q_gated, k_gated) * scale
        
        # Apply mask to scores for padded tokens.
        s = tl.where(mask_m[:, None] & mask_n[None, :], s, -float("inf"))

        # --- Online Softmax Update ---
        # 1. Find new maximum score for the row.
        m_i_new = tl.maximum(m_i, tl.max(s, 1))
        
        # 2. Rescale previous accumulator and sum of exponents.
        acc_scale = tl.exp(m_i - m_i_new)
        acc = acc * acc_scale[:, None]
        l_i = l_i * acc_scale
        
        # 3. Compute new probabilities and update sum of exponents.
        p = tl.exp(s - m_i_new[:, None])
        l_i_update = tl.sum(p, 1)
        l_i += l_i_update

        # 4. Update accumulator with new values.
        p = p.to(v.dtype)
        acc += tl.dot(p, v)
        
        # 5. Update the running max.
        m_i = m_i_new

    # Final normalization of the accumulator.
    l_i_safe = tl.where(l_i == 0, 1.0, l_i)
    acc = acc / l_i_safe[:, None]
    
    # Store the final result block to the output tensor.
    tl.store(o_ptrs, acc.to(tl.float16), mask=mask_m[:, None])


def gdpa_attn(Q: torch.Tensor, K: torch.Tensor, V: torch.Tensor, GQ: torch.Tensor, GK: torch.Tensor) -> torch.Tensor:
    """
    GDPA attention computation with gated Q and K tensors.
    
    Args:
        Q: Input tensor of shape (Z, H, M, Dq) - query tensor (float16)
        K: Input tensor of shape (Z, H, N, Dq) - key tensor (float16)
        V: Input tensor of shape (Z, H, N, Dv) - value tensor (float16)
        GQ: Input tensor of shape (Z, H, M, Dq) - query gate tensor (float16)
        GK: Input tensor of shape (Z, H, N, Dq) - key gate tensor (float16)
    
    Returns:
        Output tensor of shape (Z, H, M, Dv) - attention output (float16)
    """
    Z, H, M, Dq = Q.shape
    _, _, N, _ = K.shape
    _, _, _, Dv = V.shape

    assert Dq == Dv, "Query and Value dimensions must be equal for this kernel"
    assert Dq in {16, 32, 64, 128}, "Head dimension must be a power of two"

    O = torch.empty_like(Q)

    scale = 1.0 / (Dq ** 0.5)

    # Reshape inputs to 3D tensors (batch_and_head, seq_len, dim) for simpler kernel indexing.
    Q_ = Q.view(Z * H, M, Dq)
    K_ = K.view(Z * H, N, Dq)
    V_ = V.view(Z * H, N, Dv)
    GQ_ = GQ.view(Z * H, M, Dq)
    GK_ = GK.view(Z * H, N, Dq)
    O_ = O.view(Z * H, M, Dv)
    
    # Kernel configuration
    BLOCK_M = 128
    BLOCK_N = 64
    BLOCK_D = Dq

    grid = (Z * H, triton.cdiv(M, BLOCK_M))
    
    # Heuristically chosen parameters for good performance on modern GPUs like NVIDIA L4.
    num_warps = 4
    num_stages = 4
    if M <= 512:
        num_stages = 3  # Use less software pipelining for shorter sequences.

    # Launch the Triton kernel.
    _gdpa_attn_kernel[grid](
        Q_, K_, V_, GQ_, GK_, O_,
        Q_.stride(0), Q_.stride(1), Q_.stride(2),
        K_.stride(0), K_.stride(1), K_.stride(2),
        V_.stride(0), V_.stride(1), V_.stride(2),
        GQ_.stride(0), GQ_.stride(1), GQ_.stride(2),
        GK_.stride(0), GK_.stride(1), GK_.stride(2),
        O_.stride(0), O_.stride(1), O_.stride(2),
        M, N,
        scale=scale,
        BLOCK_M=BLOCK_M,
        BLOCK_N=BLOCK_N,
        BLOCK_D=BLOCK_D,
        num_warps=num_warps,
        num_stages=num_stages,
    )

    return O
"""
        return {"code": code}
