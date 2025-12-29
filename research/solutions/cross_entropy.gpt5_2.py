import os
import textwrap
import torch
import triton
import triton.language as tl


@triton.autotune(
    configs=[
        triton.Config({"BLOCK_N": 128}, num_warps=2, num_stages=4),
        triton.Config({"BLOCK_N": 256}, num_warps=4, num_stages=4),
        triton.Config({"BLOCK_N": 512}, num_warps=4, num_stages=4),
        triton.Config({"BLOCK_N": 1024}, num_warps=8, num_stages=5),
        triton.Config({"BLOCK_N": 2048}, num_warps=8, num_stages=5),
        triton.Config({"BLOCK_N": 4096}, num_warps=8, num_stages=5),
    ],
    key=["N"],
)
@triton.jit
def _cross_entropy_kernel(
    logits_ptr,
    targets_ptr,
    out_ptr,
    M: tl.constexpr,
    N: tl.constexpr,
    stride_am,
    stride_an,
    stride_t,
    BLOCK_N: tl.constexpr,
):
    row_id = tl.program_id(0)
    if row_id >= M:
        return

    # Base pointers
    row_logits_ptr = logits_ptr + row_id * stride_am

    # Initialize running log-sum-exp accumulators
    max_acc = tl.full([1], -float("inf"), dtype=tl.float32)
    sum_acc = tl.zeros([1], dtype=tl.float32)

    offs_n = tl.arange(0, BLOCK_N)
    n = 0
    while n < N:
        idx = n + offs_n
        mask = idx < N

        vals = tl.load(row_logits_ptr + idx * stride_an, mask=mask, other=-float("inf"))
        vals = vals.to(tl.float32)

        b_max = tl.max(vals, axis=0)
        b_sum = tl.sum(tl.exp(vals - b_max), axis=0)

        m_new = tl.maximum(max_acc, b_max)
        sum_acc = sum_acc * tl.exp(max_acc - m_new) + b_sum * tl.exp(b_max - m_new)
        max_acc = m_new

        n += BLOCK_N

    logsumexp = tl.log(sum_acc) + max_acc

    tgt_idx = tl.load(targets_ptr + row_id * stride_t).to(tl.int64)
    tgt_val = tl.load(row_logits_ptr + tgt_idx * stride_an).to(tl.float32)

    loss = logsumexp - tgt_val
    tl.store(out_ptr + row_id, loss)


def cross_entropy(logits: torch.Tensor, targets: torch.Tensor) -> torch.Tensor:
    if not logits.is_cuda or not targets.is_cuda:
        raise RuntimeError("logits and targets must be CUDA tensors")
    if logits.ndim != 2:
        raise ValueError("logits must be a 2D tensor of shape (M, N)")
    if targets.ndim != 1:
        raise ValueError("targets must be a 1D tensor of shape (M,)")
    if logits.shape[0] != targets.shape[0]:
        raise ValueError("Batch size mismatch between logits and targets")
    if targets.dtype != torch.long:
        targets = targets.to(torch.long)

    M, N = logits.shape
    device = logits.device

    out = torch.empty((M,), device=device, dtype=torch.float32)

    stride_am = logits.stride(0)
    stride_an = logits.stride(1)
    stride_t = targets.stride(0)

    grid = lambda META: (triton.cdiv(M, 1),)

    _cross_entropy_kernel[grid](
        logits,
        targets,
        out,
        M,
        N,
        stride_am,
        stride_an,
        stride_t,
    )
    return out


class Solution:
    def solve(self, spec_path: str = None) -> dict:
        code = textwrap.dedent(
            """
            import torch
            import triton
            import triton.language as tl


            @triton.autotune(
                configs=[
                    triton.Config({"BLOCK_N": 128}, num_warps=2, num_stages=4),
                    triton.Config({"BLOCK_N": 256}, num_warps=4, num_stages=4),
                    triton.Config({"BLOCK_N": 512}, num_warps=4, num_stages=4),
                    triton.Config({"BLOCK_N": 1024}, num_warps=8, num_stages=5),
                    triton.Config({"BLOCK_N": 2048}, num_warps=8, num_stages=5),
                    triton.Config({"BLOCK_N": 4096}, num_warps=8, num_stages=5),
                ],
                key=["N"],
            )
            @triton.jit
            def _cross_entropy_kernel(
                logits_ptr,
                targets_ptr,
                out_ptr,
                M: tl.constexpr,
                N: tl.constexpr,
                stride_am,
                stride_an,
                stride_t,
                BLOCK_N: tl.constexpr,
            ):
                row_id = tl.program_id(0)
                if row_id >= M:
                    return

                row_logits_ptr = logits_ptr + row_id * stride_am

                max_acc = tl.full([1], -float("inf"), dtype=tl.float32)
                sum_acc = tl.zeros([1], dtype=tl.float32)

                offs_n = tl.arange(0, BLOCK_N)
                n = 0
                while n < N:
                    idx = n + offs_n
                    mask = idx < N

                    vals = tl.load(row_logits_ptr + idx * stride_an, mask=mask, other=-float("inf"))
                    vals = vals.to(tl.float32)

                    b_max = tl.max(vals, axis=0)
                    b_sum = tl.sum(tl.exp(vals - b_max), axis=0)

                    m_new = tl.maximum(max_acc, b_max)
                    sum_acc = sum_acc * tl.exp(max_acc - m_new) + b_sum * tl.exp(b_max - m_new)
                    max_acc = m_new

                    n += BLOCK_N

                logsumexp = tl.log(sum_acc) + max_acc

                tgt_idx = tl.load(targets_ptr + row_id * stride_t).to(tl.int64)
                tgt_val = tl.load(row_logits_ptr + tgt_idx * stride_an).to(tl.float32)

                loss = logsumexp - tgt_val
                tl.store(out_ptr + row_id, loss)


            def cross_entropy(logits: torch.Tensor, targets: torch.Tensor) -> torch.Tensor:
                if not logits.is_cuda or not targets.is_cuda:
                    raise RuntimeError("logits and targets must be CUDA tensors")
                if logits.ndim != 2:
                    raise ValueError("logits must be a 2D tensor of shape (M, N)")
                if targets.ndim != 1:
                    raise ValueError("targets must be a 1D tensor of shape (M,)")
                if logits.shape[0] != targets.shape[0]:
                    raise ValueError("Batch size mismatch between logits and targets")
                if targets.dtype != torch.long:
                    targets = targets.to(torch.long)

                M, N = logits.shape
                device = logits.device

                out = torch.empty((M,), device=device, dtype=torch.float32)

                stride_am = logits.stride(0)
                stride_an = logits.stride(1)
                stride_t = targets.stride(0)

                grid = lambda META: (triton.cdiv(M, 1),)

                _cross_entropy_kernel[grid](
                    logits,
                    targets,
                    out,
                    M,
                    N,
                    stride_am,
                    stride_an,
                    stride_t,
                )
                return out
            """
        )
        return {"code": code}