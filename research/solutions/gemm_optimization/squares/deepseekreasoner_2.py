import torch
import triton
import triton.language as tl
import json
import os


@triton.jit
def gelu(x):
    return x * 0.5 * (1.0 + tl.extra.cuda.libdevice.erf(x * 0.7071067811865476))


@triton.autotune(
    configs=[
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 256, 'BLOCK_K': 64, 'GROUP_M': 8, 'SPLIT_K': 1, 'num_stages': 3, 'num_warps': 8}, num_warps=8, num_stages=3),
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 128, 'BLOCK_K': 32, 'GROUP_M': 8, 'SPLIT_K': 1, 'num_stages': 4, 'num_warps': 4}, num_warps=4, num_stages=4),
        triton.Config({'BLOCK_M': 64, 'BLOCK_N': 256, 'BLOCK_K': 32, 'GROUP_M': 8, 'SPLIT_K': 1, 'num_stages': 3, 'num_warps': 8}, num_warps=8, num_stages=3),
        triton.Config({'BLOCK_M': 256, 'BLOCK_N': 64, 'BLOCK_K': 32, 'GROUP_M': 8, 'SPLIT_K': 1, 'num_stages': 3, 'num_warps': 8}, num_warps=8, num_stages=3),
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 128, 'BLOCK_K': 64, 'GROUP_M': 8, 'SPLIT_K': 1, 'num_stages': 2, 'num_warps': 8}, num_warps=8, num_stages=2),
        triton.Config({'BLOCK_M': 64, 'BLOCK_N': 128, 'BLOCK_K': 32, 'GROUP_M': 8, 'SPLIT_K': 1, 'num_stages': 3, 'num_warps': 4}, num_warps=4, num_stages=3),
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 64, 'BLOCK_K': 32, 'GROUP_M': 8, 'SPLIT_K': 1, 'num_stages': 3, 'num_warps': 4}, num_warps=4, num_stages=3),
        triton.Config({'BLOCK_M': 256, 'BLOCK_N': 128, 'BLOCK_K': 32, 'GROUP_M': 8, 'SPLIT_K': 1, 'num_stages': 2, 'num_warps': 8}, num_warps=8, num_stages=2),
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 256, 'BLOCK_K': 32, 'GROUP_M': 8, 'SPLIT_K': 1, 'num_stages': 2, 'num_warps': 8}, num_warps=8, num_stages=2),
        triton.Config({'BLOCK_M': 64, 'BLOCK_N': 64, 'BLOCK_K': 32, 'GROUP_M': 8, 'SPLIT_K': 1, 'num_stages': 4, 'num_warps': 4}, num_warps=4, num_stages=4),
    ],
    key=['M', 'N', 'K'],
)
@triton.jit
def _matmul_kernel(
    A, B, C,
    M, N, K,
    stride_am, stride_ak,
    stride_bk, stride_bn,
    stride_cm, stride_cn,
    BLOCK_M: tl.constexpr, BLOCK_N: tl.constexpr, BLOCK_K: tl.constexpr,
    GROUP_M: tl.constexpr, SPLIT_K: tl.constexpr,
    num_stages: tl.constexpr, num_warps: tl.constexpr,
):
    pid = tl.program_id(axis=0)
    grid_m = (M + BLOCK_M - 1) // BLOCK_M
    grid_n = (N + BLOCK_N - 1) // BLOCK_N
    
    pid_m = pid // grid_n
    pid_n = pid % grid_n
    
    if SPLIT_K > 1:
        pid_k = tl.program_id(axis=1)
    else:
        pid_k = 0
    
    num_pid_m = tl.cdiv(M, BLOCK_M)
    num_pid_n = tl.cdiv(N, BLOCK_N)
    num_pid_in_group = GROUP_M * num_pid_n
    group_id = pid // num_pid_in_group
    first_pid_m = group_id * GROUP_M
    group_size_m = min(num_pid_m - first_pid_m, GROUP_M)
    pid_m = first_pid_m + (pid % group_size_m)
    pid_n = (pid % num_pid_in_group) // group_size_m
    
    rm = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
    rn = pid_n * BLOCK_N + tl.arange(0, BLOCK_N)
    
    if SPLIT_K > 1:
        rk = pid_k * BLOCK_K + tl.arange(0, BLOCK_K)
    else:
        rk = tl.arange(0, BLOCK_K)
    
    A_mask = (rm[:, None] < M) & (rk[None, :] < K)
    B_mask = (rk[:, None] < K) & (rn[None, :] < N)
    
    acc = tl.zeros((BLOCK_M, BLOCK_N), dtype=tl.float32)
    
    if SPLIT_K > 1:
        K_blocks = (K + BLOCK_K * SPLIT_K - 1) // (BLOCK_K * SPLIT_K)
    else:
        K_blocks = (K + BLOCK_K - 1) // BLOCK_K
    
    for k in range(0, K_blocks):
        k_off = k * BLOCK_K
        a = tl.load(A + rm[:, None] * stride_am + (k_off + rk[None, :]) * stride_ak, 
                    mask=A_mask & ((k_off + rk[None, :]) < K), other=0.0)
        b = tl.load(B + (k_off + rk[:, None]) * stride_bk + rn[None, :] * stride_bn,
                    mask=B_mask & ((k_off + rk[:, None]) < K), other=0.0)
        
        acc += tl.dot(a, b, out_dtype=tl.float32)
    
    if SPLIT_K > 1:
        acc = acc.to(C.dtype.element_ty)
        
        off_cm = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
        off_cn = pid_n * BLOCK_N + tl.arange(0, BLOCK_N)
        C_mask = (off_cm[:, None] < M) & (off_cn[None, :] < N)
        
        ptr_c = C + off_cm[:, None] * stride_cm + off_cn[None, :] * stride_cn
        tl.atomic_add(ptr_c, acc, mask=C_mask)
    else:
        acc = gelu(acc)
        c = acc.to(C.dtype.element_ty)
        
        off_cm = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
        off_cn = pid_n * BLOCK_N + tl.arange(0, BLOCK_N)
        C_mask = (off_cm[:, None] < M) & (off_cn[None, :] < N)
        
        ptr_c = C + off_cm[:, None] * stride_cm + off_cn[None, :] * stride_cn
        tl.store(ptr_c, c, mask=C_mask)


