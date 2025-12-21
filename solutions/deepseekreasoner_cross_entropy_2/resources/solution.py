import torch
import triton
import triton.language as tl
from typing import Optional, Tuple

@triton.autotune(
    configs=[
        triton.Config({'BLOCK_M': 64, 'BLOCK_N': 256, 'NUM_WARPS': 4}, num_stages=3),
        triton.Config({'BLOCK_M': 64, 'BLOCK_N': 512, 'NUM_WARPS': 4}, num_stages=3),
        triton.Config({'BLOCK_M': 64, 'BLOCK_N': 1024, 'NUM_WARPS': 4}, num_stages=3),
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 256, 'NUM_WARPS': 4}, num_stages=3),
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 512, 'NUM_WARPS': 4}, num_stages=3),
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 1024, 'NUM_WARPS': 4}, num_stages=3),
        triton.Config({'BLOCK_M': 256, 'BLOCK_N': 256, 'NUM_WARPS': 4}, num_stages=3),
        triton.Config({'BLOCK_M': 256, 'BLOCK_N': 512, 'NUM_WARPS': 8}, num_stages=3),
        triton.Config({'BLOCK_M': 256, 'BLOCK_N': 1024, 'NUM_WARPS': 8}, num_stages=3),
    ],
    key=['M', 'N'],
)
@triton.jit
def _cross_entropy_forward_kernel(
    logits_ptr,
    targets_ptr,
    output_ptr,
    M,
    N,
    logits_stride_m,
    logits_stride_n,
    output_stride_m,
    BLOCK_M: tl.constexpr,
    BLOCK_N: tl.constexpr,
    NUM_WARPS: tl.constexpr,
):
    pid = tl.program_id(0)
    num_m_blocks = tl.cdiv(M, BLOCK_M)
    
    m_start = pid * BLOCK_M
    m_end = tl.minimum(m_start + BLOCK_M, M)
    m_mask = tl.arange(0, BLOCK_M) < (m_end - m_start)
    
    batch_idx = tl.arange(0, BLOCK_M) + m_start
    batch_mask = batch_idx < M
    
    # Load targets for this block
    targets = tl.load(targets_ptr + batch_idx, mask=batch_mask, other=0)
    
    # Initialize max and sum for logsumexp
    max_val = tl.full((BLOCK_M,), float('-inf'), dtype=tl.float32)
    sum_exp = tl.zeros((BLOCK_M,), dtype=tl.float32)
    
    # Process logits in blocks of BLOCK_N
    for n_start in range(0, N, BLOCK_N):
        n_end = tl.minimum(n_start + BLOCK_N, N)
        n_mask = tl.arange(0, BLOCK_N) < (n_end - n_start)
        
        # Create indices for 2D loading
        m_indices = batch_idx[:, None]
        n_indices = tl.arange(0, BLOCK_N)[None, :] + n_start
        
        # Load logits block
        logits_block = tl.load(
            logits_ptr + m_indices * logits_stride_m + n_indices * logits_stride_n,
            mask=batch_mask[:, None] & n_mask[None, :],
            other=float('-inf')
        )
        
        # Update max within this block
        block_max = tl.max(logits_block, axis=1)
        new_max = tl.maximum(max_val, block_max)
        
        # Adjust sum_exp for new max
        if n_start > 0:
            sum_exp = sum_exp * tl.exp(max_val - new_max)
        
        # Update sum_exp with current block
        sum_exp = sum_exp + tl.sum(
            tl.exp(logits_block - new_max[:, None]),
            axis=1
        )
        
        max_val = new_max
    
    # Compute logsumexp = max + log(sum_exp)
    logsumexp = max_val + tl.log(sum_exp)
    
    # Load target logits
    target_indices = targets
    target_logits = tl.load(
        logits_ptr + batch_idx * logits_stride_m + target_indices * logits_stride_n,
        mask=batch_mask,
        other=float('-inf')
    )
    
    # Compute loss: logsumexp - target_logits
    loss = logsumexp - target_logits
    
    # Store results
    tl.store(
        output_ptr + batch_idx * output_stride_m,
        loss,
        mask=batch_mask
    )

