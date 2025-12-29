class Solution:
  def solve(self, spec_path: str = None) -> dict:
    cross_entropy_code = """
import torch
import triton
import triton.language as tl

@triton.autotune(
    configs=[
        triton.Config({'BLOCK_SIZE_N': 512}, num_warps=4, num_stages=4),
        triton.Config({'BLOCK_SIZE_N': 1024}, num_warps=4, num_stages=3),
        triton.Config({'BLOCK_SIZE_N': 2048}, num_warps=8, num_stages=3),
        triton.Config({'BLOCK_SIZE_N': 4096}, num_warps=8, num_stages=2),
        triton.Config({'BLOCK_SIZE_N': 8192}, num_warps=16, num_stages=2),
        triton.Config({'BLOCK_SIZE_N': 4096}, num_warps=16, num_stages=3),
        triton.Config({'BLOCK_SIZE_N': 2048}, num_warps=16, num_stages=4),
    ],
    key=['N'],
)
@triton.jit
def _cross_entropy_kernel(
    logits_ptr, targets_ptr, output_ptr,
    M, N,
    stride_logits_m, stride_logits_n,
    BLOCK_SIZE_N: tl.constexpr,
):
    pid = tl.program_id(axis=0)
    row_start_ptr = logits_ptr + pid * stride_logits_m
    offs_n = tl.arange(0, BLOCK_SIZE_N)

    row_max = -float('inf')
    lse_sum = 0.0

    for k in range(0, tl.cdiv(N, BLOCK_SIZE_N)):
        current_offs_n = (k * BLOCK_SIZE_N) + offs_n
        mask = current_offs_n < N
        
        logits_chunk = tl.load(row_start_ptr + current_offs_n * stride_logits_n, mask=mask, other=-float('inf'))
        logits_chunk_f32 = logits_chunk.to(tl.float32)

        chunk_max = tl.max(logits_chunk_f32, axis=0)
        new_max = tl.maximum(row_max, chunk_max)
        
        lse_sum = lse_sum * tl.exp(row_max - new_max)
        lse_sum += tl.sum(tl.exp(logits_chunk_f32 - new_max), axis=0)
        row_max = new_max
    
    lse = row_max + tl.log(lse_sum)

    target_idx = tl.load(targets_ptr + pid)
    target_logit_ptr = logits_ptr + pid * stride_logits_m + target_idx * stride_logits_n
    target_logit = tl.load(target_logit_ptr).to(tl.float32)

    loss = lse - target_logit
    tl.store(output_ptr + pid, loss)


def cross_entropy(logits: torch.Tensor, targets: torch.Tensor) -> torch.Tensor:
    \"\"\"
    Cross entropy loss computation.
    
    Args:
        logits: Input tensor of shape (M, N) - logits for M samples and N classes
        targets: Input tensor of shape (M,) - target class indices (int64)
    
    Returns:
        Output tensor of shape (M,) - negative log-likelihood loss for each sample
    \"\"\"
    M, N = logits.shape
    
    output = torch.empty(M, dtype=torch.float32, device=logits.device)
    
    grid = (M,)
    
    _cross_entropy_kernel[grid](
        logits, targets, output,
        M, N,
        logits.stride(0), logits.stride(1),
    )
    
    return output
"""
    return {"code": cross_entropy_code}