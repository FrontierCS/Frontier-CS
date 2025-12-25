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
def flash_kernel(
    q_ptr, k_ptr, v_ptr, o_ptr,
    M: tl.int32, N: tl.int32, head_dim_q: tl.int32, head_dim_v: tl.int32,
    scale: tl.float32,
    causal: tl.int32,
    q_stride_m: tl.int64, q_stride_d: tl.int64,
    k_stride_n: tl.int64, k_stride_d: tl.int64,
    v_stride_n: tl.int64, v_stride_v: tl.int64,
    o_stride_m: tl.int64, o_stride_d: tl.int64,
    BLOCK_M: tl.constexpr, BLOCK_N: tl.constexpr
):
    pid = tl.program_id(0)
    num_blocks = (M + BLOCK_M - 1) // BLOCK_M
    if pid >= num_blocks:
        return

    start_m = pid * BLOCK_M
    # Assume M % BLOCK_M == 0, no partial query blocks

    # Load Q block
    offs_m = start_m + tl.arange(0, BLOCK_M)
    offs_d = tl.arange(0, head_dim_q)
    q_offsets = (offs_m[:, None] * q_stride_m + offs_d[None, :] * q_stride_d).to(tl.int64)
    q = tl.load(q_ptr + q_offsets, dtype=tl.float16)

    # Initialize stats
    INIT = -1e9
    m = tl.full((BLOCK_M,), INIT, dtype=tl.float32)
    l = tl.zeros((BLOCK_M,), dtype=tl.float32)
    o = tl.zeros((BLOCK_M, head_dim_v), dtype=tl.float32)

    # KV block loop
    kv_bid = tl.zeros((1,), dtype=tl.int32)
    while True:
        start_n = kv_bid[0] * BLOCK_N
        if start_n >= N:
            break
        if causal == 1 and start_n >= start_m + BLOCK_M:
            break

        block_n = tl.minimum(BLOCK_N, N - start_n)
        offs_n = tl.arange(0, BLOCK_N)
        mask_n = offs_n < block_n
        offs_n_kv = start_n + offs_n

        # Load K
        k_offsets = (offs_n_kv[:, None] * k_stride_n + offs_d[None, :] * k_stride_d).to(tl.int64)
        k = tl.load(k_ptr + k_offsets, mask=mask_n[:, None], other=0.0, dtype=tl.float16)

        # Load V
        v_offsets = (offs_n_kv[:, None] * v_stride_n + tl.arange(0, head_dim_v)[None, :] * v_stride_v).to(tl.int64)
        v = tl.load(v_ptr + v_offsets, mask=mask_n[:, None], other=0.0, dtype=tl.float16)

        # Compute S
        q_f = q.to(tl.float32)
        k_f = k.to(tl.float32)
        s = tl.dot(q_f, tl.trans(k_f)) * scale

        # Mask padding
        INF = 1e4
        s = tl.where(mask_n[None, :], s, -INF)

        # Causal mask
        if causal == 1:
            delta = start_m - start_n
            i = tl.arange(0, BLOCK_M)[:, None]
            j = tl.arange(0, BLOCK_N)[None, :]
            mask_c = j > (i + delta)
            s = tl.where(mask_c, -INF, s)

        # Online softmax update
        local_max = tl.max(s, axis=1)
        m_new = tl.maximum(m, local_max)
        scale_prev = tl.exp(m - m_new)
        p = tl.exp(s - m_new[:, None])
        l_new = scale_prev * l + tl.sum(p, axis=1)

        v_f = v.to(tl.float32)
        o_new = scale_prev[:, None] * o + tl.dot(p, v_f)

        m = m_new
        l = l_new
        o = o_new

        kv_bid[0] += 1

    # Normalize
    o_final = tl.where(l[:, None] > 0, o / l[:, None], tl.zeros((BLOCK_M, head_dim_v), dtype=tl.float32))

    # Store
    offs_d_o = tl.arange(0, head_dim_v)
    o_offsets = (offs_m[:, None] * o_stride_m + offs_d_o[None, :] * o_stride_d).to(tl.int64)
    tl.store(o_ptr + o_offsets, o_final.to(tl.float16))

def flash_attn(Q: torch.Tensor, K: torch.Tensor, V: torch.Tensor, causal: bool = True) -> torch.Tensor:
    Z, H, M, Dq = Q.shape
    _, _, N, Dv = V.shape
    scale = 1 / math.sqrt(Dq)
    output = torch.empty(Z, H, M, Dv, dtype=Q.dtype, device=Q.device)

    BLOCK_M = 64
    BLOCK_N = 64

    for z in range(Z):
        for h in range(H):
            q = Q[z, h].contiguous()
            k = K[z, h].contiguous()
            v = V[z, h].contiguous()
            o = output[z, h]

            q_stride_m = q.stride(0) * q.element_size()
            q_stride_d = q.stride(1) * q.element_size()
            k_stride_n = k.stride(0) * k.element_size()
            k_stride_d = k.stride(1) * k.element_size()
            v_stride_n = v.stride(0) * v.element_size()
            v_stride_v = v.stride(1) * v.element_size()
            o_stride_m = o.stride(0) * o.element_size()
            o_stride_d = o.stride(1) * o.element_size()

            grid = ( (M + BLOCK_M - 1) // BLOCK_M, )
            flash_kernel[grid](
                q.data_ptr(), k.data_ptr(), v.data_ptr(), o.data_ptr(),
                tl.int32(M), tl.int32(N), tl.int32(Dq), tl.int32(Dv),
                tl.float32(scale), tl.int32(1 if causal else 0),
                tl.int64(q_stride_m), tl.int64(q_stride_d),
                tl.int64(k_stride_n), tl.int64(k_stride_d),
                tl.int64(v_stride_n), tl.int64(v_stride_v),
                tl.int64(o_stride_m), tl.int64(o_stride_d),
                BLOCK_M=BLOCK_M, BLOCK_N=BLOCK_N,
                num_stages=4,
                num_warps=8
            )

    return output
"""
        return {"code": code}
