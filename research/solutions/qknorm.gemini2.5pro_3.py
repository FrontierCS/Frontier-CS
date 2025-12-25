import torch
import triton
import triton.language as tl
import flashinfer

@triton.jit
def _qknorm_fused_kernel(
    # Pointers to tensors
    Q_ptr, K_ptr, W_ptr,
    Q_out_ptr, K_out_ptr,
    # Strides for non-contiguous memory access
    q_stride_r, q_stride_c,
    k_stride_r, k_stride_c,
    q_out_stride_r, q_out_stride_c,
    k_out_stride_r, k_out_stride_c,
    # Dimensions
    N_q, D,
    # Kernel constants
    BLOCK_SIZE_D: tl.constexpr,
    eps: tl.constexpr,
):
    """
    Fused Triton kernel for applying RMSNorm to Q and K tensors in a single launch.
    The grid is 1D, with each program instance processing one row from either Q or K.
    """
    # Each program instance computes a unique row index.
    pid = tl.program_id(0)

    # Branch to determine whether to process a row from Q or K.
    # This branch is taken once at the beginning of the program.
    if pid < N_q:
        # This instance handles a row from the Q tensor.
        row_idx = pid
        X_ptr_base = Q_ptr + row_idx * q_stride_r
        X_out_ptr_base = Q_out_ptr + row_idx * q_out_stride_r
        x_stride_c = q_stride_c
        x_out_stride_c = q_out_stride_c
    else:
        # This instance handles a row from the K tensor.
        row_idx = pid - N_q
        X_ptr_base = K_ptr + row_idx * k_stride_r
        X_out_ptr_base = K_out_ptr + row_idx * k_out_stride_r
        x_stride_c = k_stride_c
        x_out_stride_c = k_out_stride_c

    # --- RMSNorm Core Logic ---

    # 1. Calculate the sum of squares for the row (variance calculation).
    # The row is processed in blocks of size BLOCK_SIZE_D.
    offs_d = tl.arange(0, BLOCK_SIZE_D)
    var = 0.0
    for i in range(0, tl.cdiv(D, BLOCK_SIZE_D)):
        c_offs = i * BLOCK_SIZE_D + offs_d
        mask = c_offs < D
        x_ptr = X_ptr_base + c_offs * x_stride_c
        x = tl.load(x_ptr, mask=mask, other=0.0).to(tl.float32)
        var += tl.sum(x * x, axis=0)
    
    # 2. Compute the reciprocal of the root mean square (rsqrt).
    rstd = tl.math.rsqrt(var / D + eps)

    # 3. Apply normalization and scaling weights.
    # This requires a second pass over the row data.
    for i in range(0, tl.cdiv(D, BLOCK_SIZE_D)):
        c_offs = i * BLOCK_SIZE_D + offs_d
        mask = c_offs < D
        
        # Load input row data again.
        x_ptr = X_ptr_base + c_offs * x_stride_c
        x = tl.load(x_ptr, mask=mask, other=0.0)
        
        # Load scaling weights.
        w_ptr = W_ptr + c_offs
        w = tl.load(w_ptr, mask=mask, other=0.0)
        
        # Compute normalized output.
        y_out = x * rstd * w
        
        # Store the result.
        y_out_ptr = X_out_ptr_base + c_offs * x_out_stride_c
        tl.store(y_out_ptr, y_out, mask=mask)

def qknorm(q: torch.Tensor, k: torch.Tensor, norm_weight: torch.Tensor):
    """
    Apply RMSNorm to query and key tensors using a single fused Triton kernel
    to minimize launch overhead and handle non-contiguous inputs efficiently.
    
    Args:
        q: Query tensor of arbitrary shape.
        k: Key tensor of arbitrary shape.
        norm_weight: Normalization weight tensor of shape (hidden_dim,).
    
    Returns:
        Tuple of (q_normalized, k_normalized) tensors.
    """
    q_shape_orig = q.shape
    k_shape_orig = k.shape
    hidden_dim = q.shape[-1]
    
    # Reshape to 2D without data copy. This relies on the last dimension
    # being contiguous in memory relative to the view.
    q_2d = q.view(-1, hidden_dim)
    k_2d = k.view(-1, hidden_dim)

    N_q = q_2d.shape[0]
    N_k = k_2d.shape[0]
    D = hidden_dim

    total_rows = N_q + N_k
    if total_rows == 0:
        return torch.empty_like(q), torch.empty_like(k)

    # Allocate output tensors.
    q_out = torch.empty(q_shape_orig, device=q.device, dtype=q.dtype)
    k_out = torch.empty(k_shape_orig, device=k.device, dtype=k.dtype)

    q_out_2d = q_out.view(-1, hidden_dim)
    k_out_2d = k_out.view(-1, hidden_dim)
    
    assert q.is_cuda and k.is_cuda and norm_weight.is_cuda, "All tensors must be on a CUDA device"

    grid = (total_rows,)

    # Use next_power_of_2 for block size, a common Triton practice.
    BLOCK_SIZE_D = triton.next_power_of_2(D)

    # Launch the fused kernel.
    _qknorm_fused_kernel[grid](
        q_2d, k_2d, norm_weight,
        q_out_2d, k_out_2d,
        q_2d.stride(0), q_2d.stride(1),
        k_2d.stride(0), k_2d.stride(1),
        q_out_2d.stride(0), q_out_2d.stride(1),
        k_out_2d.stride(0), k_out_2d.stride(1),
        N_q, D,
        BLOCK_SIZE_D=BLOCK_SIZE_D,
        eps=1e-5,  # A standard epsilon value for RMSNorm.
        num_warps=4, # A generally good value for memory-bound kernels.
    )
    
    return q_out, k_out

class Solution:
    def solve(self, spec_path: str = None) -> dict:
        """
        Returns a dictionary indicating the path to the program file containing
        the optimized `qknorm` implementation.
        """
        return {"program_path": __file__}