@triton.autotune(
    configs=[
        triton.Config({'BLOCK_M': 64, 'NUM_WARPS': 4}, num_stages=3),
        triton.Config({'BLOCK_M': 128, 'NUM_WARPS': 4}, num_stages=3),
        triton.Config({'BLOCK_M': 256, 'NUM_WARPS': 8}, num_stages=3),
        triton.Config({'BLOCK_M': 512, 'NUM_WARPS': 8}, num_stages=3),
    ],
    key=['M'],
)
@triton.jit
def _cross_entropy_optimized_kernel(
    logits_ptr,
    targets_ptr,
    output_ptr,
    M,
    N,
    logits_stride_m,
    logits_stride_n,
    output_stride_m,
    BLOCK_M: tl.constexpr,
    NUM_WARPS: tl.constexpr,
):
    pid = tl.program_id(0)
    num_m_blocks = tl.cdiv(M, BLOCK_M)
    
    m_start = pid * BLOCK_M
    m_end = tl.minimum(m_start + BLOCK_M, M)
    m_mask = tl.arange(0, BLOCK_M) < (m_end - m_start)
    
    batch_idx = tl.arange(0, BLOCK_M) + m_start
    batch_mask = batch_idx < M
    
    # Load targets for this block
    targets = tl.load(targets_ptr + batch_idx, mask=batch_mask, other=0)
    
    # Compute logsumexp and target logits in one pass
    max_val = tl.full((BLOCK_M,), float('-inf'), dtype=tl.float32)
    sum_exp = tl.zeros((BLOCK_M,), dtype=tl.float32)
    target_logits = tl.zeros((BLOCK_M,), dtype=tl.float32)
    
    # Vectorized processing - 8 elements at a time for better cache usage
    VEC_SIZE = 8
    
    for n_start in range(0, N, VEC_SIZE):
        n_end = tl.minimum(n_start + VEC_SIZE, N)
        n_indices = tl.arange(0, VEC_SIZE)
        n_mask = n_indices < (n_end - n_start)
        
        # Create indices for vectorized loading
        m_indices = batch_idx[:, None]
        n_vec = n_indices[None, :] + n_start
        
        # Load logits vector block
        logits_vec = tl.load(
            logits_ptr + m_indices * logits_stride_m + n_vec * logits_stride_n,
            mask=batch_mask[:, None] & n_mask[None, :],
            other=float('-inf')
        )
        
        # Compare with targets to extract target logits
        target_mask = n_vec == targets[:, None]
        
        # Extract target logit if present in this vector
        target_logit_candidate = tl.where(
            target_mask & batch_mask[:, None] & n_mask[None, :],
            logits_vec,
            float('-inf')
        )
        target_logits = tl.maximum(target_logits, tl.max(target_logit_candidate, axis=1))
        
        # Update max and sum_exp
        vec_max = tl.max(logits_vec, axis=1)
        new_max = tl.maximum(max_val, vec_max)
        
        if n_start > 0:
            sum_exp = sum_exp * tl.exp(max_val - new_max)
        
        # Update sum_exp with current vector
        sum_exp = sum_exp + tl.sum(
            tl.exp(logits_vec - new_max[:, None]),
            axis=1
        )
        
        max_val = new_max
    
    # Handle remaining elements if N not divisible by VEC_SIZE
    # (already handled by masking above)
    
    # Compute logsumexp
    logsumexp = max_val + tl.log(sum_exp)
    
    # Compute final loss
    loss = logsumexp - target_logits
    
    # Store results
    tl.store(
        output_ptr + batch_idx * output_stride_m,
        loss,
        mask=batch_mask
    )

def cross_entropy(logits: torch.Tensor, targets: torch.Tensor) -> torch.Tensor:
    """
    Cross entropy loss computation.
    
    Args:
        logits: Input tensor of shape (M, N) - logits for M samples and N classes
        targets: Input tensor of shape (M,) - target class indices (int64)
    
    Returns:
        Output tensor of shape (M,) - negative log-likelihood loss for each sample
    """
    assert logits.dim() == 2, "logits must be 2D"
    assert targets.dim() == 1, "targets must be 1D"
    assert logits.size(0) == targets.size(0), "Batch size mismatch"
    
    M, N = logits.shape
    device = logits.device
    
    # Ensure tensors are on CUDA and in correct format
    if not logits.is_cuda:
        logits = logits.cuda()
    if not targets.is_cuda:
        targets = targets.cuda()
    
    # Convert targets to int64 if needed
    if targets.dtype != torch.int64:
        targets = targets.long()
    
    # Output tensor
    output = torch.empty(M, device=device, dtype=logits.dtype)
    
    # Choose kernel based on problem size
    # For very large N, use the tiled kernel, otherwise use optimized one-pass kernel
    if N > 4096:
        grid = (triton.cdiv(M, 256),)
        _cross_entropy_forward_kernel[grid](
            logits,
            targets,
            output,
            M,
            N,
            logits.stride(0),
            logits.stride(1),
            output.stride(0),
            BLOCK_M=256,
            BLOCK_N=1024,
            NUM_WARPS=8,
        )
    else:
        grid = (triton.cdiv(M, 128),)
        _cross_entropy_optimized_kernel[grid](
            logits,
            targets,
            output,
            M,
            N,
            logits.stride(0),
            logits.stride(1),
            output.stride(0),
            BLOCK_M=128,
            NUM_WARPS=4,
        )
    
    return output

class Solution:
    def solve(self, spec_path: str = None) -> dict:
        """
        Returns a dict with either:
        - {"code": "python_code_string"}
        - {"program_path": "path/to/kernel.py"}
        """
        # Return the code as a string
        import inspect
        code = inspect.getsource(inspect.getmodule(inspect.currentframe()))
        return {"code": code}
