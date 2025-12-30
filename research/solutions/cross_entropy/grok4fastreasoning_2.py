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

@triton.autotune(
    configs=[
        triton.Config({'BLOCK_M': 64, 'BLOCK_N': 128}),
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 256}),
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 512}),
        triton.Config({'BLOCK_M': 256, 'BLOCK_N': 256}),
    ],
    key=['M', 'N'],
)
@triton.jit
def cross_entropy_kernel(
    logits_ptr, targets_ptr, output_ptr,
    stride_lm, stride_ln, stride_t, stride_o,
    M: tl.int32, N: tl.int32,
    BLOCK_M: tl.constexpr,
    BLOCK_N: tl.constexpr
):
    block_start = tl.program_id(0) * BLOCK_M
    pids_m = block_start + tl.arange(0, BLOCK_M)
    mask_m = pids_m < M

    # Load targets
    target_offsets = pids_m.to(tl.int64) * stride_t
    target_ids = tl.load(targets_ptr + target_offsets, dtype=tl.int64, mask=mask_m, other=0)

    # First pass: compute max_logit
    max_logit = tl.full((BLOCK_M,), -1e30, dtype=tl.float32)
    for start_n in range(0, N, BLOCK_N):
        offsets_n = tl.arange(0, BLOCK_N)
        len_n = tl.minimum(BLOCK_N, N - start_n)
        mask_n = offsets_n < len_n
        off_m_bytes = pids_m.to(tl.int64)[:, None] * stride_lm
        off_n_bytes = (start_n + offsets_n[None, :]).to(tl.int64) * stride_ln
        ptrs = logits_ptr + off_m_bytes + off_n_bytes
        load_mask = mask_m[:, None] & mask_n[None, :]
        logits_block = tl.load(ptrs, mask=load_mask, other=-1e30)
        block_max = tl.max(logits_block, axis=1)
        max_logit = tl.maximum(max_logit, block_max)

    # Second pass: compute sum_exp
    sum_exp = tl.zeros((BLOCK_M,), dtype=tl.float32)
    for start_n in range(0, N, BLOCK_N):
        offsets_n = tl.arange(0, BLOCK_N)
        len_n = tl.minimum(BLOCK_N, N - start_n)
        mask_n = offsets_n < len_n
        off_m_bytes = pids_m.to(tl.int64)[:, None] * stride_lm
        off_n_bytes = (start_n + offsets_n[None, :]).to(tl.int64) * stride_ln
        ptrs = logits_ptr + off_m_bytes + off_n_bytes
        load_mask = mask_m[:, None] & mask_n[None, :]
        logits_block = tl.load(ptrs, mask=load_mask, other=0.0)
        shifted = tl.where(mask_m[:, None], logits_block - max_logit[:, None], 0.0)
        exped = tl.exp(shifted)
        block_sum = tl.sum(exped, axis=1)
        sum_exp += block_sum

    logsumexp = tl.log(sum_exp) + max_logit

    # Load target_logits and compute/store losses with per-element handling
    for j in range(BLOCK_M):
        m = block_start + j
        cond = m < M
        tid = target_ids[j]
        m_bytes = m.to(tl.int64) * stride_lm
        t_bytes = tid.to(tl.int64) * stride_ln
        bad_ptr = logits_ptr + m_bytes + t_bytes
        ptr = tl.where(cond, bad_ptr, logits_ptr)
        target_l = tl.load(ptr, dtype=tl.float32)
        loss = tl.where(cond, -(target_l - logsumexp[j]), 0.0)
        store_ptr = output_ptr + m.to(tl.int64) * stride_o
        tl.store(store_ptr, loss, mask=cond)

def cross_entropy(logits: torch.Tensor, targets: torch.Tensor) -> torch.Tensor:
    M, N = logits.shape
    if M == 0:
        return torch.empty((0,), dtype=torch.float32, device=logits.device)
    output = torch.empty((M,), dtype=torch.float32, device=logits.device)
    logits_ptr = logits.data_ptr()
    targets_ptr = targets.data_ptr()
    output_ptr = output.data_ptr()
    stride_lm = logits.stride(0) * logits.element_size()
    stride_ln = logits.stride(1) * logits.element_size()
    stride_t = targets.stride(0) * targets.element_size()
    stride_o = output.stride(0) * output.element_size()
    grid = lambda meta: (triton.cdiv(M, meta['BLOCK_M']), )
    cross_entropy_kernel[grid](
        logits_ptr=logits_ptr,
        targets_ptr=targets_ptr,
        output_ptr=output_ptr,
        stride_lm=stride_lm,
        stride_ln=stride_ln,
        stride_t=stride_t,
        stride_o=stride_o,
        M=M,
        N=N,
    )
    return output
"""
        return {"code": code}