import torch
import triton
import triton.language as tl

class Solution:
    def solve(self, spec_path: str = None) -> dict:
        code = r"""
import torch
import triton
import triton.language as tl

@triton.jit
def linear_ce_stage1(
    X_ptr, W_ptr, B_ptr, Targets_ptr, Workspace_ptr,
    M, N, K,
    stride_xm, stride_xk,
    stride_wk, stride_wn,
    stride_b,
    stride_ws_m, stride_ws_s,
    N_SPLIT_SIZE,
    BLOCK_M: tl.constexpr, BLOCK_N: tl.constexpr, BLOCK_K: tl.constexpr
):
    pid_m = tl.program_id(0)
    pid_n = tl.program_id(1)
    
    offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
    mask_m = offs_m < M
    
    n_start_base = pid_n * N_SPLIT_SIZE
    
    # Load targets (int64)
    # Use other=0 to avoid invalid memory access, mask_m handles validity of logic
    targets = tl.load(Targets_ptr + offs_m, mask=mask_m, other=0)
    
    m_i = tl.zeros([BLOCK_M], dtype=tl.float32) - float('inf')
    s_i = tl.zeros([BLOCK_M], dtype=tl.float32)
    t_logit = tl.zeros([BLOCK_M], dtype=tl.float32)
    
    for start_n_local in range(0, N_SPLIT_SIZE, BLOCK_N):
        start_n = n_start_base + start_n_local
        # Boundary check for N
        if start_n >= N:
            break
            
        offs_n = start_n + tl.arange(0, BLOCK_N)
        mask_n = offs_n < N
        
        # Accumulate logits
        accumulator = tl.zeros([BLOCK_M, BLOCK_N], dtype=tl.float32)
        
        for start_k in range(0, K, BLOCK_K):
            offs_k = start_k + tl.arange(0, BLOCK_K)
            
            # X shape (M, K)
            a_ptrs = X_ptr + (offs_m[:, None] * stride_xm + offs_k[None, :] * stride_xk)
            a = tl.load(a_ptrs, mask=mask_m[:, None], other=0.0)
            
            # W shape (K, N)
            b_ptrs = W_ptr + (offs_k[:, None] * stride_wk + offs_n[None, :] * stride_wn)
            b = tl.load(b_ptrs, mask=mask_n[None, :], other=0.0)
            
            accumulator += tl.dot(a, b)
            
        b_ptrs_bias = B_ptr + offs_n * stride_b
        bias = tl.load(b_ptrs_bias, mask=mask_n, other=0.0)
        logits = accumulator + bias[None, :]
        
        # Online Softmax update
        # Mask invalid columns with -inf for max/sum calc
        logits_masked = tl.where(mask_n[None, :], logits, float('-inf'))
        block_max = tl.max(logits_masked, axis=1)
        new_max = tl.maximum(m_i, block_max)
        
        scale = tl.exp(m_i - new_max)
        exp_logits = tl.exp(logits_masked - new_max[:, None])
        block_sum = tl.sum(exp_logits, axis=1)
        
        s_i = s_i * scale + block_sum
        m_i = new_max
        
        # Capture target logit
        # targets is (M,), offs_n is (N,). Compare for column index match.
        # Cast offs_n to int64 to match targets dtype
        target_mask = (targets[:, None] == offs_n[None, :].to(tl.int64))
        
        # Accumulate target logit. Only one true per row across all splits/blocks.
        # Use unmasked logits (valid values for valid N)
        # If target matches, it implies valid column index.
        t_val = tl.sum(tl.where(target_mask, logits, 0.0), axis=1)
        t_logit += t_val

    # Store partial results to workspace
    # Workspace: (M, Splits, 3)
    base_ptr = Workspace_ptr + offs_m * stride_ws_m + pid_n * stride_ws_s
    tl.store(base_ptr + 0, m_i, mask=mask_m)
    tl.store(base_ptr + 1, s_i, mask=mask_m)
    tl.store(base_ptr + 2, t_logit, mask=mask_m)

@triton.jit
def linear_ce_stage2(
    Workspace_ptr, Losses_ptr,
    M, N_SPLITS,
    stride_ws_m, stride_ws_s,
    BLOCK_M: tl.constexpr
):
    pid_m = tl.program_id(0)
    offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
    mask_m = offs_m < M
    
    m_global = tl.zeros([BLOCK_M], dtype=tl.float32) - float('inf')
    s_global = tl.zeros([BLOCK_M], dtype=tl.float32)
    t_global = tl.zeros([BLOCK_M], dtype=tl.float32)
    
    # Reduce over splits
    for s in range(N_SPLITS):
        base_ptr = Workspace_ptr + offs_m * stride_ws_m + s * stride_ws_s
        
        m_part = tl.load(base_ptr + 0, mask=mask_m, other=float('-inf'))
        s_part = tl.load(base_ptr + 1, mask=mask_m, other=0.0)
        t_part = tl.load(base_ptr + 2, mask=mask_m, other=0.0)
        
        new_max = tl.maximum(m_global, m_part)
        scale_global = tl.exp(m_global - new_max)
        scale_part = tl.exp(m_part - new_max)
        
        s_global = s_global * scale_global + s_part * scale_part
        m_global = new_max
        t_global += t_part
        
    loss = tl.log(s_global) + m_global - t_global
    tl.store(Losses_ptr + offs_m, loss, mask=mask_m)

def fused_linear_ce(X, W, B, targets):
    M, K = X.shape
    K_w, N = W.shape
    
    # Heuristics for block size and splitting
    BLOCK_M = 32
    # We aim to launch enough blocks to saturate the GPU (e.g. 60-80+ blocks)
    # Rows are split by BLOCK_M.
    row_blocks = (M + BLOCK_M - 1) // BLOCK_M
    
    # Dynamic splitting of N dimension to increase occupancy for small batch sizes
    target_total_blocks = 120
    wanted_splits = max(1, target_total_blocks // row_blocks)
    
    # Ensure split size isn't too small (overhead dominance)
    max_splits = max(1, N // 128)
    num_splits = min(max_splits, wanted_splits)
    
    # Calculate split size
    N_SPLIT_SIZE = (N + num_splits - 1) // num_splits
    
    # Workspace to store partial results: (M, num_splits, 3)
    workspace = torch.empty((M, num_splits, 3), device=X.device, dtype=torch.float32)
    losses = torch.empty(M, device=X.device, dtype=torch.float32)
    
    grid1 = (row_blocks, num_splits)
    
    linear_ce_stage1[grid1](
        X, W, B, targets, workspace,
        M, N, K,
        X.stride(0), X.stride(1),
        W.stride(0), W.stride(1),
        B.stride(0),
        workspace.stride(0), workspace.stride(1),
        N_SPLIT_SIZE,
        BLOCK_M=BLOCK_M, BLOCK_N=64, BLOCK_K=64,
        num_warps=4, num_stages=3
    )
    
    grid2 = (row_blocks,)
    linear_ce_stage2[grid2](
        workspace, losses,
        M, num_splits,
        workspace.stride(0), workspace.stride(1),
        BLOCK_M=BLOCK_M,
        num_warps=4, num_stages=2
    )
    
    return losses
"""
        return {"code": code}