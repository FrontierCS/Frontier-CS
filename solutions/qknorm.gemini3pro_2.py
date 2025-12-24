import torch
import flashinfer

class Solution:
    def solve(self, spec_path: str = None) -> dict:
        return {
            "code": r"""
import torch
import triton
import triton.language as tl
import flashinfer

@triton.jit
def _rmsnorm_kernel(
    X_ptr, Y_ptr, W_ptr,
    s0, s1, s2, s3, s4, s5,
    d0, d1, d2, d3, d4, d5,
    stride_x_last,
    N, eps,
    BLOCK_SIZE: tl.constexpr
):
    pid = tl.program_id(0)
    
    # Decompose linear index 'pid' into 6 dimensions to handle arbitrary strides
    # d5 is the innermost batch dimension
    r = pid
    i5 = r % d5; r = r // d5
    i4 = r % d4; r = r // d4
    i3 = r % d3; r = r // d3
    i2 = r % d2; r = r // d2
    i1 = r % d1; r = r // d1
    i0 = r

    # Compute memory offset for the start of the row
    # Supports non-contiguous inputs by using explicit strides
    off = i0*s0 + i1*s1 + i2*s2 + i3*s3 + i4*s4 + i5*s5
    
    # Pointers
    offs = tl.arange(0, BLOCK_SIZE)
    mask = offs < N
    
    # Load input x and weight w
    # Supports non-contiguous last dimension via stride_x_last
    x_ptr = X_ptr + off + offs * stride_x_last
    w_ptr = W_ptr + offs
    
    # Load and cast to float32 for precision
    x = tl.load(x_ptr, mask=mask, other=0.0).to(tl.float32)
    w = tl.load(w_ptr, mask=mask, other=0.0).to(tl.float32)
    
    # RMSNorm computation
    x_sq = x * x
    mean_sq = tl.sum(x_sq, axis=0) / N
    rstd = tl.math.rsqrt(mean_sq + eps)
    y = x * rstd * w
    
    # Store output
    # Output Y is allocated as contiguous, so we can use linear addressing
    y_ptr = Y_ptr + pid * N + offs
    tl.store(y_ptr, y, mask=mask)

def qknorm(q: torch.Tensor, k: torch.Tensor, norm_weight: torch.Tensor):
    # Allocate contiguous output tensors
    q_out = torch.empty(q.shape, device=q.device, dtype=q.dtype)
    k_out = torch.empty(k.shape, device=k.device, dtype=k.dtype)
    
    # FlashInfer uses 1e-6 by default usually, matching standard RMSNorm
    eps = 1e-6

    def launch(x, out, w):
        N = x.shape[-1]
        bs = x.shape[:-1]
        
        # Handle tensors with rank > 7 (6 batch dims + 1 hidden) via fallback
        if len(bs) > 6:
            x_cont = x.contiguous().view(-1, N)
            out_view = out.view(-1, N)
            flashinfer.norm.rmsnorm(x_cont, w, out=out_view, eps=eps)
            return

        # Prepare strides and shapes for the kernel
        # We map the input batch dimensions to 6 fixed dimensions
        bstr = x.stride()[:-1]
        str_last = x.stride()[-1]
        
        pad = 6 - len(bs)
        # Pad shapes with 1 and strides with 0
        s = (0,) * pad + bstr
        d = (1,) * pad + bs
        
        total_rows = 1
        for v in bs: total_rows *= v
        
        BLOCK_SIZE = triton.next_power_of_2(N)
        num_warps = 4
        if BLOCK_SIZE >= 2048: num_warps = 8
        if BLOCK_SIZE >= 4096: num_warps = 16
        
        _rmsnorm_kernel[(total_rows,)](
            x, out, w,
            s[0], s[1], s[2], s[3], s[4], s[5],
            d[0], d[1], d[2], d[3], d[4], d[5],
            str_last,
            N, eps,
            BLOCK_SIZE=BLOCK_SIZE,
            num_warps=num_warps
        )

    launch(q, q_out, norm_weight)
    launch(k, k_out, norm_weight)
    
    return q_out, k_out
"""
        }
