import math
import torch
import triton
import triton.language as tl

def cdiv(x: int, y: int) -> int:
    return (x + y - 1) // y

class Solution:
    def solve(self, spec_path: str = None) -> dict:
        code = """
import math
import torch
import triton
import triton.language as tl

def cdiv(x: int, y: int) -> int:
    return (x + y - 1) // y

@triton.jit
def attention_kernel(Q, K, V, O, M, N, D, Dv, scale: tl.float32,
                     BLOCK_M: tl.constexpr, BLOCK_N: tl.constexpr):
    pid_m = tl.program_id(0)
    block_start_m = pid_m * BLOCK_M
    offs_m = block_start_m + tl.arange(0, BLOCK_M)
    mask_m = offs_m < M
    q_ptrs = tl.make_block_ptr(
        Q,
        shape=(M, D),
        strides=(D, 1),
        offsets=(block_start_m, 0),
        block_shape=(BLOCK_M, D),
        order=(1, 0)
    )
    q = tl.load(q_ptrs, mask=mask_m[:, None], other=0.0)
    q_f32 = q.to(tl.float32)
    m = tl.full((BLOCK_M,), -1e9, dtype=tl.float32)
    l = tl.zeros((BLOCK_M,), dtype=tl.float32)
    o_acc = tl.zeros((BLOCK_M, Dv), dtype=tl.float32)
    kv_block_id = 0
    while True:
        offs_n_start = kv_block_id * BLOCK_N
        if offs_n_start >= N:
            break
        offs_n = offs_n_start + tl.arange(0, BLOCK_N)
        mask_n = offs_n < N
        k_ptrs = tl.make_block_ptr(
            K,
            shape=(N, D),
            strides=(D, 1),
            offsets=(offs_n_start, 0),
            block_shape=(BLOCK_N, D),
            order=(1, 0)
        )
        k = tl.load(k_ptrs, mask=mask_n[None, :], other=0.0)
        k_f32 = k.to(tl.float32)
        v_ptrs = tl.make_block_ptr(
            V,
            shape=(N, Dv),
            strides=(Dv, 1),
            offsets=(offs_n_start, 0),
            block_shape=(BLOCK_N, Dv),
            order=(1, 0)
        )
        v = tl.load(v_ptrs, mask=mask_n[None, :], other=0.0)
        v_f32 = v.to(tl.float32)
        s = tl.dot(q_f32, tl.trans(k_f32)) * scale
        s = tl.where(mask_n[None, :], s, -1e9)
        m_kv = tl.max(s, axis=1)
        p = tl.exp(s - m_kv[:, None])
        l_kv = tl.sum(p, axis=1)
        m_new = tl.maximum(m, m_kv)
        alpha = tl.exp(m - m_new)
        l = alpha * l + tl.exp(m_kv - m_new) * l_kv
        o_contrib = tl.dot(p, v_f32)
        o_acc = alpha[:, None] * o_acc + tl.exp(m_kv - m_new)[:, None] * o_contrib
        m = m_new
        kv_block_id += 1
    row_scale = 1.0 / (l + 1e-8)
    o = o_acc * row_scale[:, None]
    o = o.to(tl.float16)
    o_ptrs = tl.make_block_ptr(
        O,
        shape=(M, Dv),
        strides=(Dv, 1),
        offsets=(block_start_m, 0),
        block_shape=(BLOCK_M, Dv),
        order=(1, 0)
    )
    tl.store(o_ptrs, o, mask=mask_m[:, None])

def compute_attention(q: torch.Tensor, k: torch.Tensor, v: torch.Tensor, scale: float) -> torch.Tensor:
    M, D = q.shape
    N, _ = k.shape
    Dv = v.shape[1]
    o = torch.empty((M, Dv), dtype=q.dtype, device=q.device)
    if M == 0 or N == 0:
        return o
    BLOCK_M = 128
    BLOCK_N = 128
    grid = (cdiv(M, BLOCK_M), )
    attention_kernel[grid, num_warps=8, num_stages=3](
        q, k, v, o, M, N, D, Dv, torch.tensor(scale, device=q.device),
        BLOCK_M=BLOCK_M, BLOCK_N=BLOCK_N
    )
    return o

def gdpa_attn(Q: torch.Tensor, K: torch.Tensor, V: torch.Tensor, GQ: torch.Tensor, GK: torch.Tensor) -> torch.Tensor:
    Z, H, M, Dq = Q.shape
    _, _, N, Dv = V.shape[2:]
    device = Q.device
    dtype = Q.dtype
    scale = 1.0 / math.sqrt(Dq)
    Qg = Q * torch.sigmoid(GQ)
    Kg = K * torch.sigmoid(GK)
    O = torch.empty((Z, H, M, Dv), dtype=dtype, device=device)
    for z in range(Z):
        for h in range(H):
            O[z, h] = compute_attention(Qg[z, h], Kg[z, h], V[z, h], scale)
    return O
"""
        return {"code": code}