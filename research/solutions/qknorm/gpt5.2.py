import textwrap

KERNEL_CODE = textwrap.dedent(
    r"""
import torch
import flashinfer


def default_qknorm(q: torch.Tensor, k: torch.Tensor, norm_weight: torch.Tensor):
    q_2d = q.contiguous().view(-1, q.shape[-1])
    k_2d = k.contiguous().view(-1, k.shape[-1])
    q_o = torch.empty_like(q_2d)
    k_o = torch.empty_like(k_2d)
    flashinfer.norm.rmsnorm(q_2d, norm_weight, out=q_o)
    flashinfer.norm.rmsnorm(k_2d, norm_weight, out=k_o)
    return q_o.view(q.shape), k_o.view(k.shape)


def _try_make_fused_qk_view(q: torch.Tensor, k: torch.Tensor):
    if q.device != k.device or q.dtype != k.dtype:
        return None
    if q.shape != k.shape:
        return None
    if q.stride() != k.stride():
        return None
    if not q.is_cuda:
        return None

    try:
        if q.untyped_storage().data_ptr() != k.untyped_storage().data_ptr():
            return None
        q_off = int(q.storage_offset())
        k_off = int(k.storage_offset())
        delta = k_off - q_off
        if delta == 0:
            return None

        if delta > 0:
            base = q
            base_off = q_off
            first_stride = delta
            swap = False
        else:
            base = k
            base_off = k_off
            first_stride = -delta
            swap = True

        qk = base.as_strided((2,) + tuple(q.shape), (first_stride,) + tuple(q.stride()), storage_offset=base_off)

        if not swap:
            if int(qk[1].storage_offset()) != k_off:
                return None
        else:
            if int(qk[1].storage_offset()) != q_off:
                return None

        return qk, swap
    except Exception:
        return None


def qknorm(q: torch.Tensor, k: torch.Tensor, norm_weight: torch.Tensor):
    fused = _try_make_fused_qk_view(q, k)
    if fused is not None:
        qk, swap = fused
        out = torch.empty(qk.shape, device=q.device, dtype=q.dtype)
        flashinfer.norm.rmsnorm(qk, norm_weight, out=out)
        if not swap:
            return out[0], out[1]
        else:
            return out[1], out[0]

    q_o = torch.empty(q.shape, device=q.device, dtype=q.dtype)
    k_o = torch.empty(k.shape, device=k.device, dtype=k.dtype)
    flashinfer.norm.rmsnorm(q, norm_weight, out=q_o)
    flashinfer.norm.rmsnorm(k, norm_weight, out=k_o)
    return q_o, k_o
"""
).lstrip()


class Solution:
    def solve(self, spec_path: str = None) -> dict:
        return {"code": KERNEL_CODE}


# Optional: expose qknorm in this module namespace as well (for robustness)
exec_globals = {}
exec(KERNEL_CODE, exec_globals)
default_qknorm = exec_globals["default_qknorm"]
qknorm = exec_globals["qknorm"]