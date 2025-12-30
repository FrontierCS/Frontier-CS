import types

KERNEL_CODE = r"""
import torch
import triton
import triton.language as tl

@triton.jit
def gelu(x):
    return x * 0.5 * (1.0 + tl.extra.cuda.libdevice.erf(x * 0.7071067811865476))


_AUTOTUNE_CONFIGS = [
    triton.Config({"BLOCK_M": 128, "BLOCK_N": 128, "BLOCK_K": 32, "GROUP_M": 8}, num_warps=8, num_stages=4),
    triton.Config({"BLOCK_M": 128, "BLOCK_N": 128, "BLOCK_K": 64, "GROUP_M": 8}, num_warps=8, num_stages=4),
    triton.Config({"BLOCK_M": 128, "BLOCK_N": 128, "BLOCK_K": 128, "GROUP_M": 8}, num_warps=8, num_stages=3),
    triton.Config({"BLOCK_M": 128, "BLOCK_N": 64, "BLOCK_K": 64, "GROUP_M": 8}, num_warps=4, num_stages=4),
    triton.Config({"BLOCK_M": 64, "BLOCK_N": 128, "BLOCK_K": 64, "GROUP_M": 8}, num_warps=4, num_stages=4),
    triton.Config({"BLOCK_M": 64, "BLOCK_N": 64, "BLOCK_K": 128, "GROUP_M": 8}, num_warps=4, num_stages=3),
]


def _grid_1d(M, N, meta):
    return (triton.cdiv(M, meta["BLOCK_M"]) * triton.cdiv(N, meta["BLOCK_N"]),)


if hasattr(tl, "make_block_ptr") and hasattr(tl, "advance"):

    @triton.autotune(configs=_AUTOTUNE_CONFIGS, key=["K", "ALLOW_TF32"], warmup=1, rep=2)
    @triton.jit
    def _matmul_gelu_contig_kernel(
        a_ptr,
        b_ptr,
        c_ptr,
        M,
        N,
        K,
        ALLOW_TF32: tl.constexpr,
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
        pid_in_group = pid % num_pid_in_group
        pid_m = first_pid_m + (pid_in_group % group_size_m)
        pid_n = pid_in_group // group_size_m

        offs_m = pid_m * BLOCK_M
        offs_n = pid_n * BLOCK_N

        a_bp = tl.make_block_ptr(
            base=a_ptr,
            shape=(M, K),
            strides=(K, 1),
            offsets=(offs_m, 0),
            block_shape=(BLOCK_M, BLOCK_K),
            order=(1, 0),
        )
        b_bp = tl.make_block_ptr(
            base=b_ptr,
            shape=(K, N),
            strides=(N, 1),
            offsets=(0, offs_n),
            block_shape=(BLOCK_K, BLOCK_N),
            order=(1, 0),
        )
        acc = tl.zeros((BLOCK_M, BLOCK_N), dtype=tl.float32)

        for _k in range(0, K, BLOCK_K):
            a = tl.load(a_bp, boundary_check=(0, 1), padding_option="zero")
            b = tl.load(b_bp, boundary_check=(0, 1), padding_option="zero")
            acc = tl.dot(a, b, allow_tf32=ALLOW_TF32) + acc
            a_bp = tl.advance(a_bp, (0, BLOCK_K))
            b_bp = tl.advance(b_bp, (BLOCK_K, 0))

        acc = gelu(acc)

        c_bp = tl.make_block_ptr(
            base=c_ptr,
            shape=(M, N),
            strides=(N, 1),
            offsets=(offs_m, offs_n),
            block_shape=(BLOCK_M, BLOCK_N),
            order=(1, 0),
        )
        tl.store(c_bp, acc, boundary_check=(0, 1))

    @triton.autotune(configs=_AUTOTUNE_CONFIGS, key=["K", "stride_am", "stride_ak", "stride_bk", "stride_bn", "ALLOW_TF32"], warmup=1, rep=2)
    @triton.jit
    def _matmul_gelu_generic_kernel(
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
        ALLOW_TF32: tl.constexpr,
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
        pid_in_group = pid % num_pid_in_group
        pid_m = first_pid_m + (pid_in_group % group_size_m)
        pid_n = pid_in_group // group_size_m

        offs_m = pid_m * BLOCK_M
        offs_n = pid_n * BLOCK_N

        a_bp = tl.make_block_ptr(
            base=a_ptr,
            shape=(M, K),
            strides=(stride_am, stride_ak),
            offsets=(offs_m, 0),
            block_shape=(BLOCK_M, BLOCK_K),
            order=(1, 0),
        )
        b_bp = tl.make_block_ptr(
            base=b_ptr,
            shape=(K, N),
            strides=(stride_bk, stride_bn),
            offsets=(0, offs_n),
            block_shape=(BLOCK_K, BLOCK_N),
            order=(1, 0),
        )

        acc = tl.zeros((BLOCK_M, BLOCK_N), dtype=tl.float32)

        for _k in range(0, K, BLOCK_K):
            a = tl.load(a_bp, boundary_check=(0, 1), padding_option="zero")
            b = tl.load(b_bp, boundary_check=(0, 1), padding_option="zero")
            acc = tl.dot(a, b, allow_tf32=ALLOW_TF32) + acc
            a_bp = tl.advance(a_bp, (0, BLOCK_K))
            b_bp = tl.advance(b_bp, (BLOCK_K, 0))

        acc = gelu(acc)

        c_bp = tl.make_block_ptr(
            base=c_ptr,
            shape=(M, N),
            strides=(N, 1),
            offsets=(offs_m, offs_n),
            block_shape=(BLOCK_M, BLOCK_N),
            order=(1, 0),
        )
        tl.store(c_bp, acc, boundary_check=(0, 1))

else:

    @triton.autotune(configs=_AUTOTUNE_CONFIGS, key=["K", "ALLOW_TF32"], warmup=1, rep=2)
    @triton.jit
    def _matmul_gelu_contig_kernel(
        a_ptr,
        b_ptr,
        c_ptr,
        M,
        N,
        K,
        ALLOW_TF32: tl.constexpr,
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
        pid_in_group = pid % num_pid_in_group
        pid_m = first_pid_m + (pid_in_group % group_size_m)
        pid_n = pid_in_group // group_size_m

        offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
        offs_n = pid_n * BLOCK_N + tl.arange(0, BLOCK_N)
        offs_k = tl.arange(0, BLOCK_K)

        acc = tl.zeros((BLOCK_M, BLOCK_N), dtype=tl.float32)

        a_ptrs = a_ptr + offs_m[:, None] * K + offs_k[None, :]
        b_ptrs = b_ptr + offs_k[:, None] * N + offs_n[None, :]

        for k in range(0, K, BLOCK_K):
            k_mask = (k + offs_k) < K
            a = tl.load(
                a_ptrs,
                mask=(offs_m[:, None] < M) & (k_mask[None, :]),
                other=0.0,
            )
            b = tl.load(
                b_ptrs,
                mask=(k_mask[:, None]) & (offs_n[None, :] < N),
                other=0.0,
            )
            acc = tl.dot(a, b, allow_tf32=ALLOW_TF32) + acc
            a_ptrs += BLOCK_K
            b_ptrs += BLOCK_K * N

        acc = gelu(acc)

        c_ptrs = c_ptr + offs_m[:, None] * N + offs_n[None, :]
        tl.store(c_ptrs, acc, mask=(offs_m[:, None] < M) & (offs_n[None, :] < N))

    @triton.autotune(configs=_AUTOTUNE_CONFIGS, key=["K", "stride_am", "stride_ak", "stride_bk", "stride_bn", "ALLOW_TF32"], warmup=1, rep=2)
    @triton.jit
    def _matmul_gelu_generic_kernel(
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
        ALLOW_TF32: tl.constexpr,
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
        pid_in_group = pid % num_pid_in_group
        pid_m = first_pid_m + (pid_in_group % group_size_m)
        pid_n = pid_in_group // group_size_m

        offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
        offs_n = pid_n * BLOCK_N + tl.arange(0, BLOCK_N)
        offs_k = tl.arange(0, BLOCK_K)

        acc = tl.zeros((BLOCK_M, BLOCK_N), dtype=tl.float32)

        a_ptrs = a_ptr + offs_m[:, None] * stride_am + offs_k[None, :] * stride_ak
        b_ptrs = b_ptr + offs_k[:, None] * stride_bk + offs_n[None, :] * stride_bn

        for k in range(0, K, BLOCK_K):
            k_mask = (k + offs_k) < K
            a = tl.load(
                a_ptrs,
                mask=(offs_m[:, None] < M) & (k_mask[None, :]),
                other=0.0,
            )
            b = tl.load(
                b_ptrs,
                mask=(k_mask[:, None]) & (offs_n[None, :] < N),
                other=0.0,
            )
            acc = tl.dot(a, b, allow_tf32=ALLOW_TF32) + acc
            a_ptrs += BLOCK_K * stride_ak
            b_ptrs += BLOCK_K * stride_bk

        acc = gelu(acc)
        c_ptrs = c_ptr + offs_m[:, None] * N + offs_n[None, :]
        tl.store(c_ptrs, acc, mask=(offs_m[:, None] < M) & (offs_n[None, :] < N))


def matmul(a: torch.Tensor, b: torch.Tensor) -> torch.Tensor:
    if a.ndim != 2 or b.ndim != 2:
        raise ValueError("matmul expects 2D tensors")
    if not a.is_cuda or not b.is_cuda:
        raise ValueError("matmul expects CUDA tensors")
    M, K = a.shape
    K2, N = b.shape
    if K != K2:
        raise ValueError("incompatible shapes")
    if a.dtype != b.dtype:
        b = b.to(dtype=a.dtype)

    out = torch.empty((M, N), device=a.device, dtype=a.dtype)

    allow_tf32 = 1 if a.dtype == torch.float32 else 0
    grid = lambda meta: _grid_1d(M, N, meta)

    if a.is_contiguous() and b.is_contiguous() and a.stride(1) == 1 and b.stride(1) == 1:
        _matmul_gelu_contig_kernel[grid](
            a,
            b,
            out,
            M,
            N,
            K,
            ALLOW_TF32=allow_tf32,
        )
    else:
        _matmul_gelu_generic_kernel[grid](
            a,
            b,
            out,
            M,
            N,
            K,
            a.stride(0),
            a.stride(1),
            b.stride(0),
            b.stride(1),
            ALLOW_TF32=allow_tf32,
        )
    return out
"""

_exec_ns = {}
exec(KERNEL_CODE, _exec_ns)
matmul = _exec_ns["matmul"]
gelu = _exec_ns["gelu"]


class Solution:
    def solve(self, spec_path: str = None) -> dict:
        return {"code": KERNEL_CODE}