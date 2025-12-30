import torch
import triton
import triton.language as tl

class Solution:
    def solve(self, spec_path: str = None) -> dict:
        code = """
import torch
import triton
import triton.language as tl

def cross_entropy(logits: torch.Tensor, targets: torch.Tensor) -> torch.Tensor:
    M, N = logits.shape
    output = torch.empty(M, dtype=torch.float32, device=logits.device)
    if M == 0:
        return output
    assert targets.shape[0] == M
    assert logits.dtype == torch.float32
    assert targets.dtype == torch.int64
    stride_h = logits.stride(0) // 4
    stride_w = logits.stride(1) // 4
    stride_t = targets.stride(0) // 8

    BLOCK_SIZES = [64, 128, 256, 512, 1024, 2048]

    @triton.autotune(
        configs=[
            triton.Config(
                {'BLOCK_SIZE': bs},
                num_stages=2 + (bs // 256),
                num_warps=max(4, bs // 256)
            )
            for bs in BLOCK_SIZES
            if bs <= N
        ],
        key=['N'],
    )
    @triton.jit
    def kernel(
        logits_ptr,
        targets_ptr,
        output_ptr,
        stride_h,
        stride_w,
        stride_t,
        M,
        N,
        BLOCK_SIZE: tl.constexpr
    ):
        pid = tl.program_id(0)
        if pid >= M:
            return

        target = tl.load(targets_ptr + pid * stride_t, dtype=tl.int64)

        # Compute max_val
        max_val = -1e9
        for start in range(0, N, BLOCK_SIZE):
            cols = tl.arange(0, BLOCK_SIZE)
            mask = cols < (N - start)
            offsets = (pid * stride_h + (start + cols) * stride_w).to(logits_ptr.dtype.element_ty)
            x = tl.load(logits_ptr + offsets, mask=mask, other=-1e9)
            max_val = tl.maximum(max_val, tl.max(x, axis=0))

        # Compute sum_exp
        sum_exp = 0.0
        for start in range(0, N, BLOCK_SIZE):
            cols = tl.arange(0, BLOCK_SIZE)
            mask = cols < (N - start)
            offsets = (pid * stride_h + (start + cols) * stride_w).to(logits_ptr.dtype.element_ty)
            x = tl.load(logits_ptr + offsets, mask=mask, other=max_val)
            x_minus_max = x - max_val
            exp_x = tl.exp(x_minus_max)
            exp_x = tl.where(mask, exp_x, 0.0)
            sum_exp += tl.sum(exp_x, axis=0)

        logsumexp = tl.log(sum_exp) + max_val

        # Compute loss
        y_offset = (pid * stride_h + target * stride_w).to(logits_ptr.dtype.element_ty)
        logit_y = tl.load(logits_ptr + y_offset)
        loss = -(logit_y - logsumexp)
        tl.store(output_ptr + pid, loss)

    grid = (M,)
    kernel[grid](
        logits.data_ptr(),
        targets.data_ptr(),
        output.data_ptr(),
        stride_h,
        stride_w,
        stride_t,
        M,
        N
    )
    return output
"""
        return {"code": code}