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
    M, K = a.shape
    K2, N = b.shape
    assert K == K2
    assert a.dtype == b.dtype
    C = torch.empty((M, N), dtype=a.dtype, device=a.device)
    if M == 0 or N == 0 or K == 0:
        return C

    def get_dtype():
        if a.dtype == torch.float16:
            return tl.float16
        elif a.dtype == torch.bfloat16:
            return tl.bfloat16
        elif a.dtype == torch.float32:
            return tl.float32
        else:
            raise ValueError(f"Unsupported dtype {a.dtype}")

    INPUT_DTYPE = get_dtype()
    element_size = a.element_size()
    stride_am_bytes = a.stride(0) * element_size
    stride_ak_bytes = a.stride(1) * element_size
    stride_bk_bytes = b.stride(0) * element_size
    stride_bn_bytes = b.stride(1) * element_size
    stride_cm_bytes = N * element_size
    stride_cn_bytes = element_size

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
        INPUT_DTYPE: tl.constexpr,
        BLOCK_M: tl.constexpr,
        BLOCK_N: tl.constexpr,
        BLOCK_K: tl.constexpr,
    ):
        pid_m = tl.program_id(0)
        pid_n = tl.program_id(1)

        offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
        offs_n = pid_n * BLOCK_N + tl.arange(0, BLOCK_N)
        acc = tl.zeros((BLOCK_M, BLOCK_N), dtype=tl.float32)

        for start_k in range(0, K, BLOCK_K):
            block_k = start_k + tl.arange(0, BLOCK_K)
            mask_k = block_k < K

            a_ptrs = A_PTR + offs_m[:, None] * stride_am + block_k[None, :] * stride_ak
            mask_a = (offs_m[:, None] < M) & mask_k[None, :]
            a_block = tl.load(a_ptrs, mask=mask_a, other=INPUT_DTYPE(0.0)).to(tl.float32)

            b_ptrs = B_PTR + block_k[:, None] * stride_bk + offs_n[None, :] * stride_bn
            mask_b = mask_k[:, None] & (offs_n[None, :] < N)
            b_block = tl.load(b_ptrs, mask=mask_b, other=INPUT_DTYPE(0.0)).to(tl.float32)

            acc += tl.dot(a_block, b_block)

        c_ptrs = C_PTR + offs_m[:, None] * stride_cm + offs_n[None, :] * stride_cn
        mask_c = (offs_m[:, None] < M) & (offs_n[None, :] < N)
        c_block = gelu(acc).to(INPUT_DTYPE)
        tl.store(c_ptrs, c_block, mask=mask_c)

    configs = [
        triton.Config(
            {'BLOCK_M': 64, 'BLOCK_N': 64, 'BLOCK_K': 32},
            num_stages=3,
            num_warps=8
        ),
        triton.Config(
            {'BLOCK_M': 128, 'BLOCK_N': 128, 'BLOCK_K': 64},
            num_stages=4,
            num_warps=8
        ),
        triton.Config(
            {'BLOCK_M': 256, 'BLOCK_N': 256, 'BLOCK_K': 128},
            num_stages=5,
            num_warps=4
        ),
        triton.Config(
            {'BLOCK_M': 128, 'BLOCK_N': 64, 'BLOCK_K': 64},
            num_stages=4,
            num_warps=8
        ),
        triton.Config(
            {'BLOCK_M': 64, 'BLOCK_N': 128, 'BLOCK_K': 32},
            num_stages=3,
            num_warps=8
        ),
    ]

    def make_key(A_PTR, B_PTR, C_PTR, M, N, K, stride_am, stride_ak, stride_bk, stride_bn, stride_cm, stride_cn, INPUT_DTYPE):
        return (M, N, K, stride_am, stride_ak, stride_bk, stride_bn)

    kernel = triton.autotune(
        configs=[triton.Config({**c, 'INPUT_DTYPE': INPUT_DTYPE}) for c in configs],
        key=make_key,
    )(kernel)

    def grid(meta):
        return (
            triton.cdiv(M, meta['BLOCK_M']),
            triton.cdiv(N, meta['BLOCK_N']),
        )

    A_PTR = a.data_ptr()
    B_PTR = b.data_ptr()
    C_PTR = C.data_ptr()
    kernel[grid](
        A_PTR,
        B_PTR,
        C_PTR,
        M,
        N,
        K,
        stride_am_bytes,
        stride_ak_bytes,
        stride_bk_bytes,
        stride_bn_bytes,
        stride_cm_bytes,
        stride_cn_bytes,
        INPUT_DTYPE,
    )
    return C
"""
        return {"code": code}
