import os
import math
import torch
import triton
import triton.language as tl


@triton.jit
def gelu(x):
    return x * 0.5 * (1.0 + tl.extra.cuda.libdevice.erf(x * 0.7071067811865476))


@triton.autotune(
    configs=[
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 128, 'BLOCK_K': 32}, num_stages=3, num_warps=8),
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 64,  'BLOCK_K': 32}, num_stages=4, num_warps=4),
        triton.Config({'BLOCK_M': 64,  'BLOCK_N': 128, 'BLOCK_K': 32}, num_stages=4, num_warps=4),
        triton.Config({'BLOCK_M': 64,  'BLOCK_N': 256, 'BLOCK_K': 32}, num_stages=4, num_warps=8),
        triton.Config({'BLOCK_M': 256, 'BLOCK_N': 64,  'BLOCK_K': 32}, num_stages=4, num_warps=8),
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 128, 'BLOCK_K': 64}, num_stages=4, num_warps=8),
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 256, 'BLOCK_K': 64}, num_stages=4, num_warps=8),
        triton.Config({'BLOCK_M': 256, 'BLOCK_N': 128, 'BLOCK_K': 64}, num_stages=4, num_warps=8),
        triton.Config({'BLOCK_M': 64,  'BLOCK_N': 64,  'BLOCK_K': 32}, num_stages=3, num_warps=2),
    ],
    key=['M', 'N', 'K', 'EVEN_K', 'EVEN_M', 'EVEN_N', 'USE_TL_DOT'],
)
@triton.jit
def matmul_gelu_kernel(
    A, B, C,
    M, N, K,
    stride_am, stride_ak,
    stride_bk, stride_bn,
    stride_cm, stride_cn,
    EVEN_M: tl.constexpr, EVEN_N: tl.constexpr, EVEN_K: tl.constexpr,
    BLOCK_M: tl.constexpr, BLOCK_N: tl.constexpr, BLOCK_K: tl.constexpr,
    USE_TL_DOT: tl.constexpr,
):
    pid_m = tl.program_id(0)
    pid_n = tl.program_id(1)

    offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
    offs_n = pid_n * BLOCK_N + tl.arange(0, BLOCK_N)
    offs_k = tl.arange(0, BLOCK_K)

    mask_m = offs_m < M
    mask_n = offs_n < N

    acc = tl.zeros((BLOCK_M, BLOCK_N), dtype=tl.float32)

    a_ptrs = A + offs_m[:, None] * stride_am + offs_k[None, :] * stride_ak
    b_ptrs = B + offs_k[:, None] * stride_bk + offs_n[None, :] * stride_bn

    if EVEN_K:
        k = 0
        while k < K:
            a = tl.load(a_ptrs, mask=mask_m[:, None], other=0.0)
            b = tl.load(b_ptrs, mask=mask_n[None, :], other=0.0)
            if USE_TL_DOT:
                acc += tl.dot(a, b)
            else:
                for kk in range(0, BLOCK_K):
                    acc += a[:, kk][:, None] * b[kk, :][None, :]
            a_ptrs += BLOCK_K * stride_ak
            b_ptrs += BLOCK_K * stride_bk
            k += BLOCK_K
    else:
        k = 0
        while k < K:
            k_mask = k + offs_k < K
            a = tl.load(a_ptrs, mask=mask_m[:, None] & k_mask[None, :], other=0.0)
            b = tl.load(b_ptrs, mask=k_mask[:, None] & mask_n[None, :], other=0.0)
            if USE_TL_DOT:
                acc += tl.dot(a, b)
            else:
                for kk in range(0, BLOCK_K):
                    acc += a[:, kk][:, None] * b[kk, :][None, :]
            a_ptrs += BLOCK_K * stride_ak
            b_ptrs += BLOCK_K * stride_bk
            k += BLOCK_K

    acc = gelu(acc)

    c_ptrs = C + offs_m[:, None] * stride_cm + offs_n[None, :] * stride_cn
    tl.store(c_ptrs, acc, mask=mask_m[:, None] & mask_n[None, :])


def matmul(a: torch.Tensor, b: torch.Tensor) -> torch.Tensor:
    """
    Matrix multiplication with GELU activation.
    
    Args:
        a: Input tensor of shape (M, K)
        b: Input tensor of shape (K, N)
    
    Returns:
        Output tensor of shape (M, N) with GELU activation applied
    """
    assert a.is_cuda and b.is_cuda, "Inputs must be CUDA tensors"
    assert a.shape[1] == b.shape[0], "Incompatible matrix shapes"
    M, K = a.shape
    Kb, N = b.shape
    assert K == Kb

    # Determine output dtype
    out_dtype = a.dtype if a.dtype == b.dtype else torch.result_type(a, b)
    c = torch.empty((M, N), device=a.device, dtype=out_dtype)

    # Strides
    stride_am, stride_ak = a.stride()
    stride_bk, stride_bn = b.stride()
    stride_cm, stride_cn = c.stride()

    # Meta flags
    EVEN_M = (M % 1 == 0) and (M % 32 == 0)  # approximate heuristic for masking benefit
    EVEN_N = (N % 1 == 0) and (N % 32 == 0)
    # True even-K check based on various BLOCK_K; final masking still handled inside kernel
    # We'll set EVEN_K True only if divisible by the maximal BLOCK_K across configs
    # to maximize fast path; still safe due to autotuner choosing smaller BLOCK_Ks.
    max_bk = 64
    EVEN_K = (K % max_bk) == 0

    # Decide compute path
    use_tl_dot = (a.dtype in (torch.float16, torch.bfloat16)) and (b.dtype in (torch.float16, torch.bfloat16))

    def grid(meta):
        return (triton.cdiv(M, meta['BLOCK_M']), triton.cdiv(N, meta['BLOCK_N']))

    matmul_gelu_kernel[grid](
        a, b, c,
        M, N, K,
        stride_am, stride_ak,
        stride_bk, stride_bn,
        stride_cm, stride_cn,
        EVEN_M=EVEN_M, EVEN_N=EVEN_N, EVEN_K=EVEN_K,
        USE_TL_DOT=use_tl_dot,
    )
    return c


class Solution:
    def solve(self, spec_path: str = None) -> dict:
        try:
            return {"program_path": os.path.abspath(__file__)}
        except NameError:
            # __file__ may not be defined in some execution contexts
            # Fallback to returning code string of this module
            import inspect
            return {"code": inspect.getsource(type(self).__module__)}
