import torch
import triton
import triton.language as tl
import inspect

@triton.autotune(
    configs=[
        triton.Config({'BLOCK_SIZE_N': 64,  'BLOCK_SIZE_K': 64, 'num_stages': 2, 'num_warps': 4}),
        triton.Config({'BLOCK_SIZE_N': 128, 'BLOCK_SIZE_K': 32, 'num_stages': 2, 'num_warps': 4}),
        triton.Config({'BLOCK_SIZE_N': 256, 'BLOCK_SIZE_K': 32, 'num_stages': 2, 'num_warps': 8}),
        triton.Config({'BLOCK_SIZE_N': 128, 'BLOCK_SIZE_K': 64, 'num_stages': 3, 'num_warps': 8}),
        triton.Config({'BLOCK_SIZE_N': 64,  'BLOCK_SIZE_K': 128,'num_stages': 3, 'num_warps': 8}),
        triton.Config({'BLOCK_SIZE_N': 256, 'BLOCK_SIZE_K': 64, 'num_stages': 3, 'num_warps': 8}),
        triton.Config({'BLOCK_SIZE_N': 128, 'BLOCK_SIZE_K': 128,'num_stages': 4, 'num_warps': 8}),
    ],
    key=['N', 'K'],
)
@triton.jit
def _jsd_fwd_kernel_lse(
    X, W1, B1, W2, B2, LSE1, LSE2,
    M, N, K,
    stride_xm, stride_xk,
    stride_w1k, stride_w1n,
    stride_w2k, stride_w2n,
    stride_b1n, stride_b2n,
    stride_lse1m, stride_lse2m,
    BLOCK_SIZE_N: tl.constexpr, BLOCK_SIZE_K: tl.constexpr,
):
    pid_m = tl.program_id(0)
    
    k_range = tl.arange(0, BLOCK_SIZE_K)
    n_range = tl.arange(0, BLOCK_SIZE_N)
    
    x_ptrs = X + pid_m * stride_xm

    m1, l1 = -float('inf'), 0.0
    m2, l2 = -float('inf'), 0.0

    for n_offset in range(0, N, BLOCK_SIZE_N):
        n_mask = (n_range + n_offset) < N
        
        w1_ptrs = W1 + k_range[:, None] * stride_w1k + (n_range[None, :] + n_offset)
        w2_ptrs = W2 + k_range[:, None] * stride_w2k + (n_range[None, :] + n_offset)
        
        acc1 = tl.zeros((BLOCK_SIZE_N,), dtype=tl.float32)
        acc2 = tl.zeros((BLOCK_SIZE_N,), dtype=tl.float32)

        for k_offset in range(0, K, BLOCK_SIZE_K):
            k_mask = (k_range + k_offset) < K
            x = tl.load(x_ptrs + (k_range + k_offset) * stride_xk, mask=k_mask, other=0.0)
            
            w_mask = k_mask[:, None] & n_mask[None, :]
            w1 = tl.load(w1_ptrs + k_offset * stride_w1k, mask=w_mask, other=0.0)
            w2 = tl.load(w2_ptrs + k_offset * stride_w2k, mask=w_mask, other=0.0)
            
            x_reshaped = tl.reshape(x, (1, BLOCK_SIZE_K))
            acc1 += tl.dot(x_reshaped, w1, allow_tf32=True)[0]
            acc2 += tl.dot(x_reshaped, w2, allow_tf32=True)[0]
        
        b1_ptrs = B1 + n_offset + n_range
        b2_ptrs = B2 + n_offset + n_range
        b1 = tl.load(b1_ptrs, mask=n_mask, other=0.0)
        b2 = tl.load(b2_ptrs, mask=n_mask, other=0.0)
        
        logits1 = acc1 + b1
        logits2 = acc2 + b2
        
        logits1 = tl.where(n_mask, logits1, -float('inf'))
        logits2 = tl.where(n_mask, logits2, -float('inf'))
        
        m1_curr = tl.max(logits1, 0)
        m1_new = tl.maximum(m1, m1_curr)
        l1 = l1 * tl.exp(m1 - m1_new) + tl.sum(tl.exp(logits1 - m1_new), 0)
        m1 = m1_new

        m2_curr = tl.max(logits2, 0)
        m2_new = tl.maximum(m2, m2_curr)
        l2 = l2 * tl.exp(m2 - m2_new) + tl.sum(tl.exp(logits2 - m2_new), 0)
        m2 = m2_new
        
    lse1_val = m1 + tl.log(l1)
    lse2_val = m2 + tl.log(l2)

    tl.store(LSE1 + pid_m * stride_lse1m, lse1_val)
    tl.store(LSE2 + pid_m * stride_lse2m, lse2_val)

