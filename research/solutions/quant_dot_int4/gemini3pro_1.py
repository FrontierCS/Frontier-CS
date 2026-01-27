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
        triton.Config({'BLOCK_M': 16, 'BLOCK_N': 64}, num_stages=1, num_warps=2),
        triton.Config({'BLOCK_M': 32, 'BLOCK_N': 64}, num_stages=1, num_warps=4),
        triton.Config({'BLOCK_M': 64, 'BLOCK_N': 64}, num_stages=1, num_warps=4),
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 64}, num_stages=1, num_warps=4),
        triton.Config({'BLOCK_M': 32, 'BLOCK_N': 128}, num_stages=1, num_warps=4),
        triton.Config({'BLOCK_M': 64, 'BLOCK_N': 128}, num_stages=1, num_warps=4),
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 128}, num_stages=1, num_warps=8),
        triton.Config({'BLOCK_M': 64, 'BLOCK_N': 256}, num_stages=1, num_warps=8),
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 256}, num_stages=1, num_warps=8),
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
    BLOCK_M: tl.constexpr, BLOCK_N: tl.constexpr
):
    pid_m = tl.program_id(0)
    pid_n = tl.program_id(1)
    
    # --------------------------------------------------------------------------
    # Pointers and Masks
    # --------------------------------------------------------------------------
    # Grid handles tiling. We compute offsets for the block.
    offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
    offs_n = pid_n * BLOCK_N + tl.arange(0, BLOCK_N)
    
    m_mask = offs_m < M
    n_mask = offs_n < N
    
    # --------------------------------------------------------------------------
    # Load and Unpack Weights (M, 64)
    # --------------------------------------------------------------------------
    # weight_packed shape: (M, 8). Each int32 contains 8 int4 weights.
    # Total cols = 8 * 8 = 64.
    
    offs_k_packed = tl.arange(0, 8)
    w_ptrs = weight_ptr + (offs_m[:, None] * stride_weight_m) + (offs_k_packed[None, :] * stride_weight_k)
    w_packed = tl.load(w_ptrs, mask=m_mask[:, None])
    
    # Unpack logic:
    # 1. Expand dims to broadcast against the inner packing dim
    # 2. Shift and mask to extract int4s
    # Shape transition: (BLOCK_M, 8) -> (BLOCK_M, 8, 8) -> (BLOCK_M, 64)
    
    w_exp = tl.reshape(w_packed, (BLOCK_M, 8, 1))
    w_exp = tl.broadcast_to(w_exp, (BLOCK_M, 8, 8))
    
    shifts = tl.arange(0, 8) * 4
    shifts = tl.reshape(shifts, (1, 1, 8))
    
    w_unpacked = (w_exp >> shifts) & 0xF
    w_unpacked = tl.reshape(w_unpacked, (BLOCK_M, 64))
    
    # --------------------------------------------------------------------------
    # Load and Unpack Offsets (M, 64)
    # --------------------------------------------------------------------------
    # offset_packed shape: (M,). Each int32 contains 8 int4 offsets (one per group).
    
    o_ptrs = offset_ptr + (offs_m * stride_offset_m)
    o_packed = tl.load(o_ptrs, mask=m_mask)
    
    # Unpack logic:
    # Extract 8 offsets per row -> Broadcast each offset to 8 cols in its group
    o_packed_exp = tl.reshape(o_packed, (BLOCK_M, 1))
    o_shifts = tl.reshape(tl.arange(0, 8) * 4, (1, 8))
    o_groups = (o_packed_exp >> o_shifts) & 0xF
    
    o_groups_exp = tl.reshape(o_groups, (BLOCK_M, 8, 1))
    o_groups_exp = tl.broadcast_to(o_groups_exp, (BLOCK_M, 8, 8))
    o_unpacked = tl.reshape(o_groups_exp, (BLOCK_M, 64))
    
    # --------------------------------------------------------------------------
    # Load Scales (M, 64)
    # --------------------------------------------------------------------------
    # scale shape: (M, 8). One float scale per group.
    
    s_ptrs = scale_ptr + (offs_m[:, None] * stride_scale_m) + (offs_k_packed[None, :] * stride_scale_k)
    s_vals = tl.load(s_ptrs, mask=m_mask[:, None])
    
    s_vals_exp = tl.reshape(s_vals, (BLOCK_M, 8, 1))
    s_vals_exp = tl.broadcast_to(s_vals_exp, (BLOCK_M, 8, 8))
    s_expanded = tl.reshape(s_vals_exp, (BLOCK_M, 64))
    
    # --------------------------------------------------------------------------
    # Compute Dequantized A
    # --------------------------------------------------------------------------
    # A = scale * (weight - offset)
    # Ensure float16 for Tensor Core compatibility with B
    
    a_vals = s_expanded.to(tl.float16) * (w_unpacked.to(tl.float16) - o_unpacked.to(tl.float16))
    
    # --------------------------------------------------------------------------
    # Load Activation B
    # --------------------------------------------------------------------------
    # B shape (64, N). We load the whole K=64 dimension.
    
    offs_k = tl.arange(0, 64)
    b_ptrs = activation_ptr + (offs_k[:, None] * stride_act_k) + (offs_n[None, :] * stride_act_n)
    b_vals = tl.load(b_ptrs, mask=n_mask[None, :], other=0.0)
    
    # --------------------------------------------------------------------------
    # Dot Product and Store
    # --------------------------------------------------------------------------
    
    res = tl.dot(a_vals, b_vals)
    
    c_ptrs = output_ptr + (offs_m[:, None] * stride_out_m) + (offs_n[None, :] * stride_out_n)
    tl.store(c_ptrs, res.to(tl.float16), mask=m_mask[:, None] & n_mask[None, :])

def quant_dot(scale: torch.Tensor, offset_packed: torch.Tensor, weight_packed: torch.Tensor, activation: torch.Tensor) -> torch.Tensor:
    M, _ = scale.shape
    _, N = activation.shape
    # K is fixed to 64 per problem spec
    
    output = torch.empty((M, N), device=scale.device, dtype=torch.float16)
    
    grid = lambda META: (
        triton.cdiv(M, META['BLOCK_M']),
        triton.cdiv(N, META['BLOCK_N'])
    )
    
    _quant_dot_kernel[grid](
        scale, offset_packed, weight_packed, activation, output,
        M, N, 64,
        scale.stride(0), scale.stride(1),
        offset_packed.stride(0),
        weight_packed.stride(0), weight_packed.stride(1),
        activation.stride(0), activation.stride(1),
        output.stride(0), output.stride(1)
    )
    
    return output
"""
        return {"code": code}