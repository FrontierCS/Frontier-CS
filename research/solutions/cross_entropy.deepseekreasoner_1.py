import torch
import triton
import triton.language as tl

@triton.autotune(
    configs=[
        triton.Config({'BLOCK_SIZE_M': 128, 'BLOCK_SIZE_N': 128}, num_warps=4),
        triton.Config({'BLOCK_SIZE_M': 256, 'BLOCK_SIZE_N': 128}, num_warps=4),
        triton.Config({'BLOCK_SIZE_M': 128, 'BLOCK_SIZE_N': 256}, num_warps=4),
        triton.Config({'BLOCK_SIZE_M': 256, 'BLOCK_SIZE_N': 256}, num_warps=4),
        triton.Config({'BLOCK_SIZE_M': 512, 'BLOCK_SIZE_N': 128}, num_warps=4),
        triton.Config({'BLOCK_SIZE_M': 128, 'BLOCK_SIZE_N': 512}, num_warps=4),
        triton.Config({'BLOCK_SIZE_M': 256, 'BLOCK_SIZE_N': 512}, num_warps=8),
        triton.Config({'BLOCK_SIZE_M': 512, 'BLOCK_SIZE_N': 256}, num_warps=8),
        triton.Config({'BLOCK_SIZE_M': 512, 'BLOCK_SIZE_N': 512}, num_warps=8),
    ],
    key=['M', 'N']
)
@triton.jit
def _cross_entropy_kernel(
    logits_ptr, targets_ptr, output_ptr,
    M, N,
    stride_logits_m, stride_logits_n,
    BLOCK_SIZE_M: tl.constexpr, BLOCK_SIZE_N: tl.constexpr
):
    pid_m = tl.program_id(0)
    
    # Load targets for this block of rows
    row_start = pid_m * BLOCK_SIZE_M
    row_offsets = row_start + tl.arange(0, BLOCK_SIZE_M)
    row_mask = row_offsets < M
    targets = tl.load(targets_ptr + row_offsets, mask=row_mask, other=0)
    
    # Initialize accumulators for max and sum_exp
    max_val = tl.full((BLOCK_SIZE_M,), float('-inf'), dtype=tl.float32)
    sum_exp = tl.zeros((BLOCK_SIZE_M,), dtype=tl.float32)
    target_logits = tl.zeros((BLOCK_SIZE_M,), dtype=tl.float32)
    
    # Process logits in blocks of columns
    for col_start in range(0, N, BLOCK_SIZE_N):
        col_offsets = col_start + tl.arange(0, BLOCK_SIZE_N)
        col_mask = col_offsets < N
        
        # Create 2D mask for valid entries
        valid_mask = row_mask[:, None] & col_mask[None, :]
        
        # Load block of logits
        logits_ptrs = (logits_ptr + 
                      row_offsets[:, None] * stride_logits_m + 
                      col_offsets[None, :] * stride_logits_n)
        logits_block = tl.load(logits_ptrs, mask=valid_mask, other=float('-inf'))
        
        # Update max values
        max_val_new = tl.maximum(max_val[:, None], logits_block)
        max_val_new = tl.max(max_val_new, axis=1)
        
        # Compute scaling for numerical stability
        scale_old = tl.exp(max_val - max_val_new)
        scale_new = tl.exp(logits_block - max_val_new[:, None])
        
        # Update sum_exp
        sum_exp = sum_exp * scale_old + tl.sum(scale_new, axis=1)
        max_val = max_val_new
        
        # Extract target logits using 2D indexing
        target_mask = (col_offsets[None, :] == targets[:, None]) & valid_mask
        target_logits_block = tl.sum(logits_block * target_mask, axis=1)
        target_logits += target_logits_block
    
    # Compute final loss: -target_logit + log(sum_exp) + max_val
    log_sum_exp = tl.log(sum_exp) + max_val
    loss = log_sum_exp - target_logits
    
    # Store results
    tl.store(output_ptr + row_offsets, loss, mask=row_mask)

@triton.jit
def _cross_entropy_small_kernel(
    logits_ptr, targets_ptr, output_ptr,
    M, N,
    stride_logits_m, stride_logits_n
):
    pid = tl.program_id(0)
    
    if pid >= M:
        return
    
    # Load target for this row
    target_idx = tl.load(targets_ptr + pid)
    
    # Initialize accumulators
    max_val = float('-inf')
    sum_exp = 0.0
    target_logit = 0.0
    
    # Process entire row
    for i in range(0, N, 1024):
        col_offsets = i + tl.arange(0, 1024)
        mask = col_offsets < N
        
        # Load chunk of logits
        logits_chunk = tl.load(
            logits_ptr + pid * stride_logits_m + col_offsets * stride_logits_n,
            mask=mask,
            other=float('-inf')
        )
        
        # Update max
        chunk_max = tl.max(logits_chunk, axis=0)
        max_val_new = tl.maximum(max_val, chunk_max)
        
        # Update sum_exp with numerical stability
        scale_old = tl.exp(max_val - max_val_new)
        scale_new = tl.exp(logits_chunk - max_val_new)
        
        sum_exp = sum_exp * scale_old + tl.sum(scale_new, axis=0)
        max_val = max_val_new
        
        # Check if target is in this chunk
        target_in_chunk = (col_offsets == target_idx) & mask
        target_logit += tl.sum(logits_chunk * target_in_chunk, axis=0)
    
    # Compute loss
    log_sum_exp = tl.log(sum_exp) + max_val
    loss = log_sum_exp - target_logit
    
    tl.store(output_ptr + pid, loss)

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
    
    # Allocate output tensor
    loss = torch.empty(M, device=device, dtype=torch.float32)
    
    # Choose kernel based on size
    if N <= 1024:
        # For small vocab sizes, use simpler kernel
        grid = (triton.cdiv(M, 1),)
        _cross_entropy_small_kernel[grid](
            logits, targets, loss,
            M, N,
            logits.stride(0), logits.stride(1)
        )
    else:
        # For larger vocab sizes, use tiled kernel
        grid = (triton.cdiv(M, 128),)
        _cross_entropy_kernel[grid](
            logits, targets, loss,
            M, N,
            logits.stride(0), logits.stride(1),
            BLOCK_SIZE_M=128, BLOCK_SIZE_N=256
        )
    
    return loss

class Solution:
    def solve(self, spec_path: str = None) -> dict:
        return {"code": self._get_code()}
    
    def _get_code(self) -> str:
        import inspect
        return inspect.getsource(__module__)
