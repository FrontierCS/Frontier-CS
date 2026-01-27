import torch
import triton
import triton.language as tl


@triton.jit
def _quant_dot_kernel(
    scale_ptr, offset_ptr, weight_ptr, act_ptr, out_ptr,
    M, N,
    scale_stride_m, scale_stride_g,
    offset_stride_m,
    weight_stride_m, weight_stride_g,
    act_stride_k, act_stride_n,
    out_stride_m, out_stride_n,
    BLOCK_M: tl.constexpr, BLOCK_N: tl.constexpr
):
    pid_m = tl.program_id(0)
    pid_n = tl.program_id(1)

    offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
    offs_n = pid_n * BLOCK_N + tl.arange(0, BLOCK_N)
    mask_m = offs_m < M
    mask_n = offs_n < N

    acc = tl.zeros((BLOCK_M, BLOCK_N), dtype=tl.float32)

    # Preload offset packed per row (int32)
    off_pack = tl.load(offset_ptr + offs_m * offset_stride_m, mask=mask_m, other=0)

    # Precompute shifts [0,4,8,...,28] for nibble extraction
    shifts = tl.arange(0, 8, dtype=tl.int32) * 4

    # Loop over the 8 groups (K/8 = 8)
    for j in range(8):
        # Load scale per row for this group j
        s_vec = tl.load(scale_ptr + offs_m * scale_stride_m + j * scale_stride_g, mask=mask_m, other=0).to(tl.float32)

        # Extract offset nibble for this group j
        off_j = tl.bitwise_and(tl.shr(off_pack, j * 4), 0xF).to(tl.int32)

        # Load weight pack for this group j per row
        w_pack = tl.load(weight_ptr + offs_m * weight_stride_m + j * weight_stride_g, mask=mask_m, other=0)

        # Expand to (BLOCK_M, 8) and extract 8 int4 weights per pack
        w_pack_exp = tl.view(w_pack, (BLOCK_M, 1))
        nibs = tl.bitwise_and(tl.shr(w_pack_exp, shifts[None, :]), 0xF).to(tl.int32)  # (BM, 8)

        # Dequantize: (w - off_j) * scale
        off_mat = tl.view(off_j, (BLOCK_M, 1)).to(tl.float32)
        s_mat = tl.view(s_vec, (BLOCK_M, 1))
        deq = (nibs.to(tl.float32) - off_mat) * s_mat  # (BM, 8), f32

        # Load activations for k indices j*8 + [0..7]
        k_idx = j * 8 + tl.arange(0, 8)
        act_ptrs = act_ptr + k_idx[:, None] * act_stride_k + offs_n[None, :] * act_stride_n
        act_tile = tl.load(act_ptrs, mask=(k_idx[:, None] < 64) & mask_n[None, :], other=0).to(tl.float32)  # (8, BN)

        # Accumulate: deq (BM,8) @ act_tile (8,BN) => (BM,BN)
        acc += tl.dot(deq, act_tile)

    # Store result as fp16
    out_ptrs = out_ptr + offs_m[:, None] * out_stride_m + offs_n[None, :] * out_stride_n
    tl.store(out_ptrs, acc.to(tl.float16), mask=mask_m[:, None] & mask_n[None, :])


