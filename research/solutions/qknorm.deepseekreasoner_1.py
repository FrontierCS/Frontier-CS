import torch
import flashinfer
import triton
import triton.language as tl
from typing import Optional, Tuple

@triton.jit
def _rmsnorm_kernel(
    x_ptr,
    weight_ptr,
    output_ptr,
    N: tl.constexpr,
    eps: tl.constexpr,
    stride_x_batch,
    stride_x_n,
    stride_output_batch,
    stride_output_n,
    BLOCK_SIZE_N: tl.constexpr,
    USE_VECTOR_LOAD: tl.constexpr,
    RESIDUAL_OUT: tl.constexpr,
):
    pid_batch = tl.program_id(0)
    
    if USE_VECTOR_LOAD:
        vec_size = 4 if x_ptr.dtype.element_ty == tl.float32 else 8
        offs_n = tl.arange(0, BLOCK_SIZE_N // vec_size)
        offs_n = offs_n * vec_size
        
        x_ptrs = x_ptr + pid_batch * stride_x_batch + offs_n[:, None] * stride_x_n + tl.arange(0, vec_size)[None, :]
        weight_ptrs = weight_ptr + offs_n[:, None] * stride_x_n + tl.arange(0, vec_size)[None, :]
        
        x = tl.load(x_ptrs, mask=offs_n[:, None] * vec_size + tl.arange(0, vec_size)[None, :] < N, other=0.0)
        weight = tl.load(weight_ptrs, mask=offs_n[:, None] * vec_size + tl.arange(0, vec_size)[None, :] < N, other=0.0)
        
        x_flat = tl.reshape(x, (BLOCK_SIZE_N,))
        weight_flat = tl.reshape(weight, (BLOCK_SIZE_N,))
        
        x_masked = tl.where(tl.arange(0, BLOCK_SIZE_N) < N, x_flat, 0.0)
        weight_masked = tl.where(tl.arange(0, BLOCK_SIZE_N) < N, weight_flat, 0.0)
    else:
        offs_n = tl.arange(0, BLOCK_SIZE_N)
        x_ptrs = x_ptr + pid_batch * stride_x_batch + offs_n * stride_x_n
        weight_ptrs = weight_ptr + offs_n * stride_x_n
        
        x_masked = tl.load(x_ptrs, mask=offs_n < N, other=0.0)
        weight_masked = tl.load(weight_ptrs, mask=offs_n < N, other=0.0)
    
    x_float = x_masked.to(tl.float32)
    mean_sq = tl.sum(x_float * x_float, axis=0) / N
    rms = tl.sqrt(mean_sq + eps)
    
    normalized = x_float / rms
    output = normalized * weight_masked.to(tl.float32)
    
    if USE_VECTOR_LOAD:
        output_stored = tl.reshape(output, (BLOCK_SIZE_N // vec_size, vec_size))
        output_ptrs = output_ptr + pid_batch * stride_output_batch + offs_n[:, None] * stride_output_n + tl.arange(0, vec_size)[None, :]
        tl.store(output_ptrs, output_stored, mask=offs_n[:, None] * vec_size + tl.arange(0, vec_size)[None, :] < N)
    else:
        output_ptrs = output_ptr + pid_batch * stride_output_batch + offs_n * stride_output_n
        tl.store(output_ptrs, output, mask=offs_n < N)

class QKNormTriton:
    @staticmethod
    def forward(q, k, norm_weight, eps=1e-6):
        assert q.dim() >= 2 and k.dim() >= 2
        assert q.shape[-1] == k.shape[-1] == norm_weight.shape[0]
        
        q_orig_shape = q.shape
        k_orig_shape = k.shape
        hidden_dim = norm_weight.shape[0]
        
        q_2d = q.view(-1, hidden_dim)
        k_2d = k.view(-1, hidden_dim)
        
        batch_size_q = q_2d.shape[0]
        batch_size_k = k_2d.shape[0]
        
        dtype = q.dtype
        device = q.device
        
        q_output = torch.empty_like(q_2d)
        k_output = torch.empty_like(k_2d)
        
        def get_config(N):
            if N % 256 == 0 and dtype in [torch.float16, torch.bfloat16]:
                return 256, True
            elif N % 128 == 0:
                return 128, dtype in [torch.float16, torch.bfloat16]
            elif N % 64 == 0:
                return 64, dtype in [torch.float16, torch.bfloat16]
            else:
                return 64, False
        
        block_n, use_vector_load = get_config(hidden_dim)
        
        grid_q = (batch_size_q,)
        grid_k = (batch_size_k,)
        
        if batch_size_q > 0:
            _rmsnorm_kernel[grid_q](
                q_2d,
                norm_weight,
                q_output,
                hidden_dim,
                eps,
                q_2d.stride(0),
                q_2d.stride(1),
                q_output.stride(0),
                q_output.stride(1),
                BLOCK_SIZE_N=block_n,
                USE_VECTOR_LOAD=use_vector_load,
                RESIDUAL_OUT=False,
            )
        
        if batch_size_k > 0:
            _rmsnorm_kernel[grid_k](
                k_2d,
                norm_weight,
                k_output,
                hidden_dim,
                eps,
                k_2d.stride(0),
                k_2d.stride(1),
                k_output.stride(0),
                k_output.stride(1),
                BLOCK_SIZE_N=block_n,
                USE_VECTOR_LOAD=use_vector_load,
                RESIDUAL_OUT=False,
            )
        
        return q_output.view(q_orig_shape), k_output.view(k_orig_shape)

def qknorm(q: torch.Tensor, k: torch.Tensor, norm_weight: torch.Tensor):
    if q.device.type == 'cuda' and q.dim() >= 2 and k.dim() >= 2:
        try:
            return QKNormTriton.forward(q, k, norm_weight)
        except Exception:
            pass
    
    q_2d = q.view(-1, q.shape[-1])
    k_2d = k.view(-1, k.shape[-1])
    
    if q_2d.is_contiguous() and k_2d.is_contiguous():
        q_o = torch.empty_like(q_2d)
        k_o = torch.empty_like(k_2d)
        flashinfer.norm.rmsnorm(q_2d, norm_weight, out=q_o)
        flashinfer.norm.rmsnorm(k_2d, norm_weight, out=k_o)
    else:
        q_o = torch.empty_like(q)
        k_o = torch.empty_like(k)
        flashinfer.norm.rmsnorm(q, norm_weight, out=q_o)
        flashinfer.norm.rmsnorm(k, norm_weight, out=k_o)
    
    return q_o.view(q.shape), k_o.view(k.shape)

class Solution:
    def solve(self, spec_path: str = None) -> dict:
        code = '''
import torch
import flashinfer
import triton
import triton.language as tl
from typing import Optional, Tuple

@triton.jit
def _rmsnorm_kernel(
    x_ptr,
    weight_ptr,
    output_ptr,
    N: tl.constexpr,
    eps: tl.constexpr,
    stride_x_batch,
    stride_x_n,
    stride_output_batch,
    stride_output_n,
    BLOCK_SIZE_N: tl.constexpr,
    USE_VECTOR_LOAD: tl.constexpr,
    RESIDUAL_OUT: tl.constexpr,
):
    pid_batch = tl.program_id(0)
    
    if USE_VECTOR_LOAD:
        vec_size = 4 if x_ptr.dtype.element_ty == tl.float32 else 8
        offs_n = tl.arange(0, BLOCK_SIZE_N // vec_size)
        offs_n = offs_n * vec_size
        
        x_ptrs = x_ptr + pid_batch * stride_x_batch + offs_n[:, None] * stride_x_n + tl.arange(0, vec_size)[None, :]
        weight_ptrs = weight_ptr + offs_n[:, None] * stride_x_n + tl.arange(0, vec_size)[None, :]
        
        x = tl.load(x_ptrs, mask=offs_n[:, None] * vec_size + tl.arange(0, vec_size)[None, :] < N, other=0.0)
        weight = tl.load(weight_ptrs, mask=offs_n[:, None] * vec_size + tl.arange(0, vec_size)[None, :] < N, other=0.0)
        
        x_flat = tl.reshape(x, (BLOCK_SIZE_N,))
        weight_flat = tl.reshape(weight, (BLOCK_SIZE_N,))
        
        x_masked = tl.where(tl.arange(0, BLOCK_SIZE_N) < N, x_flat, 0.0)
        weight_masked = tl.where(tl.arange(0, BLOCK_SIZE_N) < N, weight_flat, 0.0)
    else:
        offs_n = tl.arange(0, BLOCK_SIZE_N)
        x_ptrs = x_ptr + pid_batch * stride_x_batch + offs_n * stride_x_n
        weight_ptrs = weight_ptr + offs_n * stride_x_n
        
        x_masked = tl.load(x_ptrs, mask=offs_n < N, other=0.0)
        weight_masked = tl.load(weight_ptrs, mask=offs_n < N, other=0.0)
    
    x_float = x_masked.to(tl.float32)
    mean_sq = tl.sum(x_float * x_float, axis=0) / N
    rms = tl.sqrt(mean_sq + eps)
    
    normalized = x_float / rms
    output = normalized * weight_masked.to(tl.float32)
    
    if USE_VECTOR_LOAD:
        output_stored = tl.reshape(output, (BLOCK_SIZE_N // vec_size, vec_size))
        output_ptrs = output_ptr + pid_batch * stride_output_batch + offs_n[:, None] * stride_output_n + tl.arange(0, vec_size)[None, :]
        tl.store(output_ptrs, output_stored, mask=offs_n[:, None] * vec_size + tl.arange(0, vec_size)[None, :] < N)
    else:
        output_ptrs = output_ptr + pid_batch * stride_output_batch + offs_n * stride_output_n
        tl.store(output_ptrs, output, mask=offs_n < N)

class QKNormTriton:
    @staticmethod
    def forward(q, k, norm_weight, eps=1e-6):
        assert q.dim() >= 2 and k.dim() >= 2
        assert q.shape[-1] == k.shape[-1] == norm_weight.shape[0]
        
        q_orig_shape = q.shape
        k_orig_shape = k.shape
        hidden_dim = norm_weight.shape[0]
        
        q_2d = q.view(-1, hidden_dim)
        k_2d = k.view(-1, hidden_dim)
        
        batch_size_q = q_2d.shape[0]
        batch_size_k = k_2d.shape[0]
        
        dtype = q.dtype
        device = q.device
        
        q_output = torch.empty_like(q_2d)
        k_output = torch.empty_like(k_2d)
        
        def get_config(N):
            if N % 256 == 0 and dtype in [torch.float16, torch.bfloat16]:
                return 256, True
            elif N % 128 == 0:
                return 128, dtype in [torch.float16, torch.bfloat16]
            elif N % 64 == 0:
                return 64, dtype in [torch.float16, torch.bfloat16]
            else:
                return 64, False
        
        block_n, use_vector_load = get_config(hidden_dim)
        
        grid_q = (batch_size_q,)
        grid_k = (batch_size_k,)
        
        if batch_size_q > 0:
            _rmsnorm_kernel[grid_q](
                q_2d,
                norm_weight,
                q_output,
                hidden_dim,
                eps,
                q_2d.stride(0),
                q_2d.stride(1),
                q_output.stride(0),
                q_output.stride(1),
                BLOCK_SIZE_N=block_n,
                USE_VECTOR_LOAD=use_vector_load,
                RESIDUAL_OUT=False,
            )
        
        if batch_size_k > 0:
            _rmsnorm_kernel[grid_k](
                k_2d,
                norm_weight,
                k_output,
                hidden_dim,
                eps,
                k_2d.stride(0),
                k_2d.stride(1),
                k_output.stride(0),
                k_output.stride(1),
                BLOCK_SIZE_N=block_n,
                USE_VECTOR_LOAD=use_vector_load,
                RESIDUAL_OUT=False,
            )
        
        return q_output.view(q_orig_shape), k_output.view(k_orig_shape)

def qknorm(q: torch.Tensor, k: torch.Tensor, norm_weight: torch.Tensor):
    if q.device.type == "cuda" and q.dim() >= 2 and k.dim() >= 2:
        try:
            return QKNormTriton.forward(q, k, norm_weight)
        except Exception:
            pass
    
    q_2d = q.view(-1, q.shape[-1])
    k_2d = k.view(-1, k.shape[-1])
    
    if q_2d.is_contiguous() and k_2d.is_contiguous():
        q_o = torch.empty_like(q_2d)
        k_o = torch.empty_like(k_2d)
        flashinfer.norm.rmsnorm(q_2d, norm_weight, out=q_o)
        flashinfer.norm.rmsnorm(k_2d, norm_weight, out=k_o)
    else:
        q_o = torch.empty_like(q)
        k_o = torch.empty_like(k)
        flashinfer.norm.rmsnorm(q, norm_weight, out=q_o)
        flashinfer.norm.rmsnorm(k, norm_weight, out=k_o)
    
    return q_o.view(q.shape), k_o.view(k.shape)
'''
        return {"code": code}