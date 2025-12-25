import torch
import flashinfer

class Solution:
    def solve(self, spec_path: str = None) -> dict:
        code = r'''
import torch
import flashinfer

def _rmsnorm_cpu_like(x: torch.Tensor, w: torch.Tensor, out: torch.Tensor = None, eps: float = 1e-6):
    # Generic RMSNorm using torch ops, works on both CPU and CUDA as a fallback
    orig_dtype = x.dtype
    x_f = x.float()
    ms = x_f.pow(2).mean(dim=-1, keepdim=True)
    inv_rms = (ms + eps).rsqrt()
    y = x_f * inv_rms
    # broadcast weight across leading dims
    w_view = [1] * (x.dim() - 1) + [-1]
    y = (y * w.view(w_view)).to(orig_dtype)
    if out is None:
        return y
    out.copy_(y)
    return out

def _launch_rmsnorm(x: torch.Tensor, w: torch.Tensor, out: torch.Tensor):
    # Prefer 2D view when both are contiguous to improve kernel scheduling/efficiency
    if x.is_contiguous() and out.is_contiguous():
        x2d = x.view(-1, x.shape[-1])
        o2d = out.view(-1, out.shape[-1])
        flashinfer.norm.rmsnorm(x2d, w, out=o2d)
    else:
        flashinfer.norm.rmsnorm(x, w, out=out)

def qknorm(q: torch.Tensor, k: torch.Tensor, norm_weight: torch.Tensor):
    # Handle devices and availability
    use_flashinfer = hasattr(flashinfer, "norm") and hasattr(flashinfer.norm, "rmsnorm")
    same_device = q.device == k.device
    on_cuda = q.is_cuda and k.is_cuda

    if not use_flashinfer:
        # Fallback for environments without flashinfer
        q_o = torch.empty(q.shape, device=q.device, dtype=q.dtype)
        k_o = torch.empty(k.shape, device=k.device, dtype=k.dtype)
        _rmsnorm_cpu_like(q, norm_weight.to(q.device), out=q_o)
        _rmsnorm_cpu_like(k, norm_weight.to(k.device), out=k_o)
        return q_o, k_o

    # Ensure weight is on proper device(s)
    if on_cuda:
        if norm_weight.device != q.device:
            norm_weight_q = norm_weight.to(q.device)
        else:
            norm_weight_q = norm_weight
        if norm_weight.device != k.device:
            norm_weight_k = norm_weight.to(k.device)
        else:
            norm_weight_k = norm_weight
    else:
        norm_weight_q = norm_weight.to(q.device)
        norm_weight_k = norm_weight.to(k.device)

    q_o = torch.empty(q.shape, device=q.device, dtype=q.dtype)
    k_o = torch.empty(k.shape, device=k.device, dtype=k.dtype)

    if on_cuda and same_device:
        # Overlap the two tiny kernels on different streams for better utilization
        s_main = torch.cuda.current_stream(device=q.device)
        s_aux = torch.cuda.Stream(device=q.device)

        # Ensure k's stream observes any prior work on the main stream without waiting for q's rmsnorm
        s_aux.wait_stream(s_main)

        with torch.cuda.stream(s_aux):
            _launch_rmsnorm(k, norm_weight_k, out=k_o)

        # Launch q on the main stream concurrently
        _launch_rmsnorm(q, norm_weight_q, out=q_o)

        # Ensure downstream work on main stream sees k_o completion
        s_main.wait_stream(s_aux)
    else:
        # Different devices or CPU fallback path: just run independently
        _launch_rmsnorm(q, norm_weight_q, out=q_o)
        _launch_rmsnorm(k, norm_weight_k, out=k_o)

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
