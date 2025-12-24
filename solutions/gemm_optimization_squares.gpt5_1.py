import os
import torch
import triton
import triton.language as tl


@triton.jit
def gelu(x):
    return x * 0.5 * (1.0 + tl.extra.cuda.libdevice.erf(x * 0.7071067811865476))


@triton.autotune(
    configs=[
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 128, 'BLOCK_K': 64, 'GROUP_M': 8}, num_warps=8, num_stages=4),
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 256, 'BLOCK_K': 64, 'GROUP_M': 4}, num_warps=8, num_stages=4),
        triton.Config({'BLOCK_M': 256, 'BLOCK_N': 128, 'BLOCK_K': 64, 'GROUP_M': 4}, num_warps=8, num_stages=4),
        triton.Config({'BLOCK_M': 64,  'BLOCK_N': 256, 'BLOCK_K': 64, 'GROUP_M': 8}, num_warps=8, num_stages=4),
        triton.Config({'BLOCK_M': 256, 'BLOCK_N': 64,  'BLOCK_K': 64, 'GROUP_M': 8}, num_warps=8, num_stages=4),
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 128, 'BLOCK_K': 32, 'GROUP_M': 8}, num_warps=4, num_stages=5),
        triton.Config({'BLOCK_M': 64,  'BLOCK_N': 128, 'BLOCK_K': 64, 'GROUP_M': 8}, num_warps=4, num_stages=4),
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 64,  'BLOCK_K': 64, 'GROUP_M': 8}, num_warps=4, num_stages=4),
    ],
    key=['M', 'N', 'K'],
)
@triton.jit
def _matmul_gelu_kernel(
    a_ptr, b_ptr, c_ptr,
    M, N, K,
    stride_am, stride_ak,
    stride_bk, stride_bn,
    stride_cm, stride_cn,
    out_dtype_id: tl.constexpr,
    BLOCK_M: tl.constexpr, BLOCK_N: tl.constexpr, BLOCK_K: tl.constexpr,
    GROUP_M: tl.constexpr,
):
    pid = tl.program_id(axis=0)
    num_pid_m = tl.cdiv(M, BLOCK_M)
    num_pid_n = tl.cdiv(N, BLOCK_N)
    num_pid_in_group = GROUP_M * num_pid_n
    group_id = pid // num_pid_in_group
    first_pid_m = group_id * GROUP_M
    group_size_m = tl.minimum(num_pid_m - first_pid_m, GROUP_M)
    pid_m = first_pid_m + (pid % group_size_m)
    pid_n = (pid % num_pid_in_group) // group_size_m

    offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
    offs_n = pid_n * BLOCK_N + tl.arange(0, BLOCK_N)
    offs_k = tl.arange(0, BLOCK_K)

    a_ptrs = a_ptr + (offs_m[:, None] * stride_am + offs_k[None, :] * stride_ak)
    b_ptrs = b_ptr + (offs_k[:, None] * stride_bk + offs_n[None, :] * stride_bn)

    acc = tl.zeros((BLOCK_M, BLOCK_N), dtype=tl.float32)

    k_iter = tl.cdiv(K, BLOCK_K)
    for ki in range(0, k_iter):
        k_base = ki * BLOCK_K
        a_mask = (offs_m[:, None] < M) & (k_base + offs_k[None, :] < K)
        b_mask = (k_base + offs_k[:, None] < K) & (offs_n[None, :] < N)

        a = tl.load(a_ptrs, mask=a_mask, other=0.0)
        b = tl.load(b_ptrs, mask=b_mask, other=0.0)
        acc += tl.dot(a, b)

        a_ptrs += BLOCK_K * stride_ak
        b_ptrs += BLOCK_K * stride_bk

    # GELU activation in float32, then cast to desired output dtype
    acc = gelu(acc)

    # Cast to output dtype based on id
    # 0: float16, 1: bfloat16, 2: float32
    out = acc
    if out_dtype_id == 0:
        out = out.to(tl.float16)
    elif out_dtype_id == 1:
        out = out.to(tl.bfloat16)
    else:
        out = out.to(tl.float32)

    c_ptrs = c_ptr + (offs_m[:, None] * stride_cm + offs_n[None, :] * stride_cn)
    c_mask = (offs_m[:, None] < M) & (offs_n[None, :] < N)
    tl.store(c_ptrs, out, mask=c_mask)


def _get_out_dtype_id(a: torch.dtype, b: torch.dtype) -> int:
    # Returns id matching kernel logic
    # 0: float16, 1: bfloat16, 2: float32
    if a == torch.float16 and b == torch.float16:
        return 0
    if a == torch.bfloat16 and b == torch.bfloat16:
        return 1
    # If any is float32 or mixed types, use float32 for numerical stability
    return 2


def _promote_output_dtype(a: torch.dtype, b: torch.dtype) -> torch.dtype:
    if a == torch.float16 and b == torch.float16:
        return torch.float16
    if a == torch.bfloat16 and b == torch.bfloat16:
        return torch.bfloat16
    return torch.float32


def matmul(a: torch.Tensor, b: torch.Tensor) -> torch.Tensor:
    if a.ndim != 2 or b.ndim != 2:
        raise ValueError("Input tensors must be 2D")
    if a.shape[1] != b.shape[0]:
        raise ValueError("Incompatible dimensions for matmul")
    if not a.is_cuda or not b.is_cuda:
        raise ValueError("Input tensors must be on CUDA device")
    if a.dtype not in (torch.float16, torch.bfloat16, torch.float32):
        raise TypeError("Unsupported dtype for a: {}".format(a.dtype))
    if b.dtype not in (torch.float16, torch.bfloat16, torch.float32):
        raise TypeError("Unsupported dtype for b: {}".format(b.dtype))

    M, K = a.shape
    K2, N = b.shape
    assert K == K2

    out_dtype = _promote_output_dtype(a.dtype, b.dtype)
    c = torch.empty((M, N), device=a.device, dtype=out_dtype)

    # Prepare strides in elements
    stride_am, stride_ak = a.stride()
    stride_bk, stride_bn = b.stride()
    stride_cm, stride_cn = c.stride()

    out_dtype_id = _get_out_dtype_id(a.dtype, b.dtype)

    grid = lambda META: (
        triton.cdiv(M, META['BLOCK_M']) * triton.cdiv(N, META['BLOCK_N']),
    )

    _matmul_gelu_kernel[grid](
        a, b, c,
        M, N, K,
        stride_am, stride_ak,
        stride_bk, stride_bn,
        stride_cm, stride_cn,
        out_dtype_id,
    )
    return c


class Solution:
    def solve(self, spec_path: str = None) -> dict:
        try:
            with open(__file__, "r", encoding="utf-8") as f:
                return {"code": f.read()}
        except Exception:
            return {"program_path": os.path.abspath(__file__)}
