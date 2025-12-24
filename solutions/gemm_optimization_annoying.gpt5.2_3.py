import math
import textwrap
import torch
import triton
import triton.language as tl


@triton.jit
def gelu(x):
    return x * 0.5 * (1.0 + tl.extra.cuda.libdevice.erf(x * 0.7071067811865476))


_AUTOTUNE_CONFIGS = [
    triton.Config({"BLOCK_M": 128, "BLOCK_N": 128, "BLOCK_K": 32, "GROUP_M": 8}, num_warps=8, num_stages=4),
    triton.Config({"BLOCK_M": 128, "BLOCK_N": 64, "BLOCK_K": 32, "GROUP_M": 8}, num_warps=8, num_stages=4),
    triton.Config({"BLOCK_M": 64, "BLOCK_N": 128, "BLOCK_K": 32, "GROUP_M": 8}, num_warps=8, num_stages=4),
    triton.Config({"BLOCK_M": 64, "BLOCK_N": 64, "BLOCK_K": 32, "GROUP_M": 8}, num_warps=4, num_stages=4),
    triton.Config({"BLOCK_M": 128, "BLOCK_N": 128, "BLOCK_K": 64, "GROUP_M": 8}, num_warps=8, num_stages=5),
    triton.Config({"BLOCK_M": 64, "BLOCK_N": 128, "BLOCK_K": 64, "GROUP_M": 8}, num_warps=8, num_stages=5),
]


@triton.autotune(configs=_AUTOTUNE_CONFIGS, key=["M", "N", "K", "OUT_DTYPE"])
@triton.jit
def _matmul_gelu_kernel(
    a_ptr,
    b_ptr,
    c_ptr,
    M: tl.constexpr,
    N: tl.constexpr,
    K: tl.constexpr,
    stride_am: tl.constexpr,
    stride_ak: tl.constexpr,
    stride_bk: tl.constexpr,
    stride_bn: tl.constexpr,
    stride_cm: tl.constexpr,
    stride_cn: tl.constexpr,
    OUT_DTYPE: tl.constexpr,
    BLOCK_M: tl.constexpr,
    BLOCK_N: tl.constexpr,
    BLOCK_K: tl.constexpr,
    GROUP_M: tl.constexpr,
):
    pid = tl.program_id(0)

    grid_m = tl.cdiv(M, BLOCK_M)
    grid_n = tl.cdiv(N, BLOCK_N)

    num_pid_in_group = GROUP_M * grid_n
    group_id = pid // num_pid_in_group
    first_pid_m = group_id * GROUP_M
    group_size_m = tl.minimum(grid_m - first_pid_m, GROUP_M)
    pid_in_group = pid - group_id * num_pid_in_group
    pid_m = first_pid_m + (pid_in_group % group_size_m)
    pid_n = pid_in_group // group_size_m

    offs_m = pid_m * BLOCK_M
    offs_n = pid_n * BLOCK_N

    A = tl.make_block_ptr(
        base=a_ptr,
        shape=(M, K),
        strides=(stride_am, stride_ak),
        offsets=(offs_m, 0),
        block_shape=(BLOCK_M, BLOCK_K),
        order=(1, 0),
    )
    B = tl.make_block_ptr(
        base=b_ptr,
        shape=(K, N),
        strides=(stride_bk, stride_bn),
        offsets=(0, offs_n),
        block_shape=(BLOCK_K, BLOCK_N),
        order=(0, 1),
    )

    acc = tl.zeros((BLOCK_M, BLOCK_N), dtype=tl.float32)

    k = 0
    while k < K:
        a = tl.load(A, boundary_check=(0, 1), padding_option="zero", eviction_policy="evict_first")
        b = tl.load(
            B,
            boundary_check=(0, 1),
            padding_option="zero",
            cache_modifier=".cg",
            eviction_policy="evict_last",
        )
        acc += tl.dot(a, b)
        A = tl.advance(A, (0, BLOCK_K))
        B = tl.advance(B, (BLOCK_K, 0))
        k += BLOCK_K

    acc = gelu(acc)

    if OUT_DTYPE == 0:
        out = acc.to(tl.float16)
    elif OUT_DTYPE == 1:
        out = acc.to(tl.bfloat16)
    else:
        out = acc.to(tl.float32)

    C = tl.make_block_ptr(
        base=c_ptr,
        shape=(M, N),
        strides=(stride_cm, stride_cn),
        offsets=(offs_m, offs_n),
        block_shape=(BLOCK_M, BLOCK_N),
        order=(1, 0),
    )
    tl.store(C, out, boundary_check=(0, 1))


