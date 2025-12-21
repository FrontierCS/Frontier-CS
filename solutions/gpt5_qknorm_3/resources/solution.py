import torch
import flashinfer

_STREAM_POOL = {}


def _get_stream(device):
    if not isinstance(device, torch.device):
        device = torch.device(device)
    if device.type != "cuda":
        return None
    idx = device.index if device.index is not None else torch.cuda.current_device()
    pool = _STREAM_POOL.get(idx)
    if pool is None:
        torch.cuda.set_device(idx)
        pool = [torch.cuda.Stream(device=idx)]
        _STREAM_POOL[idx] = pool
    return pool[0]


def qknorm(q: torch.Tensor, k: torch.Tensor, norm_weight: torch.Tensor):
    # Allocate output tensors preserving original strides (avoid contiguous/copies)
    q_o = torch.empty_like(q)
    k_o = torch.empty_like(k)

    same_device = (q.device == k.device)
    cuda_q = q.is_cuda
    cuda_k = k.is_cuda

    if cuda_q and cuda_k and same_device:
        # Single device: overlap two kernels via an auxiliary stream
        cur = torch.cuda.current_stream(q.device)
        alt = _get_stream(q.device)

        # Choose the larger workload for current stream, smaller for alt stream
        work_q = q.numel()
        work_k = k.numel()

        if work_q >= work_k:
            # Launch smaller (k) first on alt to overlap with q on current
            alt.wait_stream(cur)
            with torch.cuda.stream(alt):
                flashinfer.norm.rmsnorm(k, norm_weight, out=k_o)
            flashinfer.norm.rmsnorm(q, norm_weight, out=q_o)
            cur.wait_stream(alt)
        else:
            alt.wait_stream(cur)
            with torch.cuda.stream(alt):
                flashinfer.norm.rmsnorm(q, norm_weight, out=q_o)
            flashinfer.norm.rmsnorm(k, norm_weight, out=k_o)
            cur.wait_stream(alt)
    else:
        # Separate devices or CPU fallback: execute independently and ensure proper sync
        if cuda_q:
            cur_q = torch.cuda.current_stream(q.device)
            flashinfer.norm.rmsnorm(q, norm_weight, out=q_o)
        else:
            flashinfer.norm.rmsnorm(q, norm_weight, out=q_o)

        if cuda_k:
            cur_k = torch.cuda.current_stream(k.device)
            flashinfer.norm.rmsnorm(k, norm_weight, out=k_o)
        else:
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


def customized_qknorm(q: torch.Tensor, k: torch.Tensor, norm_weight: torch.Tensor):
    q_o = torch.empty(q.shape, device=q.device, dtype=q.dtype, layout=q.layout)
    k_o = torch.empty(k.shape, device=k.device, dtype=k.dtype, layout=k.layout)
    flashinfer.norm.rmsnorm(q, norm_weight, out=q_o)
    flashinfer.norm.rmsnorm(k, norm_weight, out=k_o)
    return q_o, k_o


class Solution:
    def solve(self, spec_path: str = None) -> dict:
        code = """
import torch
import flashinfer

_STREAM_POOL = {}


def _get_stream(device):
    if not isinstance(device, torch.device):
        device = torch.device(device)
    if device.type != "cuda":
        return None
    idx = device.index if device.index is not None else torch.cuda.current_device()
    pool = _STREAM_POOL.get(idx)
    if pool is None:
        torch.cuda.set_device(idx)
        pool = [torch.cuda.Stream(device=idx)]
        _STREAM_POOL[idx] = pool
    return pool[0]


def qknorm(q: torch.Tensor, k: torch.Tensor, norm_weight: torch.Tensor):
    q_o = torch.empty_like(q)
    k_o = torch.empty_like(k)

    same_device = (q.device == k.device)
    cuda_q = q.is_cuda
    cuda_k = k.is_cuda

    if cuda_q and cuda_k and same_device:
        cur = torch.cuda.current_stream(q.device)
        alt = _get_stream(q.device)

        work_q = q.numel()
        work_k = k.numel()

        if work_q >= work_k:
            alt.wait_stream(cur)
            with torch.cuda.stream(alt):
                flashinfer.norm.rmsnorm(k, norm_weight, out=k_o)
            flashinfer.norm.rmsnorm(q, norm_weight, out=q_o)
            cur.wait_stream(alt)
        else:
            alt.wait_stream(cur)
            with torch.cuda.stream(alt):
                flashinfer.norm.rmsnorm(q, norm_weight, out=q_o)
            flashinfer.norm.rmsnorm(k, norm_weight, out=k_o)
            cur.wait_stream(alt)
    else:
        if cuda_q:
            cur_q = torch.cuda.current_stream(q.device)
            flashinfer.norm.rmsnorm(q, norm_weight, out=q_o)
        else:
            flashinfer.norm.rmsnorm(q, norm_weight, out=q_o)

        if cuda_k:
            cur_k = torch.cuda.current_stream(k.device)
            flashinfer.norm.rmsnorm(k, norm_weight, out=k_o)
        else:
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


def customized_qknorm(q: torch.Tensor, k: torch.Tensor, norm_weight: torch.Tensor):
    q_o = torch.empty(q.shape, device=q.device, dtype=q.dtype, layout=q.layout)
    k_o = torch.empty(k.shape, device=k.device, dtype=k.dtype, layout=k.layout)
    flashinfer.norm.rmsnorm(q, norm_weight, out=q_o)
    flashinfer.norm.rmsnorm(k, norm_weight, out=k_o)
    return q_o, k_o
"""
        return {"code": code}
