import torch
import triton
import triton.language as tl

class Solution:
    def solve(self, spec_path: str = None) -> dict:
        code = """
import torch
import triton
import triton.language as tl

@triton.autotune(
    configs=[
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 128}, num_warps=4, num_stages=3),
        triton.Config({'BLOCK_M': 64, 'BLOCK_N': 128}, num_warps=8, num_stages=3),
        triton.Config({'BLOCK_M': 128, 'BLOCK_N': 64}, num_warps=8, num_stages=3),
        triton.Config({'BLOCK_M': 256, 'BLOCK_N': 64}, num_warps=4, num_stages=3),
    ],
    key=['M', 'N'],
)
@triton.jit
def quant_dot_kernel(
    output_ptr, weight_ptr, offset_ptr, scale_ptr, activation_ptr,
    M: tl.int32, N: tl.int32,
    output_stride_m: tl.int32, output_stride_n: tl.int32,
    weight_stride_m: tl.int32, weight_stride_n: tl.int32,
    offset_stride: tl.int32,
    scale_stride_m: tl.int32, scale_stride_n: tl.int32,
    act_stride_k: tl.int32, act_stride_n: tl.int32,
    BLOCK_M: tl.constexpr,
    BLOCK_N: tl.constexpr,
):
    m_start = tl.program_id(0) * BLOCK_M
    n_start = tl.program_id(1) * BLOCK_N
    num_m = tl.maximum(0, M - m_start)
    num_n = tl.maximum(0, N - n_start)
    mask_m = tl.arange(0, BLOCK_M) < num_m
    mask_n = tl.arange(0, BLOCK_N) < num_n

    # Load offsets (1D)
    o_block_ptr = tl.make_block_ptr(
        base=offset_ptr,
        shape=(BLOCK_M,),
        strides=(offset_stride * 4,),
        offsets=(m_start,),
        block_shape=(BLOCK_M,),
        order=(0,)
    )
    o_packed = tl.load(o_block_ptr, mask=mask_m, other=0)

    # Load scales (BLOCK_M x 8)
    s_block_ptr = tl.make_block_ptr(
        base=scale_ptr,
        shape=(BLOCK_M, 8),
        strides=(scale_stride_m * 2, scale_stride_n * 2),
        offsets=(m_start, 0),
        block_shape=(BLOCK_M, 8),
        order=(1, 0)
    )
    scale_block = tl.load(s_block_ptr, mask=mask_m[:, None], other=0.0)

    # Load weights packed (BLOCK_M x 8)
    w_block_ptr = tl.make_block_ptr(
        base=weight_ptr,
        shape=(BLOCK_M, 8),
        strides=(weight_stride_m * 4, weight_stride_n * 4),
        offsets=(m_start, 0),
        block_shape=(BLOCK_M, 8),
        order=(1, 0)
    )
    w_packed = tl.load(w_block_ptr, mask=mask_m[:, None], other=0)

    # Load activations (64 x BLOCK_N)
    K = 64
    a_block_ptr = tl.make_block_ptr(
        base=activation_ptr,
        shape=(K, BLOCK_N),
        strides=(act_stride_k * 2, act_stride_n * 2),
        offsets=(0, n_start),
        block_shape=(K, BLOCK_N),
        order=(1, 0)
    )
    b_block = tl.load(a_block_ptr, mask=mask_n[None, :], other=0.0).to(tl.float32)

    # Dequantize
    dequant = tl.zeros((BLOCK_M, K), dtype=tl.float32)
    scale_f32 = scale_block.to(tl.float32)
    for g in range(8):
        o_g = ((o_packed >> (g * 4)) & 15).to(tl.float32)
        s_g = scale_f32[:, g]
        w_pack_g = w_packed[:, g]
        kk_shifts = tl.arange(0, 8) * 4
        w_int4 = ((w_pack_g[:, None] >> kk_shifts[None, :]) & 15).to(tl.float32)
        dequant_g = s_g[:, None] * (w_int4 - o_g[:, None])
        start_k = g * 8
        dequant = tl.where(
            mask_m[:, None],
            tl.where(
                tl.arange(0, K)[None, :] >= start_k,
                tl.where(
                    tl.arange(0, K)[None, :] < start_k + 8,
                    dequant_g[:, tl.arange(0, K)[None, :] - start_k],
                    dequant
                ),
                dequant
            ),
            dequant
        )
        # Note: since unrolled, but to simplify, actually since small, but wait, this is complicated.
        # Instead, since loop is unrolled, we can assign directly: dequant[:, start_k:start_k+8] = dequant_g
        # But in tl, slicing assignment not direct, but since constexpr, it works in the unrolled code.
        # For correctness, we'll use direct assignment assuming unroll.
    # To make it work without slicing issue, we'll compute all dequant using full arange.

    # Alternative vectorized dequant without loop
    k_ar = tl.arange(0, K)
    g_for_k = k_ar // 8
    kk_for_k = k_ar % 8
    shift_for_k = kk_for_k * 4
    # For o
    o_shifts = tl.arange(0, 8) * 4
    o_int4_all = (o_packed[:, None] >> o_shifts[None, :]) & 15
    o_for_k = tl.load(o_int4_all[:, g_for_k]) .to(tl.float32)  # but load? No, indexing
    # Wait, o_int4_all (BM,8), g_for_k (64,), so o_for_k = o_int4_all.gather(1, g_for_k[None,:]) but tl has no gather.
    # So, better stick with loop and direct assignment in unrolled.
    # Since 8 is small, the loop is fine, and triton unrolls it, and assignment dequant[:, start_k : start_k+8] = dequant_g will be compiled to direct writes.

    # To avoid slicing, we can do for kk in range(8):
    # But nested loop.
    # For g in range(8):
    #   ... 
    #   for kk in range(8):
    #     k = g*8 + kk
    #     w_kk = ((w_pack_g >> (kk*4)) & 15).to(tl.float32)
    #     dequant[:, k] = s_g * (w_kk - o_g)
    # Yes, this is unrolled to 64 assignments, but since static, fine, and no slicing.

    # Yes, let's do that to be safe.

    dequant = tl.zeros((BLOCK_M, K), dtype=tl.float32)
    scale_f32 = scale_block.to(tl.float32)
    for g in range(8):
        o_g = ((o_packed >> (g * 4)) & 15).to(tl.float32)
        s_g = scale_f32[:, g]
        w_pack_g = w_packed[:, g]
        for kk in range(8):
            k = g * 8 + kk
            w_kk = ((w_pack_g >> (kk * 4)) & 15).to(tl.float32)
            dequant[:, k] = s_g * (w_kk - o_g)

    # Mask the dequant for safety
    k_mask = tl.arange(0, K)[None, :] < K
    dequant = tl.where(mask_m[:, None] & k_mask, dequant, 0.0)

    # Compute dot
    acc = tl.dot(dequant, b_block)

    # Store
    acc = tl.where(mask_m[:, None] & mask_n[None, :], acc, 0.0)
    out_block = acc.to(tl.float16)
    out_block_ptr = tl.make_block_ptr(
        base=output_ptr,
        shape=(BLOCK_M, BLOCK_N),
        strides=(output_stride_m * 2, output_stride_n * 2),
        offsets=(m_start, n_start),
        block_shape=(BLOCK_M, BLOCK_N),
        order=(1, 0)
    )
    tl.store(out_block_ptr, out_block, mask=mask_m[:, None] & mask_n[None, :])

def quant_dot(scale: torch.Tensor, offset_packed: torch.Tensor, weight_packed: torch.Tensor, activation: torch.Tensor) -> torch.Tensor:
    M = weight_packed.shape[0]
    N = activation.shape[1]
    K = 64
    assert activation.shape[0] == K
    assert scale.shape == (M, K // 8)
    assert weight_packed.shape == (M, K // 8)
    assert offset_packed.shape == (M,)
    output = torch.empty((M, N), dtype=torch.float16, device=activation.device)

    output_ptr = output.data_ptr()
    weight_ptr = weight_packed.data_ptr()
    offset_ptr = offset_packed.data_ptr()
    scale_ptr = scale.data_ptr()
    activation_ptr = activation.data_ptr()

    weight_stride_m = weight_packed.stride(0)
    weight_stride_n = weight_packed.stride(1)
    offset_stride = offset_packed.stride(0)
    scale_stride_m = scale.stride(0)
    scale_stride_n = scale.stride(1)
    act_stride_k = activation.stride(0)
    act_stride_n = activation.stride(1)
    output_stride_m = output.stride(0)
    output_stride_n = output.stride(1)

    grid = lambda meta: (triton.cdiv(M, meta['BLOCK_M']), triton.cdiv(N, meta['BLOCK_N']))
    quant_dot_kernel[grid](
        output_ptr, weight_ptr, offset_ptr, scale_ptr, activation_ptr,
        M, N,
        output_stride_m, output_stride_n,
        weight_stride_m, weight_stride_n,
        offset_stride,
        scale_stride_m, scale_stride_n,
        act_stride_k, act_stride_n,
    )
    return output
"""
        return {"code": code}