import torch
import flashinfer
from typing import Dict, Tuple

_weight_cache: Dict[Tuple[int, int, torch.dtype], torch.Tensor] = {}
_streams_cache: Dict[int, Tuple[torch.cuda.Stream, torch.cuda.Stream]] = {}


def _get_cast_weight(norm_weight: torch.Tensor, device: torch.device, dtype: torch.dtype) -> torch.Tensor:
    if norm_weight.device == device and norm_weight.dtype == dtype:
        return norm_weight
    key = (int(norm_weight.data_ptr()), device.index if device.type == "cuda" else -1, dtype)
    cached = _weight_cache.get(key, None)
    if cached is not None and cached.numel() == norm_weight.numel():
        return cached
    w = norm_weight.to(device=device, dtype=dtype, non_blocking=True)
    _weight_cache[key] = w
    return w


def customized_qknorm(q: torch.Tensor, k: torch.Tensor, norm_weight: torch.Tensor):
    q_o = torch.empty(q.shape, device=q.device, dtype=q.dtype)
    k_o = torch.empty(k.shape, device=k.device, dtype=k.dtype)
    flashinfer.norm.rmsnorm(q, norm_weight, out=q_o)
    flashinfer.norm.rmsnorm(k, norm_weight, out=k_o)
    return q_o, k_o


def default_qknorm(q: torch.Tensor, k: torch.Tensor, norm_weight: torch.Tensor):
    q_2d = q.contiguous().view(-1, q.shape[-1])
    k_2d = k.contiguous().view(-1, k.shape[-1])
    q_o = torch.empty_like(q_2d)
    k_o = torch.empty_like(k_2d)
    flashinfer.norm.rmsnorm(q_2d, norm_weight, out=q_o)
    flashinfer.norm.rmsnorm(k_2d, norm_weight, out=k_o)
    return q_o.view(q.shape), k_o.view(k.shape)


def qknorm(q: torch.Tensor, k: torch.Tensor, norm_weight: torch.Tensor):
    if q.shape[-1] != norm_weight.numel() or k.shape[-1] != norm_weight.numel():
        raise ValueError("norm_weight length must match last dimension of q and k")

    if q.device.type != "cuda" or k.device.type != "cuda":
        # Fallback to default behavior if tensors are not on CUDA
        return customized_qknorm(q, k, norm_weight)

    # Prepare weights on correct device/dtype
    w_q = _get_cast_weight(norm_weight, q.device, q.dtype)
    if k.device == q.device and k.dtype == q.dtype:
        w_k = w_q
    else:
        w_k = _get_cast_weight(norm_weight, k.device, k.dtype)

    # Attempt to overlap two tiny kernels using separate CUDA streams when on the same device
    same_device = (q.device == k.device)
    if same_device:
        dev_index = q.device.index
        if dev_index not in _streams_cache:
            _streams_cache[dev_index] = (torch.cuda.Stream(device=q.device), torch.cuda.Stream(device=q.device))
        s_q, s_k = _streams_cache[dev_index]

        default_q_stream = torch.cuda.current_stream(q.device)
        default_k_stream = default_q_stream  # same device

        # Ensure new streams wait for any prior work on default stream
        s_q.wait_stream(default_q_stream)
        s_k.wait_stream(default_k_stream)

        with torch.cuda.stream(s_q):
            q_o = torch.empty(q.shape, device=q.device, dtype=q.dtype)
            flashinfer.norm.rmsnorm(q, w_q, out=q_o)

        with torch.cuda.stream(s_k):
            k_o = torch.empty(k.shape, device=k.device, dtype=k.dtype)
            flashinfer.norm.rmsnorm(k, w_k, out=k_o)

        # Make default stream wait for completion of both
        default_q_stream.wait_stream(s_q)
        default_k_stream.wait_stream(s_k)
        return q_o, k_o
    else:
        # Different devices: run on their respective default streams
        q_o = torch.empty(q.shape, device=q.device, dtype=q.dtype)
        k_o = torch.empty(k.shape, device=k.device, dtype=k.dtype)
        flashinfer.norm.rmsnorm(q, w_q, out=q_o)
        flashinfer.norm.rmsnorm(k, w_k, out=k_o)
        return q_o, k_o


