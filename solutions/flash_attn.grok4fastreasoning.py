import torch
import triton
import triton.language as tl
import math

def flash_attn(Q: torch.Tensor, K: torch.Tensor, V: torch.Tensor, causal: bool = True) -> torch.Tensor:
    Z, H, M, Dq = Q.shape
    _, _, N, Dv = V.shape
    output = torch.empty(Z, H, M, Dv, dtype=Q.dtype, device=Q.device)
    scale = 1.0 / math.sqrt(Dq)
    BLOCK_M = 64
    BLOCK_N = 64

    @triton.jit
    def kernel(
        q_ptr, k_ptr, v_ptr, o_ptr,
        M: tl.int32, N: tl.int32, Dq: tl.int32, Dv: tl.int32,
        scale: tl.float32, causal_i: tl.int32,
        BLOCK_M: tl.constexpr, BLOCK_N: tl.constexpr
    ):
        pid_m = tl.program_id(0)
        block_start = pid_m * BLOCK_M
        if block_start >= M:
            return
        offs_m = block_start + tl.arange(0, BLOCK_M)

        # Load Q block
        q_block_ptr = tl.make_block_ptr(
            base=q_ptr + block_start * Dq,
            shape=(BLOCK_M, Dq),
            strides=(Dq, 1),
            block_shape=(BLOCK_M, Dq),
            order=(1, 0)
        )
        q = tl.load(q_block_ptr).to(tl.float32)

        # Initialize stats
        INITIAL_M = -1e9
        m_i = tl.full([BLOCK_M], INITIAL_M, dtype=tl.float32)
        l_i = tl.zeros([BLOCK_M], dtype=tl.float32)
        o_i = tl.zeros([BLOCK_M, Dv], dtype=tl.float32)

        # Loop over K/V blocks
        for start_n in range(0, N, BLOCK_N):
            if causal_i and start_n >= block_start + BLOCK_M:
                break

            # Load K block
            k_block_ptr = tl.make_block_ptr(
                base=k_ptr + start_n * Dq,
                shape=(BLOCK_N, Dq),
                strides=(Dq, 1),
                block_shape=(BLOCK_N, Dq),
                order=(1, 0)
            )
            k = tl.load(k_block_ptr).to(tl.float32)

            # Load V block
            v_block_ptr = tl.make_block_ptr(
                base=v_ptr + start_n * Dv,
                shape=(BLOCK_N, Dv),
                strides=(Dv, 1),
                block_shape=(BLOCK_N, Dv),
                order=(1, 0)
            )
            v = tl.load(v_block_ptr).to(tl.float32)

            # Compute attention scores
            s = tl.dot(q, tl.trans(k)) * scale

            # Causal mask for diagonal block
            if causal_i and start_n == block_start:
                i_idx = tl.arange(0, BLOCK_M)
                j_idx = tl.arange(0, BLOCK_N)
                mask = j_idx[None, :] > i_idx[:, None]
                s = tl.where(mask, INITIAL_M, s)

            # Online softmax update
            m_loc = tl.max(s, axis=1)
            p = tl.exp(s - m_loc[:, None])
            sum_p = tl.sum(p, axis=1)
            m_new = tl.maximum(m_i, m_loc)
            exp_delta = tl.exp(m_i - m_new)
            l_new = exp_delta * l_i + sum_p
            o_new = exp_delta[:, None] * o_i + tl.dot(p, v)
            m_i = m_new
            l_i = l_new
            o_i = o_new

        # Normalize and store
        row_scale = 1.0 / l_i
        o_final = o_i * row_scale[:, None]

        o_block_ptr = tl.make_block_ptr(
            base=o_ptr + block_start * Dv,
            shape=(BLOCK_M, Dv),
            strides=(Dv, 1),
            block_shape=(BLOCK_M, Dv),
            order=(1, 0)
        )
        tl.store(o_block_ptr, o_final.to(tl.float16))

    num_qblocks = M // BLOCK_M
    for z in range(Z):
        for h in range(H):
            q_ptr = int(Q.data_ptr() + z * Q.stride(0) + h * Q.stride(1))
            k_ptr = int(K.data_ptr() + z * K.stride(0) + h * K.stride(1))
            v_ptr = int(V.data_ptr() + z * V.stride(0) + h * V.stride(1))
            o_ptr = int(output.data_ptr() + z * output.stride(0) + h * output.stride(1))

            grid = (num_qblocks,)
            kernel[grid](
                q_ptr, k_ptr, v_ptr, o_ptr,
                M, N, Dq, Dv, scale, int(causal),
                BLOCK_M=BLOCK_M, BLOCK_N=BLOCK_N
            )
    return output