@triton.autotune(
    configs=[
        triton.Config({'BLOCK_SIZE_N': 64,  'BLOCK_SIZE_K': 64, 'num_stages': 2, 'num_warps': 4}),
        triton.Config({'BLOCK_SIZE_N': 128, 'BLOCK_SIZE_K': 32, 'num_stages': 2, 'num_warps': 4}),
        triton.Config({'BLOCK_SIZE_N': 256, 'BLOCK_SIZE_K': 32, 'num_stages': 2, 'num_warps': 8}),
        triton.Config({'BLOCK_SIZE_N': 128, 'BLOCK_SIZE_K': 64, 'num_stages': 3, 'num_warps': 8}),
        triton.Config({'BLOCK_SIZE_N': 64,  'BLOCK_SIZE_K': 128,'num_stages': 3, 'num_warps': 8}),
        triton.Config({'BLOCK_SIZE_N': 256, 'BLOCK_SIZE_K': 64, 'num_stages': 3, 'num_warps': 8}),
        triton.Config({'BLOCK_SIZE_N': 128, 'BLOCK_SIZE_K': 128,'num_stages': 4, 'num_warps': 8}),
    ],
    key=['N', 'K'],
)
@triton.jit
def _jsd_fwd_kernel_jsd(
    X, W1, B1, W2, B2, LSE1, LSE2, OUT,
    M, N, K,
    stride_xm, stride_xk,
    stride_w1k, stride_w1n,
    stride_w2k, stride_w2n,
    stride_b1n, stride_b2n,
    stride_lse1m, stride_lse2m,
    stride_outm,
    BLOCK_SIZE_N: tl.constexpr, BLOCK_SIZE_K: tl.constexpr,
):
    pid_m = tl.program_id(0)
    
    lse1 = tl.load(LSE1 + pid_m * stride_lse1m)
    lse2 = tl.load(LSE2 + pid_m * stride_lse2m)
    
    k_range = tl.arange(0, BLOCK_SIZE_K)
    n_range = tl.arange(0, BLOCK_SIZE_N)
    
    x_ptrs = X + pid_m * stride_xm

    hp_acc = 0.0
    hq_acc = 0.0
    hm_acc = 0.0

    for n_offset in range(0, N, BLOCK_SIZE_N):
        n_mask = (n_range + n_offset) < N
        
        w1_ptrs = W1 + k_range[:, None] * stride_w1k + (n_range[None, :] + n_offset)
        w2_ptrs = W2 + k_range[:, None] * stride_w2k + (n_range[None, :] + n_offset)
        
        acc1 = tl.zeros((BLOCK_SIZE_N,), dtype=tl.float32)
        acc2 = tl.zeros((BLOCK_SIZE_N,), dtype=tl.float32)
        
        for k_offset in range(0, K, BLOCK_SIZE_K):
            k_mask = (k_range + k_offset) < K
            x = tl.load(x_ptrs + (k_range + k_offset) * stride_xk, mask=k_mask, other=0.0)
            
            w_mask = k_mask[:, None] & n_mask[None, :]
            w1 = tl.load(w1_ptrs + k_offset * stride_w1k, mask=w_mask, other=0.0)
            w2 = tl.load(w2_ptrs + k_offset * stride_w2k, mask=w_mask, other=0.0)
            
            x_reshaped = tl.reshape(x, (1, BLOCK_SIZE_K))
            acc1 += tl.dot(x_reshaped, w1, allow_tf32=True)[0]
            acc2 += tl.dot(x_reshaped, w2, allow_tf32=True)[0]
            
        b1_ptrs = B1 + n_offset + n_range
        b2_ptrs = B2 + n_offset + n_range
        b1 = tl.load(b1_ptrs, mask=n_mask, other=0.0)
        b2 = tl.load(b2_ptrs, mask=n_mask, other=0.0)

        logits1 = acc1 + b1
        logits2 = acc2 + b2
        
        log_p = logits1 - lse1
        log_q = logits2 - lse2
        p = tl.exp(log_p)
        q = tl.exp(log_q)
        m = 0.5 * (p + q)
        
        p = tl.where(n_mask, p, 0.0)
        q = tl.where(n_mask, q, 0.0)
        m = tl.where(n_mask, m, 0.0)
        log_p = tl.where(n_mask, log_p, 0.0)
        log_q = tl.where(n_mask, log_q, 0.0)

        hp_acc += tl.sum(tl.where(p > 0.0, p * log_p, 0.0))
        hq_acc += tl.sum(tl.where(q > 0.0, q * log_q, 0.0))
        hm_acc += tl.sum(tl.where(m > 0.0, m * tl.log(m), 0.0))
        
    jsd = -hm_acc - 0.5 * (hp_acc + hq_acc)
    tl.store(OUT + pid_m * stride_outm, jsd)

