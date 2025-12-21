import torch
import triton
import triton.language as tl

class Solution:
    def solve(self, spec_path: str = None) -> dict:
        return {
            "code": """import torch
import triton
import triton.language as tl

@triton.autotune(
    configs=[
        triton.Config({'BLOCK_M': 16, 'BLOCK_N': 64,  'BLOCK_K': 64, 'GROUP_SIZE_M': 8}, num_stages=4, num_warps=4),
        triton.Config({'BLOCK_M': 32, 'BLOCK_N': 64,  'BLOCK_K': 32, 'GROUP_SIZE_M': 8}, num_stages=4, num_warps=4),
        triton.Config({'BLOCK_M': 32, 'BLOCK_N': 32,  'BLOCK_K': 32, 'GROUP_SIZE_M': 8}, num_stages=4, num_warps=4),
        triton.Config({'BLOCK_M': 32, 'BLOCK_N': 128, 'BLOCK_K': 32, 'GROUP_SIZE_M': 8}, num_stages=3, num_warps=8),
        triton.Config({'BLOCK_M': 16, 'BLOCK_N': 128, 'BLOCK_K': 64, 'GROUP_SIZE_M': 8}, num_stages=3, num_warps=8),
        triton.Config({'BLOCK_M': 16, 'BLOCK_N': 32,  'BLOCK_K': 128,'GROUP_SIZE_M': 8}, num_stages=3, num_warps=4),
        triton.Config({'BLOCK_M': 64, 'BLOCK_N': 64,  'BLOCK_K': 32, 'GROUP_SIZE_M': 8}, num_stages=4, num_warps=4),
        triton.Config({'BLOCK_M': 64, 'BLOCK_N': 32,  'BLOCK_K': 64, 'GROUP_SIZE_M': 8}, num_stages=4, num_warps=4),
        triton.Config({'BLOCK_M': 32, 'BLOCK_N': 64,  'BLOCK_K': 64, 'GROUP_SIZE_M': 8}, num_stages=3, num_warps=8),
        triton.Config({'BLOCK_M': 16, 'BLOCK_N': 256, 'BLOCK_K': 32, 'GROUP_SIZE_M': 8}, num_stages=3, num_warps=8),
        triton.Config({'BLOCK_M': 16, 'BLOCK_N': 256, 'BLOCK_K': 64, 'GROUP_SIZE_M': 4}, num_stages=3, num_warps=8),
    ],
    key=['M', 'N', 'K'],
)
@triton.jit
def _jsd_fwd_kernel(
    X, W1, B1, W2, B2, Out, LSE,
    M, N, K,
    stride_xm, stride_xk,
    stride_w1k, stride_w1n,
    stride_w2k, stride_w2n,
    stride_lsem,
    IS_PASS_1: tl.constexpr,
    BLOCK_M: tl.constexpr, BLOCK_N: tl.constexpr, BLOCK_K: tl.constexpr,
    GROUP_SIZE_M: tl.constexpr,
):
    pid = tl.program_id(axis=0)
    num_pid_m = tl.cdiv(M, BLOCK_M)
    num_pid_in_group = GROUP_SIZE_M
    group_id = pid // num_pid_in_group
    first_pid_m = group_id * num_pid_in_group
    group_size = min(num_pid_m - first_pid_m, num_pid_in_group)
    pid_m = first_pid_m + (pid % group_size)

    m_offsets = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
    m_mask = m_offsets < M
    
    # Using float literal for -inf to be JIT-friendly
    neg_inf = -3.4028234663852886e+38

    if IS_PASS_1:
        max1 = tl.full([BLOCK_M], neg_inf, dtype=tl.float32)
        sum_exp1 = tl.zeros([BLOCK_M], dtype=tl.float32)
        max2 = tl.full([BLOCK_M], neg_inf, dtype=tl.float32)
        sum_exp2 = tl.zeros([BLOCK_M], dtype=tl.float32)
    else: # pass 2
        lse_base_ptr = LSE + m_offsets * stride_lsem
        max1 = tl.load(lse_base_ptr, mask=m_mask, other=0.0)
        sum1 = tl.load(lse_base_ptr + 1, mask=m_mask, other=0.0)
        max2 = tl.load(lse_base_ptr + 2, mask=m_mask, other=0.0)
        sum2 = tl.load(lse_base_ptr + 3, mask=m_mask, other=0.0)
        lse1 = max1 + tl.log(sum1)
        lse2 = max2 + tl.log(sum2)
        jsd = tl.zeros([BLOCK_M], dtype=tl.float32)

    for n_offset_idx in range(0, tl.cdiv(N, BLOCK_N)):
        n_offsets = n_offset_idx * BLOCK_N + tl.arange(0, BLOCK_N)
        n_mask = n_offsets < N

        acc1 = tl.zeros([BLOCK_M, BLOCK_N], dtype=tl.float32)
        acc2 = tl.zeros([BLOCK_M, BLOCK_N], dtype=tl.float32)

        for k_offset_idx in range(0, tl.cdiv(K, BLOCK_K)):
            k_offsets = k_offset_idx * BLOCK_K + tl.arange(0, BLOCK_K)
            k_mask = k_offsets < K

            x_ptrs = X + m_offsets[:, None] * stride_xm + k_offsets[None, :] * stride_xk
            w1_ptrs = W1 + k_offsets[:, None] * stride_w1k + n_offsets[None, :] * stride_w1n
            w2_ptrs = W2 + k_offsets[:, None] * stride_w2k + n_offsets[None, :] * stride_w2n
            
            x = tl.load(x_ptrs, mask=m_mask[:, None] & k_mask[None, :], other=0.0)
            w1 = tl.load(w1_ptrs, mask=k_mask[:, None] & n_mask[None, :], other=0.0)
            w2 = tl.load(w2_ptrs, mask=k_mask[:, None] & n_mask[None, :], other=0.0)
            
            acc1 += tl.dot(x, w1)
            acc2 += tl.dot(x, w2)
        
        b1 = tl.load(B1 + n_offsets, mask=n_mask, other=0.0)
        b2 = tl.load(B2 + n_offsets, mask=n_mask, other=0.0)

        logits1 = acc1 + b1[None, :]
        logits2 = acc2 + b2[None, :]

        if IS_PASS_1:
            tile_max1 = tl.max(tl.where(n_mask[None, :], logits1, neg_inf), axis=1)
            new_max1 = tl.maximum(max1, tile_max1)
            exp_term_old1 = tl.exp(max1 - new_max1)
            exp_term_old1 = tl.where(max1 == neg_inf, 0, exp_term_old1)
            sum_exp1 = sum_exp1 * exp_term_old1
            exp_term_new1 = tl.exp(logits1 - new_max1[:, None])
            sum_exp1 += tl.sum(tl.where(n_mask[None, :], exp_term_new1, 0.0), axis=1)
            max1 = new_max1

            tile_max2 = tl.max(tl.where(n_mask[None, :], logits2, neg_inf), axis=1)
            new_max2 = tl.maximum(max2, tile_max2)
            exp_term_old2 = tl.exp(max2 - new_max2)
            exp_term_old2 = tl.where(max2 == neg_inf, 0, exp_term_old2)
            sum_exp2 = sum_exp2 * exp_term_old2
            exp_term_new2 = tl.exp(logits2 - new_max2[:, None])
            sum_exp2 += tl.sum(tl.where(n_mask[None, :], exp_term_new2, 0.0), axis=1)
            max2 = new_max2
        else: # pass 2
            logp = logits1 - lse1[:, None]
            logq = logits2 - lse2[:, None]

            p = tl.exp(logp)
            q = tl.exp(logq)
            m = 0.5 * (p + q)
            logm = tl.log(m)

            kl_p_m = p * (logp - logm)
            kl_q_m = q * (logq - logm)

            jsd_tile = 0.5 * (kl_p_m + kl_q_m)
            jsd += tl.sum(tl.where(n_mask[None, :], jsd_tile, 0.0), axis=1)

    if IS_PASS_1:
        lse_base_ptr = LSE + m_offsets * stride_lsem
        tl.store(lse_base_ptr, max1, mask=m_mask)
        tl.store(lse_base_ptr + 1, sum_exp1, mask=m_mask)
        tl.store(lse_base_ptr + 2, max2, mask=m_mask)
        tl.store(lse_base_ptr + 3, sum_exp2, mask=m_mask)
    else:
        tl.store(Out + m_offsets, jsd, mask=m_mask)

def fused_linear_jsd(X: torch.Tensor, W1: torch.Tensor, B1: torch.Tensor, W2: torch.Tensor, B2: torch.Tensor) -> torch.Tensor:
    M, K = X.shape
    _K1, N = W1.shape
    assert K == _K1, "Input dimension mismatch"
    
    out = torch.empty(M, device=X.device, dtype=torch.float32)
    lse_inter = torch.empty((M, 4), device=X.device, dtype=torch.float32)

    grid = lambda META: (triton.cdiv(M, META['BLOCK_M']),)

    # Pass 1: Compute LogSumExp intermediates
    _jsd_fwd_kernel[grid](
        X, W1, B1, W2, B2, 
        out, lse_inter,
        M, N, K,
        X.stride(0), X.stride(1),
        W1.stride(0), W1.stride(1),
        W2.stride(0), W2.stride(1),
        lse_inter.stride(0),
        IS_PASS_1=True
    )
    
    # Pass 2: Compute JSD
    _jsd_fwd_kernel[grid](
        X, W1, B1, W2, B2, 
        out, lse_inter,
        M, N, K,
        X.stride(0), X.stride(1),
        W1.stride(0), W1.stride(1),
        W2.stride(0), W2.stride(1),
        lse_inter.stride(0),
        IS_PASS_1=False
    )
    return out
"""
        }
