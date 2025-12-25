import math
import textwrap
import torch
import triton
import triton.language as tl


@triton.jit
def gelu(x):
    return x * 0.5 * (1.0 + tl.extra.cuda.libdevice.erf(x * 0.7071067811865476))


def _get_autotune_configs():
    configs = []
    for bm, bn, bk, stages, warps, group_m in [
        (128, 128, 32, 4, 8, 8),
        (128, 128, 64, 4, 8, 8),
        (128, 128, 128, 3, 8, 8),
        (128, 64, 64, 4, 4, 8),
        (64, 128, 64, 4, 4, 8),
        (64, 64, 64, 4, 4, 8),
        (256, 128, 32, 3, 8, 4),
        (128, 256, 32, 3, 8, 4),
    ]:
        configs.append(
            triton.Config(
                {"BLOCK_M": bm, "BLOCK_N": bn, "BLOCK_K": bk, "GROUP_M": group_m},
                num_warps=warps,
                num_stages=stages,
            )
        )
    return configs


@triton.autotune(
    configs=_get_autotune_configs(),
    key=["M", "N", "K", "stride_am", "stride_ak", "stride_bk", "stride_bn"],
)
@triton.heuristics(
    {
        "EVEN_K": lambda args: (args["K"] % args["BLOCK_K"]) == 0,
    }
)
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
    BLOCK_M: tl.constexpr,
    BLOCK_N: tl.constexpr,
    BLOCK_K: tl.constexpr,
    GROUP_M: tl.constexpr,
    EVEN_K: tl.constexpr,
):
    pid = tl.program_id(0)
    grid_m = tl.cdiv(M, BLOCK_M)
    grid_n = tl.cdiv(N, BLOCK_N)

    group_size = GROUP_M * grid_n
    pid_group = pid // group_size
    first_pid_m = pid_group * GROUP_M
    pid_in_group = pid - pid_group * group_size
    pid_m = first_pid_m + (pid_in_group // grid_n)
    pid_n = pid_in_group % grid_n

    offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
    offs_n = pid_n * BLOCK_N + tl.arange(0, BLOCK_N)
    offs_k = tl.arange(0, BLOCK_K)

    a_ptrs = a_ptr + offs_m[:, None] * stride_am + offs_k[None, :] * stride_ak
    b_ptrs = b_ptr + offs_k[:, None] * stride_bk + offs_n[None, :] * stride_bn

    acc = tl.zeros((BLOCK_M, BLOCK_N), dtype=tl.float32)

    m_mask = offs_m[:, None] < M
    n_mask = offs_n[None, :] < N

    if EVEN_K:
        for _k in range(0, K, BLOCK_K):
            a = tl.load(a_ptrs, mask=m_mask, other=0.0)
            b = tl.load(b_ptrs, mask=n_mask, other=0.0)
            acc = tl.dot(a, b, acc=acc)
            a_ptrs += BLOCK_K * stride_ak
            b_ptrs += BLOCK_K * stride_bk
    else:
        for k in range(0, K, BLOCK_K):
            k_mask = (k + offs_k)[None, :] < K
            a = tl.load(a_ptrs, mask=m_mask & k_mask, other=0.0)
            b = tl.load(b_ptrs, mask=((k + offs_k)[:, None] < K) & n_mask, other=0.0)
            acc = tl.dot(a, b, acc=acc)
            a_ptrs += BLOCK_K * stride_ak
            b_ptrs += BLOCK_K * stride_bk

    acc = gelu(acc)

    c_ptrs = c_ptr + offs_m[:, None] * stride_cm + offs_n[None, :] * stride_cn
    out_mask = (offs_m[:, None] < M) & (offs_n[None, :] < N)
    tl.store(c_ptrs, acc, mask=out_mask)


def matmul(a: torch.Tensor, b: torch.Tensor) -> torch.Tensor:
    if not a.is_cuda or not b.is_cuda:
        raise ValueError("Inputs must be CUDA tensors.")
    if a.ndim != 2 or b.ndim != 2:
        raise ValueError("Inputs must be 2D tensors.")
    if a.shape[1] != b.shape[0]:
        raise ValueError(f"Incompatible shapes: a={tuple(a.shape)} b={tuple(b.shape)}")
    if a.dtype != b.dtype:
        raise ValueError("Inputs must have the same dtype.")

    M, K = a.shape
    _, N = b.shape

    c = torch.empty((M, N), device=a.device, dtype=a.dtype)

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

    def _get_autotune_configs():
        configs = []
        for bm, bn, bk, stages, warps, group_m in [
            (128, 128, 32, 4, 8, 8),
            (128, 128, 64, 4, 8, 8),
            (128, 128, 128, 3, 8, 8),
            (128, 64, 64, 4, 4, 8),
            (64, 128, 64, 4, 4, 8),
            (64, 64, 64, 4, 4, 8),
            (256, 128, 32, 3, 8, 4),
            (128, 256, 32, 3, 8, 4),
        ]:
            configs.append(
                triton.Config(
                    {"BLOCK_M": bm, "BLOCK_N": bn, "BLOCK_K": bk, "GROUP_M": group_m},
                    num_warps=warps,
                    num_stages=stages,
                )
            )
        return configs

    @triton.autotune(
        configs=_get_autotune_configs(),
        key=["M", "N", "K", "stride_am", "stride_ak", "stride_bk", "stride_bn"],
    )
    @triton.heuristics(
        {
            "EVEN_K": lambda args: (args["K"] % args["BLOCK_K"]) == 0,
        }
    )
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
        BLOCK_M: tl.constexpr,
        BLOCK_N: tl.constexpr,
        BLOCK_K: tl.constexpr,
        GROUP_M: tl.constexpr,
        EVEN_K: tl.constexpr,
    ):
        pid = tl.program_id(0)
        grid_m = tl.cdiv(M, BLOCK_M)
        grid_n = tl.cdiv(N, BLOCK_N)

        group_size = GROUP_M * grid_n
        pid_group = pid // group_size
        first_pid_m = pid_group * GROUP_M
        pid_in_group = pid - pid_group * group_size
        pid_m = first_pid_m + (pid_in_group // grid_n)
        pid_n = pid_in_group % grid_n

        offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
        offs_n = pid_n * BLOCK_N + tl.arange(0, BLOCK_N)
        offs_k = tl.arange(0, BLOCK_K)

        a_ptrs = a_ptr + offs_m[:, None] * stride_am + offs_k[None, :] * stride_ak
        b_ptrs = b_ptr + offs_k[:, None] * stride_bk + offs_n[None, :] * stride_bn

        acc = tl.zeros((BLOCK_M, BLOCK_N), dtype=tl.float32)

        m_mask = offs_m[:, None] < M
        n_mask = offs_n[None, :] < N

        if EVEN_K:
            for _k in range(0, K, BLOCK_K):
                a = tl.load(a_ptrs, mask=m_mask, other=0.0)
                b = tl.load(b_ptrs, mask=n_mask, other=0.0)
                acc = tl.dot(a, b, acc=acc)
                a_ptrs += BLOCK_K * stride_ak
                b_ptrs += BLOCK_K * stride_bk
        else:
            for k in range(0, K, BLOCK_K):
                k_mask = (k + offs_k)[None, :] < K
                a = tl.load(a_ptrs, mask=m_mask & k_mask, other=0.0)
                b = tl.load(b_ptrs, mask=((k + offs_k)[:, None] < K) & n_mask, other=0.0)
                acc = tl.dot(a, b, acc=acc)
                a_ptrs += BLOCK_K * stride_ak
                b_ptrs += BLOCK_K * stride_bk

        acc = gelu(acc)

        c_ptrs = c_ptr + offs_m[:, None] * stride_cm + offs_n[None, :] * stride_cn
        out_mask = (offs_m[:, None] < M) & (offs_n[None, :] < N)
        tl.store(c_ptrs, acc, mask=out_mask)

    def matmul(a: torch.Tensor, b: torch.Tensor) -> torch.Tensor:
        if not a.is_cuda or not b.is_cuda:
            raise ValueError("Inputs must be CUDA tensors.")
        if a.ndim != 2 or b.ndim != 2:
            raise ValueError("Inputs must be 2D tensors.")
        if a.shape[1] != b.shape[0]:
            raise ValueError(f"Incompatible shapes: a={tuple(a.shape)} b={tuple(b.shape)}")
        if a.dtype != b.dtype:
            raise ValueError("Inputs must have the same dtype.")

        M, K = a.shape
        _, N = b.shape

        c = torch.empty((M, N), device=a.device, dtype=a.dtype)

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
        )
        return c
    """
).lstrip()


class Solution:
    def solve(self, spec_path: str = None) -> dict:
        return {"code": _KERNEL_CODE}