def fused_linear_jsd(X: torch.Tensor, W1: torch.Tensor, B1: torch.Tensor, W2: torch.Tensor, B2: torch.Tensor) -> torch.Tensor:
    M, K = X.shape
    K_W, N = W1.shape
    
    assert X.is_cuda and W1.is_cuda and B1.is_cuda and W2.is_cuda and B2.is_cuda
    assert X.dtype == torch.float16
    assert W1.dtype == torch.float16 and W2.dtype == torch.float16
    assert B1.dtype == torch.float32 and B2.dtype == torch.float32
    assert K == K_W
    
    LSE1 = torch.empty((M,), dtype=torch.float32, device='cuda')
    LSE2 = torch.empty((M,), dtype=torch.float32, device='cuda')
    OUT = torch.empty((M,), dtype=torch.float32, device='cuda')
    
    grid = (M, )

    _jsd_fwd_kernel_lse[grid](
        X, W1, B1, W2, B2, LSE1, LSE2,
        M, N, K,
        X.stride(0), X.stride(1),
        W1.stride(0), W1.stride(1),
        W2.stride(0), W2.stride(1),
        B1.stride(0), B2.stride(0),
        LSE1.stride(0), LSE2.stride(0),
    )
    
    _jsd_fwd_kernel_jsd[grid](
        X, W1, B1, W2, B2, LSE1, LSE2, OUT,
        M, N, K,
        X.stride(0), X.stride(1),
        W1.stride(0), W1.stride(1),
        W2.stride(0), W2.stride(1),
        B1.stride(0), B2.stride(0),
        LSE1.stride(0), LSE2.stride(0),
        OUT.stride(0),
    )
    
    return OUT

class Solution:
    def solve(self, spec_path: str = None) -> dict:
        
        # Get source code of the functions
        imports_code = """
import torch
import triton
import triton.language as tl
"""
        kernel_lse_code = inspect.getsource(_jsd_fwd_kernel_lse)
        kernel_jsd_code = inspect.getsource(_jsd_fwd_kernel_jsd)
        main_func_code = inspect.getsource(fused_linear_jsd)

        # Combine them into a single string
        full_code = f"{imports_code}\n{kernel_lse_code}\n{kernel_jsd_code}\n{main_func_code}"
        
        return {"code": full_code}
