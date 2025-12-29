class Solution:
    def solve(self, spec_path: str = None) -> dict:
        code = """
import torch
import triton
import triton.language as tl

configs = [
    triton.Config({'BLOCK_N': 256}),
    triton.Config({'BLOCK_N': 512}),
    triton.Config({'BLOCK_N': 1024}),
]

@triton.autotune(
    configs=configs,
    key=['N'],
)
@triton.jit
def cross_entropy_kernel(
    logits_ptr,
    targets_ptr,
    output_ptr,
    M,
    N,
    STRIDE_M,
    STRIDE_N,
    STRIDE_T,
    STRIDE_O,
    BLOCK_N: tl.constexpr,
):
    pid = tl.program_id(0)
    if pid >= M:
        return
    m = pid

    target_offset = m * STRIDE_T
    target = tl.load(targets_ptr + target_offset)

    # First pass: compute max_logit
    max_logit = -1e9
    for start_n in range(0, N, BLOCK_N):
        col_indices = start_n + tl.arange(0, BLOCK_N)
        mask = col_indices < N
        offsets = m * STRIDE_M + col_indices * STRIDE_N
        chunk = tl.load(logits_ptr + offsets, mask=mask, other=-1e9)
        local_max = tl.max(chunk, axis=0)
        max_logit = tl.maximum(max_logit, local_max)

    # Second pass: compute sum_exp
    sum_exp = 0.0
    for start_n in range(0, N, BLOCK_N):
        col_indices = start_n + tl.arange(0, BLOCK_N)
        mask = col_indices < N
        offsets = m * STRIDE_M + col_indices * STRIDE_N
        chunk = tl.load(logits_ptr + offsets, mask=mask, other=0.0)
        shifted = chunk - max_logit
        exp_chunk = tl.exp(shifted)
        local_sum = tl.sum(exp_chunk, axis=0)
        sum_exp += local_sum

    logsumexp = max_logit + tl.log(sum_exp)

    # Load target logit
    target_offset_logit = m * STRIDE_M + target * STRIDE_N
    target_logit = tl.load(logits_ptr + target_offset_logit)

    # Compute loss
    loss = logsumexp - target_logit

    # Store
    output_offset = m * STRIDE_O
    tl.store(output_ptr + output_offset, loss)

def cross_entropy(logits: torch.Tensor, targets: torch.Tensor) -> torch.Tensor:
    M, N = logits.shape
    output = torch.empty((M,), dtype=torch.float32, device=logits.device)
    if M == 0:
        return output
    STRIDE_M = logits.stride(0)
    STRIDE_N = logits.stride(1)
    STRIDE_T = targets.stride(0)
    STRIDE_O = output.stride(0)
    grid = (M,)
    cross_entropy_kernel[grid](
        logits, targets, output, M, N,
        STRIDE_M, STRIDE_N, STRIDE_T, STRIDE_O
    )
    return output
"""
        return {"code": code}