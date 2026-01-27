import torch
import triton
import triton.language as tl

@triton.jit
def quant_dot_kernel(
    scale_ptr,
    offset_packed_ptr,
    weight_packed_ptr,
    activation_ptr,
    output_ptr,
    M, N, K,
    stride_sm, stride_sk,
    stride_om,
    stride_wm, stride_wk,
    stride_ak, stride_an,
    stride_om_out, stride_on_out,
    BLOCK_M: tl.constexpr,
    BLOCK_N: tl.constexpr,
    GROUP_SIZE: tl.constexpr,
    FPINT: tl.constexpr,
    ACC_TYPE: tl.constexpr,
):
    pid_m = tl.program_id(0)
    pid_n = tl.program_id(1)
    
    m_off = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
    n_off = pid_n * BLOCK_N + tl.arange(0, BLOCK_N)
    
    # Mask for M and N dimensions
    m_mask = m_off < M
    n_mask = n_off < N
    
    # Accumulator initialization
    acc = tl.zeros((BLOCK_M, BLOCK_N), dtype=ACC_TYPE)
    
    # Process K dimension in groups of 8 (64 total, 8 groups of 8)
    for group in range(FPINT):
        # Load scale for this group
        scale_ptrs = scale_ptr + m_off[:, None] * stride_sm + group * stride_sk
        scales = tl.load(scale_ptrs, mask=m_mask[:, None], other=0.0)
        
        # Load and unpack offset for this group
        offset_val = tl.load(offset_packed_ptr + m_off, mask=m_mask, other=0)
        # Extract 4-bit offset for this group (8 offsets packed in int32)
        offset_int4 = (offset_val >> (group * 4)) & 0xF
        # Convert to signed: values 8-15 represent -8 to -1
        offset = tl.where(offset_int4 >= 8, offset_int4 - 16, offset_int4)
        offset = offset.to(ACC_TYPE)
        
        # Load packed weights for this group
        w_ptrs = weight_packed_ptr + m_off[:, None] * stride_wm + group * stride_wk
        packed_weights = tl.load(w_ptrs, mask=m_mask[:, None], other=0)
        
        # Process 8 weight values in this group
        for sub_k in range(GROUP_SIZE):
            k_idx = group * GROUP_SIZE + sub_k
            
            # Extract 4-bit weight
            shift = sub_k * 4
            weight_int4 = (packed_weights >> shift) & 0xF
            # Convert to signed
            weight = tl.where(weight_int4 >= 8, weight_int4 - 16, weight_int4)
            weight = weight.to(ACC_TYPE)
            
            # Dequantize: scale * (weight - offset)
            dequant_weight = scales * (weight - offset[:, None])
            
            # Load activation for this k position
            a_ptrs = activation_ptr + k_idx * stride_ak + n_off[None, :] * stride_an
            activation = tl.load(a_ptrs, mask=n_mask[None, :], other=0.0).to(ACC_TYPE)
            
            # Accumulate
            acc += dequant_weight * activation
    
    # Convert accumulator to fp16 and store
    output_ptrs = output_ptr + m_off[:, None] * stride_om_out + n_off[None, :] * stride_on_out
    tl.store(output_ptrs, acc.to(tl.float16), mask=m_mask[:, None] & n_mask[None, :])

def quant_dot(
    scale: torch.Tensor,
    offset_packed: torch.Tensor,
    weight_packed: torch.Tensor,
    activation: torch.Tensor,
) -> torch.Tensor:
    """
    Optimized quantized matrix multiplication with int4 packed weights.
    
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
    M, _ = scale.shape
    K, N = activation.shape
    output = torch.empty((M, N), device=activation.device, dtype=torch.float16)
    
    # Constants from problem specification
    FPINT = 8
    GROUP_SIZE = 8
    assert K == FPINT * GROUP_SIZE, f"K must be {FPINT * GROUP_SIZE}, got {K}"
    
    # Grid configuration
    BLOCK_M = 128
    BLOCK_N = 64
    grid = (triton.cdiv(M, BLOCK_M), triton.cdiv(N, BLOCK_N))
    
    # Choose accumulator type based on scale dtype
    ACC_TYPE = tl.float32 if scale.dtype == torch.float32 else tl.float16
    
    quant_dot_kernel[grid](
        scale,
        offset_packed,
        weight_packed,
        activation,
        output,
        M, N, K,
        scale.stride(0), scale.stride(1),
        offset_packed.stride(0),
        weight_packed.stride(0), weight_packed.stride(1),
        activation.stride(0), activation.stride(1),
        output.stride(0), output.stride(1),
        BLOCK_M=BLOCK_M,
        BLOCK_N=BLOCK_N,
        GROUP_SIZE=GROUP_SIZE,
        FPINT=FPINT,
        ACC_TYPE=ACC_TYPE,
        num_warps=8,
        num_stages=3,
    )
    
    return output

class Solution:
    def solve(self, spec_path: str = None) -> dict:
        return {"code": """import torch
import triton
import triton.language as tl

@triton.jit
def quant_dot_kernel(
    scale_ptr,
    offset_packed_ptr,
    weight_packed_ptr,
    activation_ptr,
    output_ptr,
    M, N, K,
    stride_sm, stride_sk,
    stride_om,
    stride_wm, stride_wk,
    stride_ak, stride_an,
    stride_om_out, stride_on_out,
    BLOCK_M: tl.constexpr,
    BLOCK_N: tl.constexpr,
    GROUP_SIZE: tl.constexpr,
    FPINT: tl.constexpr,
    ACC_TYPE: tl.constexpr,
):
    pid_m = tl.program_id(0)
    pid_n = tl.program_id(1)
    
    m_off = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
    n_off = pid_n * BLOCK_N + tl.arange(0, BLOCK_N)
    
    m_mask = m_off < M
    n_mask = n_off < N
    
    acc = tl.zeros((BLOCK_M, BLOCK_N), dtype=ACC_TYPE)
    
    for group in range(FPINT):
        scale_ptrs = scale_ptr + m_off[:, None] * stride_sm + group * stride_sk
        scales = tl.load(scale_ptrs, mask=m_mask[:, None], other=0.0)
        
        offset_val = tl.load(offset_packed_ptr + m_off, mask=m_mask, other=0)
        offset_int4 = (offset_val >> (group * 4)) & 0xF
        offset = tl.where(offset_int4 >= 8, offset_int4 - 16, offset_int4)
        offset = offset.to(ACC_TYPE)
        
        w_ptrs = weight_packed_ptr + m_off[:, None] * stride_wm + group * stride_wk
        packed_weights = tl.load(w_ptrs, mask=m_mask[:, None], other=0)
        
        for sub_k in range(GROUP_SIZE):
            k_idx = group * GROUP_SIZE + sub_k
            
            shift = sub_k * 4
            weight_int4 = (packed_weights >> shift) & 0xF
            weight = tl.where(weight_int4 >= 8, weight_int4 - 16, weight_int4)
            weight = weight.to(ACC_TYPE)
            
            dequant_weight = scales * (weight - offset[:, None])
            
            a_ptrs = activation_ptr + k_idx * stride_ak + n_off[None, :] * stride_an
            activation = tl.load(a_ptrs, mask=n_mask[None, :], other=0.0).to(ACC_TYPE)
            
            acc += dequant_weight * activation
    
    output_ptrs = output_ptr + m_off[:, None] * stride_om_out + n_off[None, :] * stride_on_out
    tl.store(output_ptrs, acc.to(tl.float16), mask=m_mask[:, None] & n_mask[None, :])

def quant_dot(
    scale: torch.Tensor,
    offset_packed: torch.Tensor,
    weight_packed: torch.Tensor,
    activation: torch.Tensor,
) -> torch.Tensor:
    M, _ = scale.shape
    K, N = activation.shape
    output = torch.empty((M, N), device=activation.device, dtype=torch.float16)
    
    FPINT = 8
    GROUP_SIZE = 8
    assert K == FPINT * GROUP_SIZE, f"K must be {FPINT * GROUP_SIZE}, got {K}"
    
    BLOCK_M = 128
    BLOCK_N = 64
    grid = (triton.cdiv(M, BLOCK_M), triton.cdiv(N, BLOCK_N))
    
    ACC_TYPE = tl.float32 if scale.dtype == torch.float32 else tl.float16
    
    quant_dot_kernel[grid](
        scale,
        offset_packed,
        weight_packed,
        activation,
        output,
        M, N, K,
        scale.stride(0), scale.stride(1),
        offset_packed.stride(0),
        weight_packed.stride(0), weight_packed.stride(1),
        activation.stride(0), activation.stride(1),
        output.stride(0), output.stride(1),
        BLOCK_M=BLOCK_M,
        BLOCK_N=BLOCK_N,
        GROUP_SIZE=GROUP_SIZE,
        FPINT=FPINT,
        ACC_TYPE=ACC_TYPE,
        num_warps=8,
        num_stages=3,
    )
    
    return output
"""}