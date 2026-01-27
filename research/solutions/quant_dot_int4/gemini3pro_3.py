import torch
import triton
import triton.language as tl
import sys

class Solution:
    def solve(self, spec_path: str = None) -> dict:
        return {"program_path": __file__}

# Configurations for autotuning
configs = [
    triton.Config({'BLOCK_M': 128, 'BLOCK_N': 128}, num_warps=8),
    triton.Config({'BLOCK_M': 64, 'BLOCK_N': 128}, num_warps=4),
    triton.Config({'BLOCK_M': 128, 'BLOCK_N': 64}, num_warps=4),
    triton.Config({'BLOCK_M': 64, 'BLOCK_N': 64}, num_warps=4),
    triton.Config({'BLOCK_M': 128, 'BLOCK_N': 32}, num_warps=4),
    triton.Config({'BLOCK_M': 32, 'BLOCK_N': 128}, num_warps=4),
    triton.Config({'BLOCK_M': 32, 'BLOCK_N': 32}, num_warps=2),
]

@triton.autotune(configs=configs, key=['M', 'N'])
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
    # Grid Logic
    pid_m = tl.program_id(0)
    pid_n = tl.program_id(1)
    
    offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
    offs_n = pid_n * BLOCK_N + tl.arange(0, BLOCK_N)
    offs_k = tl.arange(0, K) # K is fixed at 64

    # Masks
    mask_m = offs_m < M
    mask_n = offs_n < N

    # --- 1. Load Packed Weights (int32) ---
    # Shape: (M, 8) -> Each row has 8 int32s, covering 64 weights
    offs_k_packed = tl.arange(0, 8)
    w_ptr = weight_ptr + (offs_m[:, None] * stride_weight_m + offs_k_packed[None, :] * stride_weight_k)
    w_packed = tl.load(w_ptr, mask=mask_m[:, None]) # (BLOCK_M, 8)

    # --- 2. Load Scales (fp16/fp32) ---
    # Shape: (M, 8) -> One scale per group of 8 weights
    s_ptr = scale_ptr + (offs_m[:, None] * stride_scale_m + offs_k_packed[None, :] * stride_scale_k)
    scales = tl.load(s_ptr, mask=mask_m[:, None]) # (BLOCK_M, 8)

    # --- 3. Load Packed Offsets (int32) ---
    # Shape: (M,) -> One int32 per row, packing 8 int4 offsets
    o_ptr = offset_ptr + (offs_m * stride_offset_m)
    offsets_packed = tl.load(o_ptr, mask=mask_m) # (BLOCK_M,)

    # --- 4. Unpack and Dequantize ---
    # Shift values for unpacking 8 nibbles: 0, 4, ..., 28
    shifts = tl.arange(0, 8) * 4

    # A. Unpack Weights -> (BLOCK_M, 64)
    # w_packed is (BLOCK_M, 8). 
    # Broadcast to (BLOCK_M, 8, 8) to extract 8 nibbles per int32
    w_exp = w_packed[:, :, None]
    shifts_exp = shifts[None, None, :]
    w_unpacked = (w_exp >> shifts_exp) & 0xF
    # Flatten last two dims to get K=64
    w_final = tl.reshape(w_unpacked, (BLOCK_M, 64))

    # B. Unpack Offsets -> (BLOCK_M, 64)
    # offsets_packed is (BLOCK_M). Each int32 has 8 group offsets.
    # Extract nibble 'g' for group 'g'
    o_exp = offsets_packed[:, None] # (BLOCK_M, 1)
    shifts_row = shifts[None, :]    # (1, 8)
    o_groups = (o_exp >> shifts_row) & 0xF # (BLOCK_M, 8)
    # Broadcast group offset to the 8 weights in the group
    o_broad = tl.broadcast_to(o_groups[:, :, None], (BLOCK_M, 8, 8))
    o_final = tl.reshape(o_broad, (BLOCK_M, 64))

    # C. Expand Scales -> (BLOCK_M, 64)
    # scales is (BLOCK_M, 8). Broadcast to (BLOCK_M, 8, 8)
    s_broad = tl.broadcast_to(scales[:, :, None], (BLOCK_M, 8, 8))
    s_final = tl.reshape(s_broad, (BLOCK_M, 64))

    # D. Compute Dequantized A (fp16)
    # A = scale * (w - o)
    # Perform arithmetic in fp32 for precision/safety
    w_f32 = w_final.to(tl.float32)
    o_f32 = o_final.to(tl.float32)
    s_f32 = s_final.to(tl.float32)
    
    a_res = s_f32 * (w_f32 - o_f32)
    a_op = a_res.to(tl.float16)

    # --- 5. Load Activation (fp16) ---
    # Shape: (K, N) -> (64, N)
    # Load block (64, BLOCK_N)
    b_ptr = activation_ptr + (offs_k[:, None] * stride_act_k + offs_n[None, :] * stride_act_n)
    b_val = tl.load(b_ptr, mask=mask_n[None, :], other=0.0)

    # --- 6. Dot Product ---
    acc = tl.dot(a_op, b_val)

    # --- 7. Store Output ---
    out_ptr = output_ptr + (offs_m[:, None] * stride_out_m + offs_n[None, :] * stride_out_n)
    tl.store(out_ptr, acc.to(tl.float16), mask=(mask_m[:, None] & mask_n[None, :]))

def quant_dot(scale: torch.Tensor, offset_packed: torch.Tensor, weight_packed: torch.Tensor, activation: torch.Tensor) -> torch.Tensor:
    M, K_packed = weight_packed.shape
    K = K_packed * 8
    _, N = activation.shape
    
    output = torch.empty((M, N), dtype=torch.float16, device=scale.device)
    
    grid = lambda META: (triton.cdiv(M, META['BLOCK_M']), triton.cdiv(N, META['BLOCK_N']))
    
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