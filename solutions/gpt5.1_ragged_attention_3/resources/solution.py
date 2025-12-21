import math
import textwrap
import torch
import triton
import triton.language as tl


@triton.jit
def _ragged_attn_kernel(
    Q, K, V, ROW_LENS, O,
    M, N, D, Dv,
    stride_qm, stride_qd,
    stride_kn, stride_kd,
    stride_vn, stride_vd,
    stride_om, stride_od,
    scale,
    BLOCK_M: tl.constexpr,
    BLOCK_N: tl.constexpr,
    BLOCK_DMODEL: tl.constexpr,
    BLOCK_DV: tl.constexpr,
):
    pid_m = tl.program_id(0)
    offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
    mask_m = offs_m < M

    offs_d = tl.arange(0, BLOCK_DMODEL)
    mask_d = offs_d < D

    # Load Q block [BLOCK_M, BLOCK_DMODEL]
    q_ptrs = Q + offs_m[:, None] * stride_qm + offs_d[None, :] * stride_qd
    q = tl.load(q_ptrs, mask=mask_m[:, None] & mask_d[None, :], other=0.0)
    q = q.to(tl.float32)

    # Load row lengths for each row in the block
    row_lens = tl.load(ROW_LENS + offs_m, mask=mask_m, other=0)

    offs_dv = tl.arange(0, BLOCK_DV)
    mask_dv = offs_dv < Dv

    # Initialize streaming softmax statistics
    m_i = tl.full([BLOCK_M], -float("inf"), dtype=tl.float32)
    l_i = tl.zeros([BLOCK_M], dtype=tl.float32)
    o = tl.zeros([BLOCK_M, BLOCK_DV], dtype=tl.float32)

    for start_n in range(0, N, BLOCK_N):
        offs_n = start_n + tl.arange(0, BLOCK_N)
        mask_n = offs_n < N

        # Load K and V tiles
        k_ptrs = K + offs_n[:, None] * stride_kn + offs_d[None, :] * stride_kd
        v_ptrs = V + offs_n[:, None] * stride_vn + offs_dv[None, :] * stride_vd

        k = tl.load(k_ptrs, mask=mask_n[:, None] & mask_d[None, :], other=0.0)
        v = tl.load(v_ptrs, mask=mask_n[:, None] & mask_dv[None, :], other=0.0)

        k = k.to(tl.float32)
        v = v.to(tl.float32)

        # Compute attention logits: [BLOCK_M, BLOCK_N]
        logits = tl.dot(q, tl.trans(k)) * scale

        # Ragged masking based on row_lens
        valid = (offs_n[None, :] < row_lens[:, None]) & mask_m[:, None] & mask_n[None, :]
        logits = tl.where(valid, logits, float("-inf"))

        # Streaming softmax update
        current_max = tl.max(logits, axis=1)
        new_m_i = tl.maximum(m_i, current_max)

        exp_logits = tl.exp(logits - new_m_i[:, None])
        l_i = tl.exp(m_i - new_m_i) * l_i + tl.sum(exp_logits, axis=1)

        o = o * tl.exp(m_i - new_m_i)[:, None] + tl.dot(exp_logits, v)
        m_i = new_m_i

    # Normalize and store result
    o = o / l_i[:, None]
    out = o.to(tl.float16)

    out_ptrs = O + offs_m[:, None] * stride_om + offs_dv[None, :] * stride_od
    tl.store(out_ptrs, out, mask=mask_m[:, None] & mask_dv[None, :])


def ragged_attn(Q: torch.Tensor, K: torch.Tensor, V: torch.Tensor, row_lens: torch.Tensor) -> torch.Tensor:
    """
    Ragged attention computation.

    Args:
        Q: (M, D) float16
        K: (N, D) float16
        V: (N, Dv) float16
        row_lens: (M,) int32/int64

    Returns:
        (M, Dv) float16
    """
    assert Q.is_cuda and K.is_cuda and V.is_cuda, "Q, K, V must be CUDA tensors"
    assert Q.dtype == torch.float16 and K.dtype == torch.float16 and V.dtype == torch.float16, "Q, K, V must be float16"
    assert Q.dim() == 2 and K.dim() == 2 and V.dim() == 2, "Q, K, V must be 2D"

    M, D = Q.shape
    N, Dk = K.shape
    Nv, Dv = V.shape
    assert Dk == D, "K dimension mismatch"
    assert Nv == N, "V dimension mismatch"

    if row_lens.device != Q.device:
        row_lens = row_lens.to(Q.device)
    if row_lens.dtype != torch.int32:
        row_lens = row_lens.to(torch.int32)

    # Clamp row lengths to [0, N]
    row_lens = torch.clamp(row_lens, 0, N).contiguous()

    O = torch.empty((M, Dv), device=Q.device, dtype=torch.float16)

    scale = 1.0 / math.sqrt(D)

    # Kernel launch configuration
    BLOCK_M = 32
    BLOCK_N = 64
    BLOCK_DMODEL = 64
    BLOCK_DV = 64

    grid = (triton.cdiv(M, BLOCK_M),)

    _ragged_attn_kernel[grid](
        Q, K, V, row_lens, O,
        M, N, D, Dv,
        Q.stride(0), Q.stride(1),
        K.stride(0), K.stride(1),
        V.stride(0), V.stride(1),
        O.stride(0), O.stride(1),
        scale,
        BLOCK_M=BLOCK_M,
        BLOCK_N=BLOCK_N,
        BLOCK_DMODEL=BLOCK_DMODEL,
        BLOCK_DV=BLOCK_DV,
        num_warps=4,
        num_stages=2,
    )

    return O


