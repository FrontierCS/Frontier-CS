import os
import textwrap

class Solution:
    def solve(self, spec_path: str = None) -> dict:
        code = textwrap.dedent(
            """
            import os
            import torch
            import flashinfer

            _QKNORM_PARALLEL_STREAMS = bool(int(os.environ.get("QKNORM_PARALLEL_STREAMS", "0")))
            _qknorm_streams = {}

            def _get_streams(device):
                dev_idx = torch.device(device).index if isinstance(device, torch.device) else device
                if dev_idx not in _qknorm_streams:
                    s1 = torch.cuda.Stream(device=dev_idx)
                    s2 = torch.cuda.Stream(device=dev_idx)
                    _qknorm_streams[dev_idx] = (s1, s2)
                return _qknorm_streams[dev_idx]

            def _ensure_weight_on(x: torch.Tensor, w: torch.Tensor):
                if w.device != x.device or w.dtype != x.dtype:
                    # non_blocking is safe if pinned or same device, otherwise becomes blocking
                    return w.to(device=x.device, dtype=x.dtype, non_blocking=True)
                return w

            def _rmsnorm_apply(x: torch.Tensor, w: torch.Tensor):
                # Fast path: if input is fully contiguous, flatten for optimal access; otherwise keep original shape
                D = x.shape[-1]
                w = _ensure_weight_on(x, w)

                if x.is_contiguous():
                    x2d = x.view(-1, D)
                    out2d = torch.empty_like(x2d)
                    flashinfer.norm.rmsnorm(x2d, w, out=out2d)
                    return out2d.view(x.shape)
                else:
                    out = torch.empty(x.shape, device=x.device, dtype=x.dtype)
                    flashinfer.norm.rmsnorm(x, w, out=out)
                    return out

            def qknorm(q: torch.Tensor, k: torch.Tensor, norm_weight: torch.Tensor):
                """
                Apply RMSNorm to query and key tensors.

                Args:
                    q: Query tensor of arbitrary shape (will be reshaped to 2D when contiguous)
                    k: Key tensor of arbitrary shape (will be reshaped to 2D when contiguous)
                    norm_weight: Normalization weight tensor of shape (hidden_dim,)

                Returns:
                    Tuple of (q_normalized, k_normalized) tensors
                """
                assert q.shape[-1] == k.shape[-1], "Last dimension (hidden size) must match between q and k"
                assert norm_weight.dim() == 1 and norm_weight.numel() == q.shape[-1], "norm_weight shape must match hidden size"

                # Optionally run q and k normalization in parallel streams to reduce launch-bound overhead
                if _QKNORM_PARALLEL_STREAMS and q.is_cuda and k.is_cuda and q.device == k.device:
                    s1, s2 = _get_streams(q.device)
                    q_out = torch.empty(q.shape, device=q.device, dtype=q.dtype) if not q.is_contiguous() else torch.empty_like(q)
                    k_out = torch.empty(k.shape, device=k.device, dtype=k.dtype) if not k.is_contiguous() else torch.empty_like(k)

                    D = q.shape[-1]
                    wq = _ensure_weight_on(q, norm_weight)
                    wk = _ensure_weight_on(k, norm_weight)

                    if q.is_contiguous():
                        q2d = q.view(-1, D)
                        q_out2d = q_out.view(-1, D)
                        with torch.cuda.stream(s1):
                            flashinfer.norm.rmsnorm(q2d, wq, out=q_out2d)
                    else:
                        with torch.cuda.stream(s1):
                            flashinfer.norm.rmsnorm(q, wq, out=q_out)

                    if k.is_contiguous():
                        k2d = k.view(-1, D)
                        k_out2d = k_out.view(-1, D)
                        with torch.cuda.stream(s2):
                            flashinfer.norm.rmsnorm(k2d, wk, out=k_out2d)
                    else:
                        with torch.cuda.stream(s2):
                            flashinfer.norm.rmsnorm(k, wk, out=k_out)

                    # Ensure default stream waits for both streams before returning
                    torch.cuda.current_stream(device=q.device).wait_stream(s1)
                    torch.cuda.current_stream(device=k.device).wait_stream(s2)
                    return q_out, k_out
                else:
                    q_o = _rmsnorm_apply(q, norm_weight)
                    k_o = _rmsnorm_apply(k, norm_weight)
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