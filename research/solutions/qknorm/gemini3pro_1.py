import torch
import flashinfer
import triton
import triton.language as tl

class Solution:
    def solve(self, spec_path: str = None) -> dict:
        return {"code": self.code()}

    def code(self):
        return """
import torch
import flashinfer
import triton
import triton.language as tl

@triton.jit
def _fused_qknorm_kernel(
    Q_ptr, K_ptr, W_ptr,
    Q_out_ptr, K_out_ptr,
    stride_q_row, stride_k_row,
    stride_q_out_row, stride_k_out_row,
    N_q, N_k, D,
    eps,
    BLOCK_SIZE: tl.constexpr
):
    pid = tl.program_id(0)
    
    # Determine if we are processing Q (0..N_q-1) or K (N_q..N_q+N_k-1)
    if pid < N_q:
        # Process Query
        row_idx = pid
        # Calculate pointers
        row_start_ptr = Q_ptr + row_idx * stride_q_row
        out_start_ptr = Q_out_ptr + row_idx * stride_q_out_row
        
        # Load Q row
        cols = tl.arange(0, BLOCK_SIZE)
        mask = cols < D
        x_ptr = row_start_ptr + cols
        x = tl.load(x_ptr, mask=mask, other=0.0).to(tl.float32)
        
        # Compute RMSNorm
        # x_norm = x * w / sqrt(mean(x^2) + eps)
        var = tl.sum(x * x, axis=0) / D
        rstd = 1 / tl.sqrt(var + eps)
        
        # Load weight
        w_ptr = W_ptr + cols
        w = tl.load(w_ptr, mask=mask, other=0.0).to(tl.float32)
        
        # Normalize and scale
        y = x * rstd * w
        
        # Store
        tl.store(out_start_ptr + cols, y, mask=mask)
        
    else:
        # Process Key
        row_idx = pid - N_q
        
        # Calculate pointers
        row_start_ptr = K_ptr + row_idx * stride_k_row
        out_start_ptr = K_out_ptr + row_idx * stride_k_out_row
        
        # Load K row
        cols = tl.arange(0, BLOCK_SIZE)
        mask = cols < D
        x_ptr = row_start_ptr + cols
        x = tl.load(x_ptr, mask=mask, other=0.0).to(tl.float32)
        
        # Compute RMSNorm
        var = tl.sum(x * x, axis=0) / D
        rstd = 1 / tl.sqrt(var + eps)
        
        # Load weight (same weight for Q and K)
        w_ptr = W_ptr + cols
        w = tl.load(w_ptr, mask=mask, other=0.0).to(tl.float32)
        
        # Normalize and scale
        y = x * rstd * w
        
        # Store
        tl.store(out_start_ptr + cols, y, mask=mask)

def qknorm(q: torch.Tensor, k: torch.Tensor, norm_weight: torch.Tensor):
    # Flatten Q and K to (N, D) while preserving the last dimension D.
    # We attempt to create a view. If not contiguous in memory logic, we use reshape (copy).
    # To maximize performance on strided inputs, we'd ideally handle strides in kernel,
    # but the fused launch + triton overhead reduction is the primary gain here.
    
    # Check if last dimension is contiguous (stride 1) for optimal vector load
    # If q or k are not last-dim contiguous, we force contiguous.
    if q.stride(-1) != 1:
        q = q.contiguous()
    if k.stride(-1) != 1:
        k = k.contiguous()
        
    # Reshape to 2D: (Total_Rows, Hidden_Dim)
    # We use reshape() which returns a view if possible, or a copy if needed.
    # Since we ensured last dim is contiguous, view logic often works if dims are packed.
    # If not packed (gaps between rows), reshape might copy.
    q_2d = q.reshape(-1, q.shape[-1])
    k_2d = k.reshape(-1, k.shape[-1])
    
    # We must ensure the 2D view is effectively contiguous for the kernel to use a simple stride.
    # If reshape caused a copy, it's contiguous. If it's a view of a strided tensor,
    # stride(0) might be non-uniform? No, view(-1, D) requires compatible strides.
    # If view fails, reshape copies. So q_2d is safe to use with stride(0).
    
    # However, to avoid implicit copies in reshape when possible, we can check.
    # But for robustness and strict 2D grid mapping, we stick to this.
    
    N_q, D = q_2d.shape
    N_k = k_2d.shape[0]
    
    # Alloc outputs
    q_out = torch.empty_like(q_2d)
    k_out = torch.empty_like(k_2d)
    
    # Heuristic: Block size
    # Power of 2 >= D
    BLOCK_SIZE = triton.next_power_of_2(D)
    
    # Launch Grid: Total rows of Q + Total rows of K
    grid = (N_q + N_k,)
    
    _fused_qknorm_kernel[grid](
        q_2d, k_2d, norm_weight,
        q_out, k_out,
        q_2d.stride(0), k_2d.stride(0),
        q_out.stride(0), k_out.stride(0),
        N_q, N_k, D,
        1e-6,
        BLOCK_SIZE=BLOCK_SIZE
    )
    
    return q_out.view(q.shape), k_out.view(k.shape)
"""