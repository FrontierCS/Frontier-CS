import triton
import triton.language as tl
import torch


class Solution:
    def solve(self, spec_path: str = None) -> dict:
        kernel_code = '''
import torch
import triton
import triton.language as tl


@triton.jit
def gelu(x):
    return x * 0.5 * (1.0 + tl.extra.cuda.libdevice.erf(x * 0.7071067811865476))


configs = [
    triton.Config({"BLOCK_M": 128, "BLOCK_N": 128, "BLOCK_K": 32, "GROUP_M": 8}, num_warps=8, num_stages=3),
    triton.Config({"BLOCK_M": 128, "BLOCK_N": 64,  "BLOCK_K": 32, "GROUP_M": 8}, num_warps=4, num_stages=4),
    triton.Config({"BLOCK_M": 64,  "BLOCK_N": 128, "BLOCK_K": 32, "GROUP_M": 8}, num_warps=4, num_stages=4),
    triton.Config({"BLOCK_M": 64,  "BLOCK_N": 64,  "BLOCK_K": 64, "GROUP_M": 8}, num_warps=4, num_stages=3),
    triton.Config({"BLOCK_M": 128, "BLOCK_N": 128, "BLOCK_K": 64, "GROUP_M": 8}, num_warps=8, num_stages=3),
    triton.Config({"BLOCK_M": 256, "BLOCK_N": 64,  "BLOCK_K": 32, "GROUP_M": 8}, num_warps=8, num_stages=4),
    triton.Config({"BLOCK_M": 64,  "BLOCK_N": 256, "BLOCK_K": 32, "GROUP_M": 8}, num_warps=8, num_stages=4),
    triton.Config({"BLOCK_M": 128, "BLOCK_N": 128, "BLOCK_K": 16, "GROUP_M": 8}, num_warps=4, num_stages=2),
    triton.Config({"BLOCK_M": 128, "BLOCK_N": 32,  "BLOCK_K": 32, "GROUP_M": 8}, num_warps=4, num_stages=4),
    triton.Config({"BLOCK_M": 32,  "BLOCK_N": 128, "BLOCK_K": 32, "GROUP_M": 8}, num_warps=4, num_stages=4),
    triton.Config({"BLOCK_M": 128, "BLOCK_N": 128, "BLOCK_K": 128,"GROUP_M": 8}, num_warps=8, num_stages=4),
]


@triton.autotune(configs=configs, key=["M", "N", "K"])
@triton.jit
def _matmul_gelu_kernel(
    A, B, C,
    M, N, K,
    stride_am, stride_ak,
    stride_bk, stride_bn,
    stride_cm, stride_cn,
    BLOCK_M: tl.constexpr, BLOCK_N: tl.constexpr, BLOCK_K: tl.constexpr,
    GROUP_M: tl.constexpr,
    OUT_TYPE: tl.constexpr,  # 0=fp16, 1=fp32, 2=bf16
):
    pid = tl.program_id(axis=0)
    grid_m = (M + BLOCK_M - 1) // BLOCK_M
    grid_n = (N + BLOCK_N - 1) // BLOCK_N

    group_size = GROUP_M
    width = group_size * grid_n
    group_id = pid // width
    first_pid_m = group_id * group_size
    pid_in_group = pid % width
    pid_m = first_pid_m + (pid_in_group % group_size)
    pid_n = pid_in_group // group_size

    offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
    offs_n = pid_n * BLOCK_N + tl.arange(0, BLOCK_N)
    a_mmask = offs_m < M
    b_nmask = offs_n < N

    offs_k = tl.arange(0, BLOCK_K)
    a_ptrs = A + (offs_m[:, None] * stride_am + offs_k[None, :] * stride_ak)
    b_ptrs = B + (offs_k[:, None] * stride_bk + offs_n[None, :] * stride_bn)

    acc = tl.zeros((BLOCK_M, BLOCK_N), dtype=tl.float32)

    k_end = (K // BLOCK_K) * BLOCK_K
    for k in range(0, k_end, BLOCK_K):
        a = tl.load(a_ptrs, mask=a_mmask[:, None], other=0.0)
        b = tl.load(b_ptrs, mask=b_nmask[None, :], other=0.0)
        a = a.to(tl.float16)
        b = b.to(tl.float16)
        acc += tl.dot(a, b)
        a_ptrs += BLOCK_K * stride_ak
        b_ptrs += BLOCK_K * stride_bk

    if k_end < K:
        tail = tl.arange(0, BLOCK_K)
        k_mask = (k_end + tail) < K
        a_ptrs2 = A + (offs_m[:, None] * stride_am + (k_end + tail)[None, :] * stride_ak)
        b_ptrs2 = B + ((k_end + tail)[:, None] * stride_bk + offs_n[None, :] * stride_bn)
        a = tl.load(a_ptrs2, mask=a_mmask[:, None] & k_mask[None, :], other=0.0)
        b = tl.load(b_ptrs2, mask=k_mask[:, None] & b_nmask[None, :], other=0.0)
        a = a.to(tl.float16)
        b = b.to(tl.float16)
        acc += tl.dot(a, b)

    acc = gelu(acc)

    c_ptrs = C + (offs_m[:, None] * stride_cm + offs_n[None, :] * stride_cn)
    mask_c = a_mmask[:, None] & b_nmask[None, :]
    if OUT_TYPE == 0:
        out = acc.to(tl.float16)
    elif OUT_TYPE == 2:
        out = acc.to(tl.bfloat16)
    else:
        out = acc.to(tl.float32)
    tl.store(c_ptrs, out, mask=mask_c)


def matmul(a: torch.Tensor, b: torch.Tensor) -> torch.Tensor:
    """
    Matrix multiplication with GELU activation.

    Args:
        a: Input tensor of shape (M, K)
        b: Input tensor of shape (K, N)

    Returns:
        Output tensor of shape (M, N) with GELU activation applied
    """
    assert a.ndim == 2 and b.ndim == 2, "Inputs must be 2D"
    assert a.shape[1] == b.shape[0], "Incompatible dimensions"
    assert a.is_cuda and b.is_cuda, "Inputs must be on CUDA device"
    M, K = a.shape
    K2, N = b.shape
    device = a.device
    assert device == b.device, "Inputs must be on the same device"

    # Determine output dtype
    if a.dtype == b.dtype:
        out_dtype = a.dtype
    elif torch.float32 in (a.dtype, b.dtype):
        out_dtype = torch.float32
    else:
        # Fallback to higher precision if mixed lower-precision types appear
        out_dtype = torch.float32

    # Only support common dtypes directly; others cast to fp16 compute + f32 accum
    supported_out = {torch.float16, torch.float32, torch.bfloat16}
    if out_dtype not in supported_out:
        out_dtype = torch.float32

    C = torch.empty((M, N), device=device, dtype=out_dtype)

    # Select OUT_TYPE encoding for kernel
    if out_dtype == torch.float16:
        OUT_TYPE = 0
    elif out_dtype == torch.bfloat16:
        OUT_TYPE = 2
    else:
        OUT_TYPE = 1

    # Compute grid
    def grid(meta):
        return (triton.cdiv(M, meta["BLOCK_M"]) * triton.cdiv(N, meta["BLOCK_N"]),)

    _matmul_gelu_kernel[grid](
        a, b, C,
        M, N, K,
        a.stride(0), a.stride(1),
        b.stride(0), b.stride(1),
        C.stride(0), C.stride(1),
        OUT_TYPE=OUT_TYPE,
    )
    return C
'''
        return {"code": kernel_code}