def quant_dot(scale: torch.Tensor, offset_packed: torch.Tensor, weight_packed: torch.Tensor, activation: torch.Tensor) -> torch.Tensor:
    FPINT = 8
    GROUP = 8
    K = FPINT * GROUP  # 64

    assert scale.is_cuda and offset_packed.is_cuda and weight_packed.is_cuda and activation.is_cuda
    assert activation.dtype == torch.float16
    assert weight_packed.dtype == torch.int32
    assert offset_packed.dtype == torch.int32
    assert scale.dtype in (torch.float16, torch.float32)

    M = scale.shape[0]
    assert scale.shape[1] == K // 8
    assert weight_packed.shape == (M, K // 8)
    assert activation.shape[0] == K
    N = activation.shape[1]
    assert offset_packed.shape[0] == M

    # Allocate output
    out = torch.empty((M, N), dtype=torch.float16, device=activation.device)

    # Strides
    scale_stride_m = scale.stride(0)
    scale_stride_g = scale.stride(1)
    offset_stride_m = offset_packed.stride(0)
    weight_stride_m = weight_packed.stride(0)
    weight_stride_g = weight_packed.stride(1)
    act_stride_k = activation.stride(0)
    act_stride_n = activation.stride(1)
    out_stride_m = out.stride(0)
    out_stride_n = out.stride(1)

    # Tiling parameters
    # Choose larger N tile when N is big to improve bandwidth usage
    BLOCK_M = 64
    BLOCK_N = 256 if N >= 256 else 128

    grid = (triton.cdiv(M, BLOCK_M), triton.cdiv(N, BLOCK_N))

    _quant_dot_kernel[grid](
        scale, offset_packed, weight_packed, activation, out,
        M, N,
        scale_stride_m, scale_stride_g,
        offset_stride_m,
        weight_stride_m, weight_stride_g,
        act_stride_k, act_stride_n,
        out_stride_m, out_stride_n,
        BLOCK_M=BLOCK_M, BLOCK_N=BLOCK_N,
        num_warps=8 if BLOCK_N >= 256 else 4,
        num_stages=2,
    )

    return out


class Solution:
    def solve(self, spec_path: str = None) -> dict:
        code = r'''
import torch
import triton
import triton.language as tl


@triton.jit
def _quant_dot_kernel(
    scale_ptr, offset_ptr, weight_ptr, act_ptr, out_ptr,
    M, N,
    scale_stride_m, scale_stride_g,
    offset_stride_m,
    weight_stride_m, weight_stride_g,
    act_stride_k, act_stride_n,
    out_stride_m, out_stride_n,
    BLOCK_M: tl.constexpr, BLOCK_N: tl.constexpr
):
    pid_m = tl.program_id(0)
    pid_n = tl.program_id(1)

    offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
    offs_n = pid_n * BLOCK_N + tl.arange(0, BLOCK_N)
    mask_m = offs_m < M
    mask_n = offs_n < N

    acc = tl.zeros((BLOCK_M, BLOCK_N), dtype=tl.float32)

    # Preload offset packed per row (int32)
    off_pack = tl.load(offset_ptr + offs_m * offset_stride_m, mask=mask_m, other=0)

    # Precompute shifts [0,4,8,...,28] for nibble extraction
    shifts = tl.arange(0, 8, dtype=tl.int32) * 4

    # Loop over the 8 groups (K/8 = 8)
    for j in range(8):
        # Load scale per row for this group j
        s_vec = tl.load(scale_ptr + offs_m * scale_stride_m + j * scale_stride_g, mask=mask_m, other=0).to(tl.float32)

        # Extract offset nibble for this group j
        off_j = tl.bitwise_and(tl.shr(off_pack, j * 4), 0xF).to(tl.int32)

        # Load weight pack for this group j per row
        w_pack = tl.load(weight_ptr + offs_m * weight_stride_m + j * weight_stride_g, mask=mask_m, other=0)

        # Expand to (BLOCK_M, 8) and extract 8 int4 weights per pack
        w_pack_exp = tl.view(w_pack, (BLOCK_M, 1))
        nibs = tl.bitwise_and(tl.shr(w_pack_exp, shifts[None, :], ), 0xF).to(tl.int32)  # (BM, 8)

        # Dequantize: (w - off_j) * scale
        off_mat = tl.view(off_j, (BLOCK_M, 1)).to(tl.float32)
        s_mat = tl.view(s_vec, (BLOCK_M, 1))
        deq = (nibs.to(tl.float32) - off_mat) * s_mat  # (BM, 8), f32

        # Load activations for k indices j*8 + [0..7]
        k_idx = j * 8 + tl.arange(0, 8)
        act_ptrs = act_ptr + k_idx[:, None] * act_stride_k + offs_n[None, :] * act_stride_n
        act_tile = tl.load(act_ptrs, mask=(k_idx[:, None] < 64) & mask_n[None, :], other=0).to(tl.float32)  # (8, BN)

        # Accumulate: deq (BM,8) @ act_tile (8,BN) => (BM,BN)
        acc += tl.dot(deq, act_tile)

    # Store result as fp16
    out_ptrs = out_ptr + offs_m[:, None] * out_stride_m + offs_n[None, :] * out_stride_n
    tl.store(out_ptrs, acc.to(tl.float16), mask=mask_m[:, None] & mask_n[None, :])


def quant_dot(scale: torch.Tensor, offset_packed: torch.Tensor, weight_packed: torch.Tensor, activation: torch.Tensor) -> torch.Tensor:
    FPINT = 8
    GROUP = 8
    K = FPINT * GROUP  # 64

    assert scale.is_cuda and offset_packed.is_cuda and weight_packed.is_cuda and activation.is_cuda
    assert activation.dtype == torch.float16
    assert weight_packed.dtype == torch.int32
    assert offset_packed.dtype == torch.int32
    assert scale.dtype in (torch.float16, torch.float32)

    M = scale.shape[0]
    assert scale.shape[1] == K // 8
    assert weight_packed.shape == (M, K // 8)
    assert activation.shape[0] == K
    N = activation.shape[1]
    assert offset_packed.shape[0] == M

    # Allocate output
    out = torch.empty((M, N), dtype=torch.float16, device=activation.device)

    # Strides
    scale_stride_m = scale.stride(0)
    scale_stride_g = scale.stride(1)
    offset_stride_m = offset_packed.stride(0)
    weight_stride_m = weight_packed.stride(0)
    weight_stride_g = weight_packed.stride(1)
    act_stride_k = activation.stride(0)
    act_stride_n = activation.stride(1)
    out_stride_m = out.stride(0)
    out_stride_n = out.stride(1)

    # Tiling parameters
    BLOCK_M = 64
    BLOCK_N = 256 if N >= 256 else 128

    grid = (triton.cdiv(M, BLOCK_M), triton.cdiv(N, BLOCK_N))

    _quant_dot_kernel[grid](
        scale, offset_packed, weight_packed, activation, out,
        M, N,
        scale_stride_m, scale_stride_g,
        offset_stride_m,
        weight_stride_m, weight_stride_g,
        act_stride_k, act_stride_n,
        out_stride_m, out_stride_n,
        BLOCK_M=BLOCK_M, BLOCK_N=BLOCK_N,
        num_warps=8 if BLOCK_N >= 256 else 4,
        num_stages=2,
    )

    return out
'''
        return {"code": code}