def matmul(a: torch.Tensor, b: torch.Tensor) -> torch.Tensor:
    if not a.is_cuda or not b.is_cuda:
        return torch.nn.functional.gelu(a @ b)
    if a.ndim != 2 or b.ndim != 2:
        raise ValueError("matmul expects 2D tensors")
    M, K = a.shape
    K2, N = b.shape
    if K != K2:
        raise ValueError(f"incompatible shapes: {a.shape} x {b.shape}")

    if a.dtype != b.dtype:
        raise ValueError("a and b must have the same dtype")

    if a.dtype == torch.float16:
        out_dtype = 0
        c = torch.empty((M, N), device=a.device, dtype=torch.float16)
    elif a.dtype == torch.bfloat16:
        out_dtype = 1
        c = torch.empty((M, N), device=a.device, dtype=torch.bfloat16)
    elif a.dtype == torch.float32:
        out_dtype = 2
        c = torch.empty((M, N), device=a.device, dtype=torch.float32)
    else:
        return torch.nn.functional.gelu(a @ b)

    stride_am, stride_ak = a.stride()
    stride_bk, stride_bn = b.stride()
    stride_cm, stride_cn = c.stride()

    grid = lambda meta: (triton.cdiv(M, meta["BLOCK_M"]) * triton.cdiv(N, meta["BLOCK_N"]),)

    _matmul_gelu_kernel[grid](
        a,
        b,
        c,
        M=M,
        N=N,
        K=K,
        stride_am=stride_am,
        stride_ak=stride_ak,
        stride_bk=stride_bk,
        stride_bn=stride_bn,
        stride_cm=stride_cm,
        stride_cn=stride_cn,
        OUT_DTYPE=out_dtype,
    )
    return c


