import torch
import triton
import triton.language as tl

@triton.jit
def gelu(x):
    return x * 0.5 * (1.0 + tl.extra.cuda.libdevice.erf(x * 0.7071067811865476))

configs = [
    triton.Config({'BLOCK_M': 128, 'BLOCK_N': 128, 'BLOCK_K': 64}, num_stages=3, num_warps=8),
    triton.Config({'BLOCK_M': 256, 'BLOCK_N': 64, 'BLOCK_K': 64}, num_stages=3, num_warps=8),
    triton.Config({'BLOCK_M': 64, 'BLOCK_N': 256, 'BLOCK_K': 64}, num_stages=3, num_warps=8),
    triton.Config({'BLOCK_M': 128, 'BLOCK_N': 128, 'BLOCK_K': 128}, num_stages=4, num_warps=4),
    triton.Config({'BLOCK_M': 128, 'BLOCK_N': 128, 'BLOCK_K': 32}, num_stages=2, num_warps=8),
    triton.Config({'BLOCK_M': 128, 'BLOCK_N': 64, 'BLOCK_K': 64}, num_stages=4, num_warps=4),
    triton.Config({'BLOCK_M': 64, 'BLOCK_N': 128, 'BLOCK_K': 64}, num_stages=4, num_warps=4),
]

@triton.autotune(configs, key=['M', 'N', 'K'])
@triton.jit
def matmul_kernel(
    A_PTR, B_PTR, C_PTR, M, N, K,
    stride_am, stride_ak, stride_bk, stride_bn, stride_cm, stride_cn,
    BLOCK_M: tl.constexpr,
    BLOCK_N: tl.constexpr,
    BLOCK_K: tl.constexpr
):
    pid_m = tl.program_id(0)
    pid_n = tl.program_id(1)
    acc = tl.zeros((BLOCK_M, BLOCK_N), dtype=tl.float32)
    for ko in range(0, K, BLOCK_K):
        rm = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
        rk = ko + tl.arange(0, BLOCK_K)
        a_ptrs = A_PTR + rm[:, None] * stride_am + rk[None, :] * stride_ak
        a_mask = (rm[:, None] < M) & (rk[None, :] < K)
        A = tl.load(a_ptrs, mask=a_mask, other=0.0)
        rn = pid_n * BLOCK_N + tl.arange(0, BLOCK_N)
        b_ptrs = B_PTR + rk[:, None] * stride_bk + rn[None, :] * stride_bn
        b_mask = (rk[:, None] < K) & (rn[None, :] < N)
        B = tl.load(b_ptrs, mask=b_mask, other=0.0)
        acc += tl.dot(A, B)
    acc = gelu(acc)
    c_ptrs = C_PTR + rm[:, None] * stride_cm + rn[None, :] * stride_cn
    c_mask = (rm[:, None] < M) & (rn[None, :] < N)
    tl.store(c_ptrs, acc, mask=c_mask)

def matmul(a: torch.Tensor, b: torch.Tensor) -> torch.Tensor:
    M, K = a.shape
    assert b.shape[0] == K
    N = b.shape[1]
    output = torch.empty((M, N), dtype=a.dtype, device=a.device)
    def grid(meta):
        return (
            triton.cdiv(M, meta['BLOCK_M']),
            triton.cdiv(N, meta['BLOCK_N']),
        )
    matmul_kernel[grid](
        a.data_ptr(),
        b.data_ptr(),
        output.data_ptr(),
        M,
        N,
        K,
        a.stride(0),
        a.stride(1),
        b.stride(0),
        b.stride(1),
        output.stride(0),
        output.stride(1),
    )
    return output

class Solution:
    def solve(self, spec_path: str = None) -> dict:
        return {"code": "import torch\nimport triton\nimport triton.language as tl\n\n@triton.jit\ndef gelu(x):\n    return x * 0.5 * (1.0 + tl.extra.cuda.libdevice.erf(x * 0.7071067811865476))\n\nconfigs = [\n    triton.Config({'BLOCK_M': 128, 'BLOCK_N': 128, 'BLOCK_K': 64}, num_stages=3, num_warps=8),\n    triton.Config({'BLOCK_M': 256, 'BLOCK_N': 64, 'BLOCK_K': 64}, num_stages=3, num_warps=8),\n    triton.Config({'BLOCK_M': 64, 'BLOCK_N': 256, 'BLOCK_K': 64}, num_stages=3, num_warps=8),\n    triton.Config({'BLOCK_M': 128, 'BLOCK_N': 128, 'BLOCK_K': 128}, num_stages=4, num_warps=4),\n    triton.Config({'BLOCK_M': 128, 'BLOCK_N': 128, 'BLOCK_K': 32}, num_stages=2, num_warps=8),\n    triton.Config({'BLOCK_M': 128, 'BLOCK_N': 64, 'BLOCK_K': 64}, num_stages=4, num_warps=4),\n    triton.Config({'BLOCK_M': 64, 'BLOCK_N': 128, 'BLOCK_K': 64}, num_stages=4, num_warps=4),\n]\n\n@triton.autotune(configs, key=['M', 'N', 'K'])\n@triton.jit\ndef matmul_kernel(\n    A_PTR, B_PTR, C_PTR, M, N, K,\n    stride_am, stride_ak, stride_bk, stride_bn, stride_cm, stride_cn,\n    BLOCK_M: tl.constexpr,\n    BLOCK_N: tl.constexpr,\n    BLOCK_K: tl.constexpr\n):\n    pid_m = tl.program_id(0)\n    pid_n = tl.program_id(1)\n    acc = tl.zeros((BLOCK_M, BLOCK_N), dtype=tl.float32)\n    for ko in range(0, K, BLOCK_K):\n        rm = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)\n        rk = ko + tl.arange(0, BLOCK_K)\n        a_ptrs = A_PTR + rm[:, None] * stride_am + rk[None, :] * stride_ak\n        a_mask = (rm[:, None] < M) & (rk[None, :] < K)\n        A = tl.load(a_ptrs, mask=a_mask, other=0.0)\n        rn = pid_n * BLOCK_N + tl.arange(0, BLOCK_N)\n        b_ptrs = B_PTR + rk[:, None] * stride_bk + rn[None, :] * stride_bn\n        b_mask = (rk[:, None] < K) & (rn[None, :] < N)\n        B = tl.load(b_ptrs, mask=b_mask, other=0.0)\n        acc += tl.dot(A, B)\n    acc = gelu(acc)\n    c_ptrs = C_PTR + rm[:, None] * stride_cm + rn[None, :] * stride_cn\n    c_mask = (rm[:, None] < M) & (rn[None, :] < N)\n    tl.store(c_ptrs, acc, mask=c_mask)\n\ndef matmul(a: torch.Tensor, b: torch.Tensor) -> torch.Tensor:\n    M, K = a.shape\n    assert b.shape[0] == K\n    N = b.shape[1]\n    output = torch.empty((M, N), dtype=a.dtype, device=a.device)\n    def grid(meta):\n        return (\n            triton.cdiv(M, meta['BLOCK_M']),\n            triton.cdiv(N, meta['BLOCK_N']),\n        )\n    matmul_kernel[grid](\n        a.data_ptr(),\n        b.data_ptr(),\n        output.data_ptr(),\n        M,\n        N,\n        K,\n        a.stride(0),\n        a.stride(1),\n        b.stride(0),\n        b.stride(1),\n        output.stride(0),\n        output.stride(1),\n    )\n    return output"}