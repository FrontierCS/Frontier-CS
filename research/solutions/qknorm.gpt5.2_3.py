import textwrap

_KERNEL_CODE = textwrap.dedent(
    r"""
    import os
    from typing import Tuple, Dict, Any

    import torch
    import flashinfer


    _MAX_OUT_CACHE = int(os.environ.get("QKNORM_MAX_OUT_CACHE", "32"))

    _out_cache: Dict[Any, Tuple[torch.Tensor, torch.Tensor]] = {}
    _out_cache_fifo = []

    _weight_cast_cache: Dict[Any, torch.Tensor] = {}
    _weight_cast_cache_fifo = []
    _MAX_WEIGHT_CACHE = int(os.environ.get("QKNORM_MAX_WEIGHT_CACHE", "32"))


    def _get_cached_weight(norm_weight: torch.Tensor, target_dtype: torch.dtype) -> torch.Tensor:
        if norm_weight.dtype == target_dtype:
            return norm_weight
        key = (norm_weight.data_ptr(), norm_weight.device, norm_weight.dtype, target_dtype, norm_weight.shape, norm_weight.stride())
        w = _weight_cast_cache.get(key, None)
        if w is None:
            w = norm_weight.to(dtype=target_dtype)
            _weight_cast_cache[key] = w
            _weight_cast_cache_fifo.append(key)
            if len(_weight_cast_cache_fifo) > _MAX_WEIGHT_CACHE:
                old = _weight_cast_cache_fifo.pop(0)
                _weight_cast_cache.pop(old, None)
        return w


    def default_qknorm(q: torch.Tensor, k: torch.Tensor, norm_weight: torch.Tensor):
        q_2d = q.contiguous().view(-1, q.shape[-1])
        k_2d = k.contiguous().view(-1, k.shape[-1])
        q_o = torch.empty_like(q_2d)
        k_o = torch.empty_like(k_2d)
        wq = _get_cached_weight(norm_weight, q_2d.dtype)
        wk = wq if (k_2d.dtype == q_2d.dtype) else _get_cached_weight(norm_weight, k_2d.dtype)
        flashinfer.norm.rmsnorm(q_2d, wq, out=q_o)
        flashinfer.norm.rmsnorm(k_2d, wk, out=k_o)
        return q_o.view(q.shape), k_o.view(k.shape)


    def customized_qknorm(q: torch.Tensor, k: torch.Tensor, norm_weight: torch.Tensor):
        q_o = torch.empty(q.shape, device=q.device, dtype=q.dtype)
        k_o = torch.empty(k.shape, device=k.device, dtype=k.dtype)
        wq = _get_cached_weight(norm_weight, q.dtype)
        wk = wq if (k.dtype == q.dtype) else _get_cached_weight(norm_weight, k.dtype)
        flashinfer.norm.rmsnorm(q, wq, out=q_o)
        flashinfer.norm.rmsnorm(k, wk, out=k_o)
        return q_o, k_o


    def qknorm(q: torch.Tensor, k: torch.Tensor, norm_weight: torch.Tensor):
        if q.numel() == 0:
            return torch.empty_like(q), torch.empty_like(k)
        if k.numel() == 0:
            return torch.empty_like(q), torch.empty_like(k)

        if q.shape[-1] != norm_weight.shape[0] or k.shape[-1] != norm_weight.shape[0]:
            raise ValueError("q/k last dim must match norm_weight.shape[0]")

        if q.stride(-1) != 1 or k.stride(-1) != 1 or norm_weight.stride(0) != 1:
            return default_qknorm(q, k, norm_weight)

        q_dev = q.device
        k_dev = k.device
        if q_dev != k_dev:
            raise ValueError("q and k must be on the same device")

        wq = _get_cached_weight(norm_weight, q.dtype)
        wk = wq if (k.dtype == q.dtype) else _get_cached_weight(norm_weight, k.dtype)

        key = (q_dev, q.dtype, q.shape, k.dtype, k.shape)
        out_pair = _out_cache.get(key, None)
        if out_pair is None or out_pair[0].shape != q.shape or out_pair[1].shape != k.shape:
            q_o = torch.empty(q.shape, device=q_dev, dtype=q.dtype)
            k_o = torch.empty(k.shape, device=q_dev, dtype=k.dtype)
            _out_cache[key] = (q_o, k_o)
            _out_cache_fifo.append(key)
            if len(_out_cache_fifo) > _MAX_OUT_CACHE:
                old = _out_cache_fifo.pop(0)
                _out_cache.pop(old, None)
        else:
            q_o, k_o = out_pair

        flashinfer.norm.rmsnorm(q, wq, out=q_o)
        flashinfer.norm.rmsnorm(k, wk, out=k_o)
        return q_o, k_o
    """
).lstrip()


class Solution:
    def solve(self, spec_path: str = None) -> dict:
        return {"code": _KERNEL_CODE}