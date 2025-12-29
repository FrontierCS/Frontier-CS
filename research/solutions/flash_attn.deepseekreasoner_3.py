import torch
import triton
import triton.language as tl
from typing import Tuple

@triton.jit
def _fwd_kernel(
    Q, K, V, Out,
    stride_qz, stride_qh, stride_qm, stride_qd,
    stride_kz, stride_kh, stride_kn, stride_kd,
    stride_vz, stride_vh, stride_vn, stride_vd,
    stride_oz, stride_oh, stride_om, stride_od,
    Z, H, M, N, Dq, Dv,
    BLOCK_M: tl.constexpr, BLOCK_N: tl.constexpr,
    BLOCK_Dq: tl.constexpr, BLOCK_Dv: tl.constexpr,
    CAUSAL: tl.constexpr,
    USE_BLOCK_PTR: tl.constexpr
):
    # ----------------------------------------------------------
    # Program ID
    pid_z = tl.program_id(0)  # batch
    pid_h = tl.program_id(1)  # head
    pid_m = tl.program_id(2)  # query block index
    
    # ----------------------------------------------------------
    # Initialize pointers
    if USE_BLOCK_PTR:
        # Use block pointers for better memory access patterns
        q_block_ptr = tl.make_block_ptr(
            base=Q + pid_z * stride_qz + pid_h * stride_qh,
            shape=(M, Dq),
            strides=(stride_qm, stride_qd),
            offsets=(pid_m * BLOCK_M, 0),
            block_shape=(BLOCK_M, BLOCK_Dq),
            order=(1, 0)
        )
        
        out_block_ptr = tl.make_block_ptr(
            base=Out + pid_z * stride_oz + pid_h * stride_oh,
            shape=(M, Dv),
            strides=(stride_om, stride_od),
            offsets=(pid_m * BLOCK_M, 0),
            block_shape=(BLOCK_M, BLOCK_Dv),
            order=(1, 0)
        )
    
    # ----------------------------------------------------------
    # Initialize accumulators
    acc = tl.zeros([BLOCK_M, BLOCK_Dv], dtype=tl.float32)
    m_i = tl.full([BLOCK_M], float('-inf'), dtype=tl.float32)
    l_i = tl.zeros([BLOCK_M], dtype=tl.float32)
    
    # ----------------------------------------------------------
    # Load query block
    if USE_BLOCK_PTR:
        q = tl.load(q_block_ptr, boundary_check=(0, 1), padding_option="zero")
    else:
        offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
        offs_d = tl.arange(0, BLOCK_Dq)
        q_ptrs = Q + pid_z * stride_qz + pid_h * stride_qh + \
                 (offs_m[:, None] * stride_qm + offs_d[None, :] * stride_qd)
        mask_m = offs_m < M
        q = tl.load(q_ptrs, mask=mask_m[:, None], other=0.0)
    
    # ----------------------------------------------------------
    # Loop over key/value blocks
    for block_n in range(0, tl.cdiv(N, BLOCK_N)):
        # ------------------------------------------------------
        # Load key block
        if USE_BLOCK_PTR:
            k_block_ptr = tl.make_block_ptr(
                base=K + pid_z * stride_kz + pid_h * stride_kh,
                shape=(N, Dq),
                strides=(stride_kn, stride_kd),
                offsets=(block_n * BLOCK_N, 0),
                block_shape=(BLOCK_N, BLOCK_Dq),
                order=(1, 0)
            )
            k = tl.load(k_block_ptr, boundary_check=(0, 1), padding_option="zero")
        else:
            offs_n = block_n * BLOCK_N + tl.arange(0, BLOCK_N)
            k_ptrs = K + pid_z * stride_kz + pid_h * stride_kh + \
                     (offs_n[:, None] * stride_kn + offs_d[None, :] * stride_kd)
            mask_n = offs_n < N
            k = tl.load(k_ptrs, mask=mask_n[:, None], other=0.0)
        
        # ------------------------------------------------------
        # Load value block
        if USE_BLOCK_PTR:
            v_block_ptr = tl.make_block_ptr(
                base=V + pid_z * stride_vz + pid_h * stride_vh,
                shape=(N, Dv),
                strides=(stride_vn, stride_vd),
                offsets=(block_n * BLOCK_N, 0),
                block_shape=(BLOCK_N, BLOCK_Dv),
                order=(1, 0)
            )
            v = tl.load(v_block_ptr, boundary_check=(0, 1), padding_option="zero")
        else:
            offs_vd = tl.arange(0, BLOCK_Dv)
            v_ptrs = V + pid_z * stride_vz + pid_h * stride_vh + \
                     (offs_n[:, None] * stride_vn + offs_vd[None, :] * stride_vd)
            v = tl.load(v_ptrs, mask=mask_n[:, None], other=0.0)
        
        # ------------------------------------------------------
        # Compute QK^T
        qk = tl.dot(q, tl.trans(k))
        qk = qk * (1.0 / tl.sqrt(Dq * 1.0))
        
        # ------------------------------------------------------
        # Apply causal mask if needed
        if CAUSAL:
            m_idx = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)[:, None]
            n_idx = block_n * BLOCK_N + tl.arange(0, BLOCK_N)[None, :]
            mask = m_idx >= n_idx
            qk = tl.where(mask, qk, float('-inf'))
        
        # ------------------------------------------------------
        # Apply block mask
        mask_m_ = (pid_m * BLOCK_M + tl.arange(0, BLOCK_M)[:, None]) < M
        mask_n_ = (block_n * BLOCK_N + tl.arange(0, BLOCK_N)[None, :]) < N
        block_mask = mask_m_ & mask_n_
        qk = tl.where(block_mask, qk, float('-inf'))
        
        # ------------------------------------------------------
        # Compute softmax
        m_ij = tl.maximum(m_i[:, None], tl.max(qk, 1))
        p = tl.exp(qk - m_ij)
        l_ij = tl.exp(m_i - m_ij) * l_i + tl.sum(p, 1)
        
        # ------------------------------------------------------
        # Update accumulators
        alpha = tl.exp(m_i - m_ij)
        acc = acc * alpha[:, None]
        
        p = p.to(v.dtype)
        acc += tl.dot(p, v)
        
        # Update m_i and l_i
        m_i = m_ij
        l_i = l_ij
    
    # ----------------------------------------------------------
    # Store output
    out = acc / l_i[:, None]
    out = out.to(Q.dtype)
    
    if USE_BLOCK_PTR:
        tl.store(out_block_ptr, out, boundary_check=(0, 1))
    else:
        offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
        offs_d = tl.arange(0, BLOCK_Dv)
        out_ptrs = Out + pid_z * stride_oz + pid_h * stride_oh + \
                   (offs_m[:, None] * stride_om + offs_d[None, :] * stride_od)
        mask_m = offs_m < M
        tl.store(out_ptrs, out, mask=mask_m[:, None])