class Solution:
    def solve(self, spec_path: str = None) -> dict:
        code = '''
import torch
import flashinfer
from typing import Dict, Tuple

_weight_cache: Dict[Tuple[int, int, torch.dtype], torch.Tensor] = {}
_streams_cache: Dict[int, Tuple[torch.cuda.Stream, torch.cuda.Stream]] = {}


def _get_cast_weight(norm_weight: torch.Tensor, device: torch.device, dtype: torch.dtype) -> torch.Tensor:
    if norm_weight.device == device and norm_weight.dtype == dtype:
        return norm_weight
    key = (int(norm_weight.data_ptr()), device.index if device.type == "cuda" else -1, dtype)
    cached = _weight_cache.get(key, None)
    if cached is not None and cached.numel() == norm_weight.numel():
        return cached
    w = norm_weight.to(device=device, dtype=dtype, non_blocking=True)
    _weight_cache[key] = w
    return w


def customized_qknorm(q: torch.Tensor, k: torch.Tensor, norm_weight: torch.Tensor):
    q_o = torch.empty(q.shape, device=q.device, dtype=q.dtype)
    k_o = torch.empty(k.shape, device=k.device, dtype=k.dtype)
    flashinfer.norm.rmsnorm(q, norm_weight, out=q_o)
    flashinfer.norm.rmsnorm(k, norm_weight, out=k_o)
    return q_o, k_o


def default_qknorm(q: torch.Tensor, k: torch.Tensor, norm_weight: torch.Tensor):
    q_2d = q.contiguous().view(-1, q.shape[-1])
    k_2d = k.contiguous().view(-1, k.shape[-1])
    q_o = torch.empty_like(q_2d)
    k_o = torch.empty_like(k_2d)
    flashinfer.norm.rmsnorm(q_2d, norm_weight, out=q_o)
    flashinfer.norm.rmsnorm(k_2d, norm_weight, out=k_o)
    return q_o.view(q.shape), k_o.view(k.shape)


def qknorm(q: torch.Tensor, k: torch.Tensor, norm_weight: torch.Tensor):
    if q.shape[-1] != norm_weight.numel() or k.shape[-1] != norm_weight.numel():
        raise ValueError("norm_weight length must match last dimension of q and k")

    if q.device.type != "cuda" or k.device.type != "cuda":
        return customized_qknorm(q, k, norm_weight)

    w_q = _get_cast_weight(norm_weight, q.device, q.dtype)
    if k.device == q.device and k.dtype == q.dtype:
        w_k = w_q
    else:
        w_k = _get_cast_weight(norm_weight, k.device, k.dtype)

    same_device = (q.device == k.device)
    if same_device:
        dev_index = q.device.index
        if dev_index not in _streams_cache:
            _streams_cache[dev_index] = (torch.cuda.Stream(device=q.device), torch.cuda.Stream(device=q.device))
        s_q, s_k = _streams_cache[dev_index]

        default_q_stream = torch.cuda.current_stream(q.device)
        default_k_stream = default_q_stream

        s_q.wait_stream(default_q_stream)
        s_k.wait_stream(default_k_stream)

        with torch.cuda.stream(s_q):
            q_o = torch.empty(q.shape, device=q.device, dtype=q.dtype)
            flashinfer.norm.rmsnorm(q, w_q, out=q_o)

        with torch.cuda.stream(s_k):
            k_o = torch.empty(k.shape, device=k.device, dtype=k.dtype)
            flashinfer.norm.rmsnorm(k, w_k, out=k_o)

        default_q_stream.wait_stream(s_q)
        default_k_stream.wait_stream(s_k)
        return q_o, k_o
    else:
        q_o = torch.empty(q.shape, device=q.device, dtype=q.dtype)
        k_o = torch.empty(k.shape, device=k.device, dtype=k.dtype)
        flashinfer.norm.rmsnorm(q, w_q, out=q_o)
        flashinfer.norm.rmsnorm(k, w_k, out=k_o)
        return q_o, k_o
'''
        return {"code": code}