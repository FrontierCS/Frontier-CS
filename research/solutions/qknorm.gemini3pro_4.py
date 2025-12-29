import torch
import triton
import triton.language as tl
import flashinfer

class Solution:
    def solve(self, spec_path: str = None) -> dict:
        code = r"""
import torch
import triton
import triton.language as tl
import flashinfer

@triton.jit
def _qknorm_fused_kernel(
    Q_ptr, K_ptr, W_ptr,
    Q_Out_ptr, K_Out_ptr,
    # Q dims/strides (Inner to Outer)
    q_d0, q_s0, q_d1, q_s1, q_d2, q_s2, q_d3, q_s3,
    # K dims/strides (Inner to Outer)
    k_d0, k_s0, k_d1, k_s1, k_d2, k_s2, k_d3, k_s3,
    n_q_rows, n_k_rows,
    D, eps,
    BLOCK_SIZE: tl.constexpr
):
    pid = tl.program_id(0)
    
    # Determine if processing Q or K
    is_q = pid < n_q_rows
    
    # Variables for offset calc
    # We initialize variables to default to avoid branching complexity, 
    # though branching is used for the logic selection.
    curr_idx = 0
    base_ptr = Q_ptr 
    out_ptr = Q_Out_ptr 
    off = 0
    
    if is_q:
        curr_idx = pid
        base_ptr = Q_ptr
        out_ptr = Q_Out_ptr
        
        # Dim 0 (Inner-most batch dim)
        rem = curr_idx % q_d0
        off += rem * q_s0
        curr_idx = curr_idx // q_d0
        
        # Dim 1
        rem = curr_idx % q_d1
        off += rem * q_s1
        curr_idx = curr_idx // q_d1
        
        # Dim 2
        rem = curr_idx % q_d2
        off += rem * q_s2
        curr_idx = curr_idx // q_d2
        
        # Dim 3
        rem = curr_idx % q_d3
        off += rem * q_s3
        
    else:
        curr_idx = pid - n_q_rows
        base_ptr = K_ptr
        out_ptr = K_Out_ptr
        
        # Dim 0
        rem = curr_idx % k_d0
        off += rem * k_s0
        curr_idx = curr_idx // k_d0
        
        # Dim 1
        rem = curr_idx % k_d1
        off += rem * k_s1
        curr_idx = curr_idx // k_d1
        
        # Dim 2
        rem = curr_idx % k_d2
        off += rem * k_s2
        curr_idx = curr_idx // k_d2
        
        # Dim 3
        rem = curr_idx % k_d3
        off += rem * k_s3
    
    # RMSNorm Logic
    cols = tl.arange(0, BLOCK_SIZE)
    mask = cols < D
    
    # Load Input
    # Assumes last dim stride is 1 (contiguous), which is standard for Q/K fusion
    x_ptr = base_ptr + off + cols
    x = tl.load(x_ptr, mask=mask, other=0.0).to(tl.float32)
    
    # Compute stats
    x_sq = x * x
    sum_sq = tl.sum(x_sq, axis=0)
    mean_sq = sum_sq / D
    rstd = 1.0 / tl.sqrt(mean_sq + eps)
    
    # Load Weight
    w = tl.load(W_ptr + cols, mask=mask, other=0.0).to(tl.float32)
    
    # Normalize
    y = x * rstd * w
    
    # Store Output
    # Output is contiguous, so row offset is just index * D
    store_row_idx = pid if is_q else (pid - n_q_rows)
    out_row_ptr = out_ptr + store_row_idx * D + cols
    tl.store(out_row_ptr, y, mask=mask)

def _get_layout(t):
    # Analyzes tensor layout to support efficient non-contiguous access
    # Returns dimensions and strides collapsed where possible, ordered Inner->Outer
    shape = t.shape
    strides = t.stride()
    
    # If only D dim
    if len(shape) < 2:
        return [1], [0]
    
    dims = []
    strs = []
    
    # Start analysis from the inner-most batch dimension (excluding D)
    curr_d = shape[-2]
    curr_s = strides[-2]
    
    # Collapse contiguous dimensions
    for i in range(len(shape)-3, -1, -1):
        d = shape[i]
        s = strides[i]
        if s == curr_d * curr_s:
            curr_d *= d
        else:
            dims.append(curr_d)
            strs.append(curr_s)
            curr_d = d
            curr_s = s
    dims.append(curr_d)
    strs.append(curr_s)
    
    return dims, strs

def qknorm(q: torch.Tensor, k: torch.Tensor, norm_weight: torch.Tensor):
    D = q.shape[-1]
    
    # Allocate outputs (contiguous)
    # Using empty is faster than zeros/empty_like if we fill it
    q_o = torch.empty(q.shape, device=q.device, dtype=q.dtype)
    k_o = torch.empty(k.shape, device=k.device, dtype=k.dtype)
    
    # Analyze layout for non-contiguous support
    q_dims, q_strs = _get_layout(q)
    k_dims, k_strs = _get_layout(k)
    
    # Pad layout descriptions to 4 dimensions for the kernel
    def pad(d, s):
        pd = d + [1]*(4-len(d))
        ps = s + [0]*(4-len(s))
        return pd, ps
        
    q_d, q_s = pad(q_dims, q_strs)
    k_d, k_s = pad(k_dims, k_strs)
    
    # Calculate total logical rows
    n_q = 1
    for x in q_dims: n_q *= x
    n_k = 1
    for x in k_dims: n_k *= x
    
    # Launch Fused Kernel (handles both Q and K in one launch)
    grid = (n_q + n_k,)
    BLOCK_SIZE = triton.next_power_of_2(D)
    
    # Using small epsilon consistent with typical RMSNorm usage (e.g. Llama)
    # If FlashInfer defaults differ, 1e-6 is generally safe/standard
    
    _qknorm_fused_kernel[grid](
        q, k, norm_weight,
        q_o, k_o,
        q_d[0], q_s[0], q_d[1], q_s[1], q_d[2], q_s[2], q_d[3], q_s[3],
        k_d[0], k_s[0], k_d[1], k_s[1], k_d[2], k_s[2], k_d[3], k_s[3],
        n_q, n_k,
        D, 1e-6,
        BLOCK_SIZE=BLOCK_SIZE,
        num_warps=4 if D <= 256 else 8
    )
    
    return q_o, k_o
"""
        return {"code": code}