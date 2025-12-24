import os
import textwrap
import torch

try:
    import triton
    import triton.language as tl
except Exception:
    triton = None
    tl = None


if triton is not None:

    @triton.autotune(
        configs=[
            triton.Config({"BLOCK_N": 256}, num_warps=4, num_stages=4),
            triton.Config({"BLOCK_N": 512}, num_warps=4, num_stages=4),
            triton.Config({"BLOCK_N": 512}, num_warps=8, num_stages=4),
            triton.Config({"BLOCK_N": 1024}, num_warps=4, num_stages=4),
            triton.Config({"BLOCK_N": 1024}, num_warps=8, num_stages=4),
            triton.Config({"BLOCK_N": 2048}, num_warps=8, num_stages=3),
        ],
        key=["N"],
    )
    @triton.jit
    def _cross_entropy_kernel(
        logits_ptr,
        targets_ptr,
        out_ptr,
        stride_lm,
        stride_ln,
        stride_t,
        M,
        N: tl.constexpr,
        BLOCK_N: tl.constexpr,
    ):
        pid_m = tl.program_id(0)
        m_mask = pid_m < M

        row_ptr = logits_ptr + pid_m * stride_lm
        t = tl.load(targets_ptr + pid_m * stride_t, mask=m_mask, other=0).to(tl.int32)
        logit_t = tl.load(row_ptr + t * stride_ln, mask=m_mask, other=-float("inf")).to(tl.float32)

        m_val = tl.full((), -float("inf"), tl.float32)
        s_val = tl.zeros((), tl.float32)

        for off in tl.static_range(0, N, BLOCK_N):
            cols = off + tl.arange(0, BLOCK_N)
            c_mask = cols < N
            x = tl.load(row_ptr + cols * stride_ln, mask=c_mask & m_mask, other=-float("inf")).to(tl.float32)

            block_max = tl.max(x, axis=0)
            new_m = tl.maximum(m_val, block_max)
            s_val = s_val * tl.exp(m_val - new_m) + tl.sum(tl.exp(x - new_m), axis=0)
            m_val = new_m

        logsumexp = tl.log(s_val) + m_val
        loss = logsumexp - logit_t
        tl.store(out_ptr + pid_m, loss, mask=m_mask)


def cross_entropy(logits: torch.Tensor, targets: torch.Tensor) -> torch.Tensor:
    if triton is None or (not logits.is_cuda) or (not targets.is_cuda):
        logits_f = logits.float()
        m = logits_f.max(dim=1).values
        lse = (logits_f - m[:, None]).exp().sum(dim=1).log() + m
        gather = logits_f.gather(1, targets.to(torch.int64).view(-1, 1)).view(-1)
        return (lse - gather).to(torch.float32)

    assert logits.ndim == 2 and targets.ndim == 1
    assert logits.shape[0] == targets.shape[0]

    M, N = logits.shape
    out = torch.empty((M,), device=logits.device, dtype=torch.float32)

    stride_lm, stride_ln = logits.stride()
    stride_t = targets.stride(0)

    grid = (M,)
    _cross_entropy_kernel[grid](
        logits,
        targets,
        out,
        stride_lm,
        stride_ln,
        stride_t,
        M,
        N=N,
    )
    return out


_KERNEL_CODE = textwrap.dedent(
    r"""
    import torch
    import triton
    import triton.language as tl

    @triton.autotune(
        configs=[
            triton.Config({"BLOCK_N": 256}, num_warps=4, num_stages=4),
            triton.Config({"BLOCK_N": 512}, num_warps=4, num_stages=4),
            triton.Config({"BLOCK_N": 512}, num_warps=8, num_stages=4),
            triton.Config({"BLOCK_N": 1024}, num_warps=4, num_stages=4),
            triton.Config({"BLOCK_N": 1024}, num_warps=8, num_stages=4),
            triton.Config({"BLOCK_N": 2048}, num_warps=8, num_stages=3),
        ],
        key=["N"],
    )
    @triton.jit
    def _cross_entropy_kernel(
        logits_ptr,
        targets_ptr,
        out_ptr,
        stride_lm,
        stride_ln,
        stride_t,
        M,
        N: tl.constexpr,
        BLOCK_N: tl.constexpr,
    ):
        pid_m = tl.program_id(0)
        m_mask = pid_m < M

        row_ptr = logits_ptr + pid_m * stride_lm
        t = tl.load(targets_ptr + pid_m * stride_t, mask=m_mask, other=0).to(tl.int32)
        logit_t = tl.load(row_ptr + t * stride_ln, mask=m_mask, other=-float("inf")).to(tl.float32)

        m_val = tl.full((), -float("inf"), tl.float32)
        s_val = tl.zeros((), tl.float32)

        for off in tl.static_range(0, N, BLOCK_N):
            cols = off + tl.arange(0, BLOCK_N)
            c_mask = cols < N
            x = tl.load(row_ptr + cols * stride_ln, mask=c_mask & m_mask, other=-float("inf")).to(tl.float32)

            block_max = tl.max(x, axis=0)
            new_m = tl.maximum(m_val, block_max)
            s_val = s_val * tl.exp(m_val - new_m) + tl.sum(tl.exp(x - new_m), axis=0)
            m_val = new_m

        logsumexp = tl.log(s_val) + m_val
        loss = logsumexp - logit_t
        tl.store(out_ptr + pid_m, loss, mask=m_mask)

    def cross_entropy(logits: torch.Tensor, targets: torch.Tensor) -> torch.Tensor:
        if (not logits.is_cuda) or (not targets.is_cuda):
            logits_f = logits.float()
            m = logits_f.max(dim=1).values
            lse = (logits_f - m[:, None]).exp().sum(dim=1).log() + m
            gather = logits_f.gather(1, targets.to(torch.int64).view(-1, 1)).view(-1)
            return (lse - gather).to(torch.float32)

        assert logits.ndim == 2 and targets.ndim == 1
        assert logits.shape[0] == targets.shape[0]

        M, N = logits.shape
        out = torch.empty((M,), device=logits.device, dtype=torch.float32)

        stride_lm, stride_ln = logits.stride()
        stride_t = targets.stride(0)

        grid = (M,)
        _cross_entropy_kernel[grid](
            logits,
            targets,
            out,
            stride_lm,
            stride_ln,
            stride_t,
            M,
            N=N,
        )
        return out
    """
).strip() + "\n"


class Solution:
    def solve(self, spec_path: str = None) -> dict:
        return {"code": _KERNEL_CODE}
