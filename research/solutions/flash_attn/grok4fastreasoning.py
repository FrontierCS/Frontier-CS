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
import math

@triton.jit
def kernel(Q_PTR, K_PTR, V_PTR, O_PTR,
           Mq: tl.constexpr, Mk: tl.constexpr, D: tl.constexpr, Dv: tl.constexpr,
           scale: tl.float32,
           BLOCK_M: tl.constexpr, BLOCK_N: tl.constexpr,
           num_q: tl.constexpr, num_k: tl.constexpr,
           causal: tl.constexpr):
    pid = tl.program_id(0)
    q_base = Q_PTR + pid * Mq * D
    k_base = K_PTR + pid * Mk * D
    v_base = V_PTR + pid * Mk * Dv
    o_base = O_PTR + pid * Mq * Dv
    for qi in range(num_q):
        start_m = qi * BLOCK_M
        q_ptr = tl.make_block_ptr(
            q_base, (Mq, D), (D, 1), (start_m, 0), (BLOCK_M, D)
        )
        q = tl.load(q_ptr)
        m = tl.full((BLOCK_M,), tl.float32("-inf"), dtype=tl.float32)
        l = tl.zeros((BLOCK_M,), dtype=tl.float32)
        o = tl.zeros((BLOCK_M, Dv), dtype=tl.float32)
        for ki in range(num_k):
            start_n = ki * BLOCK_N
            k_ptr = tl.make_block_ptr(
                k_base, (Mk, D), (D, 1), (start_n, 0), (BLOCK_N, D)
            )
            k = tl.load(k_ptr)
            v_ptr = tl.make_block_ptr(
                v_base, (Mk, Dv), (Dv, 1), (start_n, 0), (BLOCK_N, Dv)
            )
            v = tl.load(v_ptr)
            k_t = tl.trans(k)
            s = scale * tl.dot(q, k_t)
            if causal:
                im = tl.arange(0, BLOCK_M)[:, None] + start_m
                jn = tl.arange(0, BLOCK_N)[None, :] + start_n
                s = tl.where(jn < im, s, -10000.0)
            m_loc = tl.max(s, axis=1)
            p = tl.exp(s - m_loc[:, None])
            l_loc = tl.sum(p, axis=1)
            o_loc = tl.dot(p, v)
            new_m = tl.maximum(m, m_loc)
            exp_dm = tl.exp(m - new_m)
            exp_dl = tl.exp(m_loc - new_m)
            l = l * exp_dm + l_loc * exp_dl
            o = o * exp_dm[:, None] + o_loc * exp_dl[:, None]
        o_final = o / l[:, None]
        o_ptr = tl.make_block_ptr(
            o_base, (Mq, Dv), (Dv, 1), (start_m, 0), (BLOCK_M, Dv)
        )
        tl.store(o_ptr, o_final.to(tl.float16))

def flash_attn(Q: torch.Tensor, K: torch.Tensor, V: torch.Tensor, causal: bool = True) -> torch.Tensor:
    Z, H, M, D = Q.shape
    _, _, N, Dv = V.shape
    B = Z * H
    scale = 1.0 / math.sqrt(D)
    BLOCK_M = 64
    BLOCK_N = 64
    num_q_blocks = M // BLOCK_M
    num_k_blocks = N // BLOCK_N
    q_resh = Q.contiguous().reshape(B, M, D)
    k_resh = K.contiguous().reshape(B, N, D)
    v_resh = V.contiguous().reshape(B, N, Dv)
    o_resh = torch.empty((B, M, Dv), dtype=Q.dtype, device=Q.device)
    kernel = triton.jit(kernel)
    kernel[grid=(B,)](q_resh, k_resh, v_resh, o_resh, M, N, D, Dv, scale, BLOCK_M, BLOCK_N, num_q_blocks, num_k_blocks, causal)
    return o_resh.reshape(Z, H, M, Dv)
"""
        return {"code": code}