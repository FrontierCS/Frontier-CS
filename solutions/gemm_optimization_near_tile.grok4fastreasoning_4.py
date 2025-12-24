class Solution:
    def solve(self, spec_path: str = None) -> dict:
        code = """
import torch
import triton
import triton.language as tl

@triton.jit
def gelu(x):
    return x * 0.5 * (1.0 + tl.extra.cuda.libdevice.erf(x * 0.7071067811865476))

@triton.jit
def kernel(
    a_ptr, b_ptr, c_ptr,
    M: tl.int32, N: tl.int32, K: tl.int32,
    stride_am: tl.int32, stride_ak: tl.int32,
    stride_bk: tl.int32, stride_bn: tl.int32,
    stride_cm: tl.int32, stride_cn: tl.int32,
    BLOCK_M: tl.constexpr,
    BLOCK_N: tl.constexpr,
    BLOCK_K: tl.constexpr,
):
    pid_m = tl.program_id(0)
    pid_n = tl.program_id(1)
    offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
    offs_n = pid_n * BLOCK_N + tl.arange(0, BLOCK_N)
    acc = tl.zeros((BLOCK_M, BLOCK_N), dtype=tl.float32)
    lo = 0
    while lo < K:
        offs_k = lo + tl.arange(0, BLOCK_K)
        mask_k = offs_k < K
        mask_m = offs_m < M
        mask_n = offs_n < N
        a_offsets = (offs_m[:, None] * stride_am + offs_k[None, :] * stride_ak).to(tl.int32)
        a_mask = mask_m[:, None] & mask_k[None, :]
        a = tl.load(a_ptr + a_offsets, mask=a_mask, other=0.0)
        a = a.to(tl.float32)
        b_offsets = (offs_k[:, None] * stride_bk + offs_n[None, :] * stride_bn).to(tl.int32)
        b_mask = mask_k[:, None] & mask_n[None, :]
        b = tl.load(b_ptr + b_offsets, mask=b_mask, other=0.0)
        b = b.to(tl.float32)
        acc += tl.dot(a, b)
        lo += BLOCK_K
    c = gelu(acc)
    mask_c = mask_m[:, None] & mask_n[None, :]
    c_offsets = (offs_m[:, None] * stride_cm + offs_n[None, :] * stride_cn).to(tl.int32)
    tl.store(c_ptr + c_offsets, c, mask=mask_c)

_autotune_cache = {}
configs = [
    {'BLOCK_M': 64, 'BLOCK_N': 64, 'BLOCK_K': 64, 'num_stages': 2, 'num_warps': 4},
    {'BLOCK_M': 128, 'BLOCK_N': 128, 'BLOCK_K': 64, 'num_stages': 3, 'num_warps': 8},
    {'BLOCK_M': 256, 'BLOCK_N': 256, 'BLOCK_K': 128, 'num_stages': 4, 'num_warps': 8},
    {'BLOCK_M': 64, 'BLOCK_N': 128, 'BLOCK_K': 32, 'num_stages': 2, 'num_warps': 4},
    {'BLOCK_M': 128, 'BLOCK_N': 64, 'BLOCK_K': 32, 'num_stages': 3, 'num_warps': 4},
    {'BLOCK_M': 128, 'BLOCK_N': 256, 'BLOCK_K': 128, 'num_stages': 4, 'num_warps': 8},
    {'BLOCK_M': 256, 'BLOCK_N': 128, 'BLOCK_K': 128, 'num_stages': 4, 'num_warps': 8},
]

def autotune(M, N, K, stride_am, stride_ak, stride_bk, stride_bn, a, b, configs):
    device = a.device
    C_temp = torch.empty((M, N), dtype=torch.float32, device=device)
    stride_cm = C_temp.stride(0)
    stride_cn = C_temp.stride(1)
    best_time = float('inf')
    best_config = None
    for conf in configs:
        BLOCK_M = conf['BLOCK_M']
        BLOCK_N = conf['BLOCK_N']
        BLOCK_K = conf['BLOCK_K']
        num_stages = conf['num_stages']
        num_warps = conf['num_warps']
        grid = (triton.cdiv(M, BLOCK_M), triton.cdiv(N, BLOCK_N))
        def kernel_fn():
            kernel[grid, num_stages=num_stages, num_warps=num_warps](
                a, b, C_temp, M, N, K,
                stride_am, stride_ak, stride_bk, stride_bn,
                stride_cm, stride_cn,
                BLOCK_M=BLOCK_M, BLOCK_N=BLOCK_N, BLOCK_K=BLOCK_K
            )
        for _ in range(3):
            kernel_fn()
        start = torch.cuda.Event(enable_timing=True)
        end = torch.cuda.Event(enable_timing=True)
        times = []
        for _ in range(20):
            start.record()
            kernel_fn()
            end.record()
            torch.cuda.synchronize()
            times.append(start.elapsed_time(end))
        time_avg = sum(times) / len(times)
        if time_avg < best_time:
            best_time = time_avg
            best_config = conf
    return best_config

def matmul(a: torch.Tensor, b: torch.Tensor) -> torch.Tensor:
    M, Ka = a.shape
    Kb, N = b.shape
    if Ka != Kb:
        raise ValueError("Incompatible matrix dimensions")
    K = Ka
    dtype = a.dtype
    device = a.device
    C = torch.empty((M, N), dtype=torch.float32, device=device)
    stride_am = a.stride(0)
    stride_ak = a.stride(1)
    stride_bk = b.stride(0)
    stride_bn = b.stride(1)
    stride_cm = C.stride(0)
    stride_cn = C.stride(1)
    key = (M, N, K, stride_am, stride_ak, stride_bk, stride_bn)
    if key not in _autotune_cache:
        _autotune_cache[key] = autotune(M, N, K, stride_am, stride_ak, stride_bk, stride_bn, a, b, configs)
    conf = _autotune_cache[key]
    BLOCK_M = conf['BLOCK_M']
    BLOCK_N = conf['BLOCK_N']
    BLOCK_K = conf['BLOCK_K']
    num_stages = conf['num_stages']
    num_warps = conf['num_warps']
    grid = (triton.cdiv(M, BLOCK_M), triton.cdiv(N, BLOCK_N))
    kernel[grid, num_stages=num_stages, num_warps=num_warps](
        a, b, C, M, N, K,
        stride_am, stride_ak, stride_bk, stride_bn,
        stride_cm, stride_cn,
        BLOCK_M=BLOCK_M, BLOCK_N=BLOCK_N, BLOCK_K=BLOCK_K
    )
    return C.to(dtype)
"""
        return {"code": code}
