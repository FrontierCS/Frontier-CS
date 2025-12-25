import torch
import triton
import triton.language as tl

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
    stride_m, stride_n, stride_t, stride_o,
    BLOCK_N: tl.constexpr
):
    pid_m = tl.program_id(0)
    if pid_m >= M:
        return

    target_offset = pid_m * stride_t
    target = tl.load(targets_ptr + target_offset).to(tl.int32)

    # Compute max
    max_val = tl.full([], float("-inf"), dtype=tl.float32)
    block_start = 0
    while block_start < N:
        num_elem = tl.minimum(BLOCK_N, N - block_start)
        offs = tl.arange(0, num_elem)
        col_offsets = (block_start + offs) * stride_n
        x_ptrs = logits_ptr + pid_m * stride_m + col_offsets
        x = tl.load(x_ptrs)
        local_max = tl.max(x, axis=0)
        max_val = tl.maximum(max_val, local_max)
        block_start += BLOCK_N

    # Compute sum of exps
    sum_exp = tl.zeros([], dtype=tl.float32)
    block_start = 0
    while block_start < N:
        num_elem = tl.minimum(BLOCK_N, N - block_start)
        offs = tl.arange(0, num_elem)
        col_offsets = (block_start + offs) * stride_n
        x_ptrs = logits_ptr + pid_m * stride_m + col_offsets
        x = tl.load(x_ptrs)
        x_minus_max = x - max_val
        exp_x = tl.exp(x_minus_max)
        local_sum = tl.sum(exp_x, axis=0)
        sum_exp += local_sum
        block_start += BLOCK_N

    log_sum_exp = tl.log(sum_exp) + max_val

    # Load logit at target
    target_offset_bytes = target * stride_n
    l_ptr = logits_ptr + pid_m * stride_m + target_offset_bytes
    logit_target = tl.load(l_ptr)

    # Compute loss
    loss = -(logit_target - log_sum_exp)

    # Store
    output_offset = pid_m * stride_o
    tl.store(output_ptr + output_offset, loss)

def cross_entropy(logits: torch.Tensor, targets: torch.Tensor) -> torch.Tensor:
    M, N = logits.shape
    output = torch.empty((M,), dtype=torch.float32, device=logits.device)
    stride_m_bytes = logits.stride(0) * logits.element_size()
    stride_n_bytes = logits.stride(1) * logits.element_size()
    stride_t_bytes = targets.stride(0) * targets.element_size()
    stride_o_bytes = output.stride(0) * output.element_size()
    grid = (M,)
    cross_entropy_kernel[grid](
        logits.data_ptr(),
        targets.data_ptr(),
        output.data_ptr(),
        M,
        N,
        stride_m_bytes,
        stride_n_bytes,
        stride_t_bytes,
        stride_o_bytes,
        BLOCK_N=1024
    )
    return output
"""
        return {"code": code}
