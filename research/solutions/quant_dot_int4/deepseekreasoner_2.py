import torch
import triton
import triton.language as tl
import os
import tempfile

@triton.jit
def quant_dot_kernel(
    scale_ptr,
    offset_packed_ptr,
    weight_packed_ptr,
    activation_ptr,
    output_ptr,
    M, N,
    stride_sm, stride_sk,
    stride_om,
    stride_wm, stride_wk,
    stride_ak, stride_an,
    stride_out_m, stride_out_n,
    BLOCK_M: tl.constexpr,
    BLOCK_N: tl.constexpr,
    GROUP_K: tl.constexpr = 8,
    FPINT: tl.constexpr = 8,
):
    pid_m = tl.program_id(0)
    pid_n = tl.program_id(1)
    
    offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
    offs_n = pid_n * BLOCK_N + tl.arange(0, BLOCK_N)
    
    offs_k = tl.arange(0, FPINT * GROUP_K)
    offs_k_group = offs_k // GROUP_K
    
    mask_m = offs_m < M
    mask_n = offs_n < N
    
    acc = tl.zeros((BLOCK_M, BLOCK_N), dtype=tl.float32)
    
    scale_ptrs = scale_ptr + offs_m[:, None] * stride_sm + offs_k_group[None, :] * stride_sk
    weight_ptrs = weight_packed_ptr + offs_m[:, None] * stride_wm + offs_k_group[None, :] * stride_wk
    offset_ptrs = offset_packed_ptr + offs_m * stride_om
    
    for _ in range(GROUP_K):
        weight_packed = tl.load(weight_ptrs, mask=mask_m[:, None] & (offs_k_group[None, :] < FPINT), other=0)
        offset_packed = tl.load(offset_ptrs, mask=mask_m, other=0)
        scale = tl.load(scale_ptrs, mask=mask_m[:, None] & (offs_k_group[None, :] < FPINT), other=0)
        
        scale = scale.to(tl.float32)
        
        weight_unpacked = tl.zeros((BLOCK_M, FPINT), dtype=tl.int32)
        offset_unpacked = tl.zeros((BLOCK_M, FPINT), dtype=tl.int32)
        
        for i in range(FPINT):
            shift = i * 4
            mask = (1 << 4) - 1
            weight_unpacked = weight_unpacked.at[:, i].set((weight_packed >> shift) & mask)
            offset_unpacked = offset_unpacked.at[:, i].set((offset_packed >> shift) & mask)
        
        weight_expanded = tl.broadcast_to(weight_unpacked[:, :, None], (BLOCK_M, FPINT, GROUP_K))
        offset_expanded = tl.broadcast_to(offset_unpacked[:, :, None], (BLOCK_M, FPINT, GROUP_K))
        scale_expanded = tl.broadcast_to(scale[:, :, None], (BLOCK_M, FPINT, GROUP_K))
        
        weight_flat = tl.reshape(weight_expanded, (BLOCK_M, FPINT * GROUP_K))
        offset_flat = tl.reshape(offset_expanded, (BLOCK_M, FPINT * GROUP_K))
        scale_flat = tl.reshape(scale_expanded, (BLOCK_M, FPINT * GROUP_K))
        
        activation_ptrs = activation_ptr + offs_k[:, None] * stride_ak + offs_n[None, :] * stride_an
        activation = tl.load(activation_ptrs, mask=(offs_k[:, None] < (FPINT * GROUP_K)) & mask_n[None, :], other=0)
        activation = activation.to(tl.float32)
        
        dequant = scale_flat * (weight_flat.to(tl.float32) - offset_flat.to(tl.float32))
        acc += tl.dot(dequant, activation)
        
        weight_ptrs += stride_wk
        scale_ptrs += stride_sk
    
    acc = acc.to(tl.float16)
    
    out_ptrs = output_ptr + offs_m[:, None] * stride_out_m + offs_n[None, :] * stride_out_n
    tl.store(out_ptrs, acc, mask=mask_m[:, None] & mask_n[None, :])

