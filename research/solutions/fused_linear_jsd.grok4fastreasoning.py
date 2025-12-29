import torch
import triton
import triton.language as tl

class Solution:
    def solve(self, spec_path: str = None) -> dict:
        code = '''
import torch
import triton
import triton.language as tl

def fused_linear_jsd(X: torch.Tensor, W1: torch.Tensor, B1: torch.Tensor, W2: torch.Tensor, B2: torch.Tensor) -> torch.Tensor:
    X = X.contiguous()
    W1 = W1.contiguous()
    B1 = B1.contiguous()
    W2 = W2.contiguous()
    B2 = B2.contiguous()
    M, K = X.shape
    _, N = W1.shape
    output = torch.empty((M,), dtype=torch.float32, device=X.device)
    MAX_K = 2048
    MAX_N = 4096
    BLOCK_SIZE = 1024

    @triton.jit
    def compute_jsd_kernel(
        x_ptr, w1_ptr, b1_ptr, w2_ptr, b2_ptr, output_ptr,
        M, K, N,
        BLOCK_SIZE: tl.constexpr,
        MAX_K: tl.constexpr,
        MAX_N: tl.constexpr
    ):
        pid = tl.program_id(0)
        if pid >= M:
            return

        shared_x = tl.empty((MAX_K,), dtype=tl.float16, block="shared")
        shared_w = tl.empty((MAX_N,), dtype=tl.float16, block="shared")
        sh_logits1 = tl.empty((MAX_N,), dtype=tl.float32, block="shared")
        sh_logits2 = tl.empty((MAX_N,), dtype=tl.float32, block="shared")

        # zero sh_logits1
        num_chunks = (N + BLOCK_SIZE - 1) // BLOCK_SIZE
        for chunk_i in range(num_chunks):
            offs = chunk_i * BLOCK_SIZE + tl.arange(0, BLOCK_SIZE)
            mask = offs < N
            z = tl.zeros((BLOCK_SIZE,), dtype=tl.float32)
            byte_offs = offs.to(tl.int32) * 4
            tl.store(sh_logits1 + byte_offs, z, mask=mask)

        # zero sh_logits2
        for chunk_i in range(num_chunks):
            offs = chunk_i * BLOCK_SIZE + tl.arange(0, BLOCK_SIZE)
            mask = offs < N
            z = tl.zeros((BLOCK_SIZE,), dtype=tl.float32)
            byte_offs = offs.to(tl.int32) * 4
            tl.store(sh_logits2 + byte_offs, z, mask=mask)

        # load shared_x
        x_row_start = pid * (K * 2)
        num_chunks_x = (K + BLOCK_SIZE - 1) // BLOCK_SIZE
        for chunk_i in range(num_chunks_x):
            offs_k = chunk_i * BLOCK_SIZE + tl.arange(0, BLOCK_SIZE)
            mask = offs_k < K
            byte_offs = offs_k.to(tl.int32) * 2
            x_chunk = tl.load(x_ptr + x_row_start + byte_offs, mask=mask, other=0.0)
            x_store_offs = offs_k.to(tl.int32) * 2
            tl.store(shared_x + x_store_offs, x_chunk, mask=mask)

        # main loop over k
        w_row_stride_bytes = N * 2
        logits_stride_bytes = 4
        w_stride_bytes = 2
        for k in range(K):
            k_byte = k * 2
            xk = tl.load(shared_x + k_byte)
            xk_f32 = tl.cast(xk, tl.float32)

            # load shared_w with W1[k]
            w1_row_start = w1_ptr + k * w_row_stride_bytes
            for chunk_i in range(num_chunks):
                offs_n = chunk_i * BLOCK_SIZE + tl.arange(0, BLOCK_SIZE)
                mask = offs_n < N
                byte_offs = offs_n.to(tl.int32) * w_stride_bytes
                w_chunk = tl.load(w1_row_start + byte_offs, mask=mask, other=0.0)
                w_store_offs = offs_n.to(tl.int32) * w_stride_bytes
                tl.store(shared_w + w_store_offs, w_chunk, mask=mask)

            # add to sh_logits1
            for chunk_i in range(num_chunks):
                offs_n = chunk_i * BLOCK_SIZE + tl.arange(0, BLOCK_SIZE)
                mask = offs_n < N
                byte_offs_w = offs_n.to(tl.int32) * w_stride_bytes
                w_chunk_f16 = tl.load(shared_w + byte_offs_w, mask=mask, other=0.0)
                w_chunk_f32 = tl.cast(w_chunk_f16, tl.float32)
                prod = xk_f32 * w_chunk_f32
                byte_offs_l = offs_n.to(tl.int32) * logits_stride_bytes
                l_chunk = tl.load(sh_logits1 + byte_offs_l, mask=mask, other=0.0)
                tl.store(sh_logits1 + byte_offs_l, l_chunk + prod, mask=mask)

            # load shared_w with W2[k]
            w2_row_start = w2_ptr + k * w_row_stride_bytes
            for chunk_i in range(num_chunks):
                offs_n = chunk_i * BLOCK_SIZE + tl.arange(0, BLOCK_SIZE)
                mask = offs_n < N
                byte_offs = offs_n.to(tl.int32) * w_stride_bytes
                w_chunk = tl.load(w2_row_start + byte_offs, mask=mask, other=0.0)
                w_store_offs = offs_n.to(tl.int32) * w_stride_bytes
                tl.store(shared_w + w_store_offs, w_chunk, mask=mask)

            # add to sh_logits2
            for chunk_i in range(num_chunks):
                offs_n = chunk_i * BLOCK_SIZE + tl.arange(0, BLOCK_SIZE)
                mask = offs_n < N
                byte_offs_w = offs_n.to(tl.int32) * w_stride_bytes
                w_chunk_f16 = tl.load(shared_w + byte_offs_w, mask=mask, other=0.0)
                w_chunk_f32 = tl.cast(w_chunk_f16, tl.float32)
                prod = xk_f32 * w_chunk_f32
                byte_offs_l = offs_n.to(tl.int32) * logits_stride_bytes
                l_chunk = tl.load(sh_logits2 + byte_offs_l, mask=mask, other=0.0)
                tl.store(sh_logits2 + byte_offs_l, l_chunk + prod, mask=mask)

        # add B1 to sh_logits1
        b_stride_bytes = 4
        for chunk_i in range(num_chunks):
            offs_n = chunk_i * BLOCK_SIZE + tl.arange(0, BLOCK_SIZE)
            mask = offs_n < N
            byte_offs_b = offs_n.to(tl.int32) * b_stride_bytes
            b_chunk = tl.load(b1_ptr + byte_offs_b, mask=mask, other=0.0)
            byte_offs_l = offs_n.to(tl.int32) * logits_stride_bytes
            l_chunk = tl.load(sh_logits1 + byte_offs_l, mask=mask, other=0.0)
            tl.store(sh_logits1 + byte_offs_l, l_chunk + b_chunk, mask=mask)

        # add B2 to sh_logits2
        for chunk_i in range(num_chunks):
            offs_n = chunk_i * BLOCK_SIZE + tl.arange(0, BLOCK_SIZE)
            mask = offs_n < N
            byte_offs_b = offs_n.to(tl.int32) * b_stride_bytes
            b_chunk = tl.load(b2_ptr + byte_offs_b, mask=mask, other=0.0)
            byte_offs_l = offs_n.to(tl.int32) * logits_stride_bytes
            l_chunk = tl.load(sh_logits2 + byte_offs_l, mask=mask, other=0.0)
            tl.store(sh_logits2 + byte_offs_l, l_chunk + b_chunk, mask=mask)

        # compute lse1
        max1 = -100000.0
        for chunk_i in range(num_chunks):
            offs_n = chunk_i * BLOCK_SIZE + tl.arange(0, BLOCK_SIZE)
            mask = offs_n < N
            byte_offs = offs_n.to(tl.int32) * 4
            chunk_vals = tl.load(sh_logits1 + byte_offs, mask=mask, other=-100000.0)
            chunk_max = tl.max(chunk_vals, axis=0)
            max1 = tl.maximum(max1, chunk_max)
        sum_exp1 = 0.0
        for chunk_i in range(num_chunks):
            offs_n = chunk_i * BLOCK_SIZE + tl.arange(0, BLOCK_SIZE)
            mask = offs_n < N
            byte_offs = offs_n.to(tl.int32) * 4
            chunk_vals = tl.load(sh_logits1 + byte_offs, mask=mask, other=0.0)
            chunk_exp = tl.exp(chunk_vals - max1)
            sum_exp1 += tl.sum(chunk_exp, axis=0)
        lse1 = tl.where(sum_exp1 > 0, max1 + tl.log(sum_exp1), max1)

        # compute lse2
        max2 = -100000.0
        for chunk_i in range(num_chunks):
            offs_n = chunk_i * BLOCK_SIZE + tl.arange(0, BLOCK_SIZE)
            mask = offs_n < N
            byte_offs = offs_n.to(tl.int32) * 4
            chunk_vals = tl.load(sh_logits2 + byte_offs, mask=mask, other=-100000.0)
            chunk_max = tl.max(chunk_vals, axis=0)
            max2 = tl.maximum(max2, chunk_max)
        sum_exp2 = 0.0
        for chunk_i in range(num_chunks):
            offs_n = chunk_i * BLOCK_SIZE + tl.arange(0, BLOCK_SIZE)
            mask = offs_n < N
            byte_offs = offs_n.to(tl.int32) * 4
            chunk_vals = tl.load(sh_logits2 + byte_offs, mask=mask, other=0.0)
            chunk_exp = tl.exp(chunk_vals - max2)
            sum_exp2 += tl.sum(chunk_exp, axis=0)
        lse2 = tl.where(sum_exp2 > 0, max2 + tl.log(sum_exp2), max2)

        # compute JSD
        jsd = 0.0
        for chunk_i in range(num_chunks):
            offs_n = chunk_i * BLOCK_SIZE + tl.arange(0, BLOCK_SIZE)
            mask = offs_n < N
            byte_offs = offs_n.to(tl.int32) * 4
            l1_chunk = tl.load(sh_logits1 + byte_offs, mask=mask, other=0.0)
            l2_chunk = tl.load(sh_logits2 + byte_offs, mask=mask, other=0.0)
            p_chunk = tl.exp(l1_chunk - lse1)
            q_chunk = tl.exp(l2_chunk - lse2)
            m_chunk = 0.5 * (p_chunk + q_chunk)
            log_p_m = tl.where(p_chunk > 0, tl.log(p_chunk / m_chunk), 0.0)
            kl_p = p_chunk * log_p_m
            log_q_m = tl.where(q_chunk > 0, tl.log(q_chunk / m_chunk), 0.0)
            kl_q = q_chunk * log_q_m
            contrib = 0.5 * (kl_p + kl_q)
            jsd += tl.sum(contrib, axis=0)

        tl.store(output_ptr + pid * 4, jsd)

    compute_jsd_kernel[(M,)](x_ptr=X.data_ptr(), w1_ptr=W1.data_ptr(), b1_ptr=B1.data_ptr(),
                             w2_ptr=W2.data_ptr(), b2_ptr=B2.data_ptr(), output_ptr=output.data_ptr(),
                             M=M, K=K, N=N,
                             BLOCK_SIZE=BLOCK_SIZE, MAX_K=MAX_K, MAX_N=MAX_N)
    return output
        '''
        return {"code": code}