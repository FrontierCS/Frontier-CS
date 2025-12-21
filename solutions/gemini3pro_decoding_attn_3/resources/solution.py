class Solution:
    def solve(self, spec_path: str = None) -> dict:
        return {
            "code": """
import torch
import triton
import triton.language as tl
import math

@triton.jit
def _fwd_kernel(
    Q, K, V, sm_scale,
    Out,
    Mid_O, Mid_L, Mid_M,
    stride_qz, stride_qh, stride_qm, stride_qd,
    stride_kz, stride_kh, stride_kn, stride_kd,
    stride_vz, stride_vh, stride_vn, stride_vd,
    stride_oz, stride_oh, stride_om, stride_od,
    Z, H, N, M,
    BLOCK_N: tl.constexpr,
    BLOCK_DMODEL: tl.constexpr,
    IS_SPLIT: tl.constexpr,
    SPLIT_K: tl.constexpr
):
    pid = tl.program_id(0)
    pid_k = tl.program_id(1)
    
    # Map pid to Batch/Head/M
    # Grid x is (Z * H * M)
    # We flatten Z, H, M into a single dimension for the grid
    
    idx_m = pid % M
    idx_h = (pid // M) % H
    idx_z = pid // (M * H)
    
    # Q offsets
    q_ptr = Q + idx_z * stride_qz + idx_h * stride_qh + idx_m * stride_qm
    k_base = K + idx_z * stride_kz + idx_h * stride_kh
    v_base = V + idx_z * stride_vz + idx_h * stride_vh
    
    # Load Q: (BLOCK_DMODEL,)
    offs_d = tl.arange(0, BLOCK_DMODEL)
    q = tl.load(q_ptr + offs_d * stride_qd)
    
    # Dimensions for K/V iteration
    # Split-K logic
    if IS_SPLIT:
        total_blocks = tl.cdiv(N, BLOCK_N)
        blocks_per_split = tl.cdiv(total_blocks, SPLIT_K)
        start_block = pid_k * blocks_per_split
        end_block = min((pid_k + 1) * blocks_per_split, total_blocks)
        n_start = start_block * BLOCK_N
        n_end = end_block * BLOCK_N
        # If this split has no work, return
        if n_start >= N:
            # We must write initialized values to Mid buffers to avoid garbage in reduction
            # But simpler to just initialize accumulators and write them
            # Logic below handles empty range by init values
            pass
    else:
        n_start = 0
        n_end = N

    # Accumulators
    m_i = -float('inf')
    l_i = 0.0
    acc = tl.zeros([BLOCK_DMODEL], dtype=tl.float32)
    
    # Scaling
    q = q * sm_scale
    
    # Loop over N
    # We iterate in chunks of BLOCK_N
    for start_n in range(n_start, n_end, BLOCK_N):
        offs_n = start_n + tl.arange(0, BLOCK_N)
        mask = offs_n < N
        
        # Load K: (BLOCK_N, BLOCK_DMODEL)
        k_ptr = k_base + (offs_n[:, None] * stride_kn + offs_d[None, :] * stride_kd)
        k = tl.load(k_ptr, mask=mask[:, None], other=0.0)
        
        # Compute scores: Q (D,) dot K.T (D, BLOCK_N) -> (BLOCK_N,)
        # Effectively sum(Q[None,:] * K, axis=1)
        qk = tl.sum(q[None, :] * k, axis=1)
        
        # Apply mask (set masked elements to -inf)
        qk = tl.where(mask, qk, -float('inf'))
        
        # Online Softmax updates
        m_curr = tl.max(qk, 0)
        p = tl.exp(qk - m_curr)
        
        # Correct previous stats
        if m_curr > m_i:
            alpha = tl.exp(m_i - m_curr)
            l_i = l_i * alpha
            acc = acc * alpha
            m_i = m_curr
        else:
            # Current max is smaller than global max
            # Scale current p by exp(m_curr - m_i)
            alpha = tl.exp(m_curr - m_i)
            p = p * alpha
            # m_i remains same
            
        # Accumulate l
        l_i += tl.sum(p, 0)
        
        # Load V: (BLOCK_N, BLOCK_DMODEL)
        v_ptr = v_base + (offs_n[:, None] * stride_vn + offs_d[None, :] * stride_vd)
        v = tl.load(v_ptr, mask=mask[:, None], other=0.0)
        
        # Accumulate O: p (BLOCK_N,) dot V (BLOCK_N, D) -> (D,)
        # p is (BLOCK_N,), v is (BLOCK_N, D). p[:, None] * v
        acc += tl.sum(p[:, None] * v, axis=0)

    # Store results
    if IS_SPLIT:
        # Store unnormalized accumulators to Scratch
        # Layout: (Batch, SPLIT_K, D)
        # Batch index = pid
        # Split index = pid_k
        
        # Pointers
        mid_o_ptr = Mid_O + (pid * SPLIT_K * BLOCK_DMODEL + pid_k * BLOCK_DMODEL + offs_d)
        mid_l_ptr = Mid_L + (pid * SPLIT_K + pid_k)
        mid_m_ptr = Mid_M + (pid * SPLIT_K + pid_k)
        
        tl.store(mid_o_ptr, acc)
        tl.store(mid_l_ptr, l_i)
        tl.store(mid_m_ptr, m_i)
    else:
        # Normalize and store to Out
        acc = acc / l_i
        
        out_ptr = Out + idx_z * stride_oz + idx_h * stride_oh + idx_m * stride_om + offs_d * stride_od
        tl.store(out_ptr, acc.to(Out.dtype.element_ty))

@triton.jit
def _reduce_kernel(
    Mid_O, Mid_L, Mid_M,
    Out,
    stride_oz, stride_oh, stride_om, stride_od,
    Z, H, M,
    SPLIT_K: tl.constexpr,
    BLOCK_DMODEL: tl.constexpr
):
    pid = tl.program_id(0)
    
    idx_m = pid % M
    idx_h = (pid // M) % H
    idx_z = pid // (M * H)
    
    offs_d = tl.arange(0, BLOCK_DMODEL)
    
    # Initialize global acc
    m_global = -float('inf')
    l_global = 0.0
    acc_global = tl.zeros([BLOCK_DMODEL], dtype=tl.float32)
    
    # Iterate over splits
    for k in range(0, SPLIT_K):
        # Load parts
        # Mid_O layout: (Batch, SPLIT_K, D)
        mid_o_ptr = Mid_O + (pid * SPLIT_K * BLOCK_DMODEL + k * BLOCK_DMODEL + offs_d)
        mid_l_ptr = Mid_L + (pid * SPLIT_K + k)
        mid_m_ptr = Mid_M + (pid * SPLIT_K + k)
        
        acc_k = tl.load(mid_o_ptr)
        l_k = tl.load(mid_l_ptr)
        m_k = tl.load(mid_m_ptr)
        
        # Merge
        if m_k > m_global:
            alpha = tl.exp(m_global - m_k)
            acc_global = acc_global * alpha + acc_k
            l_global = l_global * alpha + l_k
            m_global = m_k
        else:
            alpha = tl.exp(m_k - m_global)
            acc_global = acc_global + acc_k * alpha
            l_global = l_global + l_k * alpha
            
    # Normalize
    acc_global = acc_global / l_global
    
    # Store
    out_ptr = Out + idx_z * stride_oz + idx_h * stride_oh + idx_m * stride_om + offs_d * stride_od
    tl.store(out_ptr, acc_global.to(Out.dtype.element_ty))

def decoding_attn(Q: torch.Tensor, K: torch.Tensor, V: torch.Tensor) -> torch.Tensor:
    # Shapes
    Z, H, M, Dq = Q.shape
    _, _, N, Dv = V.shape
    
    assert Dq == Dv, "Query and Value dimensions must match for this kernel"
    D = Dq
    
    # Output buffer
    Out = torch.empty((Z, H, M, D), dtype=Q.dtype, device=Q.device)
    
    # Tuning / Heuristics
    # Basic params
    BLOCK_N = 128
    BLOCK_DMODEL = 64 # Fixed by problem spec effectively
    
    # Calculate Split-K
    # Heuristic: We want enough blocks to saturate the GPU
    # Each unit is (z, h, m)
    # Total units
    num_units = Z * H * M
    
    # Get SM count (approximate or query)
    try:
        num_sms = torch.cuda.get_device_properties(Q.device).multi_processor_count
    except:
        num_sms = 58 # L4 default
        
    target_waves = 2
    target_blocks = num_sms * target_waves
    
    # Blocks per unit required if we don't split
    blocks_per_unit_nosplit = (N + BLOCK_N - 1) // BLOCK_N
    
    # Total blocks if nosplit
    total_blocks_nosplit = num_units # We launch 1 block per unit effectively if not loop-split inside kernel
    # Wait, the kernel loops over N. So 1 threadblock per unit.
    
    if num_units >= target_blocks:
        split_k = 1
    else:
        # We need more blocks
        needed_splits = (target_blocks + num_units - 1) // num_units
        max_splits = (N + BLOCK_N - 1) // BLOCK_N
        split_k = min(needed_splits, max_splits)
        # Cap split_k to avoid excessive overhead
        split_k = min(split_k, 64)
        split_k = max(split_k, 1)

    sm_scale = 1.0 / (D ** 0.5)
    
    # Grids
    # X dimension is mapped to units (Z*H*M) if split_k=1, else handled inside
    # Actually, my kernel maps X to units, Y to splits
    
    grid_fwd = (Z * H * M, split_k)
    
    if split_k > 1:
        # Allocate scratch
        # Sizes:
        # Mid_O: (Z*H*M, split_k, D)
        # Mid_L: (Z*H*M, split_k)
        # Mid_M: (Z*H*M, split_k)
        
        # We flatten Z*H*M for scratch layout: (Batch, Split, D)
        batch_dim = Z * H * M
        Mid_O = torch.empty((batch_dim, split_k, D), dtype=torch.float32, device=Q.device)
        Mid_L = torch.empty((batch_dim, split_k), dtype=torch.float32, device=Q.device)
        Mid_M = torch.empty((batch_dim, split_k), dtype=torch.float32, device=Q.device)
        
        _fwd_kernel[grid_fwd](
            Q, K, V, sm_scale,
            Out, # Unused
            Mid_O, Mid_L, Mid_M,
            Q.stride(0), Q.stride(1), Q.stride(2), Q.stride(3),
            K.stride(0), K.stride(1), K.stride(2), K.stride(3),
            V.stride(0), V.stride(1), V.stride(2), V.stride(3),
            Out.stride(0), Out.stride(1), Out.stride(2), Out.stride(3),
            Z, H, N, M,
            BLOCK_N=BLOCK_N,
            BLOCK_DMODEL=BLOCK_DMODEL,
            IS_SPLIT=True,
            SPLIT_K=split_k,
            num_warps=4,
            num_stages=2
        )
        
        # Reduction
        grid_red = (Z * H * M,)
        _reduce_kernel[grid_red](
            Mid_O, Mid_L, Mid_M,
            Out,
            Out.stride(0), Out.stride(1), Out.stride(2), Out.stride(3),
            Z, H, M,
            SPLIT_K=split_k,
            BLOCK_DMODEL=BLOCK_DMODEL,
            num_warps=4,
            num_stages=2
        )
        
    else:
        # No split, write directly to Out
        Mid_O = Mid_L = Mid_M = None # Placeholders
        
        _fwd_kernel[grid_fwd](
            Q, K, V, sm_scale,
            Out,
            Mid_O, Mid_L, Mid_M,
            Q.stride(0), Q.stride(1), Q.stride(2), Q.stride(3),
            K.stride(0), K.stride(1), K.stride(2), K.stride(3),
            V.stride(0), V.stride(1), V.stride(2), V.stride(3),
            Out.stride(0), Out.stride(1), Out.stride(2), Out.stride(3),
            Z, H, N, M,
            BLOCK_N=BLOCK_N,
            BLOCK_DMODEL=BLOCK_DMODEL,
            IS_SPLIT=False,
            SPLIT_K=1,
            num_warps=4,
            num_stages=2
        )

    return Out
"""
        }
