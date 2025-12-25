import torch
import triton
import triton.language as tl


@triton.autotune(
    configs=[
        triton.Config({"BLOCK_N": 64}, num_warps=2, num_stages=2),
        triton.Config({"BLOCK_N": 128}, num_warps=4, num_stages=2),
        triton.Config({"BLOCK_N": 256}, num_warps=4, num_stages=3),
        triton.Config({"BLOCK_N": 512}, num_warps=8, num_stages=3),
        triton.Config({"BLOCK_N": 1024}, num_warps=8, num_stages=4),
        triton.Config({"BLOCK_N": 2048}, num_warps=8, num_stages=4),
    ],
    key=["N"],
)
@triton.jit
def _cross_entropy_kernel(
    logits_ptr,
    targets_ptr,
    out_ptr,
    M,
    N,
    stride_m,
    stride_n,
    targets_stride,
    BLOCK_N: tl.constexpr,
):
    row_id = tl.program_id(0)

    # Cast sizes/strides to known types
    N_i64 = tl.multiple_of(N, 1)
    stride_m_i64 = stride_m
    stride_n_i64 = stride_n
    targets_stride_i64 = targets_stride

    # Base pointers
    row_base_ptr = logits_ptr + row_id * stride_m_i64

    # Load target index for this row
    tgt_idx = tl.load(targets_ptr + row_id * targets_stride_i64, mask=True, other=0)
    tgt_idx = tgt_idx.to(tl.int64)

    # Gather target logit directly
    tgt_ptr = row_base_ptr + tgt_idx * stride_n_i64
    tgt_val = tl.load(tgt_ptr, mask=True, other=0).to(tl.float32)

    # Streaming log-sum-exp computation across N
    neg_inf = tl.full((), float("-inf"), tl.float32)
    m = neg_inf
    s = tl.zeros((), dtype=tl.float32)

    offs = tl.zeros((), dtype=tl.int64)
    step = tl.full((), BLOCK_N, tl.int64)

    while offs < N_i64:
        col_offsets = offs + tl.arange(0, BLOCK_N)
        mask = col_offsets < N_i64
        ptrs = row_base_ptr + col_offsets * stride_n_i64
        x = tl.load(ptrs, mask=mask, other=neg_inf).to(tl.float32)

        tile_max = tl.max(x, axis=0)
        new_m = tl.maximum(m, tile_max)
        # rescale previous sum
        s = s * tl.exp(m - new_m) + tl.sum(tl.exp(x - new_m), axis=0)
        m = new_m
        offs += step

    # Final logsumexp and loss
    lse = m + tl.log(s)
    loss = lse - tgt_val
    tl.store(out_ptr + row_id, loss)


def cross_entropy(logits: torch.Tensor, targets: torch.Tensor) -> torch.Tensor:
    if not (logits.is_cuda and targets.is_cuda):
        raise ValueError("logits and targets must be CUDA tensors")
    if logits.ndim != 2:
        raise ValueError("logits must be 2D (M, N)")
    if targets.ndim != 1:
        raise ValueError("targets must be 1D (M,)")
    M, N = logits.shape
    if targets.shape[0] != M:
        raise ValueError("targets length must match logits batch size (M)")
    if targets.dtype not in (torch.int64, torch.long):
        raise ValueError("targets must be int64")

    out = torch.empty((M,), device=logits.device, dtype=torch.float32)

    stride_m, stride_n = logits.stride()
    targets_stride = targets.stride(0)

    if M == 0:
        return out

    grid = (M,)
    _cross_entropy_kernel[grid](
        logits,
        targets,
        out,
        M,
        N,
        stride_m,
        stride_n,
        targets_stride,
    )
    return out


