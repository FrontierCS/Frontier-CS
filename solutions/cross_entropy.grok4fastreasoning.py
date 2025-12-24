class Solution:
    def solve(self, spec_path: str = None) -> dict:
        code = """
import torch
import triton
import triton.language as tl

@triton.jit
def cross_entropy_kernel(
    logits_ptr,
    targets_ptr,
    output_ptr,
    M: tl.int32,
    N: tl.int32,
    stride_lm: tl.int64,
    stride_ln: tl.int64,
    stride_t: tl.int64,
    stride_o: tl.int64,
    BLOCK_SIZE: tl.constexpr
):
    pid = tl.program_id(0)
    if pid >= M:
        return

    target_i = tl.load(targets_ptr + pid * stride_t)
    target_offset = target_i * stride_ln
    logit_target = tl.load(logits_ptr + pid * stride_lm + target_offset)

    # Compute row_max
    partial_max = tl.full((BLOCK_SIZE,), float("-inf"), dtype=tl.float32)
    row_offset = pid * stride_lm
    for start in range(0, N, BLOCK_SIZE):
        col_offsets = start + tl.arange(0, BLOCK_SIZE)
        mask = col_offsets < N
        addr = row_offset + col_offsets.to(tl.int64) * stride_ln
        vals = tl.load(logits_ptr + addr, mask=mask, other=float("-inf"))
        partial_max = tl.maximum(partial_max, vals)
    row_max = tl.max(partial_max)

    # Compute sum of exp(val - row_max)
    partial_sum = tl.zeros((BLOCK_SIZE,), dtype=tl.float32)
    for start in range(0, N, BLOCK_SIZE):
        col_offsets = start + tl.arange(0, BLOCK_SIZE)
        mask = col_offsets < N
        addr = row_offset + col_offsets.to(tl.int64) * stride_ln
        vals = tl.load(logits_ptr + addr, mask=mask, other=0.0)
        mask_f = tl.where(mask, 1.0, 0.0)
        centered = vals - row_max
        exps = tl.exp(centered) * mask_f
        partial_sum += exps
    row_sum = tl.sum(partial_sum)

    logsumexp = row_max + tl.log(row_sum)
    loss = logsumexp - logit_target

    # Store by thread 0
    pid_local = tl.arange(0, BLOCK_SIZE)[0]
    if pid_local == 0:
        tl.store(output_ptr + pid * stride_o, loss)

def cross_entropy(logits: torch.Tensor, targets: torch.Tensor) -> torch.Tensor:
    if logits.shape[0] != targets.shape[0]:
        raise ValueError("Batch sizes must match")
    if targets.dtype != torch.int64:
        targets = targets.to(torch.int64)
    M, N = logits.shape
    output = torch.empty((M,), dtype=torch.float32, device=logits.device)
    if M == 0:
        return output

    stride_lm = logits.stride(0)
    stride_ln = logits.stride(1)
    stride_t = targets.stride(0)
    stride_o = output.stride(0)

    BLOCK_SIZE = 1024
    grid = (M,)
    cross_entropy_kernel[grid](
        logits,
        targets,
        output,
        M,
        N,
        tl.int64(stride_lm),
        tl.int64(stride_ln),
        tl.int64(stride_t),
        tl.int64(stride_o),
        BLOCK_SIZE=BLOCK_SIZE,
    )
    return output
"""
        return {"code": code}
