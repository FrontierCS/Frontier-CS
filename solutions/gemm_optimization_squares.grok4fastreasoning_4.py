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
def matmul_kernel(
    A_PTR, B_PTR, C_PTR, M, N, K, stride_am, stride_ak, stride_bk, stride_bn, stride_cm, stride_cn,
    BLOCK_M: tl.constexpr,
    BLOCK_N: tl.constexpr,
    BLOCK_K: tl.constexpr
):
    num_pid_m = tl.cdiv(M, BLOCK_M)
    num_pid_n = tl.cdiv(N, BLOCK_N)
    pid = tl.program_id(0)
    pid_m = pid // num_pid_n
    pid_n = pid % num_pid_n
    offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
    offs_n = pid_n * BLOCK_N + tl.arange(0, BLOCK_N)
    acc = tl.zeros((BLOCK_M, BLOCK_N), dtype=tl.float32)
    for start_k in range(0, K, BLOCK_K):
        offs_k = start_k + tl.arange(0, BLOCK_K)
        a_mask = (offs_m[:, None] < M) & (offs_k[None, :] < K)
        a_offset = (offs_m[:, None] * stride_am + offs_k[None, :] * stride_ak).to(tl.int32)
        a_ptr = A_PTR + a_offset
        a = tl.load(a_ptr, mask=a_mask, other=0.0).to(tl.float32)
        b_mask = (offs_k[:, None] < K) & (offs_n[None, :] < N)
        b_offset = (offs_k[:, None] * stride_bk + offs_n[None, :] * stride_bn).to(tl.int32)
        b_ptr = B_PTR + b_offset
        b = tl.load(b_ptr, mask=b_mask, other=0.0).to(tl.float32)
        acc += tl.dot(a, b)
    c = gelu(acc)
    c_mask = (offs_m[:, None] < M) & (offs_n[None, :] < N)
    c_offset = (offs_m[:, None] * stride_cm + offs_n[None, :] * stride_cn).to(tl.int32)
    c_ptr = C_PTR + c_offset
    tl.store(c_ptr, c, mask=c_mask)

def matmul(a: torch.Tensor, b: torch.Tensor) -> torch.Tensor:
    M, Ka = a.shape
    Kb, N = b.shape
    assert Ka == Kb, "Incompatible dimensions"
    K = Ka
    c = torch.empty((M, N), dtype=a.dtype, device=a.device)
    BLOCK_M = 128
    BLOCK_N = 128
    BLOCK_K = 64
    grid = (triton.cdiv(M, BLOCK_M) * triton.cdiv(N, BLOCK_N), )
    matmul_kernel[grid](
        A_PTR=a,
        B_PTR=b,
        C_PTR=c,
        M=M,
        N=N,
        K=K,
        stride_am=a.stride(0),
        stride_ak=a.stride(1),
        stride_bk=b.stride(0),
        stride_bn=b.stride(1),
        stride_cm=c.stride(0),
        stride_cn=c.stride(1),
        BLOCK_M=BLOCK_M,
        BLOCK_N=BLOCK_N,
        BLOCK_K=BLOCK_K,
    )
    return c
"""
        return {"code": code}
