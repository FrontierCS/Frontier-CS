import torch
import triton
import triton.language as tl
import math
from typing import Optional

class Solution:
    def solve(self, spec_path: Optional[str] = None) -> dict:
        code = """
import torch
import triton
import triton.language as tl
import math

def decoding_attn(Q: torch.Tensor, K: torch.Tensor, V: torch.Tensor) -> torch.Tensor:
    Z, H, M, Dq = Q.shape
    _, _, N, Dv = V.shape
    _, _, _, Dk = K.shape
    assert Dk == Dq
    device = Q.device
    dtype = torch.float16
    scale = 1.0 / math.sqrt(Dq)
    stride_q = Q.stride()
    stride_k = K.stride()
    stride_v = V.stride()
    scores = torch.empty(Z, H, M, N, dtype=torch.float32, device=device)
    stride_s = scores.stride()
    BLOCK_M = 32
    BLOCK_N = 128
    BLOCK_D = 64
    @triton.jit
    def compute_scores_kernel(
        q_ptr, k_ptr, scores_ptr,
        M, N, Dq,
        stride_qm, stride_qd, stride_kn, stride_kd, stride_sm, stride_sn,
        SCALE: tl.float32,
        BLOCK_M: tl.constexpr,
        BLOCK_N: tl.constexpr,
        BLOCK_D: tl.constexpr
    ):
        pid_m = tl.program_id(0)
        pid_n = tl.program_id(1)
        block_m = pid_m * BLOCK_M
        block_n = pid_n * BLOCK_N
        offs_m = block_m + tl.arange(0, BLOCK_M)
        offs_n = block_n + tl.arange(0, BLOCK_N)
        offs_d = tl.arange(0, BLOCK_D)
        mask_m = offs_m < M
        mask_n = offs_n < N
        mask_d = offs_d < Dq
        q_ptrs = q_ptr + offs_m[:,None] * stride_qm + offs_d[None,:] * stride_qd
        q = tl.load(q_ptrs, mask=mask_m[:,None] & mask_d[None,:], other=0.0).to(tl.float32)
        k_ptrs = k_ptr + offs_n[:,None] * stride_kn + offs_d[None,:] * stride_kd
        k = tl.load(k_ptrs, mask=mask_n[:,None] & mask_d[None,:], other=0.0).to(tl.float32)
        dots = tl.dot(q, tl.trans(k)) * SCALE
        cutoffs = tl.int32(N) - tl.int32(M) + tl.int32(block_m) + tl.arange(0, BLOCK_M)[:, None]
        local_ns = tl.int32(block_n) + tl.arange(0, BLOCK_N)[None, :]
        causal_mask = local_ns <= cutoffs
        dots = tl.where(causal_mask, dots, -3e4)
        scores_ptrs = scores_ptr + offs_m[:,None] * stride_sm + offs_n[None,:] * stride_sn
        tl.store(scores_ptrs, dots, mask=mask_m[:,None] & mask_n[None,:])
    for z in range(Z):
        for h in range(H):
            q_ptr = int(Q.data_ptr() + z * stride_q[0] + h * stride_q[1])
            k_ptr = int(K.data_ptr() + z * stride_k[0] + h * stride_k[1])
            s_ptr = int(scores.data_ptr() + z * stride_s[0] + h * stride_s[1])
            grid = (triton.cdiv(M, BLOCK_M), triton.cdiv(N, BLOCK_N))
            compute_scores_kernel[grid](
                q_ptr, k_ptr, s_ptr, M, N, Dq,
                stride_q[2], stride_q[3], stride_k[2], stride_k[3],
                stride_s[2], stride_s[3], scale,
                BLOCK_M=BLOCK_M, BLOCK_N=BLOCK_N, BLOCK_D=BLOCK_D
            )
    attn = torch.softmax(scores, dim=-1)
    output_float = torch.matmul(attn, V.to(torch.float32))
    output = output_float.to(dtype)
    return output
"""
        return {"code": code}