def flash_attn(Q: torch.Tensor, K: torch.Tensor, V: torch.Tensor, causal: bool = True) -> torch.Tensor:
    """
    Flash attention computation with optional causal masking.
    """
    # Check shapes
    Z, H, M, Dq = Q.shape
    Zk, Hk, N, Dqk = K.shape
    Zv, Hv, Nv, Dv = V.shape
    
    assert Z == Zk == Zv, "Batch sizes must match"
    assert H == Hk == Hv, "Head counts must match"
    assert Dq == Dqk, "Query/key dimensions must match"
    assert N == Nv, "Key/value sequence lengths must match"
    
    # Allocate output
    Out = torch.empty((Z, H, M, Dv), device=Q.device, dtype=Q.dtype)
    
    # Choose block sizes based on problem dimensions
    BLOCK_M, BLOCK_N, BLOCK_Dq, BLOCK_Dv = _select_block_sizes(M, N, Dq, Dv)
    
    # Ensure block sizes are compatible with tensor dimensions
    BLOCK_M = min(BLOCK_M, M)
    BLOCK_N = min(BLOCK_N, N)
    BLOCK_Dq = min(BLOCK_Dq, Dq)
    BLOCK_Dv = min(BLOCK_Dv, Dv)
    
    # Ensure block sizes are powers of 2 for efficient tiling
    BLOCK_M = _next_power_of_two(BLOCK_M)
    BLOCK_N = _next_power_of_two(BLOCK_N)
    BLOCK_Dq = _next_power_of_two(BLOCK_Dq)
    BLOCK_Dv = _next_power_of_two(BLOCK_Dv)
    
    # Strides
    stride_qz, stride_qh, stride_qm, stride_qd = Q.stride()
    stride_kz, stride_kh, stride_kn, stride_kd = K.stride()
    stride_vz, stride_vh, stride_vn, stride_vd = V.stride()
    stride_oz, stride_oh, stride_om, stride_od = Out.stride()
    
    # Grid configuration
    grid = (Z, H, triton.cdiv(M, BLOCK_M))
    
    # Use block pointers for larger tensors
    USE_BLOCK_PTR = M * Dq > 4096  # Threshold for using block pointers
    
    # Launch kernel
    _fwd_kernel[grid](
        Q, K, V, Out,
        stride_qz, stride_qh, stride_qm, stride_qd,
        stride_kz, stride_kh, stride_kn, stride_kd,
        stride_vz, stride_vh, stride_vn, stride_vd,
        stride_oz, stride_oh, stride_om, stride_od,
        Z, H, M, N, Dq, Dv,
        BLOCK_M=BLOCK_M, BLOCK_N=BLOCK_N,
        BLOCK_Dq=BLOCK_Dq, BLOCK_Dv=BLOCK_Dv,
        CAUSAL=causal,
        USE_BLOCK_PTR=USE_BLOCK_PTR,
        num_warps=4 if BLOCK_M >= 128 else 2,
        num_stages=3
    )
    
    return Out

