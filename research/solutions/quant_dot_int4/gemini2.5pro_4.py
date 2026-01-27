import torch
import triton
import triton.language as tl

@triton.autotune(
    configs=[
        # Basic balanced configs
        triton.Config({'BLOCK_M': 64, 'BLOCK_N': 64}, num_stages=4, num_warps=4),
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 64}, num_stages=4, num_warps=4),
        triton.Config({'BLOCK_M': 64, 'BLOCK_N': 128}, num_stages=4, num_warps=4),
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 128}, num_stages=3, num_warps=8),
        # Configs for larger N
        triton.Config({'BLOCK_M': 32, 'BLOCK_N': 256}, num_stages=3, num_warps=4),
        triton.Config({'BLOCK_M': 64, 'BLOCK_N': 256}, num_stages=3, num_warps=8),
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 256}, num_stages=2, num_warps=8),
        # Configs for larger M
        triton.Config({'BLOCK_M': 256, 'BLOCK_N': 32}, num_stages=3, num_warps=4),
        triton.Config({'BLOCK_M': 256, 'BLOCK_N': 64}, num_stages=3, num_warps=8),
        triton.Config({'BLOCK_M': 256, 'BLOCK_N': 128}, num_stages=2, num_warps=8),
        # Smaller block sizes
        triton.Config({'BLOCK_M': 32, 'BLOCK_N': 128}, num_stages=4, num_warps=4),
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 32}, num_stages=4, num_warps=4),
    ],
    key=['M', 'N'],
)
@triton.jit
def quant_dot_kernel(
    scale_ptr, offset_packed_ptr, weight_packed_ptr, activation_ptr, output_ptr,
    stride_scale_m, stride_scale_k,
    stride_weight_m, stride_weight_k,
    stride_act_k, stride_act_n,
    stride_out_m, stride_out_n,
    M, N, K,
    BLOCK_M: tl.constexpr, BLOCK_N: tl.constexpr,
    FPINT: tl.constexpr, GROUP: tl.constexpr,
):
    """
    Triton kernel for quantized matrix multiplication.
    Computes C = A @ B, where A is dequantized on the fly.
    A is (M, K), B is (K, N), C is (M, N).
    K is fixed at 64.
    """
    # Program and thread block IDs
    pid_m = tl.program_id(axis=0)
    pid_n = tl.program_id(axis=1)

    # Offsets for the current block of the output matrix C
    offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
    offs_n = pid_n * BLOCK_N + tl.arange(0, BLOCK_N)
    
    # Boundary masks
    mask_m = offs_m < M
    mask_n = offs_n < N

    # Accumulator for the output block, initialized to zeros
    acc = tl.zeros((BLOCK_M, BLOCK_N), dtype=tl.float32)
    
    # Load the packed int4 offsets for the current rows.
    # This is loaded once and reused across the K-dimension loop.
    offset_packed_ptrs = offset_packed_ptr + offs_m
    packed_o = tl.load(offset_packed_ptrs, mask=mask_m, other=0)

    # The loop over the K dimension is unrolled by the compiler since K is small and fixed.
    # It processes the matrix in chunks of FPINT (8) columns.
    for k_pack_idx in range(0, K // FPINT):
        k_start = k_pack_idx * FPINT
        offs_k_inner = tl.arange(0, FPINT)
        offs_k = k_start + offs_k_inner

        # Load a slice of B (activation matrix) of shape (FPINT, BLOCK_N)
        b_ptrs = activation_ptr + (offs_k[:, None] * stride_act_k + offs_n[None, :] * stride_act_n)
        b_slice = tl.load(b_ptrs, mask=mask_n[None, :], other=0.0)

        # Dequantize a slice of A on-the-fly to shape (BLOCK_M, FPINT)
        # 1. Unpack the int4 offset for the current group
        # Since GROUP == FPINT, the group index is k_pack_idx.
        k_group_shift = k_pack_idx * 4
        o_int4_val = (packed_o >> k_group_shift) & 0xF

        # 2. Load the scale for the current group
        scale_ptrs = scale_ptr + (offs_m * stride_scale_m + k_pack_idx * stride_scale_k)
        scale_val = tl.load(scale_ptrs, mask=mask_m, other=0.0)

        # 3. Load the packed int4 weights for the current group
        weight_packed_ptrs = weight_packed_ptr + (offs_m * stride_weight_m + k_pack_idx * stride_weight_k)
        packed_w_val = tl.load(weight_packed_ptrs, mask=mask_m, other=0)
        
        # 4. Unpack the 8 int4 weights from the loaded int32 value
        k_in_word_shifts = offs_k_inner * 4
        w_int4_slice = (packed_w_val[:, None] >> k_in_word_shifts[None, :]) & 0xF

        # 5. Perform the dequantization: (weight - offset) * scale
        # The result is cast to the activation dtype (e.g., float16)
        a_slice_dequant = (w_int4_slice - o_int4_val[:, None]).to(b_slice.dtype)
        a_slice = a_slice_dequant * scale_val.to(b_slice.dtype)[:, None]

        # 6. Perform matrix multiplication for the slice and accumulate
        acc += tl.dot(a_slice, b_slice)

    # Store the final accumulated result to the output matrix C
    output_ptrs = output_ptr + (offs_m[:, None] * stride_out_m + offs_n[None, :] * stride_out_n)
    mask_c = mask_m[:, None] & mask_n[None, :]
    tl.store(output_ptrs, acc.to(b_slice.dtype), mask=mask_c)

def quant_dot(scale: torch.Tensor, offset_packed: torch.Tensor, weight_packed: torch.Tensor, activation: torch.Tensor) -> torch.Tensor:
    """
    Args:
        scale: float16/float32 tensor of shape (M, K/8)
        offset_packed: int32 tensor of shape (M,)
            Each int32 packs 8 int4 offsets (one per 8-wide group).
        weight_packed: int32 tensor of shape (M, K/8)
            Each int32 packs 8 int4 weights.
        activation: float16 tensor of shape (K, N)
    
    Returns:
        Output tensor of shape (M, N), dtype float16
    """
    M, K_div_8 = weight_packed.shape
    K_act, N = activation.shape

    # Constants for this problem
    K = 64
    FPINT = 8
    GROUP = 8

    # Input validation
    assert K_act == K, f"K dimension of activation must be {K}, but got {K_act}"
    assert K_div_8 * FPINT == K, f"Packed dimension of weights must be K/{FPINT}"
    
    # Allocate output tensor
    output = torch.empty((M, N), device=activation.device, dtype=activation.dtype)

    # Grid dimensions for kernel launch
    grid = lambda META: (triton.cdiv(M, META['BLOCK_M']), triton.cdiv(N, META['BLOCK_N']))

    # Launch the Triton kernel
    quant_dot_kernel[grid](
        scale, offset_packed, weight_packed, activation, output,
        # Strides for tensor access
        scale.stride(0), scale.stride(1),
        weight_packed.stride(0), weight_packed.stride(1),
        activation.stride(0), activation.stride(1),
        output.stride(0), output.stride(1),
        # Matrix dimensions
        M, N, K,
        # Compile-time constants
        FPINT=FPINT, GROUP=GROUP,
    )
    
    return output