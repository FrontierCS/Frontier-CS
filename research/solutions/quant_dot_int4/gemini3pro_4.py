import torch
import triton
import triton.language as tl
import sys
import inspect

class Solution:
    def solve(self, spec_path: str = None) -> dict:
        return {"code": inspect.getsource(sys.modules[__name__])}

@triton.autotune(
    configs=[
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 128}, num_warps=8, num_stages=3),
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 64}, num_warps=4, num_stages=3),
        triton.Config({'BLOCK_M': 64, 'BLOCK_N': 128}, num_warps=4, num_stages=3),
        triton.Config({'BLOCK_M': 64, 'BLOCK_N': 64}, num_warps=4, num_stages=3),
        triton.Config({'BLOCK_M': 32, 'BLOCK_N': 64}, num_warps=2, num_stages=2),
    ],
    key=['M', 'N'],
)
@triton.jit
def _quant_dot_kernel(
    scale_ptr,
    offset_ptr,
    weight_ptr,
    activation_ptr,
    output_ptr,
    M, N, K: tl.constexpr,
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
    # 1. Define offsets for the block
    # -----------------------------------------------------------
    offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
    offs_n = pid_n * BLOCK_N + tl.arange(0, BLOCK_N)
    offs_k = tl.arange(0, K) 
    
    # Masks for boundary check
    mask_m = offs_m < M
    mask_n = offs_n < N
    
    # -----------------------------------------------------------
    # 2. Load Packed Weights (int4 packed in int32)
    # -----------------------------------------------------------
    # Calculate pointers to weight_packed
    # weight_packed shape: (M, K/8). 
    # Logical mapping: weight_packed[m, k//8] contains w[m, k]
    # Bit shift: (k % 8) * 4
    
    packed_col_idx = offs_k // 8
    w_ptr = weight_ptr + (offs_m[:, None] * stride_weight_m) + (packed_col_idx[None, :] * stride_weight_k)
    
    # Load packed data. Shape (BLOCK_M, 64) (replicated values)
    w_packed = tl.load(w_ptr, mask=mask_m[:, None])
    
    # Unpack int4 (assume unsigned raw bits 0-15)
    w_shift = (offs_k % 8) * 4
    w_int4 = (w_packed >> w_shift[None, :]) & 0xF
    
    # -----------------------------------------------------------
    # 3. Load Packed Offsets (int4 packed in int32)
    # -----------------------------------------------------------
    # offset_packed shape: (M,).
    # One int32 per row containing 8 offsets (one per group of 8 columns).
    # k belongs to group k//8.
    
    o_ptr = offset_ptr + (offs_m * stride_offset_m)
    o_packed = tl.load(o_ptr, mask=mask_m) # Shape (BLOCK_M,)
    
    # Broadcast and unpack
    o_packed_expanded = o_packed[:, None] # (BLOCK_M, 1)
    o_shift = (offs_k // 8) * 4
    o_int4 = (o_packed_expanded >> o_shift[None, :]) & 0xF
    
    # -----------------------------------------------------------
    # 4. Load Scales
    # -----------------------------------------------------------
    # scale shape: (M, K/8)
    # scale[m, k] corresponds to scale[m, k//8]
    
    s_ptr = scale_ptr + (offs_m[:, None] * stride_scale_m) + (packed_col_idx[None, :] * stride_scale_k)
    s_val = tl.load(s_ptr, mask=mask_m[:, None])
    
    # -----------------------------------------------------------
    # 5. Dequantize A
    # -----------------------------------------------------------
    # A = scale * (w - o)
    # Compute in fp32 for better precision/handling of int conversion
    w_fp32 = w_int4.to(tl.float32)
    o_fp32 = o_int4.to(tl.float32)
    s_fp32 = s_val.to(tl.float32)
    
    a_fp32 = s_fp32 * (w_fp32 - o_fp32)
    # Convert to float16 for Tensor Core Dot
    a_fp16 = a_fp32.to(tl.float16)
    
    # -----------------------------------------------------------
    # 6. Load Activation B
    # -----------------------------------------------------------
    # activation shape: (K, N)
    
    b_ptr = activation_ptr + (offs_k[:, None] * stride_act_k) + (offs_n[None, :] * stride_act_n)
    b_fp16 = tl.load(b_ptr, mask=mask_n[None, :])
    
    # -----------------------------------------------------------
    # 7. Dot Product
    # -----------------------------------------------------------
    # Accumulate in fp32
    acc = tl.dot(a_fp16, b_fp16)
    
    # -----------------------------------------------------------
    # 8. Store Output
    # -----------------------------------------------------------
    out_ptr = output_ptr + (offs_m[:, None] * stride_out_m) + (offs_n[None, :] * stride_out_n)
    tl.store(out_ptr, acc.to(tl.float16), mask=mask_m[:, None] & mask_n[None, :])

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
    K = 64
    _, N = activation.shape
    
    # Ensure contiguous output or handle strides
    output = torch.empty((M, N), device=activation.device, dtype=torch.float16)
    
    grid = lambda META: (triton.cdiv(M, META['BLOCK_M']), triton.cdiv(N, META['BLOCK_N']))
    
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