kernel_code = textwrap.dedent('''
import math
import torch
import triton
import triton.language as tl


@triton.jit
def _ragged_attn_kernel(
    Q, K, V, ROW_LENS, O,
    M, N, D, Dv,
    stride_qm, stride_qd,
    stride_kn, stride_kd,
    stride_vn, stride_vd,
    stride_om, stride_od,
    scale,
    BLOCK_M: tl.constexpr,
    BLOCK_N: tl.constexpr,
    BLOCK_DMODEL: tl.constexpr,
    BLOCK_DV: tl.constexpr,
):
    pid_m = tl.program_id(0)
    offs_m = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
    mask_m = offs_m < M

    offs_d = tl.arange(0, BLOCK_DMODEL)
    mask_d = offs_d < D

    # Load Q block [BLOCK_M, BLOCK_DMODEL]
    q_ptrs = Q + offs_m[:, None] * stride_qm + offs_d[None, :] * stride_qd
    q = tl.load(q_ptrs, mask=mask_m[:, None] & mask_d[None, :], other=0.0)
    q = q.to(tl.float32)

    # Load row lengths for each row in the block
    row_lens = tl.load(ROW_LENS + offs_m, mask=mask_m, other=0)

    offs_dv = tl.arange(0, BLOCK_DV)
    mask_dv = offs_dv < Dv

    # Initialize streaming softmax statistics
    m_i = tl.full([BLOCK_M], -float("inf"), dtype=tl.float32)
    l_i = tl.zeros([BLOCK_M], dtype=tl.float32)
    o = tl.zeros([BLOCK_M, BLOCK_DV], dtype=tl.float32)

    for start_n in range(0, N, BLOCK_N):
        offs_n = start_n + tl.arange(0, BLOCK_N)
        mask_n = offs_n < N

        # Load K and V tiles
        k_ptrs = K + offs_n[:, None] * stride_kn + offs_d[None, :] * stride_kd
        v_ptrs = V + offs_n[:, None] * stride_vn + offs_dv[None, :] * stride_vd

        k = tl.load(k_ptrs, mask=mask_n[:, None] & mask_d[None, :], other=0.0)
        v = tl.load(v_ptrs, mask=mask_n[:, None] & mask_dv[None, :], other=0.0)

        k = k.to(tl.float32)
        v = v.to(tl.float32)

        # Compute attention logits: [BLOCK_M, BLOCK_N]
        logits = tl.dot(q, tl.trans(k)) * scale

        # Ragged masking based on row_lens
        valid = (offs_n[None, :] < row_lens[:, None]) & mask_m[:, None] & mask_n[None, :]
        logits = tl.where(valid, logits, float("-inf"))

        # Streaming softmax update
        current_max = tl.max(logits, axis=1)
        new_m_i = tl.maximum(m_i, current_max)

        exp_logits = tl.exp(logits - new_m_i[:, None])
        l_i = tl.exp(m_i - new_m_i) * l_i + tl.sum(exp_logits, axis=1)

        o = o * tl.exp(m_i - new_m_i)[:, None] + tl.dot(exp_logits, v)
        m_i = new_m_i

    # Normalize and store result
    o = o / l_i[:, None]
    out = o.to(tl.float16)

    out_ptrs = O + offs_m[:, None] * stride_om + offs_dv[None, :] * stride_od
    tl.store(out_ptrs, out, mask=mask_m[:, None] & mask_dv[None, :])


def ragged_attn(Q: torch.Tensor, K: torch.Tensor, V: torch.Tensor, row_lens: torch.Tensor) -> torch.Tensor:
    """
    Ragged attention computation.

    Args:
        Q: (M, D) float16
        K: (N, D) float16
        V: (N, Dv) float16
        row_lens: (M,) int32/int64

    Returns:
        (M, Dv) float16
    """
    assert Q.is_cuda and K.is_cuda and V.is_cuda, "Q, K, V must be CUDA tensors"
    assert Q.dtype == torch.float16 and K.dtype == torch.float16 and V.dtype == torch.float16, "Q, K, V must be float16"
    assert Q.dim() == 2 and K.dim() == 2 and V.dim() == 2, "Q, K, V must be 2D"

    M, D = Q.shape
    N, Dk = K.shape
    Nv, Dv = V.shape
    assert Dk == D, "K dimension mismatch"
    assert Nv == N, "V dimension mismatch"

    if row_lens.device != Q.device:
        row_lens = row_lens.to(Q.device)
    if row_lens.dtype != torch.int32:
        row_lens = row_lens.to(torch.int32)

    # Clamp row lengths to [0, N]
    row_lens = torch.clamp(row_lens, 0, N).contiguous()

    O = torch.empty((M, Dv), device=Q.device, dtype=torch.float16)

    scale = 1.0 / math.sqrt(D)

    # Kernel launch configuration
    BLOCK_M = 32
    BLOCK_N = 64
    BLOCK_DMODEL = 64
    BLOCK_DV = 64

    grid = (triton.cdiv(M, BLOCK_M),)

    _ragged_attn_kernel[grid](
        Q, K, V, row_lens, O,
        M, N, D, Dv,
        Q.stride(0), Q.stride(1),
        K.stride(0), K.stride(1),
        V.stride(0), V.stride(1),
        O.stride(0), O.stride(1),
        scale,
        BLOCK_M=BLOCK_M,
        BLOCK_N=BLOCK_N,
        BLOCK_DMODEL=BLOCK_DMODEL,
        BLOCK_DV=BLOCK_DV,
        num_warps=4,
        num_stages=2,
    )

    return O
''')


class Solution:
    def solve(self, spec_path: str = None) -> dict:
        return {"code": kernel_code}
