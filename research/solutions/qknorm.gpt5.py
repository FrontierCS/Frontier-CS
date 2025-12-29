import torch
import flashinfer

class Solution:
    def solve(self, spec_path: str = None) -> dict:
        code = '''import torch
import flashinfer

_qknorm_streams = {}

def _get_streams(dev):
    if not torch.cuda.is_available():
        return None
    if dev.type != "cuda":
        return None
    idx = dev.index
    if idx is None:
        idx = torch.cuda.current_device()
    streams = _qknorm_streams.get(idx, None)
    if streams is None:
        with torch.cuda.device(idx):
            s1 = torch.cuda.Stream(device=idx)
            s2 = torch.cuda.Stream(device=idx)
        _qknorm_streams[idx] = (s1, s2)
        streams = (s1, s2)
    return streams

def _prepare_weight_for(x: torch.Tensor, norm_weight: torch.Tensor):
    # Ensure weight on same device and same dtype as x
    if norm_weight.device != x.device or norm_weight.dtype != x.dtype:
        return norm_weight.to(device=x.device, dtype=x.dtype, non_blocking=True)
    return norm_weight

def qknorm(q: torch.Tensor, k: torch.Tensor, norm_weight: torch.Tensor):
    """
    Apply RMSNorm to query and key tensors with attention to non-contiguous inputs.

    Returns:
        Tuple of (q_normalized, k_normalized)
    """
    if q.dim() == 0 or k.dim() == 0:
        raise ValueError("q and k must be at least 1D tensors")
    if q.shape[-1] != k.shape[-1]:
        raise ValueError("q and k must have the same last dimension size")
    if norm_weight.numel() != q.shape[-1]:
        raise ValueError("norm_weight size must match the last dimension of q/k")

    # Allocate outputs; avoid triggering layout changes/copies on inputs
    q_o = torch.empty(q.shape, device=q.device, dtype=q.dtype)
    k_o = torch.empty(k.shape, device=k.device, dtype=k.dtype)

    # Prepare weights per tensor
    w_q = _prepare_weight_for(q, norm_weight)
    w_k = _prepare_weight_for(k, norm_weight)

    # Fast path: same CUDA device, try to overlap using two persistent streams
    same_dev_cuda = (q.is_cuda and k.is_cuda and q.device == k.device)
    if same_dev_cuda:
        streams = _get_streams(q.device)
        if streams is not None:
            s1, s2 = streams
            # Heuristic: overlap only when tensors do not share the same underlying storage
            # (to avoid unnecessary L2 contention on interleaved QKV views)
            share_storage = (q.storage().data_ptr() == k.storage().data_ptr())
            # Also avoid overlapping for very large tensors to reduce memory BW contention
            total_elems = q.numel() + k.numel()
            dtype_size = torch.finfo(q.dtype).bits // 8 if q.dtype.is_floating_point else q.element_size()
            # Threshold tuned for tiny operator launch overhead hiding
            overlap_ok = (not share_storage) and (total_elems * dtype_size <= 16 * (1 << 20))  # ~16MB
            if overlap_ok:
                curr = torch.cuda.current_stream(q.device)
                with torch.cuda.stream(s1):
                    flashinfer.norm.rmsnorm(q, w_q, out=q_o)
                with torch.cuda.stream(s2):
                    flashinfer.norm.rmsnorm(k, w_k, out=k_o)
                # Ensure default stream will wait for completion before next ops
                curr.wait_stream(s1)
                curr.wait_stream(s2)
                return q_o, k_o

    # Fallback: sequential launches (handles different devices or large tensors)
    flashinfer.norm.rmsnorm(q, w_q, out=q_o)
    flashinfer.norm.rmsnorm(k, w_k, out=k_o)
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