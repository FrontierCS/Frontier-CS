import torch
import triton
import triton.language as tl

class Solution:
    def solve(self, spec_path: str = None) -> dict:
        return {
            "code": r"""
import torch
import triton
import triton.language as tl

@triton.autotune(
    configs=[
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 128, 'BLOCK_K': 64, 'GROUP_SIZE_M': 8}, num_stages=3, num_warps=8),
        triton.Config({'BLOCK_M': 64, 'BLOCK_N': 128, 'BLOCK_K': 64, 'GROUP_SIZE_M': 8}, num_stages=3, num_warps=4),
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 64, 'BLOCK_K': 64, 'GROUP_SIZE_M': 8}, num_stages=3, num_warps=4),
        triton.Config({'BLOCK_M': 64, 'BLOCK_N': 64, 'BLOCK_K': 64, 'GROUP_SIZE_M': 8}, num_stages=3, num_warps=4),
        triton.Config({'BLOCK_M': 32, 'BLOCK_N': 64, 'BLOCK_K': 64, 'GROUP_SIZE_M': 8}, num_stages=3, num_warps=4),
    ],
    key=['M', 'N'],
)
@triton.jit
def _quant_dot_kernel(
    scale_ptr, offset_ptr, weight_ptr, activation_ptr, output_ptr,
    M, N, K,
    stride_scale_m, stride_scale_k,
    stride_offset_m,
    stride_weight_m, stride_weight_k,
    stride_act_k, stride_act_n,
    stride_out_m, stride_out_n,
    BLOCK_M: tl.constexpr, BLOCK_N: tl.constexpr, BLOCK_K: tl.constexpr,
    GROUP_SIZE_M: tl.constexpr
):
    pid = tl.program_id(axis=0)
    
    # Swizzling to improve L2 cache locality
    num_pid_m = tl.cdiv(M, BLOCK_M)
    num_pid_n = tl.cdiv(N, BLOCK_N)
    num_pid_in_group = GROUP_SIZE_M * num_pid_n
    group_id = pid // num_pid_in_group
    first_pid_m = group_id * GROUP_SIZE_M
    group_size_m = min(num_pid_m - first_pid_m, GROUP_SIZE_M)
    pid_m = first_pid_m + (pid % group_size_m)
    pid_n = (pid % num_pid_in_group) // group_size_m
    
    # Calculate offsets
    offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
    offs_n = pid_n * BLOCK_N + tl.arange(0, BLOCK_N)
    offs_k = tl.arange(0, BLOCK_K)
    
    # Masks for boundary checks
    mask_m = offs_m < M
    mask_n = offs_n < N
    
    # --- Load Packed Parameters ---
    
    # 1. Offset (M, ) int32 - Packs 8 int4 offsets per row
    # Pointer: offset_ptr + offs_m * stride_offset_m
    # We load (BLOCK_M, )
    off_ptrs = offset_ptr + offs_m * stride_offset_m
    packed_offsets = tl.load(off_ptrs, mask=mask_m, other=0) 
    
    # 2. Weights (M, K/8) int32 - Packs 8 int4 weights per int32
    # Indices: row=offs_m, col=offs_k // 8
    # NOTE: offs_k // 8 creates indices [0,0,..0, 1,1..1, ...] which matches the packed layout
    w_ptrs = weight_ptr + (offs_m[:, None] * stride_weight_m) + ((offs_k[None, :] // 8) * stride_weight_k)
    packed_weights = tl.load(w_ptrs, mask=mask_m[:, None], other=0)
    
    # 3. Scale (M, K/8) - f16 or f32
    # Same access pattern as weights (per group of 8)
    s_ptrs = scale_ptr + (offs_m[:, None] * stride_scale_m) + ((offs_k[None, :] // 8) * stride_scale_k)
    scales = tl.load(s_ptrs, mask=mask_m[:, None], other=0.0)
    
    # --- Unpack and Dequantize ---
    
    # Extract offsets:
    # There are 8 groups in K=64. Group index for a given k is k // 8.
    # The offset for group g is stored in bits (g * 4) to (g * 4 + 3).
    # Shift amount = (k // 8) * 4.
    shift_o = (offs_k[None, :] // 8) * 4
    # Broadcast packed_offsets from (BLOCK_M) to (BLOCK_M, BLOCK_K) is implicit via broadcasting with shift_o (1, BLOCK_K)
    unpacked_offsets = (packed_offsets[:, None] >> shift_o) & 0xF
    
    # Extract weights:
    # There are 8 weights in one int32. Index within int32 is k % 8.
    # Shift amount = (k % 8) * 4.
    shift_w = (offs_k[None, :] % 8) * 4
    unpacked_weights = (packed_weights >> shift_w) & 0xF
    
    # Calculation: A = scale * (w - o)
    # Ensure all operands are float16 for computation
    a_vals = scales.to(tl.float16) * (unpacked_weights.to(tl.float16) - unpacked_offsets.to(tl.float16))
    
    # --- Load Activation ---
    # Shape (K, N)
    # ptrs: activation + k*stride_k + n*stride_n
    b_ptrs = activation_ptr + (offs_k[:, None] * stride_act_k) + (offs_n[None, :] * stride_act_n)
    b_vals = tl.load(b_ptrs, mask=mask_n[None, :], other=0.0).to(tl.float16)
    
    # --- Dot Product ---
    # Accumulate in fp32 for precision
    acc = tl.dot(a_vals, b_vals, out_dtype=tl.float32)
    
    # --- Store Output ---
    out_ptrs = output_ptr + (offs_m[:, None] * stride_out_m) + (offs_n[None, :] * stride_out_n)
    tl.store(out_ptrs, acc.to(tl.float16), mask=mask_m[:, None] & mask_n[None, :])

def quant_dot(scale: torch.Tensor, offset_packed: torch.Tensor, weight_packed: torch.Tensor, activation: torch.Tensor) -> torch.Tensor:
    M = scale.shape[0]
    K = activation.shape[0]
    N = activation.shape[1]
    
    # Validation
    # K is fixed to 64 per problem spec
    assert K == 64, "K must be 64"
    assert scale.shape == (M, 8), "Scale shape mismatch"
    assert weight_packed.shape == (M, 8), "Weight packed shape mismatch"
    assert offset_packed.shape == (M,), "Offset packed shape mismatch"
    
    output = torch.empty((M, N), device=scale.device, dtype=torch.float16)
    
    grid = lambda META: (triton.cdiv(M, META['BLOCK_M']) * triton.cdiv(N, META['BLOCK_N']), )
    
    _quant_dot_kernel[grid](
        scale, offset_packed, weight_packed, activation, output,
        M, N, K,
        scale.stride(0), scale.stride(1),
        offset_packed.stride(0),
        weight_packed.stride(0), weight_packed.stride(1),
        activation.stride(0), activation.stride(1),
        output.stride(0), output.stride(1)
    )
    
    return output
"""
        }