import os
import textwrap

class Solution:
    def solve(self, spec_path: str = None) -> dict:
        module_code = r'''
import torch
import flashinfer
from typing import Tuple, Dict

_STREAMS: Dict[int, Tuple[torch.cuda.Stream, torch.cuda.Stream]] = {}
_BUFFER_CACHE: Dict[Tuple[int, torch.dtype], torch.Tensor] = {}

def _get_streams(device: torch.device) -> Tuple[torch.cuda.Stream, torch.cuda.Stream]:
    dev_index = device.index if device.index is not None else torch.cuda.current_device()
    if dev_index not in _STREAMS:
        _STREAMS[dev_index] = (torch.cuda.Stream(device=dev_index), torch.cuda.Stream(device=dev_index))
    return _STREAMS[dev_index]

def _get_combined_buffer(total_elems: int, device: torch.device, dtype: torch.dtype) -> torch.Tensor:
    key = (device.index if device.index is not None else torch.cuda.current_device(), dtype)
    buf = _BUFFER_CACHE.get(key, None)
    if buf is None or buf.numel() < total_elems or buf.device != device or buf.dtype != dtype:
        buf = torch.empty(total_elems, device=device, dtype=dtype)
        _BUFFER_CACHE[key] = buf
    return buf[:total_elems]

def _maybe_flatten_no_copy(x: torch.Tensor) -> torch.Tensor:
    if x.dim() >= 2 and x.is_contiguous():
        return x.view(-1, x.shape[-1])
    return x

def qknorm(q: torch.Tensor, k: torch.Tensor, norm_weight: torch.Tensor):
    if not q.is_cuda or not k.is_cuda:
        raise RuntimeError("qknorm expects CUDA tensors")
    if q.device != k.device:
        raise RuntimeError("q and k must be on the same device")
    if q.shape[-1] != k.shape[-1]:
        raise RuntimeError("q and k must have the same last dimension")
    if norm_weight.dim() != 1 or norm_weight.numel() != q.shape[-1]:
        raise RuntimeError("norm_weight must be 1D with size equal to the last dim of q/k")
    device = q.device
    dtype = q.dtype
    if norm_weight.device != device:
        norm_weight = norm_weight.to(device=device)
    if norm_weight.dtype != dtype:
        norm_weight = norm_weight.to(dtype=dtype)

    q_in = _maybe_flatten_no_copy(q)
    k_in = _maybe_flatten_no_copy(k)

    q_out_shape = q_in.shape
    k_out_shape = k_in.shape

    total = q_in.numel() + k_in.numel()
    out_buf = _get_combined_buffer(total, device, dtype)

    q_out = out_buf.narrow(0, 0, q_in.numel()).view(q_out_shape)
    k_out = out_buf.narrow(0, q_in.numel(), k_in.numel()).view(k_out_shape)

    # Heuristic: run in parallel on two streams when total rows are small to medium
    # Otherwise, sequential execution may be more stable for very large sizes.
    # We measure "rows" as numel // hidden_size
    hidden = q.shape[-1]
    q_rows = q_in.numel() // hidden
    k_rows = k_in.numel() // hidden
    total_rows = q_rows + k_rows
    use_parallel = True
    # If very large, avoid parallel to reduce contention
    if total_rows >= 1_500_000:
        use_parallel = False

    if use_parallel:
        s1, s2 = _get_streams(device)
        current = torch.cuda.current_stream(device=device)
        s1.wait_stream(current)
        s2.wait_stream(current)
        # Launch in parallel
        with torch.cuda.stream(s1):
            flashinfer.norm.rmsnorm(q_in, norm_weight, out=q_out)
        with torch.cuda.stream(s2):
            flashinfer.norm.rmsnorm(k_in, norm_weight, out=k_out)
        # Ensure default stream waits before using outputs
        current.wait_stream(s1)
        current.wait_stream(s2)
    else:
        flashinfer.norm.rmsnorm(q_in, norm_weight, out=q_out)
        flashinfer.norm.rmsnorm(k_in, norm_weight, out=k_out)

    # Reshape back to original shapes
    q_res = q_out.view(q.shape)
    k_res = k_out.view(k.shape)
    return q_res, k_res

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
        return {"code": textwrap.dedent(module_code)}
