import torch

class Solution:
    def solve(self, spec_path: str = None) -> dict:
        """
        Returns a dict with either:
        - {"code": "python_code_string"}
        - {"program_path": "path/to/kernel.py"}
        """
        cross_entropy_code = '''
import torch
import triton
import triton.language as tl

@triton.autotune(
    configs=[
        triton.Config({'BLOCK_SIZE_N': 512}, num_warps=4),
        triton.Config({'BLOCK_SIZE_N': 1024}, num_warps=4),
        triton.Config({'BLOCK_SIZE_N': 2048}, num_warps=8),
        triton.Config({'BLOCK_SIZE_N': 4096}, num_warps=8),
        triton.Config({'BLOCK_SIZE_N': 8192}, num_warps=16),
    ],
    key=['N'],
)
@triton.jit
def _cross_entropy_kernel(
    logits_ptr, targets_ptr, output_ptr,
    M, N,
    stride_logits_m, stride_logits_n,
    stride_targets_m,
    stride_output_m,
    BLOCK_SIZE_N: tl.constexpr,
):
    pid = tl.program_id(axis=0)
    row_logits_ptr = logits_ptr + pid * stride_logits_m

    m = -float('inf')
    s = 0.0
    offs_n = tl.arange(0, BLOCK_SIZE_N)
    
    for block_idx in range(0, tl.cdiv(N, BLOCK_SIZE_N)):
        current_offs_n = block_idx * BLOCK_SIZE_N + offs_n
        mask = current_offs_n < N
        
        logits_block = tl.load(row_logits_ptr + current_offs_n * stride_logits_n, mask=mask, other=-float('inf'))
        logits_block = logits_block.to(tl.float32)

        m_k = tl.max(logits_block, axis=0)
        m_new = tl.maximum(m, m_k)
        
        s = s * tl.exp(m - m_new)
        s += tl.sum(tl.exp(logits_block - m_new), axis=0)
        
        m = m_new

    log_sum_exp = m + tl.log(s)

    target_idx_ptr = targets_ptr + pid * stride_targets_m
    target_idx = tl.load(target_idx_ptr)
    
    target_logit_ptr = row_logits_ptr + target_idx * stride_logits_n
    target_logit = tl.load(target_logit_ptr).to(tl.float32)

    loss = log_sum_exp - target_logit

    output_ptr_row = output_ptr + pid * stride_output_m
    tl.store(output_ptr_row, loss)


def cross_entropy(logits: torch.Tensor, targets: torch.Tensor) -> torch.Tensor:
    """
    Cross entropy loss computation.
    
    Args:
        logits: Input tensor of shape (M, N) - logits for M samples and N classes
        targets: Input tensor of shape (M,) - target class indices (int64)
    
    Returns:
        Output tensor of shape (M,) - negative log-likelihood loss for each sample
    """
    M, N = logits.shape
    
    loss = torch.empty(M, device=logits.device, dtype=torch.float32)
    
    grid = (M,)
    
    _cross_entropy_kernel[grid](
        logits,
        targets,
        loss,
        M,
        N,
        logits.stride(0),
        logits.stride(1),
        targets.stride(0),
        loss.stride(0),
    )
    
    return loss
'''
        return {"code": cross_entropy_code}