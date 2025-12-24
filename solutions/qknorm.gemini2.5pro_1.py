import torch
import triton
import triton.language as tl
import numpy as np
import flashinfer

@triton.jit
def _get_offset(row_idx, shape_prods_ptr, strides_ptr, rank: tl.constexpr):
    """
    Calculates the memory offset for a given row index in a non-contiguous tensor.
    This function is designed to be called from within a Triton kernel.
    """
    offset = 0
    # This loop is unrolled at compile time because `rank` is a tl.constexpr.
    # It computes the multidimensional index from the linear row_idx and
    # then calculates the offset using the tensor's strides.
    # This pattern is used to handle generic non-contiguous tensors without
    # needing to reshape or make them contiguous on the host.
    if rank > 1:
        rem = row_idx
        # Iterate from the outermost dimension to the one before the last
        for i in range(rank - 1):
            prod = tl.load(shape_prods_ptr + i)
            stride = tl.load(strides_ptr + i)
            idx = rem // prod
            rem = rem % prod
            offset += idx * stride
    return offset

@triton.jit
def _qknorm_fwd_kernel(
    # Data Pointers
    Q_PTR, K_PTR, W_PTR, Q_OUT_PTR, K_OUT_PTR,
    # Metadata for Q
    Q_SHAPE_PRODS_PTR, Q_STRIDES_PTR,
    # Metadata for K
    K_SHAPE_PRODS_PTR, K_STRIDES_PTR,
    # Kernel Parameters
    num_rows_q, D, EPSILON,
    q_stride_d, k_stride_d,
    # Compile-time Constants
    Q_RANK: tl.constexpr, K_RANK: tl.constexpr,
    BLOCK_SIZE_D: tl.constexpr,
):
    """
    Fused Triton kernel for applying RMSNorm to Query (Q) and Key (K) tensors.
    """
    # Each program in the grid handles one row (vector) from either Q or K.
    pid = tl.program_id(0)

    # Determine if the current program is for a Q row or a K row.
    is_q = pid < num_rows_q

    # Common computations for RMSNorm
    d_offsets = tl.arange(0, BLOCK_SIZE_D)
    d_mask = d_offsets < D
    # Load the normalization weights once.
    w = tl.load(W_PTR + d_offsets, mask=d_mask, other=0.0)

    # Branching on is_q. This allows the compiler to optimize each path separately.
    if is_q:
        row_idx = pid
        # Calculate the memory offset for the current row of Q.
        offset = _get_offset(row_idx, Q_SHAPE_PRODS_PTR, Q_STRIDES_PTR, Q_RANK)
        row_ptr = Q_PTR + offset
        row_out_ptr = Q_OUT_PTR + offset

        # Load the input row from Q.
        x = tl.load(row_ptr + d_offsets * q_stride_d, mask=d_mask, other=0.0).to(tl.float32)
        # Compute variance and reciprocal standard deviation.
        var = tl.sum(x * x, axis=0) / D
        rstd = tl.math.rsqrt(var + EPSILON)
        # Normalize and apply weights.
        output = x * rstd * w
        # Store the result to the output tensor for Q.
        tl.store(row_out_ptr + d_offsets * q_stride_d, output.to(Q_PTR.dtype.element_ty), mask=d_mask)
    else:
        row_idx = pid - num_rows_q
        # Calculate the memory offset for the current row of K.
        offset = _get_offset(row_idx, K_SHAPE_PRODS_PTR, K_STRIDES_PTR, K_RANK)
        row_ptr = K_PTR + offset
        row_out_ptr = K_OUT_PTR + offset

        # Load the input row from K.
        x = tl.load(row_ptr + d_offsets * k_stride_d, mask=d_mask, other=0.0).to(tl.float32)
        # Compute variance and reciprocal standard deviation.
        var = tl.sum(x * x, axis=0) / D
        rstd = tl.math.rsqrt(var + EPSILON)
        # Normalize and apply weights.
        output = x * rstd * w
        # Store the result to the output tensor for K.
        tl.store(row_out_ptr + d_offsets * k_stride_d, output.to(K_PTR.dtype.element_ty), mask=d_mask)

def qknorm(q: torch.Tensor, k: torch.Tensor, norm_weight: torch.Tensor):
    """
    Apply RMSNorm to query and key tensors using a single fused Triton kernel.
    This implementation avoids extra memory copies and kernel launches by handling
    non-contiguous tensors directly in the kernel.
    
    Args:
        q: Query tensor of arbitrary shape (will be reshaped to 2D)
        k: Key tensor of arbitrary shape (will be reshaped to 2D)
        norm_weight: Normalization weight tensor of shape (hidden_dim,)
    
    Returns:
        Tuple of (q_normalized, k_normalized) tensors
    """
    D = q.shape[-1]
    
    q_o = torch.empty_like(q)
    k_o = torch.empty_like(k)

    num_rows_q = q.numel() // D if q.numel() > 0 else 0
    num_rows_k = k.numel() // D if k.numel() > 0 else 0
    
    total_rows = num_rows_q + num_rows_k
    if total_rows == 0:
        return q_o, k_o

    grid = (total_rows,)

    def get_shape_prods(shape):
        if len(shape) <= 1:
            return torch.empty(0, dtype=torch.int64)
        dims = shape[:-1]
        if not dims:
            return torch.tensor([1], dtype=torch.int64)
        prods = np.cumprod(dims[1:][::-1], dtype=np.int64)[::-1].copy()
        return torch.from_numpy(np.concatenate([prods, [1]])).to(torch.int64)

    q_shape_prods = get_shape_prods(q.shape).to(q.device)
    k_shape_prods = get_shape_prods(k.shape).to(k.device)

    q_strides_tensor = torch.tensor(q.stride()[:-1], dtype=torch.int64, device=q.device) if q.ndim > 1 else torch.empty(0, dtype=torch.int64, device=q.device)
    k_strides_tensor = torch.tensor(k.stride()[:-1], dtype=torch.int64, device=k.device) if k.ndim > 1 else torch.empty(0, dtype=torch.int64, device=k.device)
    
    BLOCK_SIZE_D = triton.next_power_of_2(D)

    num_warps = 4
    if BLOCK_SIZE_D >= 2048:
        num_warps = 8
    if BLOCK_SIZE_D >= 4096:
        num_warps = 16

    _qknorm_fwd_kernel[grid](
        q, k, norm_weight, q_o, k_o,
        q_shape_prods, q_strides_tensor,
        k_shape_prods, k_strides_tensor,
        num_rows_q, D, 1e-5,  # Using 1e-5 for epsilon, common in RMSNorm
        q.stride(-1), k.stride(-1),
        Q_RANK=q.ndim, K_RANK=k.ndim,
        BLOCK_SIZE_D=BLOCK_SIZE_D,
        num_warps=num_warps
    )
    return q_o, k_o

class Solution:
    def solve(self, spec_path: str = None) -> dict:
        """
        Returns a dict with either:
        - {"code": "python_code_string"}
        - {"program_path": "path/to/kernel.py"}
        """
        # Read the current file's content
        import inspect
        import os
        
        file_path = inspect.getfile(inspect.currentframe())
        with open(file_path, 'r') as f:
            code = f.read()

        return {"code": code}