def matmul(a: torch.Tensor, b: torch.Tensor) -> torch.Tensor:
    M, K = a.shape
    K, N = b.shape
    
    assert a.dtype == b.dtype, "Input tensors must have same dtype"
    assert a.is_cuda and b.is_cuda, "Input tensors must be on CUDA"
    
    c = torch.empty((M, N), device=a.device, dtype=a.dtype)
    
    if a.dtype == torch.float16:
        grid = lambda META: ((M + META['BLOCK_M'] - 1) // META['BLOCK_M']) * ((N + META['BLOCK_N'] - 1) // META['BLOCK_N'])
        _matmul_kernel[grid](
            a, b, c,
            M, N, K,
            a.stride(0), a.stride(1),
            b.stride(0), b.stride(1),
            c.stride(0), c.stride(1)
        )
    else:
        a_f16 = a.to(torch.float16)
        b_f16 = b.to(torch.float16)
        c_f16 = torch.empty((M, N), device=a.device, dtype=torch.float16)
        
        grid = lambda META: ((M + META['BLOCK_M'] - 1) // META['BLOCK_M']) * ((N + META['BLOCK_N'] - 1) // META['BLOCK_N'])
        _matmul_kernel[grid](
            a_f16, b_f16, c_f16,
            M, N, K,
            a_f16.stride(0), a_f16.stride(1),
            b_f16.stride(0), b_f16.stride(1),
            c_f16.stride(0), c_f16.stride(1)
        )
        c = c_f16.to(a.dtype)
    
    return c


class Solution:
    def solve(self, spec_path: str = None) -> dict:
        return {"code": self._generate_code()}
    
    def _generate_code(self) -> str:
        import inspect
        return inspect.getsource(matmul) + "\n\n" + inspect.getsource(Solution)