@triton.jit
def quant_dot_kernel_optimized(
    scale_ptr,
    offset_packed_ptr,
    weight_packed_ptr,
    activation_ptr,
    output_ptr,
    M, N,
    stride_sm, stride_sk,
    stride_om,
    stride_wm, stride_wk,
    stride_ak, stride_an,
    stride_out_m, stride_out_n,
    BLOCK_M: tl.constexpr,
    BLOCK_N: tl.constexpr,
    GROUP_K: tl.constexpr = 8,
    FPINT: tl.constexpr = 8,
):
    pid_m = tl.program_id(0)
    pid_n = tl.program_id(1)
    
    offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
    offs_n = pid_n * BLOCK_N + tl.arange(0, BLOCK_N)
    
    offs_k = tl.arange(0, FPINT * GROUP_K)
    offs_k_group = offs_k // GROUP_K
    
    mask_m = offs_m < M
    mask_n = offs_n < N
    
    acc = tl.zeros((BLOCK_M, BLOCK_N), dtype=tl.float32)
    
    scale_ptrs = scale_ptr + offs_m[:, None] * stride_sm + offs_k_group[None, :] * stride_sk
    weight_ptrs = weight_packed_ptr + offs_m[:, None] * stride_wm + offs_k_group[None, :] * stride_wk
    offset_ptrs = offset_packed_ptr + offs_m * stride_om
    
    for group_idx in range(GROUP_K):
        weight_packed = tl.load(weight_ptrs, mask=mask_m[:, None] & (offs_k_group[None, :] < FPINT), other=0)
        offset_packed = tl.load(offset_ptrs, mask=mask_m, other=0)
        scale = tl.load(scale_ptrs, mask=mask_m[:, None] & (offs_k_group[None, :] < FPINT), other=0)
        
        scale = scale.to(tl.float32)
        
        weight_unpacked = tl.zeros((BLOCK_M, FPINT), dtype=tl.int32)
        offset_unpacked = tl.zeros((BLOCK_M, FPINT), dtype=tl.int32)
        
        for i in tl.range(FPINT):
            shift = i * 4
            mask = 0xF
            weight_unpacked = tl.where(
                tl.full((BLOCK_M, 1), True, dtype=tl.int1),
                weight_unpacked.at[:, i].set((weight_packed >> shift) & mask),
                weight_unpacked
            )
            offset_unpacked = tl.where(
                tl.full((BLOCK_M, 1), True, dtype=tl.int1),
                offset_unpacked.at[:, i].set((offset_packed >> shift) & mask),
                offset_unpacked
            )
        
        k_start = group_idx
        k_indices = offs_k_group * GROUP_K + k_start
        k_mask = k_indices < (FPINT * GROUP_K)
        
        activation_ptrs = activation_ptr + k_indices[:, None] * stride_ak + offs_n[None, :] * stride_an
        activation = tl.load(activation_ptrs, mask=k_mask[:, None] & mask_n[None, :], other=0)
        activation = activation.to(tl.float32)
        
        weight_slice = tl.where(
            tl.full((BLOCK_M, FPINT, 1), True, dtype=tl.int1),
            weight_unpacked[:, :, None],
            weight_unpacked[:, :, None]
        )
        offset_slice = tl.where(
            tl.full((BLOCK_M, FPINT, 1), True, dtype=tl.int1),
            offset_unpacked[:, :, None],
            offset_unpacked[:, :, None]
        )
        scale_slice = tl.where(
            tl.full((BLOCK_M, FPINT, 1), True, dtype=tl.int1),
            scale[:, :, None],
            scale[:, :, None]
        )
        
        dequant_slice = scale_slice * (weight_slice.to(tl.float32) - offset_slice.to(tl.float32))
        dequant_flat = tl.reshape(dequant_slice, (BLOCK_M, FPINT))
        
        acc += tl.dot(dequant_flat, activation)
        
        weight_ptrs += stride_wk
        scale_ptrs += stride_sk
    
    acc = acc.to(tl.float16)
    
    out_ptrs = output_ptr + offs_m[:, None] * stride_out_m + offs_n[None, :] * stride_out_n
    tl.store(out_ptrs, acc, mask=mask_m[:, None] & mask_n[None, :])

