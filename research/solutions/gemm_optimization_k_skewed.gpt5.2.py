import os
import inspect
import torch
import triton
import triton.language as tl


@triton.jit
def gelu(x):
    return x * 0.5 * (1.0 + tl.extra.cuda.libdevice.erf(x * 0.7071067811865476))


def _early_config_prune(configs, named_args, **meta):
    try:
        M = int(named_args.get("M", 0))
        N = int(named_args.get("N", 0))
        K = int(named_args.get("K", 0))
    except Exception:
        return [configs[0]] if configs else configs

    if K <= 64:
        bk_pref = 16
    elif K <= 256:
        bk_pref = 32
    elif K >= 6144:
        bk_pref = 128
    else:
        bk_pref = 64

    if N <= 256:
        bn_pref = 128
    else:
        bn_pref = 256

    if N <= 256 and M >= 1024:
        bm_pref = 256
    else:
        bm_pref = 128

    def cost(c):
        kw = c.kwargs
        bm = int(kw.get("BLOCK_M", 128))
        bn = int(kw.get("BLOCK_N", 128))
        bk = int(kw.get("BLOCK_K", 32))
        cst = 0
        cst += 1000 * (0 if bk == bk_pref else 1)
        cst += 100 * abs(bk - bk_pref)
        cst += 50 * (0 if bn == bn_pref else 1)
        cst += 5 * abs(bn - bn_pref)
        cst += 10 * (0 if bm == bm_pref else 1)
        cst += abs(bm - bm_pref)
        return cst

    best = min(configs, key=cost)
    return [best]


def _autotune_decorator(configs, key, prune_configs_by=None):
    sig = inspect.signature(triton.autotune)
    kwargs = {}
    if "prune_configs_by" in sig.parameters and prune_configs_by is not None:
        kwargs["prune_configs_by"] = prune_configs_by
    if "warmup" in sig.parameters:
        kwargs["warmup"] = 1
    if "rep" in sig.parameters:
        kwargs["rep"] = 1
    return triton.autotune(configs=configs, key=key, **kwargs)


_configs = [
    triton.Config({"BLOCK_M": 128, "BLOCK_N": 128, "BLOCK_K": 16, "GROUP_M": 8}, num_warps=4, num_stages=3),
    triton.Config({"BLOCK_M": 128, "BLOCK_N": 256, "BLOCK_K": 16, "GROUP_M": 8}, num_warps=8, num_stages=3),
    triton.Config({"BLOCK_M": 128, "BLOCK_N": 256, "BLOCK_K": 32, "GROUP_M": 8}, num_warps=8, num_stages=4),
    triton.Config({"BLOCK_M": 256, "BLOCK_N": 128, "BLOCK_K": 32, "GROUP_M": 4}, num_warps=8, num_stages=4),
    triton.Config({"BLOCK_M": 128, "BLOCK_N": 256, "BLOCK_K": 64, "GROUP_M": 8}, num_warps=8, num_stages=5),
    triton.Config({"BLOCK_M": 128, "BLOCK_N": 128, "BLOCK_K": 128, "GROUP_M": 8}, num_warps=8, num_stages=6),
]


@_autotune_decorator(
    _configs,
    key=["M", "N", "K", "stride_am", "stride_ak", "stride_bk", "stride_bn"],
    prune_configs_by={"early_config_prune": _early_config_prune},
)
@triton.jit
def _matmul_gelu_kernel(
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
    OUT_DTYPE: tl.constexpr,
    BLOCK_M: tl.constexpr,
    BLOCK_N: tl.constexpr,
    BLOCK_K: tl.constexpr,
    GROUP_M: tl.constexpr,
):
    pid = tl.program_id(0)

    num_pid_m = tl.cdiv(M, BLOCK_M)
    num_pid_n = tl.cdiv(N, BLOCK_N)

    group_m = GROUP_M
    group_size = group_m * num_pid_n
    pid_group = pid // group_size
    first_pid_m = pid_group * group_m
    pid_in_group = pid - pid_group * group_size
    pid_m = first_pid_m + (pid_in_group % group_m)
    pid_n = pid_in_group // group_m

    offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
    offs_n = pid_n * BLOCK_N + tl.arange(0, BLOCK_N)
    offs_k = tl.arange(0, BLOCK_K)

    acc = tl.zeros((BLOCK_M, BLOCK_N), dtype=tl.float32)

    a_base = a_ptr + offs_m[:, None] * stride_am + offs_k[None, :] * stride_ak
    b_base = b_ptr + offs_k[:, None] * stride_bk + offs_n[None, :] * stride_bn

    k_remaining = K
    k = 0
    for _ in tl.static_range(0, 1024 * 1024, step=1):
        if k >= K:
            break
        k_mask = offs_k < k_remaining

        a = tl.load(a_base, mask=(offs_m[:, None] < M) & k_mask[None, :], other=0.0)
        b = tl.load(b_base, mask=k_mask[:, None] & (offs_n[None, :] < N), other=0.0)

        acc += tl.dot(a, b)

        k += BLOCK_K
        k_remaining -= BLOCK_K
        a_base += BLOCK_K * stride_ak
        b_base += BLOCK_K * stride_bk

    acc = gelu(acc)

    if OUT_DTYPE == 0:
        out = acc.to(tl.float16)
    elif OUT_DTYPE == 1:
        out = acc.to(tl.bfloat16)
    else:
        out = acc.to(tl.float32)

    c_ptrs = c_ptr + offs_m[:, None] * stride_cm + offs_n[None, :] * stride_cn
    mask = (offs_m[:, None] < M) & (offs_n[None, :] < N)
    tl.store(c_ptrs, out, mask=mask)


def matmul(a: torch.Tensor, b: torch.Tensor) -> torch.Tensor:
    if not (isinstance(a, torch.Tensor) and isinstance(b, torch.Tensor)):
        raise TypeError("a and b must be torch.Tensor")
    if a.ndim != 2 or b.ndim != 2:
        raise ValueError("a and b must be 2D tensors")
    if a.device.type != "cuda" or b.device.type != "cuda":
        c = a @ b
        return torch.nn.functional.gelu(c)
    if a.shape[1] != b.shape[0]:
        raise ValueError("incompatible shapes")

    M, K = a.shape
    _, N = b.shape

    out_dtype_flag = 2
    if a.dtype == torch.float16:
        out_dtype_flag = 0
        c = torch.empty((M, N), device=a.device, dtype=torch.float16)
    elif a.dtype == torch.bfloat16:
        out_dtype_flag = 1
        c = torch.empty((M, N), device=a.device, dtype=torch.bfloat16)
    else:
        out_dtype_flag = 2
        c = torch.empty((M, N), device=a.device, dtype=torch.float32)

    stride_am, stride_ak = a.stride(0), a.stride(1)
    stride_bk, stride_bn = b.stride(0), b.stride(1)
    stride_cm, stride_cn = c.stride(0), c.stride(1)

    grid = lambda META: (triton.cdiv(M, META["BLOCK_M"]) * triton.cdiv(N, META["BLOCK_N"]),)

    _matmul_gelu_kernel[grid](
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
        OUT_DTYPE=out_dtype_flag,
    )
    return c


class Solution:
    def solve(self, spec_path: str = None) -> dict:
        try:
            path = os.path.abspath(__file__)
            with open(path, "r", encoding="utf-8") as f:
                return {"code": f.read()}
        except Exception:
            return {"program_path": os.path.abspath(__file__) if "__file__" in globals() else ""}