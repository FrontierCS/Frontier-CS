import torch
import triton
import triton.language as tl
import math
from typing import Optional

class Solution:
    def solve(self, spec_path: str = None) -> dict:
        code = r'''
import torch
import triton
import triton.language as tl
import math

def ragged_attn(Q: torch.Tensor, K: torch.Tensor, V: torch.Tensor, row_lens: torch.Tensor) -> torch.Tensor:
    assert Q.is_cuda and K.is_cuda and V.is_cuda and row_lens.is_cuda
    scale = 1 / math.sqrt(Q.shape[-1])
    M, D = Q.shape
    N, Dv = V.shape
    O = torch.empty((M, Dv), dtype=Q.dtype, device=Q.device)
    row_lens_cpu = row_lens.to(torch.int32)
    BLOCK_M = 64
    BLOCK_N = 64
    MAX_K_BLOCKS = 16
    grid = lambda meta: (triton.cdiv(M, meta['BLOCK_M']),)
    @triton.jit
    def kernel(
        Q, K, V, row_lens, O,
        scale: tl.constexpr,
        BLOCK_M: tl.constexpr,
        BLOCK_N: tl.constexpr,
        MAX_K_BLOCKS: tl.constexpr
    ):
        pid = tl.program_id(0)
        block_start_q = pid * BLOCK_M
        offs_q = block_start_q + tl.arange(0, BLOCK_M)
        q_mask = offs_q < Q.shape[0]
        q = tl.load(Q[offs_q, :], mask=q_mask[:, None], other=0.0)
        row_lens_local = tl.load(row_lens[offs_q], mask=q_mask, other=0, dtype=tl.int32)
        INITIAL_M = -1e5
        m = tl.full((BLOCK_M,), INITIAL_M, dtype=tl.float32)
        l = tl.zeros((BLOCK_M,), dtype=tl.float32)
        o = tl.zeros((BLOCK_M, Dv), dtype=tl.float32)
        for bk in range(MAX_K_BLOCKS):
            start_k = bk * BLOCK_N
            if start_k >= V.shape[0]:
                break
            offs_k = start_k + tl.arange(0, BLOCK_N)
            k_mask = offs_k < V.shape[0]
            k = tl.load(K[offs_k, :], mask=k_mask[:, None], other=0.0)
            scores = tl.sum(q[:, None, :] * k[None, :, :], axis=-1) * scale
            v = tl.load(V[offs_k, :], mask=k_mask[:, None], other=0.0)
            for local_q in range(BLOCK_M):
                if not q_mask[local_q]:
                    continue
                row_len = row_lens_local[local_q]
                num_valid = tl.where(
                    row_len > start_k,
                    tl.minimum(tl.constexpr(BLOCK_N), row_len - start_k),
                    tl.constexpr(0)
                )
                local_max = INITIAL_M
                for local_k in range(BLOCK_N):
                    if local_k < num_valid and k_mask[local_k]:
                        local_max = tl.maximum(local_max, scores[local_q, local_k])
                if local_max == INITIAL_M:
                    continue
                m_new = tl.maximum(m[local_q], local_max)
                exp_old_scale = l[local_q] * tl.exp(m[local_q] - m_new)
                sum_exp_new = 0.0
                for local_k in range(BLOCK_N):
                    if local_k < num_valid and k_mask[local_k]:
                        sum_exp_new += tl.exp(scores[local_q, local_k] - m_new)
                l_new = exp_old_scale + sum_exp_new
                if l_new == 0.0:
                    continue
                scaling = exp_old_scale / l_new
                o[local_q] *= scaling
                contrib = tl.zeros((Dv,), dtype=tl.float32)
                for local_k in range(BLOCK_N):
                    if local_k < num_valid and k_mask[local_k]:
                        e = tl.exp(scores[local_q, local_k] - m_new)
                        contrib += e * v[local_k]
                o[local_q] += contrib / l_new
                m[local_q] = m_new
                l[local_q] = l_new
        o_mask = offs_q < O.shape[0]
        tl.store(O[offs_q, :], o.to(tl.float16), mask=o_mask[:, None])
    kernel[grid](
        Q, K, V, row_lens_cpu, O,
        scale=scale,
        BLOCK_M=BLOCK_M,
        BLOCK_N=BLOCK_N,
        MAX_K_BLOCKS=MAX_K_BLOCKS,
        num_stages=4,
        num_warps=4
    )
    return O
'''
        return {"code": code}
