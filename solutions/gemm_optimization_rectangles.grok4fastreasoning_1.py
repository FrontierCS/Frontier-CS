import torch
import triton
import triton.language as tl

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
    M, K_a = a.shape
    K_b, N = b.shape
    assert K_a == K_b, "Incompatible dimensions"
    c = torch.empty((M, N), device=a.device, dtype=a.dtype)
    def kernel(BLOCK_M: tl.constexpr, BLOCK_N: tl.constexpr, BLOCK_K: tl.constexpr):
        @triton.jit
        def kernel_fn(
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
        ):
            pid_m = tl.program_id(0)
            pid_n = tl.program_id(1)
            offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
            offs_n = pid_n * BLOCK_N + tl.arange(0, BLOCK_N)
            offs_k = tl.arange(0, BLOCK_K)
            acc = tl.zeros((BLOCK_M, BLOCK_N), dtype=tl.float32)
            for start_k in range(0, K, BLOCK_K):
                offs_k_cur = start_k + offs_k
                mask_a = (offs_m[:, None] < M) & (offs_k_cur[None, :] < K)
                a = tl.load(A_PTR + offs_m[:, None] * stride_am + offs_k_cur[None, :] * stride_ak, mask=mask_a, other=0.0).to(tl.float32)
                mask_b = (offs_k_cur[:, None] < K) & (offs_n[None, :] < N)
                b = tl.load(B_PTR + offs_k_cur[:, None] * stride_bk + offs_n[None, :] * stride_bn, mask=mask_b, other=0.0).to(tl.float32)
                acc += tl.dot(a, b, allow_tf32=True)
            c_vals = gelu(acc)
            mask_c = (offs_m[:, None] < M) & (offs_n[None, :] < N)
            tl.store(C_PTR + offs_m[:, None] * stride_cm + offs_n[None, :] * stride_cn, c_vals, mask=mask_c)
        grid_m = (M + BLOCK_M - 1) // BLOCK_M
        grid_n = (N + BLOCK_N - 1) // BLOCK_N
        kernel_fn[grid=(grid_m, grid_n)](
            A_PTR=a,
            B_PTR=b,
            C_PTR=c,
            M=M,
            N=N,
            K=K_a,
            stride_am=a.stride(0),
            stride_ak=a.stride(1),
            stride_bk=b.stride(0),
            stride_bn=b.stride(1),
            stride_cm=c.stride(0),
            stride_cn=c.stride(1),
        )
    configs = [
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 128, 'BLOCK_K': 64}, num_stages=4, num_warps=8),
        triton.Config({'BLOCK_M': 64, 'BLOCK_N': 256, 'BLOCK_K': 64}, num_stages=4, num_warps=8),
        triton.Config({'BLOCK_M': 256, 'BLOCK_N': 64, 'BLOCK_K': 64}, num_stages=3, num_warps=8),
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 64, 'BLOCK_K': 128}, num_stages=4, num_warps=4),
        triton.Config({'BLOCK_M': 64, 'BLOCK_N': 128, 'BLOCK_K': 128}, num_stages=3, num_warps=4),
        triton.Config({'BLOCK_M': 256, 'BLOCK_N': 32, 'BLOCK_K': 32}, num_stages=2, num_warps=4),
        triton.Config({'BLOCK_M': 32, 'BLOCK_N': 256, 'BLOCK_K': 32}, num_stages=2, num_warps=4),
    ]
    kernel_autotuned = triton.autotune(
        configs=configs,
        key=(M, N, K_a),
    )(kernel)
    kernel_autotuned(BLOCK_M=128, BLOCK_N=128, BLOCK_K=64)
    return c
"""
        return {"code": code}
