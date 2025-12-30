import torch
try:
    import flashinfer
    _has_flashinfer = True
except Exception:  # pragma: no cover
    flashinfer = None
    _has_flashinfer = False


def default_qknorm(q: torch.Tensor, k: torch.Tensor, norm_weight: torch.Tensor):
    q_2d = q.contiguous().view(-1, q.shape[-1])
    k_2d = k.contiguous().view(-1, k.shape[-1])
    q_o = torch.empty_like(q_2d)
    k_o = torch.empty_like(k_2d)
    if not _has_flashinfer:
        # Fallback RMSNorm implementation if flashinfer is unavailable
        eps = 1e-6
        var_q = q_2d.pow(2).mean(dim=-1, keepdim=True)
        inv_rms_q = torch.rsqrt(var_q + eps)
        q_o = q_2d * inv_rms_q * norm_weight

        var_k = k_2d.pow(2).mean(dim=-1, keepdim=True)
        inv_rms_k = torch.rsqrt(var_k + eps)
        k_o = k_2d * inv_rms_k * norm_weight
    else:
        flashinfer.norm.rmsnorm(q_2d, norm_weight, out=q_o)
        flashinfer.norm.rmsnorm(k_2d, norm_weight, out=k_o)
    return q_o.view(q.shape), k_o.view(k.shape)


def customized_qknorm(q: torch.Tensor, k: torch.Tensor, norm_weight: torch.Tensor):
    q_o = torch.empty(q.shape, device=q.device, dtype=q.dtype)
    k_o = torch.empty(k.shape, device=k.device, dtype=k.dtype)
    if not _has_flashinfer:
        eps = 1e-6
        var_q = q.pow(2).mean(dim=-1, keepdim=True)
        inv_rms_q = torch.rsqrt(var_q + eps)
        q_o.copy_(q * inv_rms_q * norm_weight)

        var_k = k.pow(2).mean(dim=-1, keepdim=True)
        inv_rms_k = torch.rsqrt(var_k + eps)
        k_o.copy_(k * inv_rms_k * norm_weight)
    else:
        flashinfer.norm.rmsnorm(q, norm_weight, out=q_o)
        flashinfer.norm.rmsnorm(k, norm_weight, out=k_o)
    return q_o, k_o


# Cache CUDA streams per device for concurrent Q/K normalization
_qknorm_streams = {}


def _get_qknorm_streams(device: torch.device):
    if device.type != "cuda":
        return None, None
    streams = _qknorm_streams.get(device)
    if streams is None:
        s_q = torch.cuda.Stream(device=device)
        s_k = torch.cuda.Stream(device=device)
        streams = (s_q, s_k)
        _qknorm_streams[device] = streams
    return streams


def qknorm(q: torch.Tensor, k: torch.Tensor, norm_weight: torch.Tensor):
    """
    Apply RMSNorm to query and key tensors with concurrent GPU execution.
    """
    # Fallback to default implementation if flashinfer is unavailable or tensors are not on CUDA
    if (not _has_flashinfer) or (not q.is_cuda) or (not k.is_cuda) or (not norm_weight.is_cuda):
        return customized_qknorm(q, k, norm_weight)

    # Basic consistency checks (cheap)
    if q.device != k.device or q.device != norm_weight.device:
        raise ValueError("q, k, and norm_weight must be on the same CUDA device")
    if q.shape[-1] != norm_weight.shape[0] or k.shape[-1] != norm_weight.shape[0]:
        raise ValueError("Last dimension of q and k must match norm_weight length")

    device = q.device

    # Allocate contiguous outputs (better for downstream kernels)
    q_o = torch.empty(q.shape, device=device, dtype=q.dtype)
    k_o = torch.empty(k.shape, device=device, dtype=k.dtype)

    # Handle degenerate shapes quickly
    if q.numel() == 0 and k.numel() == 0:
        return q_o, k_o

    stream_q, stream_k = _get_qknorm_streams(device)
    if stream_q is None or stream_k is None:
        # Non-CUDA device; should not happen given checks above, but be robust
        return customized_qknorm(q, k, norm_weight)

    current_stream = torch.cuda.current_stream(device)

    # Ensure new streams see prior work on current stream
    stream_q.wait_stream(current_stream)
    stream_k.wait_stream(current_stream)

    # Launch rmsnorm for q and k on separate streams to overlap execution
    if q.numel() != 0:
        with torch.cuda.stream(stream_q):
            flashinfer.norm.rmsnorm(q, norm_weight, out=q_o)
    if k.numel() != 0:
        with torch.cuda.stream(stream_k):
            flashinfer.norm.rmsnorm(k, norm_weight, out=k_o)

    # Ensure current stream waits for both computations before returning
    current_stream.wait_stream(stream_q)
    current_stream.wait_stream(stream_k)

    return q_o, k_o


class Solution:
    def solve(self, spec_path: str = None) -> dict:
        """
        Return this module's source code so the evaluator can import qknorm.
        """
        import inspect
        import sys

        module = sys.modules[__name__]
        src = inspect.getsource(module)
        return {"code": src}