import torch
import triton
import triton.language as tl


@triton.jit
def _ragged_attention_kernel(
    Q_ptr, K_ptr, V_ptr, O_ptr, row_lens_ptr,
    stride_qm, stride_qd,
    stride_kn, stride_kd,
    stride_vn, stride_vd,
    stride_om, stride_od,
    M, N, D, Dv,
    BLOCK_M: tl.constexpr,
    BLOCK_N: tl.constexpr,
    BLOCK_D: tl.constexpr,
    BLOCK_DV: tl.constexpr,
    USE_MASK: tl.constexpr,
):
    pid_m = tl.program_id(0)
    pid_n = tl.program_id(1)
    
    # Get row length for this query
    row_len = tl.load(row_lens_ptr + pid_m)
    
    # Skip if this query row has no keys to attend to
    if row_len == 0:
        return
    
    # Determine valid N range for this query
    start_n = pid_n * BLOCK_N
    end_n = tl.minimum(start_n + BLOCK_N, row_len)
    
    # Initialize pointers for Q block
    offs_qm = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
    offs_qd = tl.arange(0, BLOCK_D)
    q_ptrs = Q_ptr + offs_qm[:, None] * stride_qm + offs_qd[None, :] * stride_qd
    mask_qm = offs_qm < M
    
    # Load Q block (BLOCK_M, BLOCK_D)
    q_block = tl.load(q_ptrs, mask=mask_qm[:, None] & (offs_qd[None, :] < D), other=0.0)
    
    # Initialize pointers for K block
    offs_kn = start_n + tl.arange(0, BLOCK_N)
    offs_kd = tl.arange(0, BLOCK_D)
    k_ptrs = K_ptr + offs_kn[:, None] * stride_kn + offs_kd[None, :] * stride_kd
    mask_kn = offs_kn < end_n
    
    # Load K block (BLOCK_N, BLOCK_D)
    k_block = tl.load(k_ptrs, mask=mask_kn[:, None] & (offs_kd[None, :] < D), other=0.0)
    
    # Compute scores: (BLOCK_M, BLOCK_N)
    # Q: (BLOCK_M, BLOCK_D), K: (BLOCK_N, BLOCK_D) -> (BLOCK_M, BLOCK_N)
    scores = tl.dot(q_block, tl.trans(k_block))
    scores = scores * (1.0 / tl.sqrt(tl.float32(D)))
    
    # Apply row length masking
    if USE_MASK:
        col_mask = tl.arange(0, BLOCK_N) < (end_n - start_n)
        row_mask = tl.arange(0, BLOCK_M) < (M - pid_m * BLOCK_M)
        mask = row_mask[:, None] & col_mask[None, :]
        scores = tl.where(mask, scores, float('-inf'))
    
    # Softmax over N dimension
    m_i = tl.max(scores, axis=1)
    p = tl.exp(scores - m_i[:, None])
    l_i = tl.sum(p, axis=1)
    p = p / l_i[:, None]
    
    # Initialize pointers for V block
    offs_vd = tl.arange(0, BLOCK_DV)
    v_ptrs = V_ptr + offs_kn[:, None] * stride_vn + offs_vd[None, :] * stride_vd
    mask_vd = offs_vd < Dv
    
    # Load V block (BLOCK_N, BLOCK_DV)
    v_block = tl.load(v_ptrs, mask=mask_kn[:, None] & mask_vd[None, :], other=0.0)
    
    # Compute output: (BLOCK_M, BLOCK_DV)
    # p: (BLOCK_M, BLOCK_N), V: (BLOCK_N, BLOCK_DV) -> (BLOCK_M, BLOCK_DV)
    o_block = tl.dot(p, v_block)
    
    # Store output
    offs_od = tl.arange(0, BLOCK_DV)
    o_ptrs = O_ptr + offs_qm[:, None] * stride_om + offs_od[None, :] * stride_od
    mask_om = mask_qm[:, None] & (offs_od[None, :] < Dv)
    tl.store(o_ptrs, o_block, mask=mask_om)


