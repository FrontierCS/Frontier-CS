import math
import torch
import triton
import triton.language as tl

FPINT = 8
GROUP = 8
K_CONST = FPINT * GROUP


@triton.jit
def _quant_dot_kernel(
    scale_ptr,          # (M, FPINT) f16/f32
    offset_packed_ptr,  # (M,) i32
    weight_packed_ptr,  # (M, FPINT) i32
    act_ptr,            # (K, N) f16
    out_ptr,            # (M, N) f16
    M, N,               # sizes
    stride_sm, stride_sg,
    stride_wm, stride_wg,
    stride_om,
    stride_bk, stride_bn,
    stride_cm, stride_cn,
    BLOCK_M: tl.constexpr,
    BLOCK_N: tl.constexpr,
):
    pid_m = tl.program_id(0)
    pid_n = tl.program_id(1)

    offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
    offs_n = pid_n * BLOCK_N + tl.arange(0, BLOCK_N)
    m_mask = offs_m < M
    n_mask = offs_n < N

    acc = tl.zeros((BLOCK_M, BLOCK_N), dtype=tl.float32)

    # Prepare utility constants
    lanes = tl.arange(0, FPINT, dtype=tl.int32)  # 0..7
    shifts = lanes * 4
    n_mask_broadcast = n_mask[None, :]

    # Load offsets packed per row (M,) once, reuse across groups
    off_packed = tl.load(offset_packed_ptr + offs_m * stride_om, mask=m_mask, other=0).to(tl.int32)

    for g in range(FPINT):
        # Load weight packed column g
        w_pack = tl.load(weight_packed_ptr + offs_m * stride_wm + g * stride_wg, mask=m_mask, other=0).to(tl.int32)

        # Decode 8 int4 weights -> (BLOCK_M, 8)
        w_vals = (w_pack[:, None] >> shifts[None, :]) & 0xF

        # Decode offset for group g -> (BLOCK_M,)
        o_vals = (off_packed >> tl.full((), 4 * g, dtype=tl.int32)) & 0xF

        # Load scale for group g -> (BLOCK_M,)
        s_vals = tl.load(scale_ptr + offs_m * stride_sm + g * stride_sg, mask=m_mask, other=0.0)

        # Dequantize A tile: ((w - o) * s) -> cast to f16 for tl.dot
        a_tile = (tl.astype(w_vals, tl.float16) - tl.astype(o_vals[:, None], tl.float16)) * tl.astype(s_vals[:, None], tl.float16)

        # Load B tile: rows g*8 .. g*8+7, cols offs_n
        k0 = g * GROUP
        k_range = k0 + tl.arange(0, GROUP)
        b_ptrs = act_ptr + k_range[:, None] * stride_bk + offs_n[None, :] * stride_bn
        b_tile = tl.load(b_ptrs, mask=n_mask_broadcast, other=0).to(tl.float16)

        # Accumulate
        acc += tl.dot(a_tile, b_tile)

    # Store
    out_ptrs = out_ptr + offs_m[:, None] * stride_cm + offs_n[None, :] * stride_cn
    tl.store(out_ptrs, tl.astype(acc, tl.float16), mask=m_mask[:, None] & n_mask_broadcast)


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
    assert activation.is_cuda and weight_packed.is_cuda and offset_packed.is_cuda and scale.is_cuda, "All inputs must be CUDA tensors"
    assert activation.dtype == torch.float16, "activation must be float16"
    assert weight_packed.dtype == torch.int32, "weight_packed must be int32"
    assert offset_packed.dtype == torch.int32, "offset_packed must be int32"
    assert scale.dtype in (torch.float16, torch.float32), "scale must be float16 or float32"

    M = weight_packed.shape[0]
    assert scale.shape[0] == M and offset_packed.shape[0] == M, "M dimension mismatch"
    assert scale.shape[1] == FPINT and weight_packed.shape[1] == FPINT, "Scale and weight_packed second dim must be K/8=8"
    assert activation.shape[0] == K_CONST, "K must be 64"
    N = activation.shape[1]

    out = torch.empty((M, N), device=activation.device, dtype=torch.float16)

    # Strides
    stride_sm, stride_sg = scale.stride()
    stride_wm, stride_wg = weight_packed.stride()
    stride_om = offset_packed.stride(0)
    stride_bk, stride_bn = activation.stride()
    stride_cm, stride_cn = out.stride()

    # Choose block sizes heuristically
    # With K fixed to 64, wider N tiles often help.
    if N >= 256 and M >= 128:
        BLOCK_M = 128
        BLOCK_N = 256
        num_warps = 8
    elif N >= 128 and M >= 64:
        BLOCK_M = 128
        BLOCK_N = 128
        num_warps = 4
    else:
        BLOCK_M = 64
        BLOCK_N = 128
        num_warps = 4

    grid = (triton.cdiv(M, BLOCK_M), triton.cdiv(N, BLOCK_N))
    _quant_dot_kernel[grid](
        scale, offset_packed, weight_packed, activation, out,
        M, N,
        stride_sm, stride_sg,
        stride_wm, stride_wg,
        stride_om,
        stride_bk, stride_bn,
        stride_cm, stride_cn,
        BLOCK_M=BLOCK_M, BLOCK_N=BLOCK_N,
        num_warps=num_warps,
        num_stages=2,
    )
    return out


class Solution:
    def solve(self, spec_path: str = None) -> dict:
        code = r'''
import torch
import triton
import triton.language as tl

FPINT = 8
GROUP = 8
K_CONST = FPINT * GROUP


@triton.jit
def _quant_dot_kernel(
    scale_ptr,          # (M, FPINT) f16/f32
    offset_packed_ptr,  # (M,) i32
    weight_packed_ptr,  # (M, FPINT) i32
    act_ptr,            # (K, N) f16
    out_ptr,            # (M, N) f16
    M, N,               # sizes
    stride_sm, stride_sg,
    stride_wm, stride_wg,
    stride_om,
    stride_bk, stride_bn,
    stride_cm, stride_cn,
    BLOCK_M: tl.constexpr,
    BLOCK_N: tl.constexpr,
):
    pid_m = tl.program_id(0)
    pid_n = tl.program_id(1)

    offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
    offs_n = pid_n * BLOCK_N + tl.arange(0, BLOCK_N)
    m_mask = offs_m < M
    n_mask = offs_n < N

    acc = tl.zeros((BLOCK_M, BLOCK_N), dtype=tl.float32)

    # Prepare utility constants
    lanes = tl.arange(0, FPINT, dtype=tl.int32)  # 0..7
    shifts = lanes * 4
    n_mask_broadcast = n_mask[None, :]

    # Load offsets packed per row (M,) once, reuse across groups
    off_packed = tl.load(offset_packed_ptr + offs_m * stride_om, mask=m_mask, other=0).to(tl.int32)

    for g in range(FPINT):
        # Load weight packed column g
        w_pack = tl.load(weight_packed_ptr + offs_m * stride_wm + g * stride_wg, mask=m_mask, other=0).to(tl.int32)

        # Decode 8 int4 weights -> (BLOCK_M, 8)
        w_vals = (w_pack[:, None] >> shifts[None, :]) & 0xF

        # Decode offset for group g -> (BLOCK_M,)
        o_vals = (off_packed >> tl.full((), 4 * g, dtype=tl.int32)) & 0xF

        # Load scale for group g -> (BLOCK_M,)
        s_vals = tl.load(scale_ptr + offs_m * stride_sm + g * stride_sg, mask=m_mask, other=0.0)

        # Dequantize A tile: ((w - o) * s) -> cast to f16 for tl.dot
        a_tile = (tl.astype(w_vals, tl.float16) - tl.astype(o_vals[:, None], tl.float16)) * tl.astype(s_vals[:, None], tl.float16)

        # Load B tile: rows g*8 .. g*8+7, cols offs_n
        k0 = g * GROUP
        k_range = k0 + tl.arange(0, GROUP)
        b_ptrs = act_ptr + k_range[:, None] * stride_bk + offs_n[None, :] * stride_bn
        b_tile = tl.load(b_ptrs, mask=n_mask_broadcast, other=0).to(tl.float16)

        # Accumulate
        acc += tl.dot(a_tile, b_tile)

    # Store
    out_ptrs = out_ptr + offs_m[:, None] * stride_cm + offs_n[None, :] * stride_cn
    tl.store(out_ptrs, tl.astype(acc, tl.float16), mask=m_mask[:, None] & n_mask_broadcast)


def quant_dot(scale: torch.Tensor, offset_packed: torch.Tensor, weight_packed: torch.Tensor, activation: torch.Tensor) -> torch.Tensor:
    assert activation.is_cuda and weight_packed.is_cuda and offset_packed.is_cuda and scale.is_cuda, "All inputs must be CUDA tensors"
    assert activation.dtype == torch.float16, "activation must be float16"
    assert weight_packed.dtype == torch.int32, "weight_packed must be int32"
    assert offset_packed.dtype == torch.int32, "offset_packed must be int32"
    assert scale.dtype in (torch.float16, torch.float32), "scale must be float16 or float32"

    M = weight_packed.shape[0]
    assert scale.shape[0] == M and offset_packed.shape[0] == M, "M dimension mismatch"
    assert scale.shape[1] == FPINT and weight_packed.shape[1] == FPINT, "Scale and weight_packed second dim must be K/8=8"
    assert activation.shape[0] == K_CONST, "K must be 64"
    N = activation.shape[1]

    out = torch.empty((M, N), device=activation.device, dtype=torch.float16)

    # Strides
    stride_sm, stride_sg = scale.stride()
    stride_wm, stride_wg = weight_packed.stride()
    stride_om = offset_packed.stride(0)
    stride_bk, stride_bn = activation.stride()
    stride_cm, stride_cn = out.stride()

    if N >= 256 and M >= 128:
        BLOCK_M = 128
        BLOCK_N = 256
        num_warps = 8
    elif N >= 128 and M >= 64:
        BLOCK_M = 128
        BLOCK_N = 128
        num_warps = 4
    else:
        BLOCK_M = 64
        BLOCK_N = 128
        num_warps = 4

    grid = (triton.cdiv(M, BLOCK_M), triton.cdiv(N, BLOCK_N))
    _quant_dot_kernel[grid](
        scale, offset_packed, weight_packed, activation, out,
        M, N,
        stride_sm, stride_sg,
        stride_wm, stride_wg,
        stride_om,
        stride_bk, stride_bn,
        stride_cm, stride_cn,
        BLOCK_M=BLOCK_M, BLOCK_N=BLOCK_N,
        num_warps=num_warps,
        num_stages=2,
    )
    return out
'''
        return {"code": code}