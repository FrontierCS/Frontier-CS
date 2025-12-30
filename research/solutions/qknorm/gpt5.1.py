import torch
import flashinfer
import textwrap

_qknorm_streams = {}


def _get_streams(device):
    if not torch.cuda.is_available():
        return None, None
    dev = torch.device(device)
    idx = dev.index if dev.index is not None else torch.cuda.current_device()
    streams = _qknorm_streams.get(idx)
    if streams is None:
        with torch.cuda.device(idx):
            s1 = torch.cuda.Stream()
            s2 = torch.cuda.Stream()
        streams = (s1, s2)
        _qknorm_streams[idx] = streams
    return streams


def qknorm(q: torch.Tensor, k: torch.Tensor, norm_weight: torch.Tensor):
    """
    Apply RMSNorm to query and key tensors.

    Args:
        q: Query tensor of arbitrary shape (will be reshaped to 2D)
        k: Key tensor of arbitrary shape (will be reshaped to 2D)
        norm_weight: Normalization weight tensor of shape (hidden_dim,)

    Returns:
        Tuple of (q_normalized, k_normalized) tensors
    """
    if q.device != k.device or q.device != norm_weight.device:
        raise ValueError("q, k, and norm_weight must be on the same device")

    # CPU / non-CUDA fallback: simple PyTorch RMSNorm (correctness-focused)
    if not q.is_cuda or not torch.cuda.is_available():
        eps = 1e-6
        q_f = q.float()
        k_f = k.float()
        q_var = q_f.pow(2).mean(dim=-1, keepdim=True)
        k_var = k_f.pow(2).mean(dim=-1, keepdim=True)
        inv_rms_q = torch.rsqrt(q_var + eps).to(q.dtype)
        inv_rms_k = torch.rsqrt(k_var + eps).to(k.dtype)

        w = norm_weight.to(q.dtype)
        while w.dim() < q.dim():
            w = w.unsqueeze(0)

        q_o = q * inv_rms_q * w
        k_o = k * inv_rms_k * w
        return q_o, k_o

    q_o = torch.empty_like(q)
    k_o = torch.empty_like(k)

    s1, s2 = _get_streams(q.device)
    if s1 is None or s2 is None:
        # Fallback to sequential execution on default stream
        flashinfer.norm.rmsnorm(q, norm_weight, out=q_o)
        flashinfer.norm.rmsnorm(k, norm_weight, out=k_o)
        return q_o, k_o

    # Launch Q and K normalization concurrently on two CUDA streams
    with torch.cuda.stream(s1):
        flashinfer.norm.rmsnorm(q, norm_weight, out=q_o)
    with torch.cuda.stream(s2):
        flashinfer.norm.rmsnorm(k, norm_weight, out=k_o)

    # Ensure subsequent work on the current (default) stream sees the results
    cur_stream = torch.cuda.current_stream(q.device)
    cur_stream.wait_stream(s1)
    cur_stream.wait_stream(s2)

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
        code = textwrap.dedent(
            """
            import torch
            import flashinfer

            _qknorm_streams = {}


            def _get_streams(device):
                if not torch.cuda.is_available():
                    return None, None
                dev = torch.device(device)
                idx = dev.index if dev.index is not None else torch.cuda.current_device()
                streams = _qknorm_streams.get(idx)
                if streams is None:
                    with torch.cuda.device(idx):
                        s1 = torch.cuda.Stream()
                        s2 = torch.cuda.Stream()
                    streams = (s1, s2)
                    _qknorm_streams[idx] = streams
                return streams


            def qknorm(q: torch.Tensor, k: torch.Tensor, norm_weight: torch.Tensor):
                \"""
                Apply RMSNorm to query and key tensors.
                
                Args:
                    q: Query tensor of arbitrary shape (will be reshaped to 2D)
                    k: Key tensor of arbitrary shape (will be reshaped to 2D)
                    norm_weight: Normalization weight tensor of shape (hidden_dim,)
                
                Returns:
                    Tuple of (q_normalized, k_normalized) tensors
                \"""
                if q.device != k.device or q.device != norm_weight.device:
                    raise ValueError("q, k, and norm_weight must be on the same device")

                # CPU / non-CUDA fallback: simple PyTorch RMSNorm (correctness-focused)
                if not q.is_cuda or not torch.cuda.is_available():
                    eps = 1e-6
                    q_f = q.float()
                    k_f = k.float()
                    q_var = q_f.pow(2).mean(dim=-1, keepdim=True)
                    k_var = k_f.pow(2).mean(dim=-1, keepdim=True)
                    inv_rms_q = torch.rsqrt(q_var + eps).to(q.dtype)
                    inv_rms_k = torch.rsqrt(k_var + eps).to(k.dtype)

                    w = norm_weight.to(q.dtype)
                    while w.dim() < q.dim():
                        w = w.unsqueeze(0)

                    q_o = q * inv_rms_q * w
                    k_o = k * inv_rms_k * w
                    return q_o, k_o

                q_o = torch.empty_like(q)
                k_o = torch.empty_like(k)

                s1, s2 = _get_streams(q.device)
                if s1 is None or s2 is None:
                    # Fallback to sequential execution on default stream
                    flashinfer.norm.rmsnorm(q, norm_weight, out=q_o)
                    flashinfer.norm.rmsnorm(k, norm_weight, out=k_o)
                    return q_o, k_o

                # Launch Q and K normalization concurrently on two CUDA streams
                with torch.cuda.stream(s1):
                    flashinfer.norm.rmsnorm(q, norm_weight, out=q_o)
                with torch.cuda.stream(s2):
                    flashinfer.norm.rmsnorm(k, norm_weight, out=k_o)

                # Ensure subsequent work on the current (default) stream sees the results
                cur_stream = torch.cuda.current_stream(q.device)
                cur_stream.wait_stream(s1)
                cur_stream.wait_stream(s2)

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
            """
        )
        return {"code": code}