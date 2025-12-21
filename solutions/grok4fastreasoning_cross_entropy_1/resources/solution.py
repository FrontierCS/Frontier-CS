import torch
import triton
import triton.language as tl
import math

class Solution:
    def solve(self, spec_path: str = None) -> dict:
        code = """
import torch
import triton
import triton.language as tl

@triton.jit
def cross_entropy_kernel(
    logits_ptr, targets_ptr, output_ptr,
    M: tl.int32, N: tl.int32,
    stride_logits_m: tl.int32, stride_logits_n: tl.int32,
    stride_targets: tl.int32, stride_output: tl.int32,
    BLOCK_N: tl.constexpr
):
    pid = tl.program_id(0)
    if pid >= M:
        return

    target_i = tl.load(targets_ptr + pid * stride_targets).to(tl.int32)
    target_offset = pid * stride_logits_m + target_i * stride_logits_n
    target_logit = tl.load(logits_ptr + target_offset)

    # Compute max
    max_val = -1e9
    for start in range(0, N, BLOCK_N):
        col_offs = tl.arange(0, BLOCK_N)
        mask = col_offs < (N - start)
        offs = pid * stride_logits_m + (start + col_offs) * stride_logits_n
        x = tl.load(logits_ptr + offs, mask=mask, other=-1e9)
        max_val = tl.maximum(max_val, tl.max(x, axis=0))

    # Compute sum of exps
    sum_exp = 0.0
    for start in range(0, N, BLOCK_N):
        col_offs = tl.arange(0, BLOCK_N)
        mask = col_offs < (N - start)
        offs = pid * stride_logits_m + (start + col_offs) * stride_logits_n
        x = tl.load(logits_ptr + offs, mask=mask, other=0.0)
        x = tl.exp(x - max_val)
        sum_exp += tl.sum(x, axis=0)

    logsumexp = max_val + tl.log(sum_exp)
    loss = target_logit - logsumexp
    tl.store(output_ptr + pid * stride_output, loss)


def cross_entropy(logits: torch.Tensor, targets: torch.Tensor) -> torch.Tensor:
    M, N = logits.shape
    output = torch.empty((M,), dtype=torch.float32, device=logits.device)
    if M == 0:
        return output
    stride_lm = logits.stride(0)
    stride_ln = logits.stride(1)
    stride_t = targets.stride(0)
    stride_o = output.stride(0)
    BLOCK_N = 1024
    cross_entropy_kernel[(M,)](
        logits, targets, output,
        torch.int32(M), torch.int32(N),
        torch.int32(stride_lm), torch.int32(stride_ln),
        torch.int32(stride_t), torch.int32(stride_o),
        BLOCK_N=BLOCK_N,
        num_stages=3,
        num_warps=4
    )
    return output
"""
        return {"code": code}
