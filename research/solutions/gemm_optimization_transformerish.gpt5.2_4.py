import os
import math
import torch
import triton
import triton.language as tl

try:
    _tl_erf = tl.extra.cuda.libdevice.erf
except Exception:
    try:
        _tl_erf = tl.libdevice.erf
    except Exception:
        _tl_erf = tl.math.erf


@triton.jit
def gelu(x):
    return x * 0.5 * (1.0 + _tl_erf(x * 0.7071067811865476))


def _get_autotune_configs():
    cfgs = []
    for bm, bn, bk, nw, ns, gm in [
        (128, 128, 32, 8, 5, 8),
        (128, 128, 64, 8, 4, 8),
        (128, 64, 32, 4, 5, 8),
        (128, 64, 64, 4, 4, 8),
        (64, 128, 32, 4, 5, 8),
        (64, 128, 64, 4, 4, 8),
        (64, 64, 32, 4, 5, 8),
        (64, 64, 64, 4, 4, 8),
        (256, 64, 32, 8, 4, 4),
        (64, 256, 32, 8, 4, 4),
        (128, 256, 32, 8, 4, 4),
        (256, 128, 32, 8, 4, 4),
    ]:
        cfgs.append(
            triton.Config(
                {
                    "BLOCK_M": bm,
                    "BLOCK_N": bn,
                    "BLOCK_K": bk,
                    "GROUP_M": gm,
                },
                num_warps=nw,
                num_stages=ns,
            )
        )
    return cfgs


_HAS_BLOCK_PTR = hasattr(tl, "make_block_ptr") and hasattr(tl, "advance")


@triton.autotune(configs=_get_autotune_configs(), key=["M", "N", "K"])
@triton.jit
def _matmul_gelu_kernel_blockptr(
    a_ptr,
    b_ptr,
    c_ptr,
    M: tl.constexpr,
    N: tl.constexpr,
    K: tl.constexpr,
    stride_am,
    stride_ak,
    stride_bk,
    stride_bn,
    stride_cm,
    stride_cn,
    BLOCK_M: tl.constexpr,
    BLOCK_N: tl.constexpr,
    BLOCK_K: tl.constexpr,
    GROUP_M: tl.constexpr,
):
    pid = tl.program_id(0)

    num_pid_m = tl.cdiv(M, BLOCK_M)
    num_pid_n = tl.cdiv(N, BLOCK_N)

    group_size = GROUP_M * num_pid_n
    group_id = pid // group_size
    first_pid_m = group_id * GROUP_M
    pid_in_group = pid - group_id * group_size
    pid_m = first_pid_m + (pid_in_group % GROUP_M)
    pid_n = pid_in_group // GROUP_M

    a_block_ptr = tl.make_block_ptr(
        base=a_ptr,
        shape=(M, K),
        strides=(stride_am, stride_ak),
        offsets=(pid_m * BLOCK_M, 0),
        block_shape=(BLOCK_M, BLOCK_K),
        order=(1, 0),
    )
    b_block_ptr = tl.make_block_ptr(
        base=b_ptr,
        shape=(K, N),
        strides=(stride_bk, stride_bn),
        offsets=(0, pid_n * BLOCK_N),
        block_shape=(BLOCK_K, BLOCK_N),
        order=(1, 0),
    )
    c_block_ptr = tl.make_block_ptr(
        base=c_ptr,
        shape=(M, N),
        strides=(stride_cm, stride_cn),
        offsets=(pid_m * BLOCK_M, pid_n * BLOCK_N),
        block_shape=(BLOCK_M, BLOCK_N),
        order=(1, 0),
    )

    acc = tl.zeros((BLOCK_M, BLOCK_N), dtype=tl.float32)

    k = 0
    while k < K:
        a = tl.load(a_block_ptr, boundary_check=(0, 1), padding_option="zero")
        b = tl.load(b_block_ptr, boundary_check=(0, 1), padding_option="zero")
        acc = tl.dot(a, b, acc, out_dtype=tl.float32)
        a_block_ptr = tl.advance(a_block_ptr, (0, BLOCK_K))
        b_block_ptr = tl.advance(b_block_ptr, (BLOCK_K, 0))
        k += BLOCK_K

    out = gelu(acc)
    tl.store(c_block_ptr, out.to(tl.element_type(c_ptr)), boundary_check=(0, 1))