@triton.jit
def _ragged_attention_kernel_optimized(
    Q_ptr, K_ptr, V_ptr, O_ptr, row_lens_ptr,
    stride_qm, stride_qd,
    stride_kn, stride_kd,
    stride_vn, stride_vd,
    stride_om, stride_od,
    M, N, D, Dv,
    BLOCK_M: tl.constexpr,
    BLOCK_N: tl.constexpr,
    BLOCK_D: tl.constexpr,
    BLOCK_DV: tl.constexpr,
    NUM_STAGES: tl.constexpr,
    NUM_WARPS: tl.constexpr,
):
    pid_m = tl.program_id(0)
    pid_n = tl.program_id(1)
    
    # Get row length for this query
    row_len = tl.load(row_lens_ptr + pid_m)
    
    # Skip if this query row has no keys to attend to
    if row_len == 0:
        return
    
    # Determine valid N range for this query
    start_n = pid_n * BLOCK_N
    end_n = tl.minimum(start_n + BLOCK_N, row_len)
    
    # Initialize accumulator for output
    offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
    offs_dv = tl.arange(0, BLOCK_DV)
    acc = tl.zeros((BLOCK_M, BLOCK_DV), dtype=tl.float32)
    
    # Initialize max and sum for softmax
    m_i = tl.full((BLOCK_M,), float('-inf'), dtype=tl.float32)
    l_i = tl.zeros((BLOCK_M,), dtype=tl.float32)
    
    # Load Q block
    offs_qd = tl.arange(0, BLOCK_D)
    q_ptrs = Q_ptr + offs_m[:, None] * stride_qm + offs_qd[None, :] * stride_qd
    mask_qm = offs_m < M
    q = tl.load(q_ptrs, mask=mask_qm[:, None] & (offs_qd[None, :] < D), other=0.0)
    
    # Loop over K/V blocks
    for start_k in range(start_n, end_n, BLOCK_N):
        offs_n = start_k + tl.arange(0, BLOCK_N)
        mask_n = offs_n < end_n
        
        # Load K block
        offs_kd = tl.arange(0, BLOCK_D)
        k_ptrs = K_ptr + offs_n[:, None] * stride_kn + offs_kd[None, :] * stride_kd
        k = tl.load(k_ptrs, mask=mask_n[:, None] & (offs_kd[None, :] < D), other=0.0)
        
        # Compute scores
        scores = tl.dot(q, tl.trans(k))
        scores = scores * (1.0 / tl.sqrt(tl.float32(D)))
        
        # Apply masking
        mask = mask_qm[:, None] & mask_n[None, :]
        scores = tl.where(mask, scores, float('-inf'))
        
        # Streaming softmax update
        m_i_new = tl.maximum(m_i, tl.max(scores, axis=1))
        alpha = tl.exp(m_i - m_i_new)
        beta = tl.exp(scores - m_i_new[:, None])
        
        # Update accumulator
        offs_vd = tl.arange(0, BLOCK_DV)
        v_ptrs = V_ptr + offs_n[:, None] * stride_vn + offs_vd[None, :] * stride_vd
        v = tl.load(v_ptrs, mask=mask_n[:, None] & (offs_vd[None, :] < Dv), other=0.0)
        
        acc = acc * alpha[:, None] + tl.dot(beta, v)
        l_i = l_i * alpha + tl.sum(beta, axis=1)
        m_i = m_i_new
    
    # Normalize output
    acc = acc / l_i[:, None]
    
    # Store output
    o_ptrs = O_ptr + offs_m[:, None] * stride_om + offs_dv[None, :] * stride_od
    mask_om = mask_qm[:, None] & (offs_dv[None, :] < Dv)
    tl.store(o_ptrs, acc, mask=mask_om)


def ragged_attn(
    Q: torch.Tensor,
    K: torch.Tensor,
    V: torch.Tensor,
    row_lens: torch.Tensor
) -> torch.Tensor:
    """
    Ragged attention computation.
    
    Args:
        Q: Query tensor of shape (M, D) - query features (float16)
        K: Key tensor of shape (N, D) - key features (float16)
        V: Value tensor of shape (N, Dv) - value features (float16)
        row_lens: Row lengths tensor of shape (M,) - number of valid K/V rows per Q row (int32 or int64)
    
    Returns:
        Output tensor of shape (M, Dv) - attention output (float16)
    """
    assert Q.is_cuda and K.is_cuda and V.is_cuda and row_lens.is_cuda
    assert Q.dtype == torch.float16 and K.dtype == torch.float16 and V.dtype == torch.float16
    assert Q.dim() == 2 and K.dim() == 2 and V.dim() == 2 and row_lens.dim() == 1
    
    M, D = Q.shape
    N, D_k = K.shape
    N_v, Dv = V.shape
    assert D == D_k, f"Q dim {D} != K dim {D_k}"
    assert N == N_v, f"K rows {N} != V rows {N_v}"
    assert M == row_lens.shape[0], f"Q rows {M} != row_lens size {row_lens.shape[0]}"
    
    # Output tensor
    O = torch.empty((M, Dv), device=Q.device, dtype=torch.float16)
    
    # Configuration
    BLOCK_M = 64
    BLOCK_N = 64
    BLOCK_D = 64 if D >= 64 else D
    BLOCK_DV = 64 if Dv >= 64 else Dv
    
    # Ensure BLOCK_D and BLOCK_DV are powers of 2 for optimal performance
    def next_power_of_two(n):
        return 1 << (n - 1).bit_length()
    
    BLOCK_D = next_power_of_two(BLOCK_D)
    BLOCK_DV = next_power_of_two(BLOCK_DV)
    
    # Grid dimensions
    grid_m = triton.cdiv(M, BLOCK_M)
    max_row_len = row_lens.max().item()
    grid_n = triton.cdiv(max_row_len, BLOCK_N)
    
    # Launch kernel
    _ragged_attention_kernel_optimized[(
        grid_m,
        grid_n,
    )](
        Q, K, V, O, row_lens,
        Q.stride(0), Q.stride(1),
        K.stride(0), K.stride(1),
        V.stride(0), V.stride(1),
        O.stride(0), O.stride(1),
        M, N, D, Dv,
        BLOCK_M=BLOCK_M,
        BLOCK_N=BLOCK_N,
        BLOCK_D=BLOCK_D,
        BLOCK_DV=BLOCK_DV,
        NUM_STAGES=3,
        NUM_WARPS=8,
    )
    
    return O


class Solution:
    def solve(self, spec_path: str = None) -> dict:
        return {"code": self._get_code()}
    
    def _get_code(self):
        import inspect
        return inspect.getsource(__file__)
