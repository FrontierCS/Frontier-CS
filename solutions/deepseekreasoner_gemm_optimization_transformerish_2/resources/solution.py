import torch
import triton
import triton.language as tl
from typing import Optional, Dict

@triton.jit
def gelu(x):
    return x * 0.5 * (1.0 + tl.extra.cuda.libdevice.erf(x * 0.7071067811865476))

@triton.autotune(
    configs=[
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 256, 'BLOCK_K': 64, 'GROUP_M': 8}, num_stages=3, num_warps=8),
        triton.Config({'BLOCK_M': 256, 'BLOCK_N': 128, 'BLOCK_K': 64, 'GROUP_M': 8}, num_stages=3, num_warps=8),
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 128, 'BLOCK_K': 32, 'GROUP_M': 8}, num_stages=4, num_warps=4),
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 64, 'BLOCK_K': 32, 'GROUP_M': 8}, num_stages=4, num_warps=4),
        triton.Config({'BLOCK_M': 64, 'BLOCK_N': 128, 'BLOCK_K': 32, 'GROUP_M': 8}, num_stages=4, num_warps=4),
        triton.Config({'BLOCK_M': 64, 'BLOCK_N': 64, 'BLOCK_K': 64, 'GROUP_M': 8}, num_stages=3, num_warps=4),
        triton.Config({'BLOCK_M': 256, 'BLOCK_N': 64, 'BLOCK_K': 32, 'GROUP_M': 8}, num_stages=4, num_warps=4),
        triton.Config({'BLOCK_M': 64, 'BLOCK_N': 256, 'BLOCK_K': 32, 'GROUP_M': 8}, num_stages=4, num_warps=4),
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
    BLOCK_M: tl.constexpr,
    BLOCK_N: tl.constexpr,
    BLOCK_K: tl.constexpr,
    GROUP_M: tl.constexpr,
):
    pid = tl.program_id(0)
    grid_m = tl.cdiv(M, BLOCK_M)
    grid_n = tl.cdiv(N, BLOCK_N)
    
    width = GROUP_M * grid_n
    group_id = pid // width
    group_size = min(grid_m - group_id * GROUP_M, GROUP_M)
    pid_m = group_id * GROUP_M + (pid % group_size)
    pid_n = (pid % width) // group_size
    
    rm = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
    rn = pid_n * BLOCK_N + tl.arange(0, BLOCK_N)
    ram = tl.max_contiguous(tl.multiple_of(rm % M, BLOCK_M), BLOCK_M)
    rbn = tl.max_contiguous(tl.multiple_of(rn % N, BLOCK_N), BLOCK_N)
    
    rk = tl.arange(0, BLOCK_K)
    A_ptr = A + (ram[:, None] * stride_am + rk[None, :] * stride_ak)
    B_ptr = B + (rk[:, None] * stride_bk + rbn[None, :] * stride_bn)
    
    acc = tl.zeros((BLOCK_M, BLOCK_N), dtype=tl.float32)
    for k in range(0, tl.cdiv(K, BLOCK_K)):
        k_remaining = K - k * BLOCK_K
        a = tl.load(A_ptr, mask=rk[None, :] < k_remaining, other=0.0)
        b = tl.load(B_ptr, mask=rk[:, None] < k_remaining, other=0.0)
        acc += tl.dot(a, b, allow_tf32=True)
        A_ptr += BLOCK_K * stride_ak
        B_ptr += BLOCK_K * stride_bk
    
    acc = gelu(acc.to(tl.float32))
    
    cm = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
    cn = pid_n * BLOCK_N + tl.arange(0, BLOCK_N)
    C_ptr = C + (cm[:, None] * stride_cm + cn[None, :] * stride_cn)
    mask = (cm[:, None] < M) & (cn[None, :] < N)
    tl.store(C_ptr, acc, mask=mask)

def matmul(a: torch.Tensor, b: torch.Tensor) -> torch.Tensor:
    if a.dim() != 2 or b.dim() != 2:
        raise ValueError("Both inputs must be 2D tensors")
    
    M, K = a.shape
    K_check, N = b.shape
    if K != K_check:
        raise ValueError(f"Dimension mismatch: a.shape={a.shape}, b.shape={b.shape}")
    
    device = a.device
    if device.type != 'cuda':
        raise RuntimeError("Triton kernel requires CUDA device")
    
    if a.stride(1) != 1 and a.stride(0) != 1:
        a = a.contiguous()
    if b.stride(1) != 1 and b.stride(0) != 1:
        b = b.contiguous()
    
    c = torch.empty((M, N), device=device, dtype=a.dtype)
    
    grid = lambda META: (triton.cdiv(M, META['BLOCK_M']) * triton.cdiv(N, META['BLOCK_N']),)
    
    if a.dtype == torch.float16:
        a = a.to(torch.float32)
        b = b.to(torch.float32)
        c = c.to(torch.float32)
    
    _matmul_kernel[grid](
        a, b, c,
        M, N, K,
        a.stride(0), a.stride(1),
        b.stride(0), b.stride(1),
        c.stride(0), c.stride(1),
    )
    
    return c.to(a.dtype)

class Solution:
    def solve(self, spec_path: str = None) -> dict:
        import inspect
        import sys
        
        current_module = sys.modules[__name__]
        source = inspect.getsource(current_module)
        
        return {"code": source}
