import textwrap

kernel_code = textwrap.dedent(
    """
    import torch
    import triton
    import triton.language as tl

    @triton.autotune(
        configs=[
            triton.Config({'BLOCK_SIZE': 1024}, num_warps=4, num_stages=4),
            triton.Config({'BLOCK_SIZE': 2048}, num_warps=4, num_stages=4),
            triton.Config({'BLOCK_SIZE': 4096}, num_warps=8, num_stages=4),
        ],
        key=['n_elements'],
    )
    @triton.jit
    def _add_kernel(x_ptr, y_ptr, out_ptr, n_elements, BLOCK_SIZE: tl.constexpr):
        pid = tl.program_id(axis=0)
        block_start = pid * BLOCK_SIZE
        offsets = block_start + tl.arange(0, BLOCK_SIZE)
        mask = offsets < n_elements
        x = tl.load(x_ptr + offsets, mask=mask)
        y = tl.load(y_ptr + offsets, mask=mask)
        tl.store(out_ptr + offsets, x + y, mask=mask)

    def add(x: torch.Tensor, y: torch.Tensor) -> torch.Tensor:
        if not isinstance(x, torch.Tensor) or not isinstance(y, torch.Tensor):
            raise TypeError("x and y must be torch.Tensor")
        if x.shape != y.shape:
            raise ValueError("x and y must have the same shape")
        if x.dtype != y.dtype:
            raise ValueError("x and y must have the same dtype")
        if x.device != y.device:
            raise ValueError("x and y must be on the same device")

        # CPU fallback
        if not x.is_cuda:
            return x + y

        if not x.is_contiguous():
            x = x.contiguous()
        if not y.is_contiguous():
            y = y.contiguous()

        n_elements = x.numel()
        out = torch.empty_like(x)

        x_flat = x.view(-1)
        y_flat = y.view(-1)
        out_flat = out.view(-1)

        grid = lambda meta: (triton.cdiv(n_elements, meta['BLOCK_SIZE']),)
        _add_kernel[grid](x_flat, y_flat, out_flat, n_elements)

        return out
    """
)

exec(kernel_code, globals())


class Solution:
    def solve(self, spec_path: str = None) -> dict:
        return {"code": kernel_code}