_KERNEL_CODE = textwrap.dedent(
    r"""
    import torch
    import triton
    import triton.language as tl

    @triton.jit
    def gelu(x):
        return x * 0.5 * (1.0 + tl.extra.cuda.libdevice.erf(x * 0.7071067811865476))

    _AUTOTUNE_CONFIGS = [
        triton.Config({"BLOCK_M": 128, "BLOCK_N": 128, "BLOCK_K": 32, "GROUP_M": 8}, num_warps=8, num_stages=4),
        triton.Config({"BLOCK_M": 128, "BLOCK_N": 64, "BLOCK_K": 32, "GROUP_M": 8}, num_warps=8, num_stages=4),
        triton.Config({"BLOCK_M": 64, "BLOCK_N": 128, "BLOCK_K": 32, "GROUP_M": 8}, num_warps=8, num_stages=4),
        triton.Config({"BLOCK_M": 64, "BLOCK_N": 64, "BLOCK_K": 32, "GROUP_M": 8}, num_warps=4, num_stages=4),
        triton.Config({"BLOCK_M": 128, "BLOCK_N": 128, "BLOCK_K": 64, "GROUP_M": 8}, num_warps=8, num_stages=5),
        triton.Config({"BLOCK_M": 64, "BLOCK_N": 128, "BLOCK_K": 64, "GROUP_M": 8}, num_warps=8, num_stages=5),
    ]

    @triton.autotune(configs=_AUTOTUNE_CONFIGS, key=["M", "N", "K", "OUT_DTYPE"])
    @triton.jit
    def _matmul_gelu_kernel(
        a_ptr,
        b_ptr,
        c_ptr,
        M: tl.constexpr,
        N: tl.constexpr,
        K: tl.constexpr,
        stride_am: tl.constexpr,
        stride_ak: tl.constexpr,
        stride_bk: tl.constexpr,
        stride_bn: tl.constexpr,
        stride_cm: tl.constexpr,
        stride_cn: tl.constexpr,
        OUT_DTYPE: tl.constexpr,
        BLOCK_M: tl.constexpr,
        BLOCK_N: tl.constexpr,
        BLOCK_K: tl.constexpr,
        GROUP_M: tl.constexpr,
    ):
        pid = tl.program_id(0)

        grid_m = tl.cdiv(M, BLOCK_M)
        grid_n = tl.cdiv(N, BLOCK_N)

        num_pid_in_group = GROUP_M * grid_n
        group_id = pid // num_pid_in_group
        first_pid_m = group_id * GROUP_M
        group_size_m = tl.minimum(grid_m - first_pid_m, GROUP_M)
        pid_in_group = pid - group_id * num_pid_in_group
        pid_m = first_pid_m + (pid_in_group % group_size_m)
        pid_n = pid_in_group // group_size_m

        offs_m = pid_m * BLOCK_M
        offs_n = pid_n * BLOCK_N

        A = tl.make_block_ptr(
            base=a_ptr,
            shape=(M, K),
            strides=(stride_am, stride_ak),
            offsets=(offs_m, 0),
            block_shape=(BLOCK_M, BLOCK_K),
            order=(1, 0),
        )
        B = tl.make_block_ptr(
            base=b_ptr,
            shape=(K, N),
            strides=(stride_bk, stride_bn),
            offsets=(0, offs_n),
            block_shape=(BLOCK_K, BLOCK_N),
            order=(0, 1),
        )

        acc = tl.zeros((BLOCK_M, BLOCK_N), dtype=tl.float32)

        k = 0
        while k < K:
            a = tl.load(A, boundary_check=(0, 1), padding_option="zero", eviction_policy="evict_first")
            b = tl.load(
                B,
                boundary_check=(0, 1),
                padding_option="zero",
                cache_modifier=".cg",
                eviction_policy="evict_last",
            )
            acc += tl.dot(a, b)
            A = tl.advance(A, (0, BLOCK_K))
            B = tl.advance(B, (BLOCK_K, 0))
            k += BLOCK_K

        acc = gelu(acc)

        if OUT_DTYPE == 0:
            out = acc.to(tl.float16)
        elif OUT_DTYPE == 1:
            out = acc.to(tl.bfloat16)
        else:
            out = acc.to(tl.float32)

        C = tl.make_block_ptr(
            base=c_ptr,
            shape=(M, N),
            strides=(stride_cm, stride_cn),
            offsets=(offs_m, offs_n),
            block_shape=(BLOCK_M, BLOCK_N),
            order=(1, 0),
        )
        tl.store(C, out, boundary_check=(0, 1))

    def matmul(a: torch.Tensor, b: torch.Tensor) -> torch.Tensor:
        if not a.is_cuda or not b.is_cuda:
            return torch.nn.functional.gelu(a @ b)
        if a.ndim != 2 or b.ndim != 2:
            raise ValueError("matmul expects 2D tensors")
        M, K = a.shape
        K2, N = b.shape
        if K != K2:
            raise ValueError(f"incompatible shapes: {a.shape} x {b.shape}")
        if a.dtype != b.dtype:
            raise ValueError("a and b must have the same dtype")

        if a.dtype == torch.float16:
            out_dtype = 0
            c = torch.empty((M, N), device=a.device, dtype=torch.float16)
        elif a.dtype == torch.bfloat16:
            out_dtype = 1
            c = torch.empty((M, N), device=a.device, dtype=torch.bfloat16)
        elif a.dtype == torch.float32:
            out_dtype = 2
            c = torch.empty((M, N), device=a.device, dtype=torch.float32)
        else:
            return torch.nn.functional.gelu(a @ b)

        stride_am, stride_ak = a.stride()
        stride_bk, stride_bn = b.stride()
        stride_cm, stride_cn = c.stride()

        grid = lambda meta: (triton.cdiv(M, meta["BLOCK_M"]) * triton.cdiv(N, meta["BLOCK_N"]),)

        _matmul_gelu_kernel[grid](
            a,
            b,
            c,
            M=M,
            N=N,
            K=K,
            stride_am=stride_am,
            stride_ak=stride_ak,
            stride_bk=stride_bk,
            stride_bn=stride_bn,
            stride_cm=stride_cm,
            stride_cn=stride_cn,
            OUT_DTYPE=out_dtype,
        )
        return c
    """
).lstrip()


class Solution:
    def solve(self, spec_path: str = None) -> dict:
        return {"code": _KERNEL_CODE}
