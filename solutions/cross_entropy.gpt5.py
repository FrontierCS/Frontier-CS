import torch
import triton
import triton.language as tl


@triton.autotune(
    configs=[
        triton.Config({'BLOCK_M': 1, 'BLOCK_N': 128, 'num_warps': 4}, num_stages=3),
        triton.Config({'BLOCK_M': 1, 'BLOCK_N': 256, 'num_warps': 4}, num_stages=3),
        triton.Config({'BLOCK_M': 1, 'BLOCK_N': 512, 'num_warps': 8}, num_stages=4),
        triton.Config({'BLOCK_M': 2, 'BLOCK_N': 256, 'num_warps': 4}, num_stages=3),
        triton.Config({'BLOCK_M': 2, 'BLOCK_N': 512, 'num_warps': 8}, num_stages=4),
        triton.Config({'BLOCK_M': 4, 'BLOCK_N': 256, 'num_warps': 4}, num_stages=3),
        triton.Config({'BLOCK_M': 4, 'BLOCK_N': 512, 'num_warps': 8}, num_stages=4),
        triton.Config({'BLOCK_M': 1, 'BLOCK_N': 1024, 'num_warps': 8}, num_stages=4),
        triton.Config({'BLOCK_M': 2, 'BLOCK_N': 1024, 'num_warps': 8}, num_stages=4),
        triton.Config({'BLOCK_M': 4, 'BLOCK_N': 1024, 'num_warps': 8}, num_stages=4),
    ],
    key=['N'],
)
@triton.jit
def _cross_entropy_kernel(
    logits_ptr,          # *f16/*bf16/*f32
    targets_ptr,         # *i64
    loss_ptr,            # *f32
    M,                   # number of rows
    stride_m,            # stride along M in elements
    stride_n,            # stride along N in elements
    stride_t,            # targets stride
    N: tl.constexpr,     # number of columns (classes)
    BLOCK_M: tl.constexpr,
    BLOCK_N: tl.constexpr,
):
    pid_m = tl.program_id(axis=0)
    off_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
    mask_m = off_m < M

    offs_n_init = tl.arange(0, BLOCK_N)

    # Pass 1: compute row-wise max
    row_max = tl.full([BLOCK_M], -float('inf'), dtype=tl.float32)
    num_tiles = (N + BLOCK_N - 1) // BLOCK_N

    for tile in range(0, num_tiles):
        col_start = tile * BLOCK_N
        offs_n = col_start + offs_n_init
        mask_n = offs_n < N
        mask = mask_m[:, None] & mask_n[None, :]

        ptr = logits_ptr + off_m[:, None] * stride_m + offs_n[None, :] * stride_n
        x = tl.load(ptr, mask=mask, other=0.0)
        x = x.to(tl.float32)
        x = tl.where(mask, x, -float('inf'))
        tile_max = tl.max(x, axis=1)
        row_max = tl.maximum(row_max, tile_max)

    # Pass 2: compute row-wise log-sum-exp using max from pass 1
    expsum = tl.zeros([BLOCK_M], dtype=tl.float32)
    for tile in range(0, num_tiles):
        col_start = tile * BLOCK_N
        offs_n = col_start + offs_n_init
        mask_n = offs_n < N
        mask = mask_m[:, None] & mask_n[None, :]

        ptr = logits_ptr + off_m[:, None] * stride_m + offs_n[None, :] * stride_n
        x = tl.load(ptr, mask=mask, other=0.0)
        x = x.to(tl.float32)
        x = x - row_max[:, None]
        x = tl.exp(x)
        expsum += tl.sum(x, axis=1)

    lse = tl.log(expsum) + row_max

    # Gather target logits for each row
    tgt_idx = tl.load(targets_ptr + off_m * stride_t, mask=mask_m, other=0).to(tl.int64)
    tgt_ptrs = logits_ptr + off_m * stride_m + tgt_idx * stride_n
    tgt_logits = tl.load(tgt_ptrs, mask=mask_m, other=0.0).to(tl.float32)

    loss = lse - tgt_logits
    tl.store(loss_ptr + off_m, loss, mask=mask_m)


def cross_entropy(logits: torch.Tensor, targets: torch.Tensor) -> torch.Tensor:
    if logits.dim() != 2:
        raise ValueError("logits must be a 2D tensor of shape (M, N)")
    if targets.dim() != 1:
        raise ValueError("targets must be a 1D tensor of shape (M,)")

    M, N = logits.shape
    if targets.shape[0] != M:
        raise ValueError("targets length must match the number of rows in logits")

    if not logits.is_cuda or not targets.is_cuda:
        raise ValueError("logits and targets must be CUDA tensors")

    if targets.dtype != torch.long:
        targets = targets.long()

    loss = torch.empty(M, device=logits.device, dtype=torch.float32)

    stride_m, stride_n = logits.stride()
    stride_t = targets.stride(0)

    grid = lambda META: (triton.cdiv(M, META['BLOCK_M']),)

    _cross_entropy_kernel[grid](
        logits,
        targets,
        loss,
        M,
        stride_m,
        stride_n,
        stride_t,
        N=N,
    )

    return loss


class Solution:
    def solve(self, spec_path: str = None) -> dict:
        import inspect
        src = inspect.getsource(torch)
        # above line ensures torch is imported in the generated context
        module_code = []
        module_code.append("import torch")
        module_code.append("import triton")
        module_code.append("import triton.language as tl")
        module_code.append(inspect.getsource(_cross_entropy_kernel))
        module_code.append(inspect.getsource(cross_entropy))
        module_code.append(inspect.getsource(Solution))
        # To avoid recursive definition when executed, redefine a minimal Solution that returns this code
        final_code = "\n".join(module_code)
        return {"code": final_code}
