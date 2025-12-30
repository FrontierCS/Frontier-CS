class Solution:
    def solve(self, spec_path: str = None) -> dict:
        code = """
import torch
import triton
import triton.language as tl

@triton.jit
def cross_entropy_kernel(
    logits_ptr, targets_ptr, output_ptr,
    M, N,
    stride_m_logits, stride_n_logits,
    stride_targets, stride_output,
    BLOCK_N: tl.constexpr
):
    pid_m = tl.program_id(0)
    if pid_m >= M:
        return

    base = pid_m * stride_m_logits
    target = tl.load(targets_ptr + pid_m * stride_targets)
    target_logit = tl.load(base + target * stride_n_logits)

    # First pass: compute row_max
    row_max = tl.float32(-1e9)
    cur_col = tl.int32(0)
    N_i32 = tl.int32(N)
    while cur_col < N_i32:
        remaining = N_i32 - cur_col
        tile_size = tl.minimum(tl.int32(BLOCK_N), remaining)
        tile_offsets = tl.arange(0, tile_size)
        col_idx = cur_col + tile_offsets
        load_offsets = base + col_idx.to(tl.int64) * stride_n_logits
        logits_tile = tl.load(load_offsets)
        tile_max = tl.max(logits_tile)
        row_max = tl.maximum(row_max, tile_max)
        cur_col += tile_size

    # Second pass: compute sum_exp
    sum_exp = tl.float32(0.0)
    cur_col = tl.int32(0)
    while cur_col < N_i32:
        remaining = N_i32 - cur_col
        tile_size = tl.minimum(tl.int32(BLOCK_N), remaining)
        tile_offsets = tl.arange(0, tile_size)
        col_idx = cur_col + tile_offsets
        load_offsets = base + col_idx.to(tl.int64) * stride_n_logits
        logits_tile = tl.load(load_offsets)
        tile_exp = tl.exp(logits_tile - row_max)
        sum_exp += tl.sum(tile_exp)
        cur_col += tile_size

    log_sum_exp = row_max + tl.log(sum_exp)
    loss = -(target_logit - log_sum_exp)
    tl.store(output_ptr + pid_m * stride_output, loss)

def cross_entropy(logits: torch.Tensor, targets: torch.Tensor) -> torch.Tensor:
    M, N = logits.shape
    output = torch.empty((M,), dtype=torch.float32, device=logits.device)
    logits_ptr = logits.data_ptr()
    targets_ptr = targets.data_ptr()
    output_ptr = output.data_ptr()
    stride_m_logits = logits.stride(0)
    stride_n_logits = logits.stride(1)
    stride_targets = targets.stride(0)
    stride_output = output.stride(0)
    BLOCK_N = 1024
    num_warps = 32
    grid = (M,)
    cross_entropy_kernel[grid](
        logits_ptr, targets_ptr, output_ptr,
        M, N,
        stride_m_logits, stride_n_logits,
        stride_targets, stride_output,
        BLOCK_N=BLOCK_N,
        num_warps=num_warps
    )
    return output
"""
        return {"code": code}