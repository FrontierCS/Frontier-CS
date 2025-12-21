import torch
import flashinfer

class Solution:
    def solve(self, spec_path: str = None) -> dict:
        code = r"""import torch
import triton
import triton.language as tl
import flashinfer

@triton.jit
def _fused_qknorm_kernel(
    Q_ptr, K_ptr, W_ptr,
    Q_out_ptr, K_out_ptr,
    stride_q_chunk,
    stride_k_chunk,
    R_q, R_k,
    Total_Q,
    D: tl.constexpr,
    BLOCK_SIZE: tl.constexpr,
    EPS: tl.constexpr
):
    pid = tl.program_id(0)
    pid_64 = pid.to(tl.int64)
    
    is_q = pid < Total_Q
    
    # Calculate pointers
    # We map the linear PID to (chunk_id, row_in_chunk)
    # The input tensor is viewed as N chunks of R rows.
    # Rows within a chunk are contiguous (stride D).
    # Chunks are separated by stride_chunk.
    
    if is_q:
        idx = pid_64
        chunk_id = idx // R_q
        row_in_chunk = idx % R_q
        offset_in = chunk_id * stride_q_chunk + row_in_chunk * D
        ptr_in = Q_ptr + offset_in
        ptr_out = Q_out_ptr + idx * D
    else:
        idx = pid_64 - Total_Q
        chunk_id = idx // R_k
        row_in_chunk = idx % R_k
        offset_in = chunk_id * stride_k_chunk + row_in_chunk * D
        ptr_in = K_ptr + offset_in
        ptr_out = K_out_ptr + (pid_64 - Total_Q) * D

    offs = tl.arange(0, BLOCK_SIZE)
    mask = offs < D
    
    # Load Weight (contiguous)
    w = tl.load(W_ptr + offs, mask=mask, other=0.0)
    
    # Load Input (contiguous within row)
    x = tl.load(ptr_in + offs, mask=mask, other=0.0).to(tl.float32)

    # RMSNorm: x * w * rsqrt(mean(x^2) + eps)
    x_sq = x * x
    mean_sq = tl.sum(x_sq, axis=0) / D
    rstd = tl.rsqrt(mean_sq + EPS)
    
    out = x * rstd * w
    
    # Store Output (contiguous)
    tl.store(ptr_out + offs, out, mask=mask)

def _get_batch_params(tensor):
    # Analyzes tensor layout to see if it can be mapped to (N_chunks, R_rows, D)
    # where rows are contiguous, and chunks have a constant stride.
    # This supports efficient handling of QKV-sliced tensors without copy.
    
    shape = tensor.shape
    strides = tensor.stride()
    ndim = tensor.ndim
    if ndim < 2: return None
    
    D = shape[-1]
    # Require last dim to be contiguous for vectorized load
    if strides[-1] != 1: return None 
    
    # Identify inner contiguous block size (R)
    # Scan from second-to-last dimension backwards
    R = 1
    dim_idx = ndim - 2
    while dim_idx >= 0:
        if strides[dim_idx] == shape[dim_idx+1] * strides[dim_idx+1]:
            R *= shape[dim_idx]
            dim_idx -= 1
        else:
            break
            
    # If the whole tensor is contiguous
    if dim_idx == -1:
        return (1, R, 0)
        
    # Check if outer dimensions (0 to dim_idx) are contiguous relative to each other
    # creating a linear sequence of chunks.
    outer_contiguous = True
    for k in range(dim_idx):
        if strides[k] != shape[k+1] * strides[k+1]:
            outer_contiguous = False
            break
            
    if not outer_contiguous:
        return None
        
    # Calculate N (number of chunks)
    N = 1
    for k in range(dim_idx + 1):
        N *= shape[k]
        
    stride_chunk = strides[dim_idx]
    return (N, R, stride_chunk)

def qknorm(q: torch.Tensor, k: torch.Tensor, norm_weight: torch.Tensor):
    D = q.shape[-1]
    
    # Check compatibility for fused kernel
    if k.shape[-1] != D or norm_weight.shape[0] != D:
        # Fallback for shape mismatch
        q_o = torch.empty(q.shape, device=q.device, dtype=q.dtype)
        k_o = torch.empty(k.shape, device=k.device, dtype=k.dtype)
        flashinfer.norm.rmsnorm(q, norm_weight, out=q_o)
        flashinfer.norm.rmsnorm(k, norm_weight, out=k_o)
        return q_o, k_o

    q_params = _get_batch_params(q)
    k_params = _get_batch_params(k)

    # If layout is too complex, fallback to FlashInfer (which handles strided via copy if needed)
    if q_params is None or k_params is None:
        q_o = torch.empty(q.shape, device=q.device, dtype=q.dtype)
        k_o = torch.empty(k.shape, device=k.device, dtype=k.dtype)
        flashinfer.norm.rmsnorm(q, norm_weight, out=q_o)
        flashinfer.norm.rmsnorm(k, norm_weight, out=k_o)
        return q_o, k_o

    N_q, R_q, stride_q_chunk = q_params
    N_k, R_k, stride_k_chunk = k_params
    
    Total_Q = N_q * R_q
    Total_K = N_k * R_k
    Total = Total_Q + Total_K
    
    # Allocate outputs (always contiguous)
    q_o = torch.empty(q.shape, device=q.device, dtype=q.dtype)
    k_o = torch.empty(k.shape, device=k.device, dtype=k.dtype)
    
    if Total == 0:
        return q_o, k_o

    # Determine Block Size
    BLOCK_SIZE = 128
    while BLOCK_SIZE < D:
        BLOCK_SIZE *= 2
    
    num_warps = 4
    if BLOCK_SIZE >= 1024: num_warps = 8
    
    grid = (Total,)
    
    # Launch fused kernel
    _fused_qknorm_kernel[grid](
        q, k, norm_weight,
        q_o, k_o,
        stride_q_chunk, stride_k_chunk,
        R_q, R_k,
        Total_Q,
        D=D,
        BLOCK_SIZE=BLOCK_SIZE,
        EPS=1e-6,
        num_warps=num_warps
    )
    
    return q_o, k_o
"""
        return {"code": code}
