import torch
import triton
import triton.language as tl
from typing import Optional

@triton.autotune(
    configs=[
        triton.Config({'BLOCK_M': 64, 'BLOCK_N': 64, 'BLOCK_K': 32, 'GROUP_M': 8}, num_stages=3, num_warps=8),
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 64, 'BLOCK_K': 32, 'GROUP_M': 8}, num_stages=3, num_warps=8),
        triton.Config({'BLOCK_M': 64, 'BLOCK_N': 128, 'BLOCK_K': 32, 'GROUP_M': 8}, num_stages=3, num_warps=8),
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 128, 'BLOCK_K': 32, 'GROUP_M': 8}, num_stages=3, num_warps=8),
        triton.Config({'BLOCK_M': 64, 'BLOCK_N': 64, 'BLOCK_K': 64, 'GROUP_M': 8}, num_stages=3, num_warps=8),
        triton.Config({'BLOCK_M': 64, 'BLOCK_N': 128, 'BLOCK_K': 64, 'GROUP_M': 8}, num_stages=3, num_warps=8),
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 64, 'BLOCK_K': 64, 'GROUP_M': 8}, num_stages=3, num_warps=8),
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 128, 'BLOCK_K': 64, 'GROUP_M': 8}, num_stages=3, num_warps=8),
    ],
    key=['M', 'N', 'Dq'],
)
@triton.jit
def _gdpa_attn_kernel(
    # Pointers to matrices
    Q_ptr, K_ptr, V_ptr, GQ_ptr, GK_ptr, O_ptr,
    # Matrix dimensions
    Z, H, M, N, Dq, Dv,
    # Strides
    stride_qz, stride_qh, stride_qm, stride_qd,
    stride_kz, stride_kh, stride_kn, stride_kd,
    stride_vz, stride_vh, stride_vn, stride_vd,
    stride_gqz, stride_gqh, stride_gqm, stride_gqd,
    stride_gkz, stride_gkh, stride_gkn, stride_gkd,
    stride_oz, stride_oh, stride_om, stride_od,
    # Meta-parameters
    BLOCK_M: tl.constexpr, BLOCK_N: tl.constexpr,
    BLOCK_K: tl.constexpr, GROUP_M: tl.constexpr,
    SCALE: tl.constexpr,
):
    # -----------------------------------------------------------
    # Program ID
    pid = tl.program_id(0)
    num_pid_m = tl.cdiv(M, BLOCK_M)
    num_pid_n = tl.cdiv(N, BLOCK_N)
    num_pid_in_group = GROUP_M * num_pid_n
    group_id = pid // num_pid_in_group
    first_pid_m = group_id * GROUP_M
    group_size_m = min(num_pid_m - first_pid_m, GROUP_M)
    pid_m = first_pid_m + (pid % group_size_m)
    pid_n = (pid % num_pid_in_group) // group_size_m

    # -----------------------------------------------------------
    # Create block pointers for Q, K, V, GQ, GK
    offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
    offs_n = pid_n * BLOCK_N + tl.arange(0, BLOCK_N)
    offs_k = tl.arange(0, BLOCK_K)

    # Q and GQ pointers for block M x K
    q_ptrs = Q_ptr + offs_m[:, None] * stride_qm + offs_k[None, :] * stride_qd
    gq_ptrs = GQ_ptr + offs_m[:, None] * stride_gqm + offs_k[None, :] * stride_gqd

    # K and GK pointers for block N x K
    k_ptrs = K_ptr + offs_n[:, None] * stride_kn + offs_k[None, :] * stride_kd
    gk_ptrs = GK_ptr + offs_n[:, None] * stride_gkn + offs_k[None, :] * stride_gkd

    # -----------------------------------------------------------
    # Initialize accumulator
    acc = tl.zeros((BLOCK_M, BLOCK_N), dtype=tl.float32)
    m_i = tl.zeros((BLOCK_M,), dtype=tl.float32) - float('inf')
    l_i = tl.zeros((BLOCK_M,), dtype=tl.float32)

    # -----------------------------------------------------------
    # Loop over K dimension
    for k in range(0, tl.cdiv(Dq, BLOCK_K)):
        # -------------------------------------------------------
        # Load Q and GQ, apply sigmoid gate
        q = tl.load(q_ptrs, mask=(offs_m[:, None] < M) & (offs_k[None, :] < Dq - k * BLOCK_K), other=0.0)
        gq = tl.load(gq_ptrs, mask=(offs_m[:, None] < M) & (offs_k[None, :] < Dq - k * BLOCK_K), other=0.0)
        q_gated = q * tl.sigmoid(gq)

        # -------------------------------------------------------
        # Load K and GK, apply sigmoid gate
        k_val = tl.load(k_ptrs, mask=(offs_n[:, None] < N) & (offs_k[None, :] < Dq - k * BLOCK_K), other=0.0)
        gk = tl.load(gk_ptrs, mask=(offs_n[:, None] < N) & (offs_k[None, :] < Dq - k * BLOCK_K), other=0.0)
        k_gated = k_val * tl.sigmoid(gk)

        # -------------------------------------------------------
        # Matrix multiplication with scaling
        acc += tl.dot(q_gated, k_gated, out_dtype=tl.float32) * SCALE

        # -------------------------------------------------------
        # Update pointers
        q_ptrs += BLOCK_K * stride_qd
        gq_ptrs += BLOCK_K * stride_gqd
        k_ptrs += BLOCK_K * stride_kd
        gk_ptrs += BLOCK_K * stride_gkd

    # -----------------------------------------------------------
    # Online softmax (streaming max/softmax)
    # Find max for stability
    m_ij = tl.max(acc, 1)
    m_i_new = tl.maximum(m_i, m_ij)

    # Scale previous exponentials
    alpha = tl.exp(m_i - m_i_new)
    l_i = l_i * alpha

    # Compute current exponentials and update
    acc_scale = tl.exp(acc - m_i_new[:, None])
    l_i_new = tl.sum(acc_scale, 1) + l_i
    l_i = l_i_new
    m_i = m_i_new

    # -----------------------------------------------------------
    # Store softmax results for later use with V
    # We'll recompute softmax values when multiplying with V
    # to avoid storing large intermediate matrix
    row_idx = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
    mask_m = row_idx < M

    # -----------------------------------------------------------
    # Now process V matrix
    # Reinitialize for V accumulation
    offs_dv = tl.arange(0, BLOCK_K)
    v_ptrs = V_ptr + offs_n[:, None] * stride_vn + offs_dv[None, :] * stride_vd

    # Output accumulator
    o_acc = tl.zeros((BLOCK_M, Dv), dtype=tl.float32)

    # Loop over N dimension again for V
    for start_n in range(0, N, BLOCK_N):
        offs_n_v = start_n + tl.arange(0, BLOCK_N)
        mask_n_v = offs_n_v < N

        # Load V block
        v = tl.load(v_ptrs, mask=mask_n_v[:, None] & (offs_dv[None, :] < Dv), other=0.0)

        # Recompute attention weights for this block
        # We need to recompute QK^T for this N block
        # Reinitialize pointers for recomputation
        q_re_ptr = Q_ptr + offs_m[:, None] * stride_qm + offs_k[None, :] * stride_qd
        gq_re_ptr = GQ_ptr + offs_m[:, None] * stride_gqm + offs_k[None, :] * stride_gqd
        k_re_ptr = K_ptr + offs_n_v[:, None] * stride_kn + offs_k[None, :] * stride_kd
        gk_re_ptr = GK_ptr + offs_n_v[:, None] * stride_gkn + offs_k[None, :] * stride_gkd

        # Recompute QK^T for this block
        acc_re = tl.zeros((BLOCK_M, BLOCK_N), dtype=tl.float32)
        for k in range(0, tl.cdiv(Dq, BLOCK_K)):
            q_re = tl.load(q_re_ptr, mask=(offs_m[:, None] < M) & (offs_k[None, :] < Dq - k * BLOCK_K), other=0.0)
            gq_re = tl.load(gq_re_ptr, mask=(offs_m[:, None] < M) & (offs_k[None, :] < Dq - k * BLOCK_K), other=0.0)
            q_re_gated = q_re * tl.sigmoid(gq_re)

            k_re = tl.load(k_re_ptr, mask=(offs_n_v[:, None] < N) & (offs_k[None, :] < Dq - k * BLOCK_K), other=0.0)
            gk_re = tl.load(gk_re_ptr, mask=(offs_n_v[:, None] < N) & (offs_k[None, :] < Dq - k * BLOCK_K), other=0.0)
            k_re_gated = k_re * tl.sigmoid(gk_re)

            acc_re += tl.dot(q_re_gated, k_re_gated, out_dtype=tl.float32) * SCALE

            q_re_ptr += BLOCK_K * stride_qd
            gq_re_ptr += BLOCK_K * stride_gqd
            k_re_ptr += BLOCK_K * stride_kd
            gk_re_ptr += BLOCK_K * stride_gkd

        # Apply softmax using previously computed m_i, l_i
        # For numerical stability, use m_i as the max
        p = tl.exp(acc_re - m_i[:, None])
        p = p / l_i[:, None]

        # Accumulate output
        o_acc += tl.dot(p, v, out_dtype=tl.float32)

        # Update V pointers
        v_ptrs += BLOCK_N * stride_vn

    # -----------------------------------------------------------
    # Write back output
    offs_dv_out = tl.arange(0, Dv)
    o_ptrs = O_ptr + offs_m[:, None] * stride_om + offs_dv_out[None, :] * stride_od
    tl.store(o_ptrs, o_acc.to(tl.float16), mask=mask_m[:, None] & (offs_dv_out[None, :] < Dv))


def gdpa_attn(Q: torch.Tensor, K: torch.Tensor, V: torch.Tensor, 
              GQ: torch.Tensor, GK: torch.Tensor) -> torch.Tensor:
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
    # Check input dimensions
    Z, H, M, Dq = Q.shape
    _, _, N, Dq_k = K.shape
    _, _, N_v, Dv = V.shape
    assert Dq == Dq_k, f"Q and K must have same feature dimension, got {Dq} and {Dq_k}"
    assert N == N_v, f"K and V must have same sequence length, got {N} and {N_v}"
    
    # Allocate output tensor
    O = torch.empty((Z, H, M, Dv), device=Q.device, dtype=Q.dtype)
    
    # Compute scaling factor
    scale = 1.0 / (Dq ** 0.5)
    
    # Launch kernel for each batch and head
    for z in range(Z):
        for h in range(H):
            # Get slices for current batch and head
            Q_slice = Q[z, h]
            K_slice = K[z, h]
            V_slice = V[z, h]
            GQ_slice = GQ[z, h]
            GK_slice = GK[z, h]
            O_slice = O[z, h]
            
            # Compute grid size
            grid = lambda META: (
                triton.cdiv(M, META['BLOCK_M']) * triton.cdiv(N, META['BLOCK_N']),
            )
            
            # Launch kernel
            _gdpa_attn_kernel[grid](
                Q_slice, K_slice, V_slice, GQ_slice, GK_slice, O_slice,
                Z, H, M, N, Dq, Dv,
                Q.stride(0), Q.stride(1), Q.stride(2), Q.stride(3),
                K.stride(0), K.stride(1), K.stride(2), K.stride(3),
                V.stride(0), V.stride(1), V.stride(2), V.stride(3),
                GQ.stride(0), GQ.stride(1), GQ.stride(2), GQ.stride(3),
                GK.stride(0), GK.stride(1), GK.stride(2), GK.stride(3),
                O.stride(0), O.stride(1), O.stride(2), O.stride(3),
                SCALE=scale,
            )
    
    return O


class Solution:
    def solve(self, spec_path: str = None) -> dict:
        """
        Returns a dict with either:
        - {"code": "python_code_string"}
        - {"program_path": "path/to/kernel.py"}
        """
        # Return the code directly as a string
        import inspect
        code = inspect.getsource(_gdpa_attn_kernel) + "\n\n" + inspect.getsource(gdpa_attn) + "\n\n" + inspect.getsource(Solution)
        return {"code": code}
