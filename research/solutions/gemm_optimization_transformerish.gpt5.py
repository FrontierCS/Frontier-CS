import os
import textwrap

class Solution:
    def solve(self, spec_path: str = None) -> dict:
        code = r'''
import torch
import triton
import triton.language as tl

@triton.jit
def gelu(x):
    return x * 0.5 * (1.0 + tl.extra.cuda.libdevice.erf(x * 0.7071067811865476))


def _get_configs():
    configs = []
    # A variety of tile sizes for different problem shapes
    for BM, BN, BK, WARPS, STAGES in [
        (128, 128, 32, 8, 3),
        (128, 256, 32, 8, 4),
        (256, 128, 32, 8, 4),
        (64, 256, 64, 8, 4),
        (256, 64, 64, 8, 4),
        (128, 128, 64, 8, 4),
        (64, 128, 64, 4, 3),
        (128, 64, 64, 4, 3),
        (64, 64, 64, 4, 3),
        (64, 128, 32, 4, 3),
        (128, 64, 32, 4, 3),
    ]:
        configs.append(
            triton.Config(
                {'BLOCK_M': BM, 'BLOCK_N': BN, 'BLOCK_K': BK, 'GROUP_SIZE_M': 8},
                num_stages=STAGES,
                num_warps=WARPS,
            )
        )
    return configs


@triton.autotune(configs=_get_configs(), key=['M', 'N', 'K'])
@triton.jit
def matmul_gelu_kernel(
    a_ptr, b_ptr, c_ptr,
    M, N, K,
    stride_am, stride_ak,
    stride_bk, stride_bn,
    stride_cm, stride_cn,
    # Meta-parameters
    BLOCK_M: tl.constexpr, BLOCK_N: tl.constexpr, BLOCK_K: tl.constexpr,
    GROUP_SIZE_M: tl.constexpr,
):
    # Program id
    pid = tl.program_id(axis=0)
    num_pid_m = tl.cdiv(M, BLOCK_M)
    num_pid_n = tl.cdiv(N, BLOCK_N)
    group_size = GROUP_SIZE_M * num_pid_n

    group_id = pid // group_size
    first_pid_m = group_id * GROUP_SIZE_M
    pid_in_group = pid % group_size
    pid_m = first_pid_m + (pid_in_group % GROUP_SIZE_M)
    pid_n = pid_in_group // GROUP_SIZE_M

    offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
    offs_n = pid_n * BLOCK_N + tl.arange(0, BLOCK_N)
    offs_k = tl.arange(0, BLOCK_K)

    a_ptrs = a_ptr + (offs_m[:, None] * stride_am + offs_k[None, :] * stride_ak)
    b_ptrs = b_ptr + (offs_k[:, None] * stride_bk + offs_n[None, :] * stride_bn)

    acc = tl.zeros((BLOCK_M, BLOCK_N), dtype=tl.float32)

    k_iter = tl.cdiv(K, BLOCK_K)
    for _ in range(0, k_iter):
        a = tl.load(a_ptrs, mask=(offs_m[:, None] < M) & (offs_k[None, :] < K), other=0.0)
        b = tl.load(b_ptrs, mask=(offs_k[:, None] < K) & (offs_n[None, :] < N), other=0.0)
        acc += tl.dot(a, b)
        a_ptrs += BLOCK_K * stride_ak
        b_ptrs += BLOCK_K * stride_bk
        offs_k += BLOCK_K

    # GELU activation in fp32
    acc = gelu(acc)

    # Write back to C, cast to destination dtype
    c = acc
    c_mask = (offs_m[:, None] < M) & (offs_n[None, :] < N)
    c_ptrs = c_ptr + (offs_m[:, None] * stride_cm + offs_n[None, :] * stride_cn)

    # Determine the dtype of C from the pointer; cast acc to that dtype
    # Triton infers the dtype from the pointer on tl.store.
    tl.store(c_ptrs, c, mask=c_mask)


def _ensure_supported_dtype(t: torch.Tensor) -> torch.dtype:
    if t.dtype in (torch.float16, torch.bfloat16, torch.float32):
        return t.dtype
    # fallback cast to fp16 for unsupported types for performance
    return torch.float16


def matmul(a: torch.Tensor, b: torch.Tensor) -> torch.Tensor:
    """
    Matrix multiplication with GELU activation.

    Args:
        a: Input tensor of shape (M, K)
        b: Input tensor of shape (K, N)

    Returns:
        Output tensor of shape (M, N) with GELU activation applied
    """
    assert a.dim() == 2 and b.dim() == 2, "matmul expects 2D tensors"
    assert a.shape[1] == b.shape[0], "Incompatible dimensions"
    M, K = a.shape
    K2, N = b.shape
    assert K == K2

    if not a.is_cuda or not b.is_cuda:
        # CPU fallback
        return torch.nn.functional.gelu(a @ b)

    # Ensure data types supported and matching
    a_dtype = _ensure_supported_dtype(a)
    b_dtype = _ensure_supported_dtype(b)

    # Promote dtype sensibly:
    # If either is float32 -> float32
    # elif either is bfloat16 -> bfloat16 (assuming both are half-precision)
    # else float16
    if a_dtype == torch.float32 or b_dtype == torch.float32:
        out_dtype = torch.float32
    elif a_dtype == torch.bfloat16 or b_dtype == torch.bfloat16:
        out_dtype = torch.bfloat16
    else:
        out_dtype = torch.float16

    A = a.to(dtype=a_dtype)
    B = b.to(dtype=b_dtype)

    # Create output tensor
    C = torch.empty((M, N), device=A.device, dtype=out_dtype)

    # Get strides
    stride_am = A.stride(0)
    stride_ak = A.stride(1)
    stride_bk = B.stride(0)
    stride_bn = B.stride(1)
    stride_cm = C.stride(0)
    stride_cn = C.stride(1)

    # Launch kernel
    def grid(meta):
        return (triton.cdiv(M, meta['BLOCK_M']) * triton.cdiv(N, meta['BLOCK_N']),)

    matmul_gelu_kernel[grid](
        A, B, C,
        M, N, K,
        stride_am, stride_ak,
        stride_bk, stride_bn,
        stride_cm, stride_cn,
    )
    return C
        '''
        return {"code": textwrap.dedent(code)}
