import torch
import triton
import triton.language as tl
import inspect
import textwrap


@triton.jit
def _scan_chunk_kernel(
    X_ptr,
    A_ptr,
    B_ptr,
    Y_ptr,
    State_ptr,
    start_l,
    L,
    D,
    stride_x_l,
    stride_x_d,
    stride_a_l,
    stride_a_d,
    stride_b_l,
    stride_b_d,
    stride_y_l,
    stride_y_d,
    stride_state,
    CHUNK: tl.constexpr,
    BD: tl.constexpr,
):
    pid_d = tl.program_id(0)
    d_offsets = pid_d * BD + tl.arange(0, BD)
    d_mask = d_offsets < D

    state_ptrs = State_ptr + d_offsets * stride_state
    y_prev = tl.load(state_ptrs, mask=d_mask, other=0.0).to(tl.float32)

    for i in range(CHUNK):
        l_idx = start_l + i

        x_ptrs = X_ptr + l_idx * stride_x_l + d_offsets * stride_x_d
        a_ptrs = A_ptr + l_idx * stride_a_l + d_offsets * stride_a_d
        b_ptrs = B_ptr + l_idx * stride_b_l + d_offsets * stride_b_d

        x = tl.load(x_ptrs, mask=d_mask, other=0.0).to(tl.float32)
        a = tl.load(a_ptrs, mask=d_mask, other=0.0).to(tl.float32)
        b = tl.load(b_ptrs, mask=d_mask, other=0.0).to(tl.float32)

        y = a * y_prev + b * x

        y_ptrs = Y_ptr + l_idx * stride_y_l + d_offsets * stride_y_d
        tl.store(y_ptrs, y.to(tl.float16), mask=d_mask)

        y_prev = y

    tl.store(state_ptrs, y_prev.to(tl.float16), mask=d_mask)


def chunk_scan(X: torch.Tensor, A: torch.Tensor, B: torch.Tensor, chunk: int = 128, BD: int = 128) -> torch.Tensor:
    assert X.is_cuda and A.is_cuda and B.is_cuda, "Inputs must be CUDA tensors"
    assert X.dtype == torch.float16 and A.dtype == torch.float16 and B.dtype == torch.float16, "Inputs must be float16"
    assert X.shape == A.shape == B.shape, "X, A, B must have the same shape"
    L, D = X.shape
    assert L % chunk == 0, "Sequence length L must be divisible by chunk size"

    Y = torch.empty_like(X)
    state = torch.zeros(D, device=X.device, dtype=X.dtype)

    stride_x_l, stride_x_d = X.stride()
    stride_a_l, stride_a_d = A.stride()
    stride_b_l, stride_b_d = B.stride()
    stride_y_l, stride_y_d = Y.stride()
    stride_state = state.stride(0)

    grid = (triton.cdiv(D, BD),)

    for start_l in range(0, L, chunk):
        _scan_chunk_kernel[grid](
            X,
            A,
            B,
            Y,
            state,
            start_l,
            L,
            D,
            stride_x_l,
            stride_x_d,
            stride_a_l,
            stride_a_d,
            stride_b_l,
            stride_b_d,
            stride_y_l,
            stride_y_d,
            stride_state,
            CHUNK=chunk,
            BD=BD,
            num_warps=4,
            num_stages=2,
        )

    return Y


class Solution:
    def solve(self, spec_path: str = None) -> dict:
        header = "import torch\nimport triton\nimport triton.language as tl\n\n"
        kernel_src = textwrap.dedent(inspect.getsource(_scan_chunk_kernel))
        func_src = textwrap.dedent(inspect.getsource(chunk_scan))
        code = header + kernel_src + "\n\n" + func_src + "\n"
        return {"code": code}
