class Solution:
    def solve(self, spec_path: str = None) -> dict:
        code = '''
import torch
import triton
import triton.language as tl

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
    device = logits.device
    dtype = torch.float32
    loss = torch.empty((M,), dtype=dtype, device=device)
    if M == 0 or N == 0:
        return loss
    stride_m, stride_n = logits.stride()
    stride_t = targets.stride(0)
    stride_l = loss.stride(0)

    @triton.jit
    def kernel(
        logits_ptr, targets_ptr, loss_ptr,
        M: tl.int32, N: tl.int32,
        stride_m: tl.int64, stride_n: tl.int64,
        stride_t: tl.int64, stride_l: tl.int64,
        BLOCK_N: tl.constexpr
    ):
        pid = tl.program_id(0)
        if pid >= M:
            return

        row_start = logits_ptr + pid * stride_m
        target = tl.load(targets_ptr + pid * stride_t)
        target_idx = tl.int32(target)

        # First tile
        start_n = 0
        end_n = tl.minimum(BLOCK_N, N)
        offs_n = tl.arange(0, BLOCK_N)
        mask = offs_n < end_n
        col_idx = offs_n.to(tl.int64)
        ptr = row_start + col_idx * stride_n
        tile = tl.load(ptr, mask=mask, other=-float("inf"))
        max_val = tl.max(tile)
        sum_exp = tl.sum(tl.exp(tile - max_val))

        # Subsequent tiles
        for start_n in range(BLOCK_N, N, BLOCK_N):
            end_n = tl.minimum(start_n + BLOCK_N, N)
            len_tile = end_n - start_n
            offs_n = tl.arange(0, BLOCK_N)
            mask = offs_n < len_tile
            col_idx = (start_n + offs_n).to(tl.int64)
            ptr = row_start + col_idx * stride_n
            tile = tl.load(ptr, mask=mask, other=-float("inf"))
            tile_max = tl.max(tile)
            tile_sum = tl.sum(tl.exp(tile - tile_max))
            cond = tile_max > max_val
            exp_old_to_new = tl.exp(max_val - tile_max)
            exp_new_to_old = tl.exp(tile_max - max_val)
            new_sum = tl.where(
                cond,
                sum_exp * exp_old_to_new + tile_sum,
                sum_exp + tile_sum * exp_new_to_old
            )
            new_max = tl.where(cond, tile_max, max_val)
            sum_exp = new_sum
            max_val = new_max

        logsumexp = max_val + tl.log(sum_exp)
        target_ptr = row_start + target_idx * stride_n
        logit_target = tl.load(target_ptr)
        loss_val = logsumexp - logit_target
        tl.store(loss_ptr + pid * stride_l, loss_val)

    BLOCK_N = 1024
    grid = (M,)
    kernel[grid](
        logits, targets, loss,
        M, N,
        stride_m, stride_n,
        stride_t, stride_l,
        BLOCK_N=BLOCK_N
    )
    return loss
'''
        return {"code": code}
