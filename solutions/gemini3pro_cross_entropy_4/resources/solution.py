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

@triton.autotune(
    configs=[
        triton.Config({'BLOCK_SIZE': 1024}, num_warps=4),
        triton.Config({'BLOCK_SIZE': 2048}, num_warps=8),
        triton.Config({'BLOCK_SIZE': 4096}, num_warps=8),
        triton.Config({'BLOCK_SIZE': 8192}, num_warps=8),
    ],
    key=['N']
)
@triton.jit
def cross_entropy_kernel(
    logits_ptr, targets_ptr, out_ptr,
    stride_logits_m, stride_logits_n,
    stride_targets_m, stride_out_m,
    N,
    BLOCK_SIZE: tl.constexpr
):
    # One program instance per row
    row_idx = tl.program_id(0)
    
    # Calculate pointers for the current row
    logits_row_ptr = logits_ptr + row_idx * stride_logits_m
    target_idx_ptr = targets_ptr + row_idx * stride_targets_m
    out_row_ptr = out_ptr + row_idx * stride_out_m
    
    # Load target class index for this row
    target_idx = tl.load(target_idx_ptr)
    
    # Fetch the specific logit corresponding to the target class
    # This avoids iterating to find it, improving performance
    target_logit_ptr = logits_row_ptr + target_idx * stride_logits_n
    target_val = tl.load(target_logit_ptr).to(tl.float32)
    
    # Online Softmax / LogSumExp Computation
    # Uses the numerically stable online update to compute:
    # log(sum(exp(x_i))) = m_final + log(sum(exp(x_i - m_final)))
    
    m_prev = -float('inf')
    d_prev = 0.0
    
    # Loop over the row in chunks defined by BLOCK_SIZE
    for off in range(0, N, BLOCK_SIZE):
        cols = off + tl.arange(0, BLOCK_SIZE)
        mask = cols < N
        
        # Load chunk of logits
        # Cast to float32 is crucial for accumulation precision and stability
        a_ptr = logits_row_ptr + cols * stride_logits_n
        val = tl.load(a_ptr, mask=mask, other=-float('inf')).to(tl.float32)
        
        # Compute max in current chunk
        m_curr = tl.max(val, 0)
        
        # Update global max
        m_new = tl.maximum(m_prev, m_curr)
        
        # Update running sum of exponentials
        # d_prev is rescaled by exp(m_prev - m_new) to align with new max
        d_prev = d_prev * tl.exp(m_prev - m_new) + tl.sum(tl.exp(val - m_new), 0)
        
        # Update previous max
        m_prev = m_new

    # Calculate final loss
    # Loss = LogSumExp - TargetLogit
    # LogSumExp = m_prev + log(d_prev)
    lse = m_prev + tl.log(d_prev)
    loss = lse - target_val
    
    # Store result
    tl.store(out_row_ptr, loss)

def cross_entropy(logits: torch.Tensor, targets: torch.Tensor) -> torch.Tensor:
    M, N = logits.shape
    
    # Ensure outputs are contiguous float32 for best performance
    out = torch.empty(M, device=logits.device, dtype=torch.float32)
    
    # Grid creates one kernel instance per row (batch element)
    grid = (M,)
    
    # Launch kernel
    cross_entropy_kernel[grid](
        logits, targets, out,
        logits.stride(0), logits.stride(1),
        targets.stride(0), out.stride(0),
        N
    )
    
    return out
"""
        }