@triton.jit
def quant_dot_kernel_final(
    scale_ptr,
    offset_packed_ptr,
    weight_packed_ptr,
    activation_ptr,
    output_ptr,
    M, N,
    stride_sm, stride_sk,
    stride_om,
    stride_wm, stride_wk,
    stride_ak, stride_an,
    stride_out_m, stride_out_n,
    BLOCK_M: tl.constexpr,
    BLOCK_N: tl.constexpr,
    GROUP_K: tl.constexpr = 8,
    FPINT: tl.constexpr = 8,
):
    pid_m = tl.program_id(0)
    pid_n = tl.program_id(1)
    
    offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
    offs_n = pid_n * BLOCK_N + tl.arange(0, BLOCK_N)
    
    offs_k = tl.arange(0, FPINT * GROUP_K)
    offs_k_group = offs_k // GROUP_K
    
    mask_m = offs_m < M
    mask_n = offs_n < N
    
    acc = tl.zeros((BLOCK_M, BLOCK_N), dtype=tl.float32)
    
    for group_idx in range(GROUP_K):
        scale_group_ptrs = scale_ptr + offs_m[:, None] * stride_sm + tl.arange(0, FPINT)[None, :] * stride_sk
        weight_group_ptrs = weight_packed_ptr + offs_m[:, None] * stride_wm + tl.arange(0, FPINT)[None, :] * stride_wk
        offset_ptrs = offset_packed_ptr + offs_m * stride_om
        
        weight_packed = tl.load(weight_group_ptrs, mask=mask_m[:, None] & (tl.arange(0, FPINT)[None, :] < FPINT), other=0)
        offset_packed = tl.load(offset_ptrs, mask=mask_m, other=0)
        scale = tl.load(scale_group_ptrs, mask=mask_m[:, None] & (tl.arange(0, FPINT)[None, :] < FPINT), other=0)
        
        scale = scale.to(tl.float32)
        
        weight_unpacked = tl.zeros((BLOCK_M, FPINT), dtype=tl.int32)
        offset_unpacked = tl.zeros((BLOCK_M, FPINT), dtype=tl.int32)
        
        for i in tl.range(FPINT):
            shift = i * 4
            mask = 0xF
            w_col = (weight_packed >> shift) & mask
            o_col = (offset_packed >> shift) & mask
            weight_unpacked = weight_unpacked.at[:, i].set(w_col)
            offset_unpacked = offset_unpacked.at[:, i].set(o_col)
        
        k_indices = tl.arange(0, FPINT) * GROUP_K + group_idx
        k_mask = k_indices < (FPINT * GROUP_K)
        
        activation_ptrs = activation_ptr + k_indices[:, None] * stride_ak + offs_n[None, :] * stride_an
        activation = tl.load(activation_ptrs, mask=k_mask[:, None] & mask_n[None, :], other=0)
        activation = activation.to(tl.float32)
        
        weight_float = weight_unpacked.to(tl.float32)
        offset_float = offset_unpacked.to(tl.float32)
        dequant = scale * (weight_float - offset_float)
        
        acc += tl.dot(dequant, activation)
    
    acc = acc.to(tl.float16)
    
    out_ptrs = output_ptr + offs_m[:, None] * stride_out_m + offs_n[None, :] * stride_out_n
    tl.store(out_ptrs, acc, mask=mask_m[:, None] & mask_n[None, :])

def quant_dot(
    scale: torch.Tensor,
    offset_packed: torch.Tensor,
    weight_packed: torch.Tensor,
    activation: torch.Tensor,
) -> torch.Tensor:
    M, K_div = scale.shape
    K = K_div * 8
    N = activation.shape[1]
    
    assert K == 64, f"K must be 64, got {K}"
    assert activation.shape[0] == K, f"activation must have shape ({K}, N), got {activation.shape}"
    
    output = torch.empty((M, N), device=activation.device, dtype=activation.dtype)
    
    FPINT = 8
    GROUP_K = 8
    
    if M <= 64:
        BLOCK_M = 64
    elif M <= 128:
        BLOCK_M = 128
    else:
        BLOCK_M = 256
    
    if N <= 64:
        BLOCK_N = 64
    elif N <= 128:
        BLOCK_N = 128
    else:
        BLOCK_N = 256
    
    BLOCK_M = min(BLOCK_M, M)
    BLOCK_N = min(BLOCK_N, N)
    
    grid = (triton.cdiv(M, BLOCK_M), triton.cdiv(N, BLOCK_N))
    
    quant_dot_kernel_final[grid](
        scale,
        offset_packed,
        weight_packed,
        activation,
        output,
        M, N,
        scale.stride(0), scale.stride(1),
        offset_packed.stride(0),
        weight_packed.stride(0), weight_packed.stride(1),
        activation.stride(0), activation.stride(1),
        output.stride(0), output.stride(1),
        BLOCK_M=BLOCK_M,
        BLOCK_N=BLOCK_N,
        GROUP_K=GROUP_K,
        FPINT=FPINT,
        num_warps=4 if BLOCK_N <= 64 else 8,
        num_stages=3,
    )
    
    return output