def _select_block_sizes(M: int, N: int, Dq: int, Dv: int) -> Tuple[int, int, int, int]:
    """Select optimal block sizes based on tensor dimensions."""
    # Base block sizes for L4 GPU (24GB VRAM)
    if M <= 512:
        BLOCK_M = 128
        BLOCK_N = 64
    elif M <= 1024:
        BLOCK_M = 64
        BLOCK_N = 64
    else:  # M <= 2048
        BLOCK_M = 32
        BLOCK_N = 64
    
    # Adjust for memory constraints
    total_memory = BLOCK_M * BLOCK_N + BLOCK_M * Dq + BLOCK_N * Dq + BLOCK_N * Dv
    while total_memory > 16384:  # Limit shared memory usage
        if BLOCK_M > 16:
            BLOCK_M //= 2
        elif BLOCK_N > 16:
            BLOCK_N //= 2
        else:
            break
        total_memory = BLOCK_M * BLOCK_N + BLOCK_M * Dq + BLOCK_N * Dq + BLOCK_N * Dv
    
    BLOCK_Dq = min(64, Dq)
    BLOCK_Dv = min(64, Dv)
    
    return BLOCK_M, BLOCK_N, BLOCK_Dq, BLOCK_Dv

def _next_power_of_two(n: int) -> int:
    """Return the next power of two greater than or equal to n."""
    n -= 1
    n |= n >> 1
    n |= n >> 2
    n |= n >> 4
    n |= n >> 8
    n |= n >> 16
    return n + 1

class Solution:
    def solve(self, spec_path: str = None) -> dict:
        return {"code": self._get_code()}
    
    def _get_code(self) -> str:
        import inspect
        return inspect.getsource(__module__)