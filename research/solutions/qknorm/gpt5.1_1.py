import textwrap

class Solution:
    def solve(self, spec_path: str = None) -> dict:
        code = '''
import torch
import flashinfer

_streams = {}


def _get_aux_stream(device: torch.device):
    if device.type != "cuda":
        return None
    index = device.index
    if index is None:
        index = torch.cuda.current_device()
    stream = _streams.get(index)
    if stream is None:
        with torch.cuda.device(index):
            stream = torch.cuda.Stream()
        _streams[index] = stream
    return stream


def qknorm(q: torch.Tensor, k: torch.Tensor, norm_weight: torch.Tensor):
    """
    Apply RMSNorm to query and key tensors.

    Args:
        q: Query tensor of arbitrary shape (will be normalized over last dim)
        k: Key tensor of arbitrary shape (will be normalized over last dim)
        norm_weight: Normalization weight tensor of shape (hidden_dim,)

    Returns:
        Tuple of (q_normalized, k_normalized) tensors
    """
    # Allocate outputs with same shape, dtype, and device
    q_o = torch.empty_like(q)
    k_o = torch.empty_like(k)

    # Fast path for CUDA tensors on the same device: launch norms on two streams
    if q.is_cuda and k.is_cuda and q.device == k.device and norm_weight.is_cuda:
        device = q.device
        main_stream = torch.cuda.current_stream(device)
        aux_stream = _get_aux_stream(device)

        # Launch RMSNorm for q on the caller's current stream
        with torch.cuda.stream(main_stream):
            flashinfer.norm.rmsnorm(q, norm_weight, out=q_o)

        # Launch RMSNorm for k concurrently on the auxiliary stream
        with torch.cuda.stream(aux_stream):
            flashinfer.norm.rmsnorm(k, norm_weight, out=k_o)
    else:
        # Fallback: sequential execution (e.g., CPU tensors or device mismatch)
        # For non-CUDA tensors, flashinfer may not be available; implement a
        # simple RMSNorm in pure PyTorch as a safe fallback.
        if q.is_cuda and norm_weight.is_cuda:
            flashinfer.norm.rmsnorm(q, norm_weight, out=q_o)
        else:
            eps = 1e-6
            q_ = q.to(dtype=torch.float32)
            w_ = norm_weight.to(dtype=torch.float32, device=q.device)
            var = (q_ * q_).mean(dim=-1, keepdim=True)
            scale = torch.rsqrt(var + eps)
            q_o.copy_((q_ * scale) * w_)
        if k.is_cuda and norm_weight.is_cuda:
            flashinfer.norm.rmsnorm(k, norm_weight, out=k_o)
        else:
            eps = 1e-6
            k_ = k.to(dtype=torch.float32)
            w_ = norm_weight.to(dtype=torch.float32, device=k.device)
            var = (k_ * k_).mean(dim=-1, keepdim=True)
            scale = torch.rsqrt(var + eps)
            k_o.copy_((k_ * scale) * w_)

    return q_o, k_o


def default_qknorm(q: torch.Tensor, k: torch.Tensor, norm_weight: torch.Tensor):
    q_2d = q.contiguous().view(-1, q.shape[-1])
    k_2d = k.contiguous().view(-1, k.shape[-1])
    q_o = torch.empty_like(q_2d)
    k_o = torch.empty_like(k_2d)
    flashinfer.norm.rmsnorm(q_2d, norm_weight, out=q_o)
    flashinfer.norm.rmsnorm(k_2d, norm_weight, out=k_o)
    return q_o.view(q.shape), k_o.view(k.shape)


def customized_qknorm(q: torch.Tensor, k: torch.Tensor, norm_weight: torch.Tensor):
    q_o = torch.empty(q.shape, device=q.device, dtype=q.dtype)
    k_o = torch.empty(k.shape, device=k.device, dtype=k.dtype)
    flashinfer.norm.rmsnorm(q, norm_weight, out=q_o)
    flashinfer.norm.rmsnorm(k, norm_weight, out=k_o)
    return q_o, k_o
'''
        return {"code": textwrap.dedent(code)}