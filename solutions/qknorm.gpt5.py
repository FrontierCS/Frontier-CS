import torch
import flashinfer

_stream_cache = {}


def _get_streams(device: torch.device):
    if device.type != "cuda":
        return None, None
    dev_idx = device.index
    if dev_idx is None:
        dev_idx = torch.cuda.current_device()
    streams = _stream_cache.get(dev_idx, None)
    if streams is None:
        try:
            s1 = torch.cuda.Stream(device=dev_idx)
            s2 = torch.cuda.Stream(device=dev_idx)
        except Exception:
            s1, s2 = None, None
        _get_streams[dev_idx] = (s1, s2)
        _stream_cache[dev_idx] = (s1, s2)
        streams = (s1, s2)
    return streams


def qknorm(q: torch.Tensor, k: torch.Tensor, norm_weight: torch.Tensor):
    hidden = norm_weight.shape[0]
    if q.shape[-1] != hidden or k.shape[-1] != hidden:
        raise ValueError("Last dimension of q/k must match norm_weight length")
    if q.device.type != "cuda" or k.device.type != "cuda":
        # CPU or mismatched devices fallback: sequential application on respective devices
        q_w = norm_weight.to(device=q.device)
        k_w = norm_weight.to(device=k.device) if k.device != q.device else q_w
        q_o = torch.empty(q.shape, device=q.device, dtype=q.dtype)
        k_o = torch.empty(k.shape, device=k.device, dtype=k.dtype)
        flashinfer.norm.rmsnorm(q, q_w, out=q_o)
        flashinfer.norm.rmsnorm(k, k_w, out=k_o)
        return q_o, k_o

    if q.device != k.device:
        # Different GPU devices: process separately
        q_w = norm_weight.to(device=q.device)
        k_w = norm_weight.to(device=k.device)
        q_o = torch.empty(q.shape, device=q.device, dtype=q.dtype)
        k_o = torch.empty(k.shape, device=k.device, dtype=k.dtype)
        flashinfer.norm.rmsnorm(q, q_w, out=q_o)
        flashinfer.norm.rmsnorm(k, k_w, out=k_o)
        return q_o, k_o

    device = q.device
    q_o = torch.empty(q.shape, device=device, dtype=q.dtype)
    k_o = torch.empty(k.shape, device=device, dtype=k.dtype)

    total_bytes = (q.numel() * q.element_size()) + (k.numel() * k.element_size())
    use_concurrency = total_bytes <= (4 * 1024 * 1024)  # 4MB heuristic for tiny ops

    w = norm_weight if norm_weight.device == device else norm_weight.to(device=device)

    if use_concurrency:
        s1, s2 = _get_streams(device)
        if s1 is not None and s2 is not None:
            cur = torch.cuda.current_stream(device)
            s1.wait_stream(cur)
            s2.wait_stream(cur)
            with torch.cuda.stream(s1):
                flashinfer.norm.rmsnorm(q, w, out=q_o)
            with torch.cuda.stream(s2):
                flashinfer.norm.rmsnorm(k, w, out=k_o)
            cur.wait_stream(s1)
            cur.wait_stream(s2)
            return q_o, k_o

    flashinfer.norm.rmsnorm(q, w, out=q_o)
    flashinfer.norm.rmsnorm(k, w, out=k_o)
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


class Solution:
    def solve(self, spec_path: str = None) -> dict:
        code = r'''
import torch
import flashinfer

_stream_cache = {}


def _get_streams(device: torch.device):
    if device.type != "cuda":
        return None, None
    dev_idx = device.index
    if dev_idx is None:
        dev_idx = torch.cuda.current_device()
    streams = _stream_cache.get(dev_idx, None)
    if streams is None:
        try:
            s1 = torch.cuda.Stream(device=dev_idx)
            s2 = torch.cuda.Stream(device=dev_idx)
        except Exception:
            s1, s2 = None, None
        _stream_cache[dev_idx] = (s1, s2)
        streams = (s1, s2)
    return streams


def qknorm(q: torch.Tensor, k: torch.Tensor, norm_weight: torch.Tensor):
    hidden = norm_weight.shape[0]
    if q.shape[-1] != hidden or k.shape[-1] != hidden:
        raise ValueError("Last dimension of q/k must match norm_weight length")
    if q.device.type != "cuda" or k.device.type != "cuda":
        q_w = norm_weight.to(device=q.device)
        k_w = norm_weight.to(device=k.device) if k.device != q.device else q_w
        q_o = torch.empty(q.shape, device=q.device, dtype=q.dtype)
        k_o = torch.empty(k.shape, device=k.device, dtype=k.dtype)
        flashinfer.norm.rmsnorm(q, q_w, out=q_o)
        flashinfer.norm.rmsnorm(k, k_w, out=k_o)
        return q_o, k_o

    if q.device != k.device:
        q_w = norm_weight.to(device=q.device)
        k_w = norm_weight.to(device=k.device)
        q_o = torch.empty(q.shape, device=q.device, dtype=q.dtype)
        k_o = torch.empty(k.shape, device=k.device, dtype=k.dtype)
        flashinfer.norm.rmsnorm(q, q_w, out=q_o)
        flashinfer.norm.rmsnorm(k, k_w, out=k_o)
        return q_o, k_o

    device = q.device
    q_o = torch.empty(q.shape, device=device, dtype=q.dtype)
    k_o = torch.empty(k.shape, device=device, dtype=k.dtype)

    total_bytes = (q.numel() * q.element_size()) + (k.numel() * k.element_size())
    use_concurrency = total_bytes <= (4 * 1024 * 1024)

    w = norm_weight if norm_weight.device == device else norm_weight.to(device=device)

    if use_concurrency:
        s1, s2 = _get_streams(device)
        if s1 is not None and s2 is not None:
            cur = torch.cuda.current_stream(device)
            s1.wait_stream(cur)
            s2.wait_stream(cur)
            with torch.cuda.stream(s1):
                flashinfer.norm.rmsnorm(q, w, out=q_o)
            with torch.cuda.stream(s2):
                flashinfer.norm.rmsnorm(k, w, out=k_o)
            cur.wait_stream(s1)
            cur.wait_stream(s2)
            return q_o, k_o

    flashinfer.norm.rmsnorm(q, w, out=q_o)
    flashinfer.norm.rmsnorm(k, w, out=k_o)
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
        return {"code": code}
