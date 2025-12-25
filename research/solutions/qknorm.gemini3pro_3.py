import torch
import triton
import triton.language as tl
import flashinfer
import sys
import inspect

@triton.jit
def _qknorm_fused_kernel(
    Q_ptr, K_ptr, W_ptr,
    Q_out_ptr, K_out_ptr,
    stride_q0, stride_q1, stride_q2,
    shape_q0, shape_q1, shape_q2,
    stride_k0, stride_k1, stride_k2,
    shape_k0, shape_k1, shape_k2,
    n_q_rows, n_k_rows,
    D,
    eps,
    BLOCK_SIZE: tl.constexpr
):
    pid = tl.program_id(0)
    
    # Range check
    if pid >= n_q_rows + n_k_rows:
        return

    cols = tl.arange(0, BLOCK_SIZE)
    mask = cols < D
    
    # Load Weight
    w = tl.load(W_ptr + cols, mask=mask, other=0.0).to(tl.float32)

    if pid < n_q_rows:
        # Process Q
        row_idx = pid
        
        # Reconstruct indices for Q (collapsed to 3 leading dims)
        # We iterate logically over the flattened leading dimensions
        curr = row_idx
        idx2 = curr % shape_q2
        curr = curr // shape_q2
        idx1 = curr % shape_q1
        idx0 = curr // shape_q1
        
        # Compute offset in elements
        offset = idx0 * stride_q0 + idx1 * stride_q1 + idx2 * stride_q2
        ptr = Q_ptr + offset
        
        # Output is contiguous, so linear map works
        out_ptr = Q_out_ptr + row_idx * D
        
        # Load Data (Assuming stride[-1] == 1, standard for QKV fusion slices)
        val = tl.load(ptr + cols, mask=mask, other=0.0).to(tl.float32)
        
        # RMSNorm
        sq = val * val
        mean_sq = tl.sum(sq, axis=0) / D
        rstd = tl.rsqrt(mean_sq + eps)
        tl.store(out_ptr + cols, val * rstd * w, mask=mask)
        
    else:
        # Process K
        row_idx = pid - n_q_rows
        
        curr = row_idx
        idx2 = curr % shape_k2
        curr = curr // shape_k2
        idx1 = curr % shape_k1
        idx0 = curr // shape_k1
        
        offset = idx0 * stride_k0 + idx1 * stride_k1 + idx2 * stride_k2
        ptr = K_ptr + offset
        out_ptr = K_out_ptr + row_idx * D
        
        val = tl.load(ptr + cols, mask=mask, other=0.0).to(tl.float32)
        
        sq = val * val
        mean_sq = tl.sum(sq, axis=0) / D
        rstd = tl.rsqrt(mean_sq + eps)
        tl.store(out_ptr + cols, val * rstd * w, mask=mask)

def qknorm(q: torch.Tensor, k: torch.Tensor, norm_weight: torch.Tensor):
    """
    Apply RMSNorm to query and key tensors using a fused Triton kernel.
    Efficiently handles non-contiguous inputs and arbitrary shapes.
    """
    D = q.shape[-1]
    
    # Allocate contiguous outputs
    q_out = torch.empty(q.shape, device=q.device, dtype=q.dtype)
    k_out = torch.empty(k.shape, device=k.device, dtype=k.dtype)
    
    def prepare_meta(tensor):
        # Flatten leading dimensions while preserving stride logic where possible
        shape = list(tensor.shape[:-1])
        strides = list(tensor.stride()[:-1])
        
        if not shape:
            return [1, 1, 1], [0, 0, 0], 1
        
        # Collapse contiguous dimensions
        new_shape = [shape[-1]]
        new_strides = [strides[-1]]
        
        for i in range(len(shape)-2, -1, -1):
            prev_shape = new_shape[0]
            prev_stride = new_strides[0]
            # Check if dimension i and i+1 (now at 0) are contiguous
            if strides[i] == prev_shape * prev_stride:
                new_shape[0] *= shape[i]
            else:
                new_shape.insert(0, shape[i])
                new_strides.insert(0, strides[i])
        
        # Pad to 3 dimensions for the kernel
        while len(new_shape) < 3:
            new_shape.insert(0, 1)
            new_strides.insert(0, 0)
            
        num_rows = 1
        for s in new_shape: num_rows *= s
        
        return new_shape, new_strides, num_rows

    q_shape, q_strides, n_q = prepare_meta(q)
    k_shape, k_strides, n_k = prepare_meta(k)
    
    # Config
    BLOCK_SIZE = triton.next_power_of_2(D)
    if BLOCK_SIZE < 32: BLOCK_SIZE = 32
    
    # Heuristic for warps
    num_warps = 4
    if BLOCK_SIZE >= 2048: num_warps = 16
    elif BLOCK_SIZE >= 1024: num_warps = 8
    
    grid = (n_q + n_k,)
    
    _qknorm_fused_kernel[grid](
        q, k, norm_weight,
        q_out, k_out,
        q_strides[0], q_strides[1], q_strides[2],
        q_shape[0], q_shape[1], q_shape[2],
        k_strides[0], k_strides[1], k_strides[2],
        k_shape[0], k_shape[1], k_shape[2],
        n_q, n_k,
        D,
        1e-6,
        BLOCK_SIZE=BLOCK_SIZE,
        num_warps=num_warps
    )
    
    return q_out, k_out

class Solution:
    def solve(self, spec_path: str = None) -> dict:
        return {"code": open(__file__).read()}