@triton.autotune(configs=_get_autotune_configs(), key=["M", "N", "K"])
@triton.jit
def _matmul_gelu_kernel_ptrarith(
    a_ptr,
    b_ptr,
    c_ptr,
    M,
    N,
    K,
    stride_am,
    stride_ak,
    stride_bk,
    stride_bn,
    stride_cm,
    stride_cn,
    BLOCK_M: tl.constexpr,
    BLOCK_N: tl.constexpr,
    BLOCK_K: tl.constexpr,
    GROUP_M: tl.constexpr,
):
    pid = tl.program_id(0)

    num_pid_m = tl.cdiv(M, BLOCK_M)
    num_pid_n = tl.cdiv(N, BLOCK_N)

    group_size = GROUP_M * num_pid_n
    group_id = pid // group_size
    first_pid_m = group_id * GROUP_M
    pid_in_group = pid - group_id * group_size
    pid_m = first_pid_m + (pid_in_group % GROUP_M)
    pid_n = pid_in_group // GROUP_M

    offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
    offs_n = pid_n * BLOCK_N + tl.arange(0, BLOCK_N)
    offs_k = tl.arange(0, BLOCK_K)

    acc = tl.zeros((BLOCK_M, BLOCK_N), dtype=tl.float32)

    a_ptrs = a_ptr + offs_m[:, None] * stride_am + offs_k[None, :] * stride_ak
    b_ptrs = b_ptr + offs_k[:, None] * stride_bk + offs_n[None, :] * stride_bn

    k = 0
    while k < K:
        a = tl.load(a_ptrs, mask=(offs_m[:, None] < M) & (k + offs_k[None, :] < K), other=0.0)
        b = tl.load(b_ptrs, mask=(k + offs_k[:, None] < K) & (offs_n[None, :] < N), other=0.0)
        acc += tl.dot(a, b, out_dtype=tl.float32)

        k += BLOCK_K
        a_ptrs += BLOCK_K * stride_ak
        b_ptrs += BLOCK_K * stride_bk

    out = gelu(acc)

    c_ptrs = c_ptr + offs_m[:, None] * stride_cm + offs_n[None, :] * stride_cn
    tl.store(c_ptrs, out.to(tl.element_type(c_ptr)), mask=(offs_m[:, None] < M) & (offs_n[None, :] < N))


def matmul(a: torch.Tensor, b: torch.Tensor) -> torch.Tensor:
    if not (isinstance(a, torch.Tensor) and isinstance(b, torch.Tensor)):
        raise TypeError("a and b must be torch.Tensor")
    if a.dim() != 2 or b.dim() != 2:
        raise ValueError("a and b must be 2D tensors")
    if a.device.type != "cuda" or b.device.type != "cuda":
        raise ValueError("a and b must be CUDA tensors")
    if a.shape[1] != b.shape[0]:
        raise ValueError("incompatible shapes")
    if a.dtype not in (torch.float16, torch.bfloat16) or b.dtype != a.dtype:
        out = torch.matmul(a, b)
        return torch.nn.functional.gelu(out, approximate="none")

    M, K = a.shape
    _, N = b.shape
    c = torch.empty((M, N), device=a.device, dtype=a.dtype)

    stride_am, stride_ak = a.stride()
    stride_bk, stride_bn = b.stride()
    stride_cm, stride_cn = c.stride()

    grid = lambda META: (triton.cdiv(M, META["BLOCK_M"]) * triton.cdiv(N, META["BLOCK_N"]),)

    if _HAS_BLOCK_PTR:
        _matmul_gelu_kernel_blockptr[grid](
            a,
            b,
            c,
            M,
            N,
            K,
            stride_am,
            stride_ak,
            stride_bk,
            stride_bn,
            stride_cm,
            stride_cn,
        )
    else:
        _matmul_gelu_kernel_ptrarith[grid](
            a,
            b,
            c,
            M,
            N,
            K,
            stride_am,
            stride_ak,
            stride_bk,
            stride_bn,
            stride_cm,
            stride_cn,
        )
    return c


class Solution:
    def solve(self, spec_path: str = None) -> dict:
        try:
            return {"program_path": os.path.abspath(__file__)}
        except Exception:
            import inspect
            import sys
            code = inspect.getsource(sys.modules[__name__])
            return {"code": code}
