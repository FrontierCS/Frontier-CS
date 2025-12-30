class Solution:
    def solve(self, spec_path: str = None) -> dict:
        code = """
import torch
import triton
import triton.language as tl

@triton.jit
def gelu(x):
    return x * 0.5 * (1.0 + tl.extra.cuda.libdevice.erf(x * 0.7071067811865476))

@triton.autotune(
    configs=[
        triton.Config(num_stages=1, num_warps=8),
        triton.Config(num_stages=2, num_warps=8),
        triton.Config(num_stages=3, num_warps=8),
        triton.Config(num_stages=4, num_warps=4),
        triton.Config(num_stages=5, num_warps=4),
    ],
    key=['M', 'N', 'K'],
)
@triton.jit
def matmul_kernel(
    a_ptr, b_ptr, c_ptr,
    M: tl.int32, N: tl.int32, K: tl.int32,
    stride_am: tl.int32, stride_ak: tl.int32,
    stride_bk: tl.int32, stride_bn: tl.int32,
    stride_cm: tl.int32, stride_cn: tl.int32,
):
    BLOCK_M = 128
    BLOCK_N = 128
    BLOCK_K = 64
    pid_m = tl.program_id(0)
    pid_n = tl.program_id(1)
    acc = tl.zeros((BLOCK_M, BLOCK_N), dtype=tl.float32)
    for k_start in range(0, K, BLOCK_K):
        offs_am = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
        offs_ak = k_start + tl.arange(0, BLOCK_K)
        a_mask = (offs_am < M)[:, None] & (offs_ak[None, :] < K)
        a_ptrs = tl.make_block_ptr(
            base=a_ptr,
            shape=(M, K),
            strides=(stride_am, stride_ak),
            offsets=(offs_am, offs_ak),
            block_shape=(BLOCK_M, BLOCK_K),
            order=(1, 0)
        )
        a_block = tl.load(a_ptrs, mask=a_mask, other=0.0)
        offs_bk = k_start + tl.arange(0, BLOCK_K)
        offs_bn = pid_n * BLOCK_N + tl.arange(0, BLOCK_N)
        b_mask = (offs_bk[:, None] < K) & (offs_bn[None, :] < N)
        b_ptrs = tl.make_block_ptr(
            base=b_ptr,
            shape=(K, N),
            strides=(stride_bk, stride_bn),
            offsets=(offs_bk, offs_bn),
            block_shape=(BLOCK_K, BLOCK_N),
            order=(1, 0)
        )
        b_block = tl.load(b_ptrs, mask=b_mask, other=0.0)
        acc += tl.dot(a_block, b_block)
    offs_cm = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
    offs_cn = pid_n * BLOCK_N + tl.arange(0, BLOCK_N)
    c_mask = (offs_cm < M)[:, None] & (offs_cn[None, :] < N)
    c_block = gelu(acc)
    c_ptrs = tl.make_block_ptr(
        base=c_ptr,
        shape=(M, N),
        strides=(stride_cm, stride_cn),
        offsets=(offs_cm, offs_cn),
        block_shape=(BLOCK_M, BLOCK_N),
        order=(1, 0)
    )
    tl.store(c_ptrs, c_block, mask=c_mask)


def matmul(a: torch.Tensor, b: torch.Tensor) -> torch.Tensor:
    M, Ka = a.shape
    Kb, N = b.shape
    assert Ka == Kb
    K = Ka
    output = torch.empty((M, N), dtype=torch.float32, device=a.device)
    stride_am = a.stride(0)
    stride_ak = a.stride(1)
    stride_bk = b.stride(0)
    stride_bn = b.stride(1)
    stride_cm = output.stride(0)
    stride_cn = output.stride(1)
    a_ptr = a.data_ptr()
    b_ptr = b.data_ptr()
    c_ptr = output.data_ptr()
    BLOCK_M = 128
    BLOCK_N = 128
    grid = (triton.cdiv(M, BLOCK_M), triton.cdiv(N, BLOCK_N))
    matmul_kernel[grid](
        a_ptr, b_ptr, c_ptr,
        torch.int32(M), torch.int32(N), torch.int32(K),
        torch.int32(stride_am), torch.int32(stride_ak),
        torch.int32(stride_bk), torch.int32(stride_bn),
        torch.int32(stride_cm), torch.int32(stride_cn),
    )
    return output
"""
        return {"code": code}