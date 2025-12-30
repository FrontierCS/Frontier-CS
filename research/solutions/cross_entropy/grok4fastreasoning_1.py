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
import math

@triton.jit
def partial_max_kernel(
    logits_ptr, temp_max_ptr,
    stride_logits_m, stride_logits_n, stride_temp,
    M, N, num_blocks,
    BLOCK_N: tl.constexpr
):
    pid = tl.program_id(0)
    row = pid // num_blocks
    col_block = pid % num_blocks
    if row >= M:
        return
    start_n = col_block * BLOCK_N
    offsets_n = start_n + tl.arange(0, BLOCK_N)
    mask_n = offsets_n < N
    logits_offsets = row * stride_logits_m + offsets_n * stride_logits_n
    logits_block = tl.load(logits_ptr + logits_offsets, mask=mask_n, other=0.0)
    masked_logit = tl.where(mask_n, logits_block, -1e20)
    partial_max = tl.max(masked_logit, axis=0)
    temp_offset = row * num_blocks + col_block
    tl.store(temp_max_ptr + temp_offset * stride_temp, partial_max)

@triton.jit
def reduce_max_kernel(
    temp_max_ptr, max_out_ptr,
    stride_temp, stride_max_out,
    M, num_blocks,
    BLOCK_R: tl.constexpr
):
    pid = tl.program_id(0)
    if pid >= M:
        return
    offsets = tl.arange(0, BLOCK_R)
    mask = offsets < num_blocks
    partials = tl.load(temp_max_ptr + pid * num_blocks * stride_temp + offsets * stride_temp,
                       mask=mask, other=-1e20)
    row_max = tl.max(partials, axis=0)
    tl.store(max_out_ptr + pid * stride_max_out, row_max)

@triton.jit
def partial_sum_exp_kernel(
    logits_ptr, max_out_ptr, temp_sum_ptr,
    stride_logits_m, stride_logits_n,
    stride_max, stride_temp,
    M, N, num_blocks,
    BLOCK_N: tl.constexpr
):
    pid = tl.program_id(0)
    row = pid // num_blocks
    col_block = pid % num_blocks
    if row >= M:
        return
    row_max = tl.load(max_out_ptr + row * stride_max)
    start_n = col_block * BLOCK_N
    offsets_n = start_n + tl.arange(0, BLOCK_N)
    mask_n = offsets_n < N
    logits_offsets = row * stride_logits_m + offsets_n * stride_logits_n
    logits_block = tl.load(logits_ptr + logits_offsets, mask=mask_n, other=0.0)
    shifted = logits_block - row_max
    exp_block = tl.exp(shifted)
    masked_exp = tl.where(mask_n, exp_block, 0.0)
    partial_sum = tl.sum(masked_exp, axis=0)
    temp_offset = row * num_blocks + col_block
    tl.store(temp_sum_ptr + temp_offset * stride_temp, partial_sum)

@triton.jit
def reduce_sum_kernel(
    temp_sum_ptr, sum_out_ptr,
    stride_temp, stride_sum_out,
    M, num_blocks,
    BLOCK_R: tl.constexpr
):
    pid = tl.program_id(0)
    if pid >= M:
        return
    offsets = tl.arange(0, BLOCK_R)
    mask = offsets < num_blocks
    partials = tl.load(temp_sum_ptr + pid * num_blocks * stride_temp + offsets * stride_temp,
                       mask=mask, other=0.0)
    row_sum = tl.sum(partials, axis=0)
    tl.store(sum_out_ptr + pid * stride_sum_out, row_sum)

@triton.jit
def compute_loss_kernel(
    max_out_ptr, sum_out_ptr, logits_ptr, targets_ptr, output_ptr,
    stride_max, stride_sum,
    stride_logits_m, stride_logits_n,
    stride_targets, stride_output,
    M, N
):
    pid = tl.program_id(0)
    if pid >= M:
        return
    row_max = tl.load(max_out_ptr + pid * stride_max)
    row_sum_exp = tl.load(sum_out_ptr + pid * stride_sum)
    logsumexp = row_max + tl.log(row_sum_exp)
    tgt = tl.load(targets_ptr + pid * stride_targets, dtype=tl.int64)
    tgt_idx = tgt.to(tl.int32)
    tgt_offset = pid * stride_logits_m + tgt_idx * stride_logits_n
    tgt_logit = tl.load(logits_ptr + tgt_offset)
    loss = logsumexp - tgt_logit
    tl.store(output_ptr + pid * stride_output, loss)

def cross_entropy(logits: torch.Tensor, targets: torch.Tensor) -> torch.Tensor:
    device = logits.device
    dtype = logits.dtype
    M, N = logits.shape
    output = torch.empty((M,), dtype=torch.float32, device=device)
    if M == 0:
        return output
    BLOCK_N = 1024
    BLOCK_R = 32
    num_blocks = math.ceil(N / BLOCK_N)
    temp_max = torch.empty((M * num_blocks,), dtype=dtype, device=device)
    stride_logits_m = logits.stride(0)
    stride_logits_n = logits.stride(1)
    stride_temp = temp_max.stride(0)
    partial_max_kernel[(M * num_blocks,)](
        logits.data_ptr(), temp_max.data_ptr(),
        stride_logits_m, stride_logits_n, stride_temp,
        M, N, num_blocks,
        BLOCK_N=BLOCK_N
    )
    max_out = torch.empty((M,), dtype=dtype, device=device)
    stride_max_out = max_out.stride(0)
    reduce_max_kernel[(M,)](
        temp_max.data_ptr(), max_out.data_ptr(),
        stride_temp, stride_max_out,
        M, num_blocks,
        BLOCK_R=BLOCK_R
    )
    temp_sum = torch.empty((M * num_blocks,), dtype=dtype, device=device)
    stride_temp_s = temp_sum.stride(0)
    partial_sum_exp_kernel[(M * num_blocks,)](
        logits.data_ptr(), max_out.data_ptr(), temp_sum.data_ptr(),
        stride_logits_m, stride_logits_n,
        max_out.stride(0), stride_temp_s,
        M, N, num_blocks,
        BLOCK_N=BLOCK_N
    )
    sum_out = torch.empty((M,), dtype=dtype, device=device)
    stride_sum_out = sum_out.stride(0)
    reduce_sum_kernel[(M,)](
        temp_sum.data_ptr(), sum_out.data_ptr(),
        stride_temp_s, stride_sum_out,
        M, num_blocks,
        BLOCK_R=BLOCK_R
    )
    stride_targets = targets.stride(0)
    stride_output = output.stride(0)
    compute_loss_kernel[(M,)](
        max_out.data_ptr(), sum_out.data_ptr(),
        logits.data_ptr(), targets.data_ptr(), output.data_ptr(),
        max_out.stride(0), sum_out.stride(0),
        stride_logits_m, stride_logits_n,
        stride_targets, stride_output,
        M, N
    )
    return output
"""
        return {"code": code}