class Solution:
    def solve(self, spec_path: str = None) -> dict:
        code = (
            "import torch\n"
            "import triton\n"
            "import triton.language as tl\n\n"
            "@triton.autotune(\n"
            "    configs=[\n"
            "        triton.Config({'BLOCK_N': 64}, num_warps=2, num_stages=2),\n"
            "        triton.Config({'BLOCK_N': 128}, num_warps=4, num_stages=2),\n"
            "        triton.Config({'BLOCK_N': 256}, num_warps=4, num_stages=3),\n"
            "        triton.Config({'BLOCK_N': 512}, num_warps=8, num_stages=3),\n"
            "        triton.Config({'BLOCK_N': 1024}, num_warps=8, num_stages=4),\n"
            "        triton.Config({'BLOCK_N': 2048}, num_warps=8, num_stages=4),\n"
            "    ],\n"
            "    key=['N'],\n"
            ")\n"
            "@triton.jit\n"
            "def _cross_entropy_kernel(\n"
            "    logits_ptr,\n"
            "    targets_ptr,\n"
            "    out_ptr,\n"
            "    M,\n"
            "    N,\n"
            "    stride_m,\n"
            "    stride_n,\n"
            "    targets_stride,\n"
            "    BLOCK_N: tl.constexpr,\n"
            "):\n"
            "    row_id = tl.program_id(0)\n"
            "    N_i64 = tl.multiple_of(N, 1)\n"
            "    stride_m_i64 = stride_m\n"
            "    stride_n_i64 = stride_n\n"
            "    targets_stride_i64 = targets_stride\n"
            "    row_base_ptr = logits_ptr + row_id * stride_m_i64\n"
            "    tgt_idx = tl.load(targets_ptr + row_id * targets_stride_i64, mask=True, other=0)\n"
            "    tgt_idx = tgt_idx.to(tl.int64)\n"
            "    tgt_ptr = row_base_ptr + tgt_idx * stride_n_i64\n"
            "    tgt_val = tl.load(tgt_ptr, mask=True, other=0).to(tl.float32)\n"
            "    neg_inf = tl.full((), float('-inf'), tl.float32)\n"
            "    m = neg_inf\n"
            "    s = tl.zeros((), dtype=tl.float32)\n"
            "    offs = tl.zeros((), dtype=tl.int64)\n"
            "    step = tl.full((), BLOCK_N, tl.int64)\n"
            "    while offs < N_i64:\n"
            "        col_offsets = offs + tl.arange(0, BLOCK_N)\n"
            "        mask = col_offsets < N_i64\n"
            "        ptrs = row_base_ptr + col_offsets * stride_n_i64\n"
            "        x = tl.load(ptrs, mask=mask, other=neg_inf).to(tl.float32)\n"
            "        tile_max = tl.max(x, axis=0)\n"
            "        new_m = tl.maximum(m, tile_max)\n"
            "        s = s * tl.exp(m - new_m) + tl.sum(tl.exp(x - new_m), axis=0)\n"
            "        m = new_m\n"
            "        offs += step\n"
            "    lse = m + tl.log(s)\n"
            "    loss = lse - tgt_val\n"
            "    tl.store(out_ptr + row_id, loss)\n\n"
            "def cross_entropy(logits: torch.Tensor, targets: torch.Tensor) -> torch.Tensor:\n"
            "    if not (logits.is_cuda and targets.is_cuda):\n"
            "        raise ValueError('logits and targets must be CUDA tensors')\n"
            "    if logits.ndim != 2:\n"
            "        raise ValueError('logits must be 2D (M, N)')\n"
            "    if targets.ndim != 1:\n"
            "        raise ValueError('targets must be 1D (M,)')\n"
            "    M, N = logits.shape\n"
            "    if targets.shape[0] != M:\n"
            "        raise ValueError('targets length must match logits batch size (M)')\n"
            "    if targets.dtype not in (torch.int64, torch.long):\n"
            "        raise ValueError('targets must be int64')\n"
            "    out = torch.empty((M,), device=logits.device, dtype=torch.float32)\n"
            "    stride_m, stride_n = logits.stride()\n"
            "    targets_stride = targets.stride(0)\n"
            "    if M == 0:\n"
            "        return out\n"
            "    grid = (M,)\n"
            "    _cross_entropy_kernel[grid](\n"
            "        logits,\n"
            "        targets,\n"
            "        out,\n"
            "        M,\n"
            "        N,\n"
            "        stride_m,\n"
            "        stride_n,\n"
            "        targets_stride,\n"
            "    )\n"
            "    return out\n"
        )
        return {"code": code}