class Solution:
    def solve(self, spec_path: str = None) -> dict:
        kernel_code = """
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
    M, N,
    stride_sm, stride_sk,
    stride_om,
    stride_wm, stride_wk,
    stride_ak, stride_an,
    stride_out_m, stride_out_n,
    BLOCK_M: tl.constexpr,
    BLOCK_N: tl.constexpr,
    GROUP_K: tl.constexpr = 8,
    FPINT: tl.constexpr = 8,
):
    pid_m = tl.program_id(0)
    pid_n = tl.program_id(1)
    
    offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
    offs_n = pid_n * BLOCK_N + tl.arange(0, BLOCK_N)
    
    mask_m = offs_m < M
    mask_n = offs_n < N
    
    acc = tl.zeros((BLOCK_M, BLOCK_N), dtype=tl.float32)
    
    for group_idx in range(GROUP_K):
        scale_group_ptrs = scale_ptr + offs_m[:, None] * stride_sm + tl.arange(0, FPINT)[None, :] * stride_sk
        weight_group_ptrs = weight_packed_ptr + offs_m[:, None] * stride_wm + tl.arange(0, FPINT)[None, :] * stride_wk
        offset_ptrs = offset_packed_ptr + offs_m * stride_om
        
        weight_packed = tl.load(weight_group_ptrs, mask=mask_m[:, None] & (tl.arange(0, FPINT)[None, :] < FPINT), other=0)
        offset_packed = tl.load(offset_ptrs, mask=mask_m, other=0)
        scale = tl.load(scale_group_ptrs, mask=mask_m[:, None] & (tl.arange(0, FPINT)[None, :] < FPINT), other=0)
        
        scale = scale.to(tl.float32)
        
        weight_unpacked = tl.zeros((BLOCK_M, FPINT), dtype=tl.int32)
        offset_unpacked = tl.zeros((BLOCK_M, FPINT), dtype=tl.int32)
        
        for i in tl.range(FPINT):
            shift = i * 4
            mask = 0xF
            w_col = (weight_packed >> shift) & mask
            o_col = (offset_packed >> shift) & mask
            weight_unpacked = weight_unpacked.at[:, i].set(w_col)
            offset_unpacked = offset_unpacked.at[:, i].set(o_col)
        
        k_indices = tl.arange(0, FPINT) * GROUP_K + group_idx
        k_mask = k_indices < (FPINT * GROUP_K)
        
        activation_ptrs = activation_ptr + k_indices[:, None] * stride_ak + offs_n[None, :] * stride_an
        activation = tl.load(activation_ptrs, mask=k_mask[:, None] & mask_n[None, :], other=0)
        activation = activation.to(tl.float32)
        
        weight_float = weight_unpacked.to(tl.float32)
        offset_float = offset_unpacked.to(tl.float32)
        dequant = scale * (weight_float - offset_float)
        
        acc += tl.dot(dequant, activation)
    
    acc = acc.to(tl.float16)
    
    out_ptrs = output_ptr + offs_m[:, None] * stride_out_m + offs_n[None, :] * stride_out_n
    tl.store(out_ptrs, acc, mask=mask_m[:, None] & mask_n[None, :])

def quant_dot(
    scale: torch.Tensor,
    offset_packed: torch.Tensor,
    weight_packed: torch.Tensor,
    activation: torch.Tensor,
) -> torch.Tensor:
    M, K_div = scale.shape
    K = K_div * 8
    N = activation.shape[1]
    
    assert K == 64, f"K must be 64, got {K}"
    assert activation.shape[0] == K, f"activation must have shape ({K}, N), got {activation.shape}"
    
    output = torch.empty((M, N), device=activation.device, dtype=activation.dtype)
    
    FPINT = 8
    GROUP_K = 8
    
    if M <= 64:
        BLOCK_M = 64
    elif M <= 128:
        BLOCK_M = 128
    elif M <= 256:
        BLOCK_M = 256
    else:
        BLOCK_M = 512
    
    if N <= 64:
        BLOCK_N = 64
    elif N <= 128:
        BLOCK_N = 128
    elif N <= 256:
        BLOCK_N = 256
    else:
        BLOCK_N = 512
    
    BLOCK_M = min(BLOCK_M, M)
    BLOCK_N = min(BLOCK_N, N)
    
    grid = (triton.cdiv(M, BLOCK_M), triton.cdiv(N, BLOCK_N))
    
    num_warps = 4
    if BLOCK_M >= 256 and BLOCK_N >= 256:
        num_warps = 8
    elif BLOCK_M >= 128 and BLOCK_N >= 128:
        num_warps = 8
    
    quant_dot_kernel[grid](
        scale,
        offset_packed,
        weight_packed,
        activation,
        output,
        M, N,
        scale.stride(0), scale.stride(1),
        offset_packed.stride(0),
        weight_packed.stride(0), weight_packed.stride(1),
        activation.stride(0), activation.stride(1),
        output.stride(0), output.stride(1),
        BLOCK_M=BLOCK_M,
        BLOCK_N=BLOCK_N,
        GROUP_K=GROUP_K,
        FPINT=FPINT,
        num_warps=num_warps,
        num_stages=3,
    )
    
    return output
"""
        return {"code": kernel_code}