import torch
import triton
import triton.language as tl


@triton.jit
def _chunk_scan_kernel(
    X_ptr, A_ptr, B_ptr, Y_ptr,
    L, D,
    stride_x_l, stride_x_d,
    stride_a_l, stride_a_d,
    stride_b_l, stride_b_d,
    stride_y_l, stride_y_d,
    BLOCK_D: tl.constexpr,
):
    pid = tl.program_id(axis=0)
    offs_d = pid * BLOCK_D + tl.arange(0, BLOCK_D)
    mask_d = offs_d < D

    x_ptrs = X_ptr + offs_d * stride_x_d
    a_ptrs = A_ptr + offs_d * stride_a_d
    b_ptrs = B_ptr + offs_d * stride_b_d
    y_ptrs = Y_ptr + offs_d * stride_y_d

    y_prev = tl.zeros([BLOCK_D], dtype=tl.float32)

    for t in range(0, L):
        offset_x = t * stride_x_l
        offset_a = t * stride_a_l
        offset_b = t * stride_b_l
        offset_y = t * stride_y_l

        x = tl.load(x_ptrs + offset_x, mask=mask_d, other=0.0)
        a = tl.load(a_ptrs + offset_a, mask=mask_d, other=0.0)
        b = tl.load(b_ptrs + offset_b, mask=mask_d, other=0.0)

        x_f32 = x.to(tl.float32)
        a_f32 = a.to(tl.float32)
        b_f32 = b.to(tl.float32)

        y = a_f32 * y_prev + b_f32 * x_f32
        tl.store(y_ptrs + offset_y, y.to(tl.float16), mask=mask_d)
        y_prev = y


def chunk_scan(X: torch.Tensor, A: torch.Tensor, B: torch.Tensor, chunk: int = 128, BD: int = 128) -> torch.Tensor:
    assert X.is_cuda and A.is_cuda and B.is_cuda, "Tensors must be on CUDA"
    assert X.dtype == torch.float16 and A.dtype == torch.float16 and B.dtype == torch.float16, "Input tensors must be float16"
    assert X.shape == A.shape == B.shape, "Input tensors must have the same shape"
    L, D = X.shape

    Y = torch.empty_like(X)

    stride_x_l, stride_x_d = X.stride()
    stride_a_l, stride_a_d = A.stride()
    stride_b_l, stride_b_d = B.stride()
    stride_y_l, stride_y_d = Y.stride()

    BLOCK_D = BD
    grid = (triton.cdiv(D, BLOCK_D),)

    _chunk_scan_kernel[grid](
        X, A, B, Y,
        L, D,
        stride_x_l, stride_x_d,
        stride_a_l, stride_a_d,
        stride_b_l, stride_b_d,
        stride_y_l, stride_y_d,
        BLOCK_D=BLOCK_D,
        num_warps=4,
        num_stages=1,
    )

    return Y


class Solution:
    def solve(self, spec_path: str = None) -> dict:
        try:
            path = __file__
            with open(path, "r", encoding="utf-8") as f:
                code = f.read()
            return {"code": code}
        except Exception:
            code_lines = []
            code_lines.append("import torch")
            code_lines.append("import triton")
            code_lines.append("import triton.language as tl")
            code_lines.append("")
            code_lines.append("@triton.jit")
            code_lines.append("def _chunk_scan_kernel(")
            code_lines.append("    X_ptr, A_ptr, B_ptr, Y_ptr,")
            code_lines.append("    L, D,")
            code_lines.append("    stride_x_l, stride_x_d,")
            code_lines.append("    stride_a_l, stride_a_d,")
            code_lines.append("    stride_b_l, stride_b_d,")
            code_lines.append("    stride_y_l, stride_y_d,")
            code_lines.append("    BLOCK_D: tl.constexpr,")
            code_lines.append("):")
            code_lines.append("    pid = tl.program_id(axis=0)")
            code_lines.append("    offs_d = pid * BLOCK_D + tl.arange(0, BLOCK_D)")
            code_lines.append("    mask_d = offs_d < D")
            code_lines.append("")
            code_lines.append("    x_ptrs = X_ptr + offs_d * stride_x_d")
            code_lines.append("    a_ptrs = A_ptr + offs_d * stride_a_d")
            code_lines.append("    b_ptrs = B_ptr + offs_d * stride_b_d")
            code_lines.append("    y_ptrs = Y_ptr + offs_d * stride_y_d")
            code_lines.append("")
            code_lines.append("    y_prev = tl.zeros([BLOCK_D], dtype=tl.float32)")
            code_lines.append("")
            code_lines.append("    for t in range(0, L):")
            code_lines.append("        offset_x = t * stride_x_l")
            code_lines.append("        offset_a = t * stride_a_l")
            code_lines.append("        offset_b = t * stride_b_l")
            code_lines.append("        offset_y = t * stride_y_l")
            code_lines.append("")
            code_lines.append("        x = tl.load(x_ptrs + offset_x, mask=mask_d, other=0.0)")
            code_lines.append("        a = tl.load(a_ptrs + offset_a, mask=mask_d, other=0.0)")
            code_lines.append("        b = tl.load(b_ptrs + offset_b, mask=mask_d, other=0.0)")
            code_lines.append("")
            code_lines.append("        x_f32 = x.to(tl.float32)")
            code_lines.append("        a_f32 = a.to(tl.float32)")
            code_lines.append("        b_f32 = b.to(tl.float32)")
            code_lines.append("")
            code_lines.append("        y = a_f32 * y_prev + b_f32 * x_f32")
            code_lines.append("        tl.store(y_ptrs + offset_y, y.to(tl.float16), mask=mask_d)")
            code_lines.append("        y_prev = y")
            code_lines.append("")
            code_lines.append("def chunk_scan(X: torch.Tensor, A: torch.Tensor, B: torch.Tensor, chunk: int = 128, BD: int = 128) -> torch.Tensor:")
            code_lines.append("    assert X.is_cuda and A.is_cuda and B.is_cuda, 'Tensors must be on CUDA'")
            code_lines.append("    assert X.dtype == torch.float16 and A.dtype == torch.float16 and B.dtype == torch.float16, 'Input tensors must be float16'")
            code_lines.append("    assert X.shape == A.shape == B.shape, 'Input tensors must have the same shape'")
            code_lines.append("    L, D = X.shape")
            code_lines.append("")
            code_lines.append("    Y = torch.empty_like(X)")
            code_lines.append("")
            code_lines.append("    stride_x_l, stride_x_d = X.stride()")
            code_lines.append("    stride_a_l, stride_a_d = A.stride()")
            code_lines.append("    stride_b_l, stride_b_d = B.stride()")
            code_lines.append("    stride_y_l, stride_y_d = Y.stride()")
            code_lines.append("")
            code_lines.append("    BLOCK_D = BD")
            code_lines.append("    grid = (triton.cdiv(D, BLOCK_D),)")
            code_lines.append("")
            code_lines.append("    _chunk_scan_kernel[grid](")
            code_lines.append("        X, A, B, Y,")
            code_lines.append("        L, D,")
            code_lines.append("        stride_x_l, stride_x_d,")
            code_lines.append("        stride_a_l, stride_a_d,")
            code_lines.append("        stride_b_l, stride_b_d,")
            code_lines.append("        stride_y_l, stride_y_d,")
            code_lines.append("        BLOCK_D=BLOCK_D,")
            code_lines.append("        num_warps=4,")
            code_lines.append("        num_stages=1,")
            code_lines.append("    )")
            code_lines.append("    return Y")
            code = "\n".join(code_lines)
            return {"code": code}