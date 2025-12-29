import torch
import triton
import triton.language as tl

class Solution:
    def solve(self, spec_path: str = None) -> dict:
        code = """
import torch
import triton
import triton.language as tl
import flashinfer

@triton.jit
def fused_qk_rmsnorm_kernel(
    q_ptr, k_ptr, q_o_ptr, k_o_ptr, weight_ptr,
    q_stride_b, q_stride_s, k_stride_b, k_stride_s,
    Hq, Hk, D, B, S, elem_size,
    BLOCK_MAX_N: tl.constexpr = 4096,
    BLOCK_MAX_D: tl.constexpr = 128,
    EPS: tl.float32 = 1e-5
):
    b = tl.program_id(0)
    s = tl.program_id(1)
    if b >= B or s >= S:
        return

    # q
    q_offset = b * q_stride_b + s * q_stride_s
    q_start = q_ptr + (q_offset * elem_size).to(tl.int64)
    offs_q = tl.arange(0, BLOCK_MAX_N)
    mask_q = offs_q < (Hq * D)
    xq = tl.load(q_start + offs_q.to(tl.int64) * elem_size.to(tl.int64), mask=mask_q, other=0.0)

    # k
    k_offset = b * k_stride_b + s * k_stride_s
    k_start = k_ptr + (k_offset * elem_size).to(tl.int64)
    offs_k = tl.arange(0, BLOCK_MAX_N)
    mask_k = offs_k < (Hk * D)
    xk = tl.load(k_start + offs_k.to(tl.int64) * elem_size.to(tl.int64), mask=mask_k, other=0.0)

    # weight
    w_offs = tl.arange(0, BLOCK_MAX_D)
    mask_w = w_offs < D
    weight = tl.load(weight_ptr + w_offs.to(tl.int64) * elem_size.to(tl.int64), mask=mask_w, other=0.0)

    # process q
    for hh in range(Hq):
        start = hh * D
        d_offs = tl.arange(0, BLOCK_MAX_D)
        mask_d = d_offs < D
        vec = xq[start + d_offs]
        sq = vec ** 2
        sum_sq = tl.sum(sq * mask_d.to(sq.dtype))
        inv_rms = tl.rsqrt(sum_sq / D + EPS)
        y_vec = vec * weight * inv_rms * mask_d.to(vec.dtype)
        out_offset = b * (Hq * S * D) + hh * (S * D) + s * D
        out_start = q_o_ptr + (out_offset * elem_size).to(tl.int64)
        tl.store(out_start + d_offs.to(tl.int64) * elem_size.to(tl.int64), y_vec, mask=mask_d)

    # process k
    for hh in range(Hk):
        start = hh * D
        d_offs = tl.arange(0, BLOCK_MAX_D)
        mask_d = d_offs < D
        vec = xk[start + d_offs]
        sq = vec ** 2
        sum_sq = tl.sum(sq * mask_d.to(sq.dtype))
        inv_rms = tl.rsqrt(sum_sq / D + EPS)
        y_vec = vec * weight * inv_rms * mask_d.to(vec.dtype)
        out_offset = b * (Hk * S * D) + hh * (S * D) + s * D
        out_start = k_o_ptr + (out_offset * elem_size).to(tl.int64)
        tl.store(out_start + d_offs.to(tl.int64) * elem_size.to(tl.int64), y_vec, mask=mask_d)

def qknorm(q: torch.Tensor, k: torch.Tensor, norm_weight: torch.Tensor):
    if q.dim() != 4 or k.dim() != 4:
        q_2d = q.contiguous().view(-1, q.shape[-1])
        k_2d = k.contiguous().view(-1, k.shape[-1])
        q_o_2d = torch.empty_like(q_2d)
        k_o_2d = torch.empty_like(k_2d)
        flashinfer.norm.rmsnorm(q_2d, norm_weight, out=q_o_2d)
        flashinfer.norm.rmsnorm(k_2d, norm_weight, out=k_o_2d)
        return q_o_2d.view(q.shape), k_o_2d.view(k.shape)

    Bq, Hq, Sq, Dq = q.shape
    Bk, Hk, Sk, Dk = k.shape
    if Dq != Dk or q.device != k.device or q.dtype != k.dtype or Bq != Bk or Sq != Sk:
        q_o = torch.empty_like(q)
        k_o = torch.empty_like(k)
        flashinfer.norm.rmsnorm(q, norm_weight, out=q_o)
        flashinfer.norm.rmsnorm(k, norm_weight, out=k_o)
        return q_o, k_o

    B, S, D = Bq, Sq, Dq
    q_o = torch.empty_like(q)
    k_o = torch.empty_like(k)
    elem_size = q.element_size()
    grid = (B, S)
    fused_qk_rmsnorm_kernel[grid](
        q.data_ptr(),
        k.data_ptr(),
        q_o.data_ptr(),
        k_o.data_ptr(),
        norm_weight.data_ptr(),
        q.stride(0),
        q.stride(2),
        k.stride(0),
        k.stride(2),
        Hq,
        Hk,
        D,
        B,
        S,
        elem_size
    )
    return q_o, k_o
"""
        return {"code": code}