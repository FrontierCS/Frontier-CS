class Solution:
    def solve(self, spec_path: str = None) -> dict:
        code = """
import torch
import triton
import triton.language as tl

@triton.jit
def quant_dot_kernel(
    output_ptr,
    scale_ptr,
    offset_ptr,
    weight_ptr,
    act_ptr,
    M: tl.int64,
    N: tl.int64,
    scale_stride_m: tl.int64,
    scale_stride_g: tl.int64,
    offset_stride: tl.int64,
    weight_stride_m: tl.int64,
    weight_stride_g: tl.int64,
    act_stride_k: tl.int64,
    act_stride_n: tl.int64,
    output_stride_m: tl.int64,
    output_stride_n: tl.int64,
    scale_type: tl.constexpr,  # 0: fp16, 1: fp32
    BLOCK_M: tl.constexpr,
    BLOCK_N: tl.constexpr,
    FPINT: tl.constexpr,
    GROUP: tl.constexpr,
):
    pid_m = tl.program_id(0)
    pid_n = tl.program_id(1)
    block_start_m = pid_m * BLOCK_M
    block_start_n = pid_n * BLOCK_N
    rm = tl.arange(0, BLOCK_M)
    rn = tl.arange(0, BLOCK_N)
    m_mask = block_start_m + rm < M
    n_mask = block_start_n + rn < N
    offs_rm = (block_start_m + rm) * offset_stride
    offset_block = tl.load(offset_ptr + offs_rm[:, None], mask=m_mask[:, None], other=0)
    offs_wm = (block_start_m + rm)[:, None] * weight_stride_m
    offs_wg = tl.arange(0, FPINT)[None, :] * weight_stride_g
    offs_w = offs_wm + offs_wg
    w_mask = m_mask[:, None]
    weight_block = tl.load(weight_ptr + offs_w, mask=w_mask, other=0)
    offs_sm = (block_start_m + rm)[:, None] * scale_stride_m
    offs_sg = tl.arange(0, FPINT)[None, :] * scale_stride_g
    offs_s = offs_sm + offs_sg
    s_mask = w_mask
    if scale_type == 0:
        scale_block = tl.load(scale_ptr + offs_s, mask=s_mask, other=0.0, dtype=tl.float16)
    else:
        scale_block = tl.load(scale_ptr + offs_s, mask=s_mask, other=0.0, dtype=tl.float32)
    rk = tl.arange(0, FPINT * GROUP)
    offs_ak = rk[:, None] * act_stride_k
    offs_an = (block_start_n + rn)[None, :] * act_stride_n
    offs_a = offs_ak + offs_an
    a_mask = n_mask[None, :]
    act_block = tl.load(act_ptr + offs_a, mask=a_mask, other=0.0, dtype=tl.float16)
    acc = tl.zeros((BLOCK_M, BLOCK_N), dtype=tl.float32)
    for group in range(FPINT):
        o_packed = offset_block[:, 0]
        o_int4 = ((o_packed >> (group * 4)) & 15).to(tl.float32)[:, None]
        w_packed_g = weight_block[:, group]
        s_g = tl.float32(scale_block[:, group])[:, None]
        for lane in range(GROUP):
            w_int4 = ((w_packed_g >> (lane * 4)) & 15).to(tl.float32)[:, None]
            dequant = s_g * (w_int4 - o_int4)
            k_idx = group * GROUP + lane
            act_k = tl.float32(act_block[k_idx, :])[None, :]
            acc += dequant * act_k
    offs_om = (block_start_m + rm)[:, None] * output_stride_m
    offs_on = (block_start_n + rn)[None, :] * output_stride_n
    offs_o = offs_om + offs_on
    o_mask = m_mask[:, None] & n_mask[None, :]
    out = acc.to(tl.float16)
    tl.store(output_ptr + offs_o, out, mask=o_mask)

def quant_dot(scale: torch.Tensor, offset_packed: torch.Tensor, weight_packed: torch.Tensor, activation: torch.Tensor) -> torch.Tensor:
    M, _ = scale.shape
    N = activation.shape[1]
    output = torch.empty((M, N), dtype=torch.float16, device=scale.device)
    BLOCK_M = 64
    BLOCK_N = 128
    FPINT = 8
    GROUP = 8
    scale_type = 0 if scale.dtype == torch.float16 else 1
    scale_size = 2 if scale_type == 0 else 4
    scale_stride_m = scale.stride(0) * scale_size
    scale_stride_g = scale.stride(1) * scale_size
    offset_stride = offset_packed.stride(0) * 4
    weight_stride_m = weight_packed.stride(0) * 4
    weight_stride_g = weight_packed.stride(1) * 4
    act_size = activation.element_size()
    act_stride_k = activation.stride(0) * act_size
    act_stride_n = activation.stride(1) * act_size
    out_size = 2
    output_stride_m = output.stride(0) * out_size
    output_stride_n = output.stride(1) * out_size
    grid = (triton.cdiv(M, BLOCK_M), triton.cdiv(N, BLOCK_N))
    quant_dot_kernel[grid](
        output.data_ptr(),
        scale.data_ptr(),
        offset_packed.data_ptr(),
        weight_packed.data_ptr(),
        activation.data_ptr(),
        M,
        N,
        scale_stride_m,
        scale_stride_g,
        offset_stride,
        weight_stride_m,
        weight_stride_g,
        act_stride_k,
        act_stride_n,
        output_stride_m,
        output_stride_n,
        scale_type,
        BLOCK_M=BLOCK_M,
        BLOCK_N=BLOCK_N,
        FPINT=FPINT,
        GROUP=GROUP,
    )
    return output
        """
        return {"code": code}