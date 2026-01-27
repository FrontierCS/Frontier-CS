import torch
import triton
import triton.language as tl


@triton.autotune(
    configs=[
        triton.Config({'BLOCK_M': 64, 'BLOCK_N': 64, 'GROUP_M': 8}, num_warps=4),
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 128, 'GROUP_M': 8}, num_warps=8),
        triton.Config({'BLOCK_M': 256, 'BLOCK_N': 64, 'GROUP_M': 8}, num_warps=8),
        triton.Config({'BLOCK_M': 64, 'BLOCK_N': 256, 'GROUP_M': 8}, num_warps=8),
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 256, 'GROUP_M': 8}, num_warps=8),
        triton.Config({'BLOCK_M': 256, 'BLOCK_N': 128, 'GROUP_M': 8}, num_warps=8),
    ],
    key=['M', 'N', 'K_TILES'],
)
@triton.jit
def quant_dot_kernel(
    scale_ptr,
    offset_ptr,
    weight_ptr,
    activation_ptr,
    output_ptr,
    M, N, K_TILES,
    stride_ms, stride_ks,
    stride_os,
    stride_ak, stride_an,
    stride_om, stride_on,
    BLOCK_M: tl.constexpr,
    BLOCK_N: tl.constexpr,
    GROUP_M: tl.constexpr,
):
    pid = tl.program_id(0)
    num_pid_m = tl.cdiv(M, BLOCK_M)
    num_pid_n = tl.cdiv(N, BLOCK_N)
    num_pid_in_group = GROUP_M * num_pid_n
    group_id = pid // num_pid_in_group
    first_pid_m = group_id * GROUP_M
    group_size_m = min(num_pid_m - first_pid_m, GROUP_M)
    pid_m = first_pid_m + (pid % group_size_m)
    pid_n = (pid % num_pid_in_group) // group_size_m

    offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
    offs_n = pid_n * BLOCK_N + tl.arange(0, BLOCK_N)
    
    offs_k_tile = tl.arange(0, 8)
    K = K_TILES * 8
    
    scale_ptrs = scale_ptr + offs_m[:, None] * stride_ms + offs_k_tile[None, :] * stride_ks
    weight_ptrs = weight_ptr + offs_m[:, None] * stride_ms + offs_k_tile[None, :] * stride_ks
    
    offset_vals = tl.load(offset_ptr + offs_m)
    
    acc = tl.zeros((BLOCK_M, BLOCK_N), dtype=tl.float32)
    
    for k_tile in range(0, K_TILES):
        scale = tl.load(scale_ptrs).to(tl.float32)
        weights_packed = tl.load(weight_ptrs)
        
        offset_expanded = tl.view(offset_vals, (BLOCK_M, 1))
        offset_int4 = ((offset_expanded >> (offs_k_tile[None, :] * 4)) & 0xF).to(tl.int8)
        
        weights_int4 = ((weights_packed.view(tl.int32).to(tl.int8)[:, :, None] >> 
                        tl.arange(0, 4)[None, None, :]) & 0xF).to(tl.int8)
        weights_int4 = tl.view(weights_int4, (BLOCK_M, 32))
        
        weights_dequant = (weights_int4 - offset_int4[:, :, None].repeat(1, 1, 4).view(BLOCK_M, 32)).to(tl.float32)
        scale_expanded = scale[:, :, None].repeat(1, 1, 4).view(BLOCK_M, 32)
        weights_dequant = weights_dequant * scale_expanded
        
        act_ptrs = activation_ptr + (k_tile * 32 + tl.arange(0, 32)[:, None]) * stride_ak + offs_n[None, :] * stride_an
        activation = tl.load(act_ptrs, mask=tl.arange(0, 32)[:, None] < K - k_tile * 32, other=0.0).to(tl.float32)
        
        acc += tl.dot(weights_dequant, activation)
        
        scale_ptrs += 8 * stride_ks
        weight_ptrs += 8 * stride_ks
    
    offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
    offs_n = pid_n * BLOCK_N + tl.arange(0, BLOCK_N)
    output_ptrs = output_ptr + offs_m[:, None] * stride_om + offs_n[None, :] * stride_on
    
    tl.store(output_ptrs, acc.to(tl.float16), mask=(offs_m[:, None] < M) & (offs_n[None, :] < N))


def quant_dot(
    scale: torch.Tensor,
    offset_packed: torch.Tensor,
    weight_packed: torch.Tensor,
    activation: torch.Tensor,
) -> torch.Tensor:
    M, K_TILES = scale.shape
    K = K_TILES * 8
    N = activation.shape[1]
    
    assert scale.shape == (M, K_TILES)
    assert offset_packed.shape == (M,)
    assert weight_packed.shape == (M, K_TILES)
    assert activation.shape == (K, N)
    assert scale.is_cuda and offset_packed.is_cuda and weight_packed.is_cuda and activation.is_cuda
    
    output = torch.empty((M, N), device=activation.device, dtype=torch.float16)
    
    grid = lambda META: (triton.cdiv(M, META['BLOCK_M']) * triton.cdiv(N, META['BLOCK_N']),)
    
    quant_dot_kernel[grid](
        scale,
        offset_packed,
        weight_packed,
        activation,
        output,
        M, N, K_TILES,
        scale.stride(0), scale.stride(1),
        offset_packed.stride(0),
        activation.stride(0), activation.stride(1),
        output.stride(0), output.stride(1),
    )
    
    return output


class Solution:
    def solve(self, spec_path: str = None) -> dict:
        return {"code": __import__('inspect').getsource(__module__)}