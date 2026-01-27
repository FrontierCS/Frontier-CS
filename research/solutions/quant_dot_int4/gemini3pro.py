import torch
import triton
import triton.language as tl

class Solution:
    def solve(self, spec_path: str = None) -> dict:
        code = r"""
import torch
import triton
import triton.language as tl

@triton.autotune(
    configs=[
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 128}, num_stages=3, num_warps=4),
        triton.Config({'BLOCK_M': 64,  'BLOCK_N': 128}, num_stages=3, num_warps=4),
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 64},  num_stages=3, num_warps=4),
        triton.Config({'BLOCK_M': 64,  'BLOCK_N': 64},  num_stages=4, num_warps=4),
        triton.Config({'BLOCK_M': 256, 'BLOCK_N': 64},  num_stages=3, num_warps=8),
    ],
    key=['M', 'N']
)
@triton.jit
def quant_dot_kernel(
    scale_ptr, offset_ptr, weight_ptr, activation_ptr, output_ptr,
    M, N, K,
    stride_scale_m, stride_scale_k,
    stride_offset_m,
    stride_weight_m, stride_weight_k,
    stride_act_k, stride_act_n,
    stride_out_m, stride_out_n,
    BLOCK_M: tl.constexpr, BLOCK_N: tl.constexpr
):
    pid_m = tl.program_id(0)
    pid_n = tl.program_id(1)

    # -----------------------------------------------------------
    # Offsets and Masks
    # -----------------------------------------------------------
    offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
    offs_n = pid_n * BLOCK_N + tl.arange(0, BLOCK_N)
    
    mask_m = offs_m < M
    mask_n = offs_n < N

    # -----------------------------------------------------------
    # Load Constants (Weights, Scales, Offsets)
    # -----------------------------------------------------------
    # We load the full width (8 cols) for weights and scales at once.
    # This allows for more efficient memory access patterns.
    
    offs_k_packed = tl.arange(0, 8)
    
    # Load Weights (BLOCK_M, 8)
    # weight_packed has shape (M, 8)
    w_ptrs = weight_ptr + (offs_m[:, None] * stride_weight_m + offs_k_packed[None, :] * stride_weight_k)
    w_all = tl.load(w_ptrs, mask=mask_m[:, None], other=0) 

    # Load Scales (BLOCK_M, 8)
    s_ptrs = scale_ptr + (offs_m[:, None] * stride_scale_m + offs_k_packed[None, :] * stride_scale_k)
    s_all = tl.load(s_ptrs, mask=mask_m[:, None], other=0.0)

    # Load Offsets (BLOCK_M,)
    o_ptrs = offset_ptr + offs_m * stride_offset_m
    o_packed = tl.load(o_ptrs, mask=mask_m, other=0)
    
    # Unpack Offsets (BLOCK_M, 8) - One offset per group
    # o_packed is int32 containing 8 offsets.
    # Shifts: 0, 4, ..., 28
    shifts = tl.arange(0, 8) * 4
    o_all = (o_packed[:, None] >> shifts[None, :]) & 0xF

    # -----------------------------------------------------------
    # Accumulation Loop
    # -----------------------------------------------------------
    acc = tl.zeros((BLOCK_M, BLOCK_N), dtype=tl.float32)
    
    # Iterate over the 8 groups (Total K=64, Group Size=8)
    for g in tl.static_range(8):
        # 1. Get packed weights for group g
        w_g_packed = w_all[:, g] # (BLOCK_M,)
        
        # Unpack to 8 individual weights (BLOCK_M, 8)
        w_g_unpacked = (w_g_packed[:, None] >> shifts[None, :]) & 0xF
        
        # 2. Prepare Dequantization operands
        # Convert to float16 for computation
        w_val = w_g_unpacked.to(tl.float16)
        
        s_g = s_all[:, g] # (BLOCK_M,)
        o_g = o_all[:, g] # (BLOCK_M,)
        
        # Broadcast scale/offset to (BLOCK_M, 8)
        s_val = s_g[:, None].to(tl.float16)
        o_val = o_g[:, None].to(tl.float16)
        
        # 3. Dequantize A chunk
        # A = scale * (w - offset)
        a_chunk = s_val * (w_val - o_val) # (BLOCK_M, 8)
        
        # 4. Load Activation B (8, BLOCK_N)
        k_start = g * 8
        offs_k_b = k_start + tl.arange(0, 8)
        b_ptrs = activation_ptr + (offs_k_b[:, None] * stride_act_k + offs_n[None, :] * stride_act_n)
        b_chunk = tl.load(b_ptrs, mask=mask_n[None, :], other=0.0)
        
        # 5. Dot Product
        acc += tl.dot(a_chunk, b_chunk)

    # -----------------------------------------------------------
    # Store Output
    # -----------------------------------------------------------
    acc = acc.to(tl.float16)
    out_ptrs = output_ptr + (offs_m[:, None] * stride_out_m + offs_n[None, :] * stride_out_n)
    tl.store(out_ptrs, acc, mask=mask_m[:, None] & mask_n[None, :])

def quant_dot(scale: torch.Tensor, offset_packed: torch.Tensor, weight_packed: torch.Tensor, activation: torch.Tensor) -> torch.Tensor:
    M = scale.shape[0]
    N = activation.shape[1]
    K = 64
    
    output = torch.empty((M, N), dtype=torch.float16, device=scale.device)
    
    grid = lambda META: (
        (M + META['BLOCK_M'] - 1) // META['BLOCK_M'],
        (N + META['BLOCK_N'] - 1) // META['BLOCK_N']
    )
    
    quant_dot_kernel[grid](
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
        return {"code": code}