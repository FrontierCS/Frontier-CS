import torch
import flashinfer
import triton
import triton.language as tl

class Solution:
    def solve(self, spec_path: str = None) -> dict:
        code = """
import torch
import flashinfer
import triton
import triton.language as tl

def qknorm(q: torch.Tensor, k: torch.Tensor, norm_weight: torch.Tensor):
    dim = q.shape[-1]
    if (len(q.shape) != 4 or len(k.shape) != 4 or
        q.shape[-1] != k.shape[-1] or q.shape[0] != k.shape[0] or
        q.shape[2] != k.shape[2]):
        q_o = torch.empty(q.shape, device=q.device, dtype=q.dtype)
        k_o = torch.empty(k.shape, device=k.device, dtype=k.dtype)
        flashinfer.norm.rmsnorm(q, norm_weight, out=q_o)
        flashinfer.norm.rmsnorm(k, norm_weight, out=k_o)
        return q_o, k_o

    b, h_q, s, _ = q.shape
    _, h_k, _, _ = k.shape
    max_h = max(h_q, h_k)
    q_o = torch.empty_like(q)
    k_o = torch.empty_like(k)

    stride_b_q = q.stride(0)
    stride_h_q = q.stride(1)
    stride_s_q = q.stride(2)
    stride_b_k = k.stride(0)
    stride_h_k = k.stride(1)
    stride_s_k = k.stride(2)

    stride_b_qo = q_o.stride(0)
    stride_h_qo = q_o.stride(1)
    stride_s_qo = q_o.stride(2)
    stride_b_ko = k_o.stride(0)
    stride_h_ko = k_o.stride(1)
    stride_s_ko = k_o.stride(2)

    @triton.jit
    def fused_qk_norm_kernel(
        q_ptr, k_ptr, qo_ptr, ko_ptr, weight_ptr,
        stride_b_q, stride_h_q, stride_s_q,
        stride_b_k, stride_h_k, stride_s_k,
        stride_b_qo, stride_h_qo, stride_s_qo,
        stride_b_ko, stride_h_ko, stride_s_ko,
        h_q, h_k, b, s, dim
    ):
        pid_h = tl.program_id(0)
        pid_s = tl.program_id(1)
        pid_b = tl.program_id(2)

        weight = tl.load(weight_ptr + tl.arange(0, dim))
        w_f = weight.to(tl.float32)
        eps = 1e-6

        if pid_h < h_q:
            offs = pid_b * stride_b_q + pid_h * stride_h_q + pid_s * stride_s_q
            x = tl.load(q_ptr + offs + tl.arange(0, dim))
            x_f = x.to(tl.float32)
            sum_sq = tl.sum(x_f * x_f)
            rms = tl.sqrt(sum_sq * (1.0 / dim) + eps)
            inv_rms = 1.0 / rms
            out = (x_f * (w_f * inv_rms)).to(x.dtype)
            offs_o = pid_b * stride_b_qo + pid_h * stride_h_qo + pid_s * stride_s_qo
            tl.store(qo_ptr + offs_o + tl.arange(0, dim), out)

        if pid_h < h_k:
            offs = pid_b * stride_b_k + pid_h * stride_h_k + pid_s * stride_s_k
            x = tl.load(k_ptr + offs + tl.arange(0, dim))
            x_f = x.to(tl.float32)
            sum_sq = tl.sum(x_f * x_f)
            rms = tl.sqrt(sum_sq * (1.0 / dim) + eps)
            inv_rms = 1.0 / rms
            out = (x_f * (w_f * inv_rms)).to(x.dtype)
            offs_o = pid_b * stride_b_ko + pid_h * stride_h_ko + pid_s * stride_s_ko
            tl.store(ko_ptr + offs_o + tl.arange(0, dim), out)

    fused_qk_norm_kernel[(max_h, s, b)](
        q.data_ptr(), k.data_ptr(), q_o.data_ptr(), k_o.data_ptr(), norm_weight.data_ptr(),
        stride_b_q, stride_h_q, stride_s_q,
        stride_b_k, stride_h_k, stride_s_k,
        stride_b_qo, stride_h_qo, stride_s_qo,
        stride_b_ko, stride_h_ko, stride_s_ko,
        h_q, h_k, b, s, dim
    )
    return q_o, k_o
"""
        return {"code": code}