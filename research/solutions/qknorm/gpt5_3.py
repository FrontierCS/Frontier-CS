import torch
import flashinfer

KERNEL_CODE = r'''
import torch
import flashinfer

_stream_cache = {}

def _get_streams(device):
    if not torch.cuda.is_available():
        return None, None
    dev = device if isinstance(device, torch.device) else torch.device(device)
    if dev.type != "cuda":
        return None, None
    idx = dev.index if dev.index is not None else torch.cuda.current_device()
    st = _stream_cache.get(idx, None)
    if st is None:
        s1 = torch.cuda.Stream(device=idx)
        s2 = torch.cuda.Stream(device=idx)
        _stream_cache[idx] = (s1, s2)
        st = (s1, s2)
    return st

def _rmsnorm_fallback_torch(x: torch.Tensor, weight: torch.Tensor, eps: float = 1e-6, out: torch.Tensor | None = None):
    # Simple CPU RMSNorm fallback
    x_f = x.to(torch.float32) if x.dtype in (torch.float16, torch.bfloat16) else x
    var = (x_f * x_f).mean(dim=-1, keepdim=True)
    inv_rms = torch.rsqrt(var + eps)
    w = weight
    if w.dim() != 1:
        w = w.reshape(-1)
    shape = [1] * (x.dim() - 1) + [w.numel()]
    y = x_f * inv_rms * w.view(shape)
    if x_f.dtype != x.dtype:
        y = y.to(x.dtype)
    if out is not None:
        out.copy_(y)
        return out
    return y

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

def qknorm(q: torch.Tensor, k: torch.Tensor, norm_weight: torch.Tensor):
    # Validate devices
    if q.device != k.device:
        raise ValueError("q and k must be on the same device")
    # Allocate outputs (contiguous for better write efficiency)
    q_o = torch.empty(q.shape, device=q.device, dtype=q.dtype, memory_format=torch.contiguous_format)
    k_o = torch.empty(k.shape, device=k.device, dtype=k.dtype, memory_format=torch.contiguous_format)

    # GPU fast path using flashinfer, with concurrent streams to reduce launch/latency overhead
    if q.is_cuda and k.is_cuda and torch.cuda.is_available():
        s1, s2 = _get_streams(q.device)
        if s1 is None:
            # Shouldn't happen, but guard anyway
            if q.numel() > 0:
                flashinfer.norm.rmsnorm(q, norm_weight, out=q_o)
            if k.numel() > 0:
                flashinfer.norm.rmsnorm(k, norm_weight, out=k_o)
            return q_o, k_o

        cur = torch.cuda.current_stream(q.device)
        # Ensure inputs are ready on the new streams
        s1.wait_stream(cur)
        s2.wait_stream(cur)

        # Launch concurrently
        if q.numel() > 0:
            with torch.cuda.stream(s1):
                flashinfer.norm.rmsnorm(q, norm_weight, out=q_o)
        if k.numel() > 0:
            with torch.cuda.stream(s2):
                flashinfer.norm.rmsnorm(k, norm_weight, out=k_o)

        # Make default stream wait for completion
        cur.wait_stream(s1)
        cur.wait_stream(s2)
        return q_o, k_o

    # CPU fallback (for completeness)
    _rmsnorm_fallback_torch(q, norm_weight, out=q_o)
    _rmsnorm_fallback_torch(k, norm_weight, out=k_o)
    return q_o, k_o
'''

# Define qknorm and helpers in this module as well
exec(KERNEL_CODE, globals(), globals())

class Solution:
    def solve(self, spec_path: str = None) -> dict:
        return {"code": KERNEL_CODE}