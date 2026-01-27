import torch
import triton
import triton.language as tl

@triton.jit
def quant_dot_kernel(
    # Pointers to matrices
    scale_ptr, offset_ptr, weight_ptr, act_ptr, output_ptr,
    # Matrix dimensions
    M, N, K,
    # Strides
    stride_sm, stride_sk,
    stride_om, stride_ok,
    stride_wm, stride_wk,
    stride_ak, stride_an,
    stride_om, stride_on,
    # Meta-parameters
    BLOCK_SIZE_M: tl.constexpr,
    BLOCK_SIZE_N: tl.constexpr,
    GROUP_SIZE_M: tl.constexpr,
    UNROLL_N: tl.constexpr
):
    """
    Optimized kernel for quantized matrix multiplication.
    K is fixed at 64 (8 groups of 8 int4 values).
    """
    pid = tl.program_id(0)
    num_pid_n = tl.cdiv(N, BLOCK_SIZE_N)
    pid_m = pid // num_pid_n
    pid_n = (pid % num_pid_n) * BLOCK_SIZE_N
    
    # Offset for this M block
    offs_m = pid_m * BLOCK_SIZE_M + tl.arange(0, BLOCK_SIZE_M)
    offs_n = pid_n + tl.arange(0, BLOCK_SIZE_N)
    
    # Mask for M dimension
    m_mask = offs_m < M
    
    # Allocate accumulators
    acc = tl.zeros((BLOCK_SIZE_M, BLOCK_SIZE_N), dtype=tl.float32)
    
    # Process K dimension in groups of 8 (since K=64, we have 8 groups)
    for k_group in range(8):
        # Load packed weights (8 int4 values per int32)
        w_offs = offs_m[:, None] * stride_wm + k_group * stride_wk
        w_packed = tl.load(weight_ptr + w_offs, mask=m_mask[:, None], other=0)
        
        # Load scales for this group
        s_offs = offs_m[:, None] * stride_sm + k_group * stride_sk
        scale = tl.load(scale_ptr + s_offs, mask=m_mask[:, None], other=1.0)
        
        # Load and unpack offsets
        o_packed = tl.load(offset_ptr + offs_m, mask=m_mask, other=0)
        # Extract offset for this group (4 bits per offset)
        offset = (o_packed >> (k_group * 4)) & 0xF
        # Convert to signed int4 [-8, 7]
        offset = tl.where(offset >= 8, offset - 16, offset)
        offset = offset.to(tl.float32)[:, None]
        
        # Unpack 8 int4 weights from the packed int32
        w_unpacked = tl.zeros((BLOCK_SIZE_M, 8), dtype=tl.int32)
        for i in range(8):
            # Extract 4-bit weight
            w_val = (w_packed >> (i * 4)) & 0xF
            # Convert to signed int4 [-8, 7]
            w_val = tl.where(w_val >= 8, w_val - 16, w_val)
            w_unpacked = tl.where(tl.arange(0, 8)[None, :] == i, w_val, w_unpacked)
        
        # Convert to float and dequantize
        w_float = w_unpacked.to(tl.float32)
        w_dequant = scale * (w_float - offset)
        
        # Load activation block (8xN)
        for k_inner in range(8):
            k_idx = k_group * 8 + k_inner
            a_offs = k_idx * stride_ak + offs_n[None, :] * stride_an
            act = tl.load(act_ptr + a_offs, mask=offs_n[None, :] < N, other=0.0)
            
            # Accumulate
            w_col = w_dequant[:, k_inner:k_inner+1]
            acc += w_col * act
    
    # Convert to fp16 and store
    out_offs = offs_m[:, None] * stride_om + offs_n[None, :] * stride_on
    tl.store(output_ptr + out_offs, acc.to(tl.float16), 
             mask=m_mask[:, None] & (offs_n[None, :] < N))

def quant_dot(scale: torch.Tensor, offset_packed: torch.Tensor, 
              weight_packed: torch.Tensor, activation: torch.Tensor) -> torch.Tensor:
    """
    Quantized matrix multiplication with int4 packed weights.
    
    Args:
        scale: (M, 8) - fp16/fp32 scale per 8-element group
        offset_packed: (M,) - int32 packed 8 int4 offsets
        weight_packed: (M, 8) - int32 packed 8 int4 weights
        activation: (64, N) - fp16 activations
    
    Returns:
        output: (M, N) - fp16 result
    """
    M, _ = scale.shape
    K, N = activation.shape
    assert K == 64, f"K must be 64, got {K}"
    
    output = torch.empty((M, N), device=activation.device, dtype=activation.dtype)
    
    # Tuning parameters optimized for L4 GPU
    BLOCK_SIZE_M = 64
    BLOCK_SIZE_N = 128
    GROUP_SIZE_M = 8
    
    # Grid configuration
    grid = lambda META: (
        triton.cdiv(M, BLOCK_SIZE_M) * triton.cdiv(N, BLOCK_SIZE_N),
    )
    
    # Launch kernel
    quant_dot_kernel[grid](
        scale, offset_packed, weight_packed, activation, output,
        M, N, K,
        scale.stride(0), scale.stride(1),
        offset_packed.stride(0), 0,
        weight_packed.stride(0), weight_packed.stride(1),
        activation.stride(0), activation.stride(1),
        output.stride(0), output.stride(1),
        BLOCK_SIZE_M=BLOCK_SIZE_M,
        BLOCK_SIZE_N=BLOCK_SIZE_N,
        GROUP_SIZE_M=GROUP_SIZE_M,
        UNROLL_N=4
    )
    
    return output

class Solution:
    def solve(self, spec_path: str = None) -> dict:
        return {"code": __import__("inspect").getsource(__import__(__name__))}