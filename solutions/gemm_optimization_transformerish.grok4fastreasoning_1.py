import torch
import triton
import triton.language as tl
import math

class Solution:
    def solve(self, spec_path: str = None) -> dict:
        code = """
import torch
import triton
import triton.language as tl

@triton.jit
def gelu(x):
    return x * 0.5 * (1.0 + tl.extra.cuda.libdevice.erf(x * 0.7071067811865476))

def matmul(a: torch.Tensor, b: torch.Tensor) -> torch.Tensor:
    M, K1 = a.shape
    K2, N = b.shape
    assert K1 == K2
    K = K1
    dtype = a.dtype
    device = a.device
    output = torch.empty((M, N), dtype=dtype, device=device)
    out_bits = 16 if dtype == torch.float16 else 32
    stride_am = a.stride(0)
    stride_ak = a.stride(1)
    stride_bk = b.stride(0)
    stride_bn = b.stride(1)
    stride_cm = output.stride(0)
    stride_cn = output.stride(1)

    configs = [
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 128, 'BLOCK_K': 64}, num_stages=4),
        triton.Config({'BLOCK_M': 64, 'BLOCK_N': 256, 'BLOCK_K': 64}, num_stages=2),
        triton.Config({'BLOCK_M': 256, 'BLOCK_N': 64, 'BLOCK_K': 64}, num_stages=4),
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 64, 'BLOCK_K': 128}, num_stages=3),
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 256, 'BLOCK_K': 128}, num_stages=5),
        triton.Config({'BLOCK_M': 64, 'BLOCK_N': 128, 'BLOCK_K': 128}, num_stages=4),
        triton.Config({'BLOCK_M': 256, 'BLOCK_N': 128, 'BLOCK_K': 128}, num_stages=5),
    ]

    @triton.autotune(
        configs=configs,
        key=['M', 'N', 'K'],
    )
    @triton.jit
    def kernel(
        A_PTR,
        B_PTR,
        C_PTR,
        M: tl.int32,
        N: tl.int32,
        K: tl.int32,
        stride_am: tl.int32,
        stride_ak: tl.int32,
        stride_bk: tl.int32,
        stride_bn: tl.int32,
        stride_cm: tl.int32,
        stride_cn: tl.int32,
        OUT_BITS: tl.constexpr,
        BLOCK_M: tl.constexpr,
        BLOCK_N: tl.constexpr,
        BLOCK_K: tl.constexpr
    ):
        pid_m = tl.program_id(0)
        pid_n = tl.program_id(1)

        offs_am = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
        offs_bn = pid_n * BLOCK_N + tl.arange(0, BLOCK_N)
        offs_k = tl.arange(0, BLOCK_K)
        mask_am = offs_am < M
        mask_bn = offs_bn < N

        acc = tl.zeros((BLOCK_M, BLOCK_N), dtype=tl.float32)

        k = tl.zeros((1,), dtype=tl.int32)
        while k[0] < K:
            start_k = k[0]
            offs_ak = start_k + offs_k
            mask_ak = offs_ak < K

            a_ptrs = A_PTR + (offs_am[:, None] * stride_am + offs_ak[None, :] * stride_ak)
            a_mask = (mask_am[:, None], mask_ak[None, :])
            a_ptr = tl.make_block_ptr(
                base=a_ptrs,
                shape=(BLOCK_M, BLOCK_K),
                strides=(stride_am, stride_ak),
                offsets=(0, 0),
                mask=a_mask,
                other=0.0,
            )
            a_block = tl.load(a_ptr).to(tl.float32)

            b_ptrs = B_PTR + (offs_ak[:, None] * stride_bk + offs_bn[None, :] * stride_bn)
            b_mask = (mask_ak[:, None], mask_bn)
            b_ptr = tl.make_block_ptr(
                base=b_ptrs,
                shape=(BLOCK_K, BLOCK_N),
                strides=(stride_bk, stride_bn),
                offsets=(0, 0),
                mask=b_mask,
                other=0.0,
            )
            b_block = tl.load(b_ptr).to(tl.float32)

            acc += tl.dot(a_block, b_block)
            k[0] += BLOCK_K

        gelu_acc = gelu(acc)

        if OUT_BITS == 16:
            c_block = gelu_acc.to(tl.float16)
        else:
            c_block = gelu_acc.to(tl.float32)

        offs_cm = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
        offs_cn = pid_n * BLOCK_N + tl.arange(0, BLOCK_N)
        c_mask = (offs_cm < M, offs_cn < N)
        c_ptr = tl.make_block_ptr(
            base=C_PTR,
            shape=(BLOCK_M, BLOCK_N),
            strides=(stride_cm, stride_cn),
            offsets=(offs_cm, offs_cn),
            mask=c_mask,
            other=0.0,
        )
        tl.store(c_ptr, c_block, mask=c_mask)

    grid = lambda meta: (
        triton.cdiv(M, meta['BLOCK_M']),
        triton.cdiv(N, meta['BLOCK_N'])
    )
    kernel[grid](
        a, b, output,
        M, N, K,
        stride_am, stride_ak, stride_bk, stride_bn,
        stride_cm, stride_cn,
        OUT_BITS=out_bits
    )
    return output
"""
        return {"code": code}
