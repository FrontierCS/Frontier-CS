import torch
import triton
import triton.language as tl
import os
import json

@triton.autotune(
    configs=[
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 256}, num_warps=4, num_stages=3),
        triton.Config({'BLOCK_M': 256, 'BLOCK_N': 128}, num_warps=4, num_stages=3),
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 512}, num_warps=4, num_stages=2),
        triton.Config({'BLOCK_M': 256, 'BLOCK_N': 256}, num_warps=4, num_stages=3),
        triton.Config({'BLOCK_M': 512, 'BLOCK_N': 128}, num_warps=8, num_stages=2),
        triton.Config({'BLOCK_M': 64, 'BLOCK_N': 512}, num_warps=4, num_stages=3),
        triton.Config({'BLOCK_M': 256, 'BLOCK_N': 512}, num_warps=8, num_stages=2),
        triton.Config({'BLOCK_M': 512, 'BLOCK_N': 256}, num_warps=8, num_stages=2),
    ],
    key=['M', 'N'],
)
@triton.jit
def cross_entropy_kernel(
    logits_ptr, targets_ptr, output_ptr,
    M, N,
    logits_stride_m, logits_stride_n,
    targets_stride,
    output_stride,
    BLOCK_M: tl.constexpr, BLOCK_N: tl.constexpr,
):
    pid_m = tl.program_id(0)
    pid_n = tl.program_id(1)
    
    m_offset = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
    n_offset = pid_n * BLOCK_N + tl.arange(0, BLOCK_N)
    
    mask_m = m_offset < M
    mask_n = n_offset < N
    
    logits_ptrs = (
        logits_ptr + 
        m_offset[:, None] * logits_stride_m + 
        n_offset[None, :] * logits_stride_n
    )
    
    logits_block = tl.load(logits_ptrs, mask=mask_m[:, None] & mask_n[None, :], other=-float('inf'))
    
    max_vals = tl.max(logits_block, axis=1)
    
    logits_exp = tl.exp(logits_block - max_vals[:, None])
    sum_exp = tl.sum(logits_exp, axis=1)
    
    log_sum_exp = tl.log(sum_exp) + max_vals
    
    if pid_n == 0:
        output_ptrs = output_ptr + m_offset * output_stride
        tl.store(output_ptrs, -log_sum_exp, mask=mask_m)
    
    if pid_n == 0:
        targets_ptrs = targets_ptr + m_offset * targets_stride
        target_indices = tl.load(targets_ptrs, mask=mask_m, other=0)
        
        for k in range(tl.cdiv(N, BLOCK_N)):
            n_offset_k = k * BLOCK_N + tl.arange(0, BLOCK_N)
            mask_n_k = n_offset_k < N
            
            logits_ptrs_k = (
                logits_ptr + 
                m_offset[:, None] * logits_stride_m + 
                n_offset_k[None, :] * logits_stride_n
            )
            logits_block_k = tl.load(logits_ptrs_k, mask=mask_m[:, None] & mask_n_k[None, :], other=0)
            
            target_mask = target_indices[:, None] == n_offset_k[None, :]
            target_logits = tl.sum(logits_block_k * target_mask, axis=1)
            
            output_ptrs = output_ptr + m_offset * output_stride
            current = tl.load(output_ptrs, mask=mask_m, other=0)
            tl.store(output_ptrs, current + target_logits, mask=mask_m)

@triton.autotune(
    configs=[
        triton.Config({'BLOCK_M': 256}, num_warps=8),
        triton.Config({'BLOCK_M': 128}, num_warps=4),
        triton.Config({'BLOCK_M': 512}, num_warps=8),
        triton.Config({'BLOCK_M': 1024}, num_warps=8),
    ],
    key=['M'],
)
@triton.jit
def cross_entropy_fused_kernel(
    logits_ptr, targets_ptr, output_ptr,
    M, N,
    logits_stride_m, logits_stride_n,
    targets_stride,
    output_stride,
    BLOCK_M: tl.constexpr,
):
    pid = tl.program_id(0)
    m_offset = pid * BLOCK_M + tl.arange(0, BLOCK_M)
    mask = m_offset < M
    
    targets_ptrs = targets_ptr + m_offset * targets_stride
    target_indices = tl.load(targets_ptrs, mask=mask, other=0)
    
    max_val = tl.full((BLOCK_M,), -float('inf'), tl.float32)
    sum_exp = tl.zeros((BLOCK_M,), tl.float32)
    target_logit = tl.zeros((BLOCK_M,), tl.float32)
    
    for n in range(0, N):
        logits_ptrs = logits_ptr + m_offset[:, None] * logits_stride_m + n * logits_stride_n
        logits_val = tl.load(logits_ptrs, mask=mask[:, None], other=-float('inf'))
        
        max_val = tl.maximum(max_val, logits_val)
        
        target_mask = target_indices == n
        target_logit = tl.where(target_mask, logits_val, target_logit)
    
    for n in range(0, N):
        logits_ptrs = logits_ptr + m_offset[:, None] * logits_stride_m + n * logits_stride_n
        logits_val = tl.load(logits_ptrs, mask=mask[:, None], other=-float('inf'))
        
        exp_val = tl.exp(logits_val - max_val)
        sum_exp += exp_val
    
    log_sum_exp = tl.log(sum_exp) + max_val
    loss = -target_logit + log_sum_exp
    
    output_ptrs = output_ptr + m_offset * output_stride
    tl.store(output_ptrs, loss, mask=mask)

def cross_entropy(logits: torch.Tensor, targets: torch.Tensor) -> torch.Tensor:
    if logits.numel() == 0:
        return torch.empty_like(logits[:, 0])
    
    M, N = logits.shape
    assert targets.shape == (M,), f"Targets shape {targets.shape} doesn't match batch size {M}"
    
    output = torch.empty(M, device=logits.device, dtype=logits.dtype)
    
    if N <= 8192:
        grid = lambda META: (
            triton.cdiv(M, META['BLOCK_M']),
        )
        cross_entropy_fused_kernel[grid](
            logits, targets, output,
            M, N,
            logits.stride(0), logits.stride(1),
            targets.stride(0),
            output.stride(0),
        )
    else:
        grid = lambda META: (
            triton.cdiv(M, META['BLOCK_M']),
            triton.cdiv(N, META['BLOCK_N']),
        )
        cross_entropy_kernel[grid](
            logits, targets, output,
            M, N,
            logits.stride(0), logits.stride(1),
            targets.stride(0),
            output.stride(0),
        )
    
    return output

class Solution:
    def solve(self, spec_path: str = None) -> dict:
        return {"code": f"""
import torch
import triton
import triton.language as tl

{inspect.getsource(cross_entropy_kernel).replace('@triton.autotune(.*?)\n@triton.jit', '@triton.autotune(\\1)\\n@triton.jit', flags=re.DOTALL)}

{inspect.getsource(cross_entropy_fused_kernel).replace('@triton.autotune(.*?)\n@triton.jit', '@triton.autotune(\\1)\\n@triton.jit', flags=re.DOTALL)}

{inspect.getsource(cross_entropy)}

if __name__ == "__main__":
    import numpy as np
    
    torch.manual_seed(42)
    M, N = 1024, 8192
    logits = torch.randn(M, N, device='cuda', dtype=torch.float32)
    targets = torch.randint(0, N, (M,), device='cuda', dtype=torch.int64)
    
    output = cross_entropy(logits, targets)
    print(f"Output shape: {{output.shape}}")
    print(f"First 5 values: {{output[:5]}}")
"""}
