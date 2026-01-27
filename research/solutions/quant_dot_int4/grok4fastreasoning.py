import torch
import triton
import triton.language as tl

@triton.jit
def quant_dot_kernel(
    scale_ptr, offset_ptr, weight_ptr, activ_ptr, output_ptr,
    M: tl.int32, N: tl.int32, K: tl.constexpr,
    stride_scale_m: tl.int64,
    stride_scale_k: tl.int64,
    stride_offset_m: tl.int64,
    stride_weight_m: tl.int64,
    stride_weight_k: tl.int64,
    stride_activ_k: tl.int64,
    stride_activ_n: tl.int64,
    stride_out_m: tl.int64,
    stride_out_n: tl.int64,
    BLOCK_M: tl.constexpr,
    BLOCK_N: tl.constexpr,
):
    pid_m = tl.program_id(0)
    pid_n = tl.program_id(1)

    offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
    offs_n = pid_n * BLOCK_N + tl.arange(0, BLOCK_N)

    mask_m = offs_m < M
    mask_n = offs_n < N

    ar_g = tl.arange(0, 8)

    scale_offsets = offs_m[:, None].to(tl.int64) * stride_scale_m + ar_g[None, :].to(tl.int64) * stride_scale_k
    scale_block = tl.load(scale_ptr + scale_offsets, mask=mask_m[:, None], other=0.0)

    weight_offsets = offs_m[:, None].to(tl.int64) * stride_weight_m + ar_g[None, :].to(tl.int64) * stride_weight_k
    weight_block = tl.load(weight_ptr + weight_offsets, mask=mask_m[:, None], other=0).to(tl.int32)

    offset_offsets = offs_m.to(tl.int64) * stride_offset_m
    offset_block = tl.load(offset_ptr + offset_offsets, mask=mask_m, other=0).to(tl.int32)

    o_int4 = tl.zeros((BLOCK_M, 8), dtype=tl.int32)
    for g in range(8):
        shift = g * 4
        vals = (offset_block >> shift) & 15
        signs = (vals >> 3) & 1
        signed = tl.int32(vals) - 16 * tl.int32(signs)
        o_int4[:, g] = signed

    acc = tl.zeros((BLOCK_M, BLOCK_N), dtype=tl.float32)

    for ki in range(K):
        g = ki // 8
        i = ki % 8
        w_pack_g = weight_block[:, g]
        shift = i * 4
        vals = (w_pack_g >> shift) & 15
        signs = (vals >> 3) & 1
        w_signed = tl.int32(vals) - 16 * tl.int32(signs)
        o_g = o_int4[:, g]
        s_g = scale_block[:, g]
        a_k = (tl.float32(w_signed) - tl.float32(o_g)) * tl.float32(s_g)

        activ_offsets = tl.int64(ki) * stride_activ_k + offs_n.to(tl.int64) * stride_activ_n
        b_k = tl.load(activ_ptr + activ_offsets, mask=mask_n, other=0.0).to(tl.float32)

        acc += a_k[:, None] * b_k[None, :]

    mask_out = mask_m[:, None] & mask_n[None, :]
    out_offsets = offs_m[:, None].to(tl.int64) * stride_out_m + offs_n[None, :].to(tl.int64) * stride_out_n
    tl.store(output_ptr + out_offsets, acc.to(tl.float16), mask=mask_out)

def quant_dot(scale: torch.Tensor, offset_packed: torch.Tensor, weight_packed: torch.Tensor, activation: torch.Tensor) -> torch.Tensor:
    M, G = scale.shape
    assert G == 8
    K = 64
    N = activation.shape[1]
    assert activation.shape[0] == K
    device = activation.device
    output = torch.zeros((M, N), dtype=torch.float16, device=device)
    if M == 0 or N == 0:
        return output

    BLOCK_M = 128
    BLOCK_N = 128
    grid = (triton.cdiv(M, BLOCK_M), triton.cdiv(N, BLOCK_N))

    es_scale = scale.element_size()
    stride_scale_m = scale.stride(0) * es_scale
    stride_scale_k = scale.stride(1) * es_scale

    es_offset = offset_packed.element_size()
    stride_offset_m = offset_packed.stride(0) * es_offset

    es_weight = weight_packed.element_size()
    stride_weight_m = weight_packed.stride(0) * es_weight
    stride_weight_k = weight_packed.stride(1) * es_weight

    es_activ = activation.element_size()
    stride_activ_k = activation.stride(0) * es_activ
    stride_activ_n = activation.stride(1) * es_activ

    es_out = output.element_size()
    stride_out_m = output.stride(0) * es_out
    stride_out_n = output.stride(1) * es_out

    quant_dot_kernel[grid](
        scale.data_ptr(),
        offset_packed.data_ptr(),
        weight_packed.data_ptr(),
        activation.data_ptr(),
        output.data_ptr(),
        M,
        N,
        K,
        stride_scale_m,
        stride_scale_k,
        stride_offset_m,
        stride_weight_m,
        stride_weight_k,
        stride_activ_k,
        stride_activ_n,
        stride_out_m,
        stride_out_n,
        BLOCK_M=BLOCK_M,
        BLOCK_N=BLOCK_N,
        num_warps=4,
        num_stages=1,
    )
    return output