import torch
import triton
import triton.language as tl

class Solution:
    def solve(self, spec_path: str = None) -> dict:
        code = r'''
import torch
import triton
import triton.language as tl


@triton.jit
def gelu(x):
    return x * 0.5 * (1.0 + tl.extra.cuda.libdevice.erf(x * 0.7071067811865476))


@triton.autotune(
    configs=[
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 128, 'BLOCK_K': 32, 'GROUP_M': 8}, num_stages=3, num_warps=8),
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 64,  'BLOCK_K': 64, 'GROUP_M': 8}, num_stages=4, num_warps=8),
        triton.Config({'BLOCK_M': 64,  'BLOCK_N': 128, 'BLOCK_K': 64, 'GROUP_M': 8}, num_stages=4, num_warps=8),
        triton.Config({'BLOCK_M': 64,  'BLOCK_N': 256, 'BLOCK_K': 32, 'GROUP_M': 8}, num_stages=3, num_warps=8),
        triton.Config({'BLOCK_M': 256, 'BLOCK_N': 64,  'BLOCK_K': 32, 'GROUP_M': 8}, num_stages=3, num_warps=8),
        triton.Config({'BLOCK_M': 64,  'BLOCK_N': 64,  'BLOCK_K': 64, 'GROUP_M': 8}, num_stages=4, num_warps=4),
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
    ALLOW_TF32: tl.constexpr,
    BLOCK_M: tl.constexpr, BLOCK_N: tl.constexpr, BLOCK_K: tl.constexpr,
    GROUP_M: tl.constexpr,
):
    pid = tl.program_id(axis=0)
    num_pid_m = tl.cdiv(M, BLOCK_M)
    num_pid_n = tl.cdiv(N, BLOCK_N)
    group_size = GROUP_M
    group_id = pid // (group_size * num_pid_n)
    first_pid_m = group_id * group_size
    pid_in_group = pid % (group_size * num_pid_n)
    pid_m = first_pid_m + (pid_in_group % group_size)
    pid_n = pid_in_group // group_size

    offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
    offs_n = pid_n * BLOCK_N + tl.arange(0, BLOCK_N)
    offs_k = tl.arange(0, BLOCK_K)

    a_ptrs = a_ptr + (offs_m[:, None] * stride_am + offs_k[None, :] * stride_ak)
    b_ptrs = b_ptr + (offs_k[:, None] * stride_bk + offs_n[None, :] * stride_bn)

    acc = tl.zeros((BLOCK_M, BLOCK_N), dtype=tl.float32)

    k = 0
    while k < K:
        a = tl.load(
            a_ptrs,
            mask=(offs_m[:, None] < M) & (k + offs_k[None, :] < K),
            other=0.0,
        )
        b = tl.load(
            b_ptrs,
            mask=(k + offs_k[:, None] < K) & (offs_n[None, :] < N),
            other=0.0,
        )
        acc += tl.dot(a, b, allow_tf32=ALLOW_TF32)
        a_ptrs += BLOCK_K * stride_ak
        b_ptrs += BLOCK_K * stride_bk
        k += BLOCK_K

    acc = gelu(acc)
    c_mask = (offs_m[:, None] < M) & (offs_n[None, :] < N)
    # Cast to output dtype based on pointer type of c_ptr
    # Triton infers dtype from pointer; we cast accordingly.
    out = acc
    tl.store(c_ptr + offs_m[:, None] * stride_cm + offs_n[None, :] * stride_cn, out, mask=c_mask)


def _promote_dtype(a: torch.Tensor, b: torch.Tensor) -> torch.dtype:
    # Allow float16, bfloat16, float32. Fallback to float32 otherwise.
    supported = {torch.float16, torch.bfloat16, torch.float32}
    if a.dtype == b.dtype and a.dtype in supported:
        return a.dtype
    # Try promote
    dt = torch.promote_types(a.dtype, b.dtype)
    if dt not in supported:
        dt = torch.float32
    return dt


def matmul(a: torch.Tensor, b: torch.Tensor) -> torch.Tensor:
    """
    Matrix multiplication with GELU activation.
    a: (M, K)
    b: (K, N)
    returns: (M, N) with GELU applied
    """
    if not (a.is_cuda and b.is_cuda):
        return torch.nn.functional.gelu(a @ b)
    assert a.shape[1] == b.shape[0], "Incompatible dimensions"
    assert a.device == b.device, "Tensors must be on the same device"

    M, K = a.shape
    K2, N = b.shape
    assert K == K2

    dt = _promote_dtype(a, b)
    a_ = a.to(dt)
    b_ = b.to(dt)

    # Allocate output
    c = torch.empty((M, N), device=a.device, dtype=torch.float32)  # kernel stores float32 then can cast outside if needed

    # Strides in elements
    stride_am = a_.stride(0)
    stride_ak = a_.stride(1)
    stride_bk = b_.stride(0)
    stride_bn = b_.stride(1)
    stride_cm = c.stride(0)
    stride_cn = c.stride(1)

    def grid(meta):
        return (triton.cdiv(M, meta['BLOCK_M']) * triton.cdiv(N, meta['BLOCK_N']),)

    allow_tf32 = True

    _matmul_gelu_kernel[grid](
        a_, b_, c,
        M, N, K,
        stride_am, stride_ak,
        stride_bk, stride_bn,
        stride_cm, stride_cn,
        allow_tf32,
    )

    # Cast to input dtype if desired
    if dt != torch.float32:
        return c.to(dt)
    return c
'''
        return {"code": code}