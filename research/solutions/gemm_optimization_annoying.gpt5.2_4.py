import textwrap

KERNEL_CODE = textwrap.dedent(r'''
import math
import torch
import triton
import triton.language as tl

@triton.jit
def gelu(x):
    return x * 0.5 * (1.0 + tl.extra.cuda.libdevice.erf(x * 0.7071067811865476))

def _get_autotune_configs():
    configs = []
    # L4 (SM89) generally likes 128x128/64x128/128x64 tiles with BK=32/64 for fp16/bf16
    for bm, bn, bk, warps, stages, gm in [
        (128, 128, 32, 8, 5, 8),
        (128, 128, 64, 8, 4, 8),
        (128,  64, 32, 8, 5, 8),
        (128,  64, 64, 8, 4, 8),
        ( 64, 128, 32, 8, 5, 8),
        ( 64, 128, 64, 8, 4, 8),
        ( 64,  64, 32, 4, 5, 8),
        ( 64,  64, 64, 4, 4, 8),
        (128,  32, 32, 4, 5, 8),
        ( 32, 128, 32, 4, 5, 8),
        ( 32,  64, 32, 4, 5, 8),
        ( 64,  32, 32, 4, 5, 8),
    ]:
        configs.append(triton.Config(
            {"BLOCK_M": bm, "BLOCK_N": bn, "BLOCK_K": bk, "GROUP_M": gm},
            num_warps=warps,
            num_stages=stages,
        ))
    return configs

@triton.autotune(
    configs=_get_autotune_configs(),
    key=["M", "N", "K", "stride_am", "stride_ak", "stride_bk", "stride_bn"],
)
@triton.jit
def _matmul_gelu_kernel(
    a_ptr, b_ptr, c_ptr,
    M: tl.constexpr, N: tl.constexpr, K: tl.constexpr,
    stride_am: tl.constexpr, stride_ak: tl.constexpr,
    stride_bk: tl.constexpr, stride_bn: tl.constexpr,
    stride_cm: tl.constexpr, stride_cn: tl.constexpr,
    OUT_DTYPE: tl.constexpr,
    BLOCK_M: tl.constexpr, BLOCK_N: tl.constexpr, BLOCK_K: tl.constexpr,
    GROUP_M: tl.constexpr,
):
    pid = tl.program_id(0)
    grid_m = tl.cdiv(M, BLOCK_M)
    grid_n = tl.cdiv(N, BLOCK_N)

    group_size = GROUP_M
    num_pid_in_group = group_size * grid_n
    pid_group = pid // num_pid_in_group
    first_pid_m = pid_group * group_size
    group_m = tl.minimum(grid_m - first_pid_m, group_size)
    pid_in_group = pid - pid_group * num_pid_in_group
    pid_m = first_pid_m + (pid_in_group % group_m)
    pid_n = pid_in_group // group_m

    offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
    offs_n = pid_n * BLOCK_N + tl.arange(0, BLOCK_N)
    offs_k = tl.arange(0, BLOCK_K)

    a_ptrs = a_ptr + offs_m[:, None] * stride_am + offs_k[None, :] * stride_ak
    b_ptrs = b_ptr + offs_k[:, None] * stride_bk + offs_n[None, :] * stride_bn

    acc = tl.zeros((BLOCK_M, BLOCK_N), dtype=tl.float32)

    # Unrolled K loop (K is constexpr)
    for k in range(0, K, BLOCK_K):
        k_mask = (k + offs_k) < K
        a = tl.load(a_ptrs, mask=(offs_m[:, None] < M) & (k_mask[None, :]), other=0.0)
        b = tl.load(b_ptrs, mask=(k_mask[:, None]) & (offs_n[None, :] < N), other=0.0)
        acc = tl.dot(a, b, acc=acc)
        a_ptrs += BLOCK_K * stride_ak
        b_ptrs += BLOCK_K * stride_bk

    acc = gelu(acc)
    out = tl.cast(acc, OUT_DTYPE)

    c_ptrs = c_ptr + offs_m[:, None] * stride_cm + offs_n[None, :] * stride_cn
    tl.store(c_ptrs, out, mask=(offs_m[:, None] < M) & (offs_n[None, :] < N))

def matmul(a: torch.Tensor, b: torch.Tensor) -> torch.Tensor:
    if a.ndim != 2 or b.ndim != 2:
        raise ValueError("matmul expects 2D tensors")
    if a.shape[1] != b.shape[0]:
        raise ValueError(f"incompatible shapes: a={tuple(a.shape)}, b={tuple(b.shape)}")
    if not a.is_cuda or not b.is_cuda:
        return torch.nn.functional.gelu(a @ b, approximate="none")
    if a.dtype != b.dtype:
        # keep correctness, prioritize typical fp16/bf16 path
        return torch.nn.functional.gelu(a @ b, approximate="none")

    M, K = a.shape
    K2, N = b.shape
    if M == 0 or N == 0 or K == 0:
        return torch.empty((M, N), device=a.device, dtype=a.dtype)

    if a.dtype not in (torch.float16, torch.bfloat16):
        return torch.nn.functional.gelu(a @ b, approximate="none")

    c = torch.empty((M, N), device=a.device, dtype=a.dtype)

    stride_am, stride_ak = a.stride()
    stride_bk, stride_bn = b.stride()
    stride_cm, stride_cn = c.stride()

    grid = lambda meta: (triton.cdiv(M, meta["BLOCK_M"]) * triton.cdiv(N, meta["BLOCK_N"]),)

    out_dtype = tl.float16 if a.dtype == torch.float16 else tl.bfloat16

    _matmul_gelu_kernel[grid](
        a, b, c,
        M=M, N=N, K=K,
        stride_am=stride_am, stride_ak=stride_ak,
        stride_bk=stride_bk, stride_bn=stride_bn,
        stride_cm=stride_cm, stride_cn=stride_cn,
        OUT_DTYPE=out_dtype,
    )
    return c
''')

exec(KERNEL_CODE, globals())

class Solution:
    def solve(self, spec_path: str = None) -> dict:
        return {"code": KERNEL_